"""
LLMAnalyzerService — async deep analysis via Featherless (OpenAI-compatible).
Uses the official openai AsyncOpenAI SDK with a custom base_url.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一位專業的網路安全分析專家。
請基於提供的威脅情報平台檢測結果，分析目標網址的風險。

輸出要求：
1. 使用結構化 JSON 格式
2. 解釋為什麼被標記為不安全
3. 提供具體的用戶建議
4. 如果證據不足，請明確說明不確定性

JSON 欄位：
{
  "risk_level": "critical/high/medium/low/inconclusive",
  "confidence": "high/medium/low",
  "risk_score": 0-100,
  "threat_summary": "一句話總結主要威脅",
  "evidence_analysis": ["證據1", "證據2", ...],
  "why_unsafe": "詳細解釋為什麼不安全（200-300字）",
  "technical_details": {
    "detected_by": ["平台1", "平台2"],
    "threat_types": ["類型1", "類型2"],
    "indicators": ["指標1", "指標2"]
  },
  "user_warnings": ["警告1", "警告2", ...],
  "recommendations": ["建議1", "建議2", ...],
  "uncertainties": ["不確定因素1", ...]
}

🎮 **互動教學任務（JSON 輸出）**：
請額外生成一個「創意選擇題」，幫助讀者學習辨識可疑網址。
要求：
1. 題目要有趣、不寫死格式（可以是情境題、找不同、排序題等）
2. 提供 4 個選項（A/B/C/D）
3. 標明正確答案
4. 每個選項都要有「為什麼對/錯」的簡單解釋（小朋友聽得懂的語言）
5. 可選：加一個小提示（hint）增加趣味性

請將題目放在 JSON 的 "quiz" 欄位，格式如下：
{
  "quiz": {
    "question": "你的創意題目",
    "hint": "可選的小提示",
    "type": "single_choice",
    "options": [
      {"id": "A", "text": "選項 A 文字"},
      {"id": "B", "text": "選項 B 文字"},
      {"id": "C", "text": "選項 C 文字"},
      {"id": "D", "text": "選項 D 文字"}
    ],
    "correct_answer": "C",
    "explanations": {
      "A": "為什麼 A 不對的解釋",
      "B": "為什麼 B 不對的解釋",
      "C": "為什麼 C 對的解釋",
      "D": "為什麼 D 不對的解釋"
    },
    "learning_point": "本題想教會讀者什麼",
    "difficulty": "easy"
  }
}
"""


class LLMAnalyzerService:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=Config.FEATHERLESS_BASE_URL,
            api_key=Config.FEATHERLESS_API_KEY,
        )
        self.model = Config.FEATHERLESS_MODEL
        self.temperature = Config.FEATHERLESS_TEMPERATURE
        self.max_tokens = Config.FEATHERLESS_MAX_TOKENS

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_prompt(
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
                evidence_items.append(f"• [{src}] 威脅類型: {r['threat_type']}")
            cats = r.get("categories")
            if cats:
                if isinstance(cats, list):
                    evidence_items.append(f"• [{src}] 分類: {', '.join(cats[:3])}")
                elif isinstance(cats, dict):
                    evidence_items.append(f"• [{src}] 分類: {', '.join(list(cats.keys())[:3])}")
            stats = r.get("stats")
            if stats and isinstance(stats, dict):
                mal, sus = stats.get("malicious", 0), stats.get("suspicious", 0)
                if mal or sus:
                    evidence_items.append(f"• [{src}] 惡意:{mal} 可疑:{sus}")
            tags = r.get("tags")
            if tags:
                tag_list = tags if isinstance(tags, list) else [str(tags)]
                evidence_items.append(f"• [{src}] 標籤: {', '.join(tag_list[:3])}")

        crit_text = "\n".join(
            f"- {f['source']}: {f.get('threat_type') or '未知威脅'}"
            for f in critical_flags
        ) or "無重大警告"
        warn_text = "\n".join(
            f"- {w['source']}: {str(w.get('reason', '未知原因'))[:100]}"
            for w in warnings
        ) or "無次要警告"
        evidence_text = "\n".join(evidence_items) or "• 未偵測到具體威脅指標"

        return f"""\
請分析以下網址的安全性：

🎯 目標網址: {target_url}

📊 威脅情報平台檢測結果:
- 整體風險評估: {security_results.get('overall_risk', 'unknown')}
- 信心程度: {security_results.get('confidence', 'unknown')}
- 風險分數: {security_results.get('risk_score', 'N/A')}/100
- 已檢查來源數: {security_results.get('checked_sources', 0)}

🚨 關鍵警告 ({len(critical_flags)} 項):
{crit_text}

⚠️ 次要警告 ({len(warnings)} 項):
{warn_text}

🔍 詳細證據:
{evidence_text}

請基於以上資訊，輸出結構化的 JSON 分析結果。"""

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback(security_results: dict[str, Any]) -> dict[str, Any]:
        risk = security_results.get("overall_risk", "inconclusive")
        critical = security_results.get("critical_flags", [])
        return {
            "risk_level": risk,
            "confidence": "low",
            "risk_score": security_results.get("risk_score", 50),
            "threat_summary": "無法進行深度分析，請參考原始檢測結果",
            "evidence_analysis": [
                f"• {c['source']}: {c.get('threat_type', '未知')}" for c in critical
            ],
            "why_unsafe": "由於 API 呼叫異常，無法提供詳細分析。建議直接參考 VirusTotal、URLhaus 等平台的原始檢測結果。",
            "technical_details": {
                "detected_by": [c["source"] for c in critical],
                "threat_types": [c.get("threat_type") for c in critical if c.get("threat_type")],
                "indicators": [],
            },
            "user_warnings": ["分析服務暫時不可用，請謹慎訪問此網址"],
            "recommendations": [
                "避免在此網站輸入任何個人資訊",
                "使用其他安全工具進行二次驗證",
                "如已輸入敏感資料，立即更改密碼",
            ],
            "uncertainties": ["LLM 分析服務呼叫失敗"],
            "fallback_mode": True,
        }

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------

    async def analyze(
        self, target_url: str, security_results: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info("LLM analysis started for %s", target_url)

        user_prompt = self._build_user_prompt(target_url, security_results)

        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.9,
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
            return self._fallback(security_results)
        except Exception as exc:
            logger.error("LLM API call failed: %s", exc)
            return self._fallback(security_results)
