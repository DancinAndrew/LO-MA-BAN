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
你是一位關心 18 歲以下兒童的網路安全輔導員。當使用者已經被告知某個連結有風險（可能是釣魚詐騙、色情、暴力等），但仍說出想進去的理由時，你要用溫暖但堅定的方式勸阻並教育。

請基於「第一階段安全報告」與「用戶自述的理由」，輸出結構化 JSON：

{
  "behavior_consequence_warning": "具體說明執意進入的後果（2–4 句，語氣嚴謹但友善）",
  "reason_analysis": {
    "is_reasonable": false,
    "analysis": "分析用戶理由，說明為什麼這種心態仍有風險",
    "empathy_note": "先同理用戶的心情，再解釋風險（例如：我理解你的好奇心，但是...）"
  },
  "general_warnings": [
    "提醒1",
    "提醒2",
    "提醒3"
  ],
  "recommended_actions": [
    "具體建議1（例如：和爸媽討論你看到的東西）",
    "具體建議2（例如：用安全工具查詢）",
    "具體建議3"
  ],
  "encouraging_message": "一句鼓勵的話（讓使用者覺得被理解，而不是被責備）"
}

注意：
- 用小朋友聽得懂的語言
- 先表達理解（同理心），再說明風險
- 不要恐嚇，而是引導
- 根據風險類型調整語氣（釣魚 -> 強調個資安全；色情 -> 強調身心影響；暴力 -> 強調心理健康）
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
        target_url = report.get("report_metadata", {}).get("target_url", "未知網址")
        risk_info = report.get("report_metadata", {}).get("risk", {})
        kid_summary = report.get("kid_friendly_summary", {})
        raw = report.get("raw_analysis", {})

        content_type = raw.get("content_risk_type", "")
        threat_types = raw.get("technical_details", {}).get("threat_types", [])
        risk_source = "content" if (
            content_type or any(t in str(threat_types) for t in ["色情", "暴力", "血腥", "成人"])
        ) else "phishing"

        return f"""\
以下是使用者「明知有風險」仍想點擊的自述理由：

---
{user_input}
---

第一階段安全報告摘要：
• 目標網址：{target_url}
• 風險等級：{risk_info.get('label', '未知')}（分數 {risk_info.get('score', 'N/A')}/100）
• 風險來源：{'釣魚/資安' if risk_source == 'phishing' else f'不適合兒童的內容（{content_type}）'}
• 簡要說明：{kid_summary.get('short_explanation', raw.get('why_unsafe', ''))}
• 威脅類型：{', '.join(threat_types) if threat_types else '未知'}

請輸出結構化 JSON（包含 behavior_consequence_warning、reason_analysis、general_warnings、recommended_actions、encouraging_message）。"""

    @staticmethod
    def _fallback() -> dict[str, Any]:
        return {
            "behavior_consequence_warning": "分析服務暫時不可用，但請注意：進入有風險的網站可能導致個資外洩、裝置中毒等問題。",
            "reason_analysis": {
                "is_reasonable": False,
                "analysis": "無法分析",
                "empathy_note": "我理解你的好奇心，但安全第一喔！",
            },
            "general_warnings": ["不要在不明網站輸入個人資料", "遇到問題請找大人幫忙"],
            "recommended_actions": ["關閉此網站", "詢問家長或老師"],
            "encouraging_message": "保護自己的網路安全，你做得很好！",
        }
