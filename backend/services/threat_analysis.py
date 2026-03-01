"""
ThreatAnalysisService — async deep analysis via Featherless (OpenAI-compatible).
Supports phishing analysis AND content-risk analysis (child counselor persona).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import Settings

logger = logging.getLogger(__name__)

# ── Phishing / Security prompt (child counselor) ──

PHISHING_SYSTEM_PROMPT = """\
You are a friendly internet safety counselor for children under 18. Explain online risks in a warm, easy-to-understand manner that kids can follow.

Based on the threat intelligence platform detection results provided, analyze the risk of the target URL. Use simple, kid-friendly language and avoid excessive technical jargon.

Output requirements:
1. Use structured JSON format
2. Explain in simple terms why this URL is dangerous
3. Provide concrete, practical advice (suitable for children and parents)
4. If evidence is insufficient, clearly state the uncertainties
5. **Phishing-specific**:
   - Based on the phishing URL's appearance, infer 2-4 "correct/official URLs the user likely intended to visit". E.g.: paypa1.com -> paypal.com; allegrolokalnie.pl-xxx.cfd -> allegrolokalnie.pl. Put them in the likely_intended_urls array.
   - Based on the inferred site type (shopping, finance, social media, etc.), recommend 2-4 "legitimate alternatives of the same type". E.g.: if impersonating allegrolokalnie (shopping), recommend Shopee, Amazon, PChome, etc.; if impersonating PayPal, recommend other legitimate payment platforms. Put them in the alternative_recommendations array.

JSON fields:
{
  "risk_level": "critical/high/medium/low/inconclusive",
  "confidence": "high/medium/low",
  "risk_score": 0-100,
  "threat_summary": "one-sentence summary of the main threat",
  "likely_intended_urls": ["url1", "url2", ...],
  "intended_url_reason": "brief explanation of why these URLs were inferred (under 50 words)",
  "alternative_recommendations": [
    {"name": "Shopee", "url": "https://shopee.tw"},
    {"name": "Amazon", "url": "https://www.amazon.com"}
  ],
  "evidence_analysis": ["evidence1", "evidence2", ...],
  "why_unsafe": "detailed explanation of why it is unsafe (200-300 words)",
  "technical_details": {
    "detected_by": ["platform1", "platform2"],
    "threat_types": ["type1", "type2"],
    "indicators": ["indicator1", "indicator2"]
  },
  "user_warnings": ["warning1", "warning2", ...],
  "recommendations": ["recommendation1", "recommendation2", ...],
  "uncertainties": ["uncertainty1", ...]
}

🎮 **Interactive Learning Task (JSON output)**:
Also generate a creative multiple-choice quiz to help kids learn to identify dangerous URLs or harmful content.
Requirements:
1. The question should be fun and varied (scenario-based, spot-the-difference, ordering, etc.)
2. Provide 4 options (A/B/C/D)
3. Mark the correct answer
4. Each option should have a simple explanation of why it is right/wrong (in kid-friendly language)
5. Optional: add a hint for extra fun

Place the quiz in the "quiz" field of the JSON, formatted as:
{
  "quiz": {
    "question": "your creative question",
    "hint": "optional hint",
    "type": "single_choice",
    "options": [
      {"id": "A", "text": "option A text"},
      {"id": "B", "text": "option B text"},
      {"id": "C", "text": "option C text"},
      {"id": "D", "text": "option D text"}
    ],
    "correct_answer": "C",
    "explanations": {
      "A": "why A is wrong",
      "B": "why B is wrong",
      "C": "why C is correct",
      "D": "why D is wrong"
    },
    "learning_point": "what this question teaches the reader",
    "difficulty": "easy"
  }
}
"""

# ── Content risk prompt (age-appropriateness) ──

CONTENT_RISK_SYSTEM_PROMPT = """\
You are a friendly internet safety counselor for children under 18. This time, analyze "web content unsuitable for children" (e.g., pornography, violence, gore), NOT phishing scams.

Use a warm, easy-to-understand tone to help kids understand why certain websites are not appropriate for them and how to protect themselves. Avoid scare tactics; use a positive, educational voice.

Output JSON format (same structure as security analysis):
{
  "risk_level": "high",
  "confidence": "high/medium/low",
  "risk_score": 70-100,
  "threat_summary": "one-sentence summary (e.g., this page contains content unsuitable for children)",
  "evidence_analysis": ["content evidence 1", "content evidence 2", ...],
  "why_unsafe": "detailed explanation of why it is unsuitable for children (200-300 words, in kid-friendly language)",
  "technical_details": {
    "detected_by": ["content analysis"],
    "threat_types": ["pornography", "violence", ...],
    "indicators": []
  },
  "content_risk_type": "pornography/violence/other inappropriate content",
  "user_warnings": ["warning1", "warning2", ...],
  "recommendations": ["recommendation1", "recommendation2", ...],
  "uncertainties": []
}

Also generate a creative multiple-choice quiz (quiz field) to help kids learn "how to identify inappropriate websites" or "what to do when encountering inappropriate content". Use the same format as the security analysis quiz."""


class ThreatAnalysisService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.featherless_base_url,
            api_key=settings.featherless_api_key,
        )
        self.model = settings.featherless_model
        self.temperature = settings.featherless_temperature
        self.max_tokens = settings.featherless_max_tokens
        self.top_p = settings.featherless_top_p

    @staticmethod
    def _build_phishing_user_prompt(
        target_url: str, security_results: dict[str, Any]
    ) -> str:
        critical_flags = security_results.get("critical_flags", [])
        warnings = security_results.get("warnings", [])
        raw_results = security_results.get("raw_results", [])

        evidence_items: list[str] = []
        for r in raw_results:
            if not r.get("found"):
                continue
            src = r["source"]
            if r.get("threat_type"):
                evidence_items.append(f"• [{src}] Threat type: {r['threat_type']}")
            cats = r.get("categories")
            if cats:
                if isinstance(cats, list):
                    evidence_items.append(f"• [{src}] Categories: {', '.join(cats[:3])}")
                elif isinstance(cats, dict):
                    evidence_items.append(f"• [{src}] Categories: {', '.join(list(cats.keys())[:3])}")
            stats = r.get("stats")
            if stats and isinstance(stats, dict):
                mal, sus = stats.get("malicious", 0), stats.get("suspicious", 0)
                if mal or sus:
                    evidence_items.append(f"• [{src}] Malicious:{mal} Suspicious:{sus}")
            tags = r.get("tags")
            if tags:
                tag_list = tags if isinstance(tags, list) else [str(tags)]
                evidence_items.append(f"• [{src}] Tags: {', '.join(tag_list[:3])}")

        crit_text = "\n".join(
            f"- {f['source']}: {f.get('threat_type') or 'unknown threat'}" for f in critical_flags
        ) or "No critical alerts"
        warn_text = "\n".join(
            f"- {w['source']}: {str(w.get('reason', 'unknown reason'))[:100]}" for w in warnings
        ) or "No minor alerts"
        evidence_text = "\n".join(evidence_items) or "• No specific threat indicators detected"

        return f"""\
Analyze the safety of the following URL:

🎯 Target URL: {target_url}

📊 Threat intelligence platform detection results:
- Overall risk assessment: {security_results.get('overall_risk', 'unknown')}
- Confidence level: {security_results.get('confidence', 'unknown')}
- Risk score: {security_results.get('risk_score', 'N/A')}/100
- Sources checked: {security_results.get('checked_sources', 0)}

🚨 Critical alerts ({len(critical_flags)}):
{crit_text}

⚠️ Minor alerts ({len(warnings)}):
{warn_text}

🔍 Detailed evidence:
{evidence_text}

Based on the above information, output a structured JSON analysis result.
If determined to be a phishing site, make sure to fill in likely_intended_urls, intended_url_reason, and alternative_recommendations."""

    @staticmethod
    def _build_content_risk_user_prompt(
        target_url: str, page_content: str, content_classification: dict[str, Any]
    ) -> str:
        labels = content_classification.get("labels", [])
        primary = content_classification.get("primary_label", "unknown")
        explanation = content_classification.get("explanation", "")
        content_preview = (page_content[:2000] + "...") if len(page_content) > 2000 else page_content

        return f"""\
Analyze the age-appropriateness of the following webpage:

URL: {target_url}

Preliminary content classification:
- Primary label: {primary}
- Label list: {', '.join(labels)}
- Explanation: {explanation}

Page content preview:
---
{content_preview}
---

Output structured JSON including why_unsafe, recommendations, quiz, etc., in a child counselor tone."""

    @staticmethod
    def _fallback_phishing(security_results: dict[str, Any]) -> dict[str, Any]:
        risk = security_results.get("overall_risk", "inconclusive")
        critical = security_results.get("critical_flags", [])
        return {
            "risk_level": risk,
            "confidence": "low",
            "risk_score": security_results.get("risk_score", 50),
            "threat_summary": "Deep analysis unavailable — refer to the raw detection results",
            "likely_intended_urls": [],
            "intended_url_reason": None,
            "alternative_recommendations": [],
            "evidence_analysis": [
                f"• {c['source']}: {c.get('threat_type', 'unknown')}" for c in critical
            ],
            "why_unsafe": "The analysis service is temporarily unable to provide a detailed explanation. We recommend not clicking this link for now — ask a parent or teacher to double-check it with another safety tool!",
            "technical_details": {
                "detected_by": [c["source"] for c in critical],
                "threat_types": [c.get("threat_type") for c in critical if c.get("threat_type")],
                "indicators": [],
            },
            "user_warnings": ["Analysis service temporarily unavailable — proceed with caution"],
            "recommendations": [
                "Do not enter any personal information on this site",
                "Use another safety tool to verify",
                "If you already entered sensitive data, change your password immediately",
            ],
            "uncertainties": ["LLM analysis service call failed"],
            "fallback_mode": True,
        }

    @staticmethod
    def _fallback_content_risk(content_classification: dict[str, Any]) -> dict[str, Any]:
        primary = content_classification.get("primary_label", "inappropriate content")
        return {
            "risk_level": "high",
            "confidence": "medium",
            "risk_score": 80,
            "threat_summary": f"This page may contain content unsuitable for children ({primary})",
            "evidence_analysis": [f"Content classification: {primary}"],
            "why_unsafe": f"Based on our analysis, this page may contain {primary} material that is not appropriate for children under 18. We recommend not clicking it — talk to a parent or teacher if you have questions.",
            "technical_details": {
                "detected_by": ["content analysis"],
                "threat_types": content_classification.get("labels", [primary]),
                "indicators": [],
            },
            "content_risk_type": primary,
            "user_warnings": ["This site may contain content unsuitable for children"],
            "recommendations": [
                "Do not click or browse this link",
                "If you accidentally opened it, close it immediately and tell a parent or teacher",
                "Stay alert online — ask for help when you see something strange",
            ],
            "uncertainties": [],
            "fallback_mode": True,
        }

    async def analyze_phishing(
        self, target_url: str, security_results: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info("LLM phishing analysis started for %s", target_url)
        user_prompt = self._build_phishing_user_prompt(target_url, security_results)
        return await self._call_llm(
            system_prompt=PHISHING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback_fn=lambda: self._fallback_phishing(security_results),
        )

    async def analyze_content_risk(
        self,
        target_url: str,
        page_content: str,
        content_classification: dict[str, Any],
    ) -> dict[str, Any]:
        logger.info("LLM content-risk analysis started for %s", target_url)
        user_prompt = self._build_content_risk_user_prompt(
            target_url, page_content, content_classification
        )
        result = await self._call_llm(
            system_prompt=CONTENT_RISK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback_fn=lambda: self._fallback_content_risk(content_classification),
        )
        result["content_risk_type"] = content_classification.get("primary_label", "inappropriate content")
        return result

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_fn: Any,
    ) -> dict[str, Any]:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            analysis: dict[str, Any] = json.loads(content)
            analysis["llm_metadata"] = {
                "model": self.model,
                "usage": {
                    "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                    "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                    "total_tokens": resp.usage.total_tokens if resp.usage else 0,
                },
            }
            logger.info("LLM analysis completed")
            return analysis
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON: %s", exc)
            return fallback_fn()
        except Exception as exc:
            logger.error("LLM API call failed: %s", exc)
            return fallback_fn()
