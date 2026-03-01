"""
PersuasionService — async analysis for users who insist on visiting a harmful site.
Combines user's stated reason with first-stage report for persuasion + education.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import Settings

logger = logging.getLogger(__name__)

PERSUASION_SYSTEM_PROMPT = """\
You are a friendly internet safety counselor for children under 18. When a user has already been warned that a link is risky (possibly phishing, pornography, violence, etc.) but still gives a reason for wanting to visit, you should discourage and educate them in a warm yet firm manner.

Based on the "first-stage safety report" and the "user's stated reason", output structured JSON:

{
  "behavior_consequence_warning": "specifically describe the consequences of insisting on visiting (2-4 sentences, serious but friendly tone)",
  "reason_analysis": {
    "is_reasonable": false,
    "analysis": "analyze the user's reason and explain why this mindset is still risky",
    "empathy_note": "first empathize with the user's feelings, then explain the risk (e.g., I understand your curiosity, but...)"
  },
  "general_warnings": [
    "reminder 1",
    "reminder 2",
    "reminder 3"
  ],
  "recommended_actions": [
    "specific suggestion 1 (e.g., discuss what you saw with your parents)",
    "specific suggestion 2 (e.g., use a safety tool to check)",
    "specific suggestion 3"
  ],
  "encouraging_message": "one encouraging sentence (make the user feel understood, not scolded)"
}

Guidelines:
- Use simple, kid-friendly language
- Show empathy first, then explain the risk
- Don't intimidate — guide instead
- Adjust tone based on risk type (phishing -> emphasize personal data safety; pornography -> emphasize well-being; violence -> emphasize mental health)
"""


class PersuasionService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.featherless_base_url,
            api_key=settings.featherless_api_key,
        )
        self.model = settings.featherless_model
        self.temperature = settings.persuasion_temperature
        self.max_tokens = settings.persuasion_max_tokens

    async def analyze(
        self, user_input: str, first_stage_report: dict[str, Any]
    ) -> dict[str, Any]:
        user_prompt = self._build_user_prompt(user_input, first_stage_report)

        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PERSUASION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            result: dict[str, Any] = json.loads(content)
        except Exception as exc:
            logger.error("Persuasion LLM call failed: %s", exc)
            result = self._fallback()

        risk_meta = first_stage_report.get("report_metadata", {}).get("risk", {})
        raw = first_stage_report.get("raw_analysis", {})
        content_type = raw.get("content_risk_type", "")
        risk_source = "content" if content_type else "phishing"

        return {
            "user_input": user_input,
            "first_stage_report_summary": {
                "target_url": first_stage_report.get("report_metadata", {}).get("target_url"),
                "risk_level": risk_meta.get("level"),
                "risk_label": risk_meta.get("label"),
                "risk_score": risk_meta.get("score"),
                "risk_source": risk_source,
            },
            "second_stage_result": result,
        }

    @staticmethod
    def _build_user_prompt(user_input: str, report: dict[str, Any]) -> str:
        target_url = report.get("report_metadata", {}).get("target_url", "unknown URL")
        risk_info = report.get("report_metadata", {}).get("risk", {})
        kid_summary = report.get("kid_friendly_summary", {})
        raw = report.get("raw_analysis", {})

        content_type = raw.get("content_risk_type", "")
        threat_types = raw.get("technical_details", {}).get("threat_types", [])
        risk_source = "content" if (
            content_type or any(t in str(threat_types) for t in ["pornography", "violence", "gore", "adult"])
        ) else "phishing"

        return f"""\
The following is the user's stated reason for wanting to click despite knowing the risk:

---
{user_input}
---

First-stage safety report summary:
• Target URL: {target_url}
• Risk level: {risk_info.get('label', 'unknown')} (score {risk_info.get('score', 'N/A')}/100)
• Risk source: {'phishing / security threat' if risk_source == 'phishing' else f'content unsuitable for children ({content_type})'}
• Brief explanation: {kid_summary.get('short_explanation', raw.get('why_unsafe', ''))}
• Threat types: {', '.join(threat_types) if threat_types else 'unknown'}

Output structured JSON (including behavior_consequence_warning, reason_analysis, general_warnings, recommended_actions, encouraging_message)."""

    @staticmethod
    def _fallback() -> dict[str, Any]:
        return {
            "behavior_consequence_warning": "The analysis service is temporarily unavailable, but please note: visiting risky websites could lead to personal data leaks, device infections, and other problems.",
            "reason_analysis": {
                "is_reasonable": False,
                "analysis": "Unable to analyze",
                "empathy_note": "I understand your curiosity, but safety comes first!",
            },
            "general_warnings": ["Don't enter personal info on unknown sites", "Ask an adult for help if something feels off"],
            "recommended_actions": ["Close this website", "Talk to a parent or teacher"],
            "encouraging_message": "Protecting your online safety is awesome — keep it up!",
        }
