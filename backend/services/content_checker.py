"""
ContentCheckerService — async Exa AI content fetching + Featherless safety classification.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from openai import AsyncOpenAI

from config import Settings, UNSUITABLE_LABELS

logger = logging.getLogger(__name__)


def is_unsuitable_for_children(classification: dict[str, Any]) -> bool:
    labels = classification.get("labels", []) or []
    primary = (classification.get("primary_label") or "").lower()
    for lbl in [*labels, primary]:
        lbl_lower = str(lbl).lower()
        for kw in UNSUITABLE_LABELS:
            if kw in lbl_lower:
                return True
    return False


class ContentCheckerService:
    """Fetch web content via Exa, classify suitability via Featherless."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._openai = AsyncOpenAI(
            base_url=settings.featherless_base_url,
            api_key=settings.featherless_api_key,
        )

    # ── Exa content fetch ──

    async def fetch_content(self, target_url: str) -> tuple[str | None, str | None]:
        """Fetch page content via Exa /contents, with cache + search fallback."""
        if not self._s.exa_api_key:
            return None, "EXA_API_KEY not configured"

        content, err, tag = await self._exa_contents(target_url)
        if content:
            return content, None

        if tag == "CRAWL_LIVECRAWL_TIMEOUT":
            content, err2, _ = await self._exa_contents(target_url, max_age_hours=-1)
            if content:
                return content, None

        if tag in ("CRAWL_LIVECRAWL_TIMEOUT", "CRAWL_NOT_FOUND"):
            content, search_err = await self._exa_search(target_url)
            if content:
                return content, None
            return None, search_err or err

        return None, err or "Exa crawl failed"

    async def _exa_contents(
        self,
        target_url: str,
        max_age_hours: int | None = None,
        livecrawl_timeout_ms: int | None = None,
    ) -> tuple[str | None, str | None, str | None]:
        if max_age_hours is None:
            max_age_hours = self._s.exa_max_age_hours
        if livecrawl_timeout_ms is None:
            livecrawl_timeout_ms = self._s.exa_livecrawl_timeout_ms

        headers = {"x-api-key": self._s.exa_api_key, "Content-Type": "application/json"}
        payload: dict[str, Any] = {"urls": [target_url], "text": True, "highlights": True}
        if max_age_hours is not None:
            payload["maxAgeHours"] = max_age_hours
        if livecrawl_timeout_ms is not None:
            payload["livecrawlTimeout"] = livecrawl_timeout_ms

        async with httpx.AsyncClient(timeout=self._s.exa_timeout) as client:
            resp = await client.post(
                f"{self._s.exa_base_url}/contents", headers=headers, json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if results:
            return self._merge_results(results), None, None

        for s in data.get("statuses", []):
            if s.get("status") == "error":
                tag = s.get("error", {}).get("tag", "unknown")
                return None, f"Exa crawl failed: {tag}", tag
        return None, "Exa returned no content", None

    async def _exa_search(
        self, target_url: str, num_results: int | None = None,
    ) -> tuple[str | None, str | None]:
        if num_results is None:
            num_results = self._s.exa_search_num_results

        headers = {"x-api-key": self._s.exa_api_key, "Content-Type": "application/json"}
        payload = {
            "query": target_url,
            "type": "auto",
            "numResults": num_results,
            "contents": {"text": True, "summary": True},
        }
        try:
            async with httpx.AsyncClient(timeout=self._s.exa_timeout) as client:
                resp = await client.post(
                    f"{self._s.exa_base_url}/search", headers=headers, json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results", [])
            if not results:
                return None, "Exa search returned no results"
            parts: list[str] = []
            for r in results:
                if r.get("text"):
                    parts.append(r["text"])
                if r.get("summary"):
                    parts.append(f"[Summary] {r['summary']}")
            return "\n\n".join(parts).strip() or None, None
        except Exception as exc:
            return None, f"Exa search request failed: {exc}"

    @staticmethod
    def _merge_results(results: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for r in results:
            if r.get("text"):
                parts.append(r["text"])
            if r.get("highlights"):
                for h in (r["highlights"] if isinstance(r["highlights"], list) else [r["highlights"]]):
                    if isinstance(h, str):
                        parts.append(h)
                    elif isinstance(h, dict):
                        parts.append(h.get("text", h.get("snippet", str(h))))
        return "\n\n".join(parts).strip()

    # ── Featherless content classification ──

    async def classify_safety(
        self, target_url: str, page_content: str
    ) -> dict[str, Any]:
        """Classify whether the page is suitable for children (<18)."""
        max_chars = self._s.content_max_chars
        truncated = page_content[:max_chars] + "\n\n[... content truncated ...]" if len(page_content) > max_chars else page_content

        system_prompt = """You are a child internet safety expert. Based on the provided URL and page content, determine whether this webpage is **suitable for children under 18**.

Focus on: pornography, adult content, extreme violence, gore, horror, and other inappropriate material.

Output structured JSON:
{
  "labels": ["label1", "label2"],
  "primary_label": "main label",
  "confidence": "high/medium/low",
  "explanation": "brief explanation (under 50 words)",
  "is_unsuitable_for_children": true or false
}

If the content involves pornography, adult material, violence, gore, etc., is_unsuitable_for_children MUST be true."""

        user_content = f"Analyze whether the following webpage is suitable for children:\n\nURL: {target_url}\n\nPage content:\n---\n{truncated}\n---\n\nOutput JSON."

        try:
            resp = await self._openai.chat.completions.create(
                model=self._s.featherless_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=self._s.content_classify_temperature,
                max_tokens=self._s.content_classify_max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            classification: dict[str, Any] = json.loads(content)
            classification["is_unsuitable_for_children"] = classification.get(
                "is_unsuitable_for_children", is_unsuitable_for_children(classification)
            )
            return classification
        except Exception as exc:
            logger.error("Content classification failed: %s", exc)
            return {"labels": [], "primary_label": "unknown", "is_unsuitable_for_children": False, "error": str(exc)}
