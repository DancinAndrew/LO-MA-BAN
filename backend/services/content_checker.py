"""
ContentCheckerService — async Exa AI content fetching + Featherless safety classification.
Replaces the old sync requests-based content_risk_checker.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from openai import AsyncOpenAI

from config import Config

logger = logging.getLogger(__name__)

UNSUITABLE_LABELS = frozenset([
    "色情", "成人", "暴力", "血腥", "gore", "porn", "nsfw", "explicit",
    "裸露", "不雅", "極端暴力", "恐怖",
])


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

    def __init__(self) -> None:
        self._openai = AsyncOpenAI(
            base_url=Config.FEATHERLESS_BASE_URL,
            api_key=Config.FEATHERLESS_API_KEY,
        )

    # ── Exa content fetch ──

    async def fetch_content(self, target_url: str) -> tuple[str | None, str | None]:
        """Fetch page content via Exa /contents, with cache + search fallback."""
        if not Config.EXA_API_KEY:
            return None, "EXA_API_KEY 未設定"

        content, err, tag = await self._exa_contents(target_url, max_age_hours=24)
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

        return None, err or "Exa 爬取失敗"

    async def _exa_contents(
        self,
        target_url: str,
        max_age_hours: int = 24,
        livecrawl_timeout_ms: int | None = 25000,
    ) -> tuple[str | None, str | None, str | None]:
        headers = {"x-api-key": Config.EXA_API_KEY, "Content-Type": "application/json"}
        payload: dict[str, Any] = {"urls": [target_url], "text": True, "highlights": True}
        if max_age_hours is not None:
            payload["maxAgeHours"] = max_age_hours
        if livecrawl_timeout_ms is not None:
            payload["livecrawlTimeout"] = livecrawl_timeout_ms

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("https://api.exa.ai/contents", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if results:
            return self._merge_results(results), None, None

        for s in data.get("statuses", []):
            if s.get("status") == "error":
                tag = s.get("error", {}).get("tag", "unknown")
                return None, f"Exa 爬取失敗: {tag}", tag
        return None, "Exa 未回傳任何內容", None

    async def _exa_search(
        self, target_url: str, num_results: int = 5
    ) -> tuple[str | None, str | None]:
        headers = {"x-api-key": Config.EXA_API_KEY, "Content-Type": "application/json"}
        payload = {
            "query": target_url,
            "type": "auto",
            "numResults": num_results,
            "contents": {"text": True, "summary": True},
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post("https://api.exa.ai/search", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results", [])
            if not results:
                return None, "Exa 搜尋無結果"
            parts: list[str] = []
            for r in results:
                if r.get("text"):
                    parts.append(r["text"])
                if r.get("summary"):
                    parts.append(f"[摘要] {r['summary']}")
            return "\n\n".join(parts).strip() or None, None
        except Exception as exc:
            return None, f"Exa 搜尋請求失敗: {exc}"

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
        max_chars = 8000
        truncated = page_content[:max_chars] + "\n\n[... 內容已截斷 ...]" if len(page_content) > max_chars else page_content

        system_prompt = """你是一位關心兒童網路安全的專家。請根據提供的網頁 URL 與內容，判斷這個網頁**是否適合 18 歲以下兒童**瀏覽。

重點檢查：色情、成人內容、極端暴力、血腥、恐怖等不適當內容。

請輸出結構化 JSON：
{
  "labels": ["標籤1", "標籤2"],
  "primary_label": "主要標籤",
  "confidence": "high/medium/low",
  "explanation": "簡短說明（50字內）",
  "is_unsuitable_for_children": true 或 false
}

若內容涉及色情、成人、暴力、血腥等，is_unsuitable_for_children 必須為 true。"""

        user_content = f"請分析以下網頁是否適合兒童：\n\nURL: {target_url}\n\n網頁內容：\n---\n{truncated}\n---\n\n輸出 JSON。"

        try:
            resp = await self._openai.chat.completions.create(
                model=Config.FEATHERLESS_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=400,
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
            return {"labels": [], "primary_label": "不明", "is_unsuitable_for_children": False, "error": str(exc)}

    async def classify_and_analyze(
        self, target_url: str, page_content: str
    ) -> dict[str, Any]:
        """Single LLM call: classify suitability AND generate analysis."""
        max_chars = self._s.content_max_chars
        truncated = page_content[:max_chars] + "\n..." if len(page_content) > max_chars else page_content

        system_prompt = """\
你是兒童網路安全專家。判斷網頁是否適合 18 歲以下兒童，並提供分析。

**規則：每個句子只說一次，禁止重複。所有文字欄位限 100 字以內。**

輸出 JSON：
{
  "is_unsuitable_for_children": true/false,
  "labels": ["標籤1", "標籤2"],
  "primary_label": "主要標籤",
  "confidence": "high/medium/low",
  "explanation": "50字內說明",
  "risk_level": "high/medium/low",
  "risk_score": 0-100,
  "threat_summary": "一句話總結(30字內)",
  "evidence_analysis": ["證據1(30字內)", "證據2"],
  "why_unsafe": "為什麼不適合兒童(100字內，不重複)",
  "content_risk_type": "色情/暴力/其他/安全",
  "user_warnings": ["警告1"],
  "recommendations": ["建議1", "建議2"]
}"""

        user_content = f"URL: {target_url}\n\n網頁內容：\n---\n{truncated}\n---"

        try:
            resp = await self._openai.chat.completions.create(
                model=self._s.featherless_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=self._s.content_classify_temperature,
                max_tokens=600,
                frequency_penalty=1.2,
                presence_penalty=0.6,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            result: dict[str, Any] = json.loads(content)
            result["is_unsuitable_for_children"] = result.get(
                "is_unsuitable_for_children", is_unsuitable_for_children(result)
            )
            return result
        except Exception as exc:
            logger.error("Classify-and-analyze failed: %s", exc)
            return {
                "labels": [], "primary_label": "不明",
                "is_unsuitable_for_children": False, "error": str(exc),
            }
