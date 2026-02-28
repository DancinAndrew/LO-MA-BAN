"""
ThreatAnalysisService — async deep analysis via Featherless (OpenAI-compatible).
Supports phishing analysis AND content-risk analysis (child counselor persona).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from config import Settings

logger = logging.getLogger(__name__)

# ── Phishing / Security prompt (兒童輔導員) ──

PHISHING_SYSTEM_PROMPT = """\
你是一位關心 18 歲以下兒童網路安全的輔導員，用親切、易懂的方式幫助孩子理解網路風險。

請基於提供的威脅情報平台檢測結果，分析目標網址的風險。用「小朋友聽得懂」的語言解釋，避免太多專業術語。

輸出要求：
1. 使用結構化 JSON 格式
2. 用簡單的話解釋為什麼這個網址有危險
3. 提供具體、實用的建議（適合兒童與家長）
4. 如果證據不足，請明確說明不確定性
5. **釣魚網站專屬**：
   - 根據釣魚網址的樣貌，推測 2～4 個「使用者可能想去的正確/官方網址」。例如：paypa1.com → paypal.com；allegrolokalnie.pl-xxx.cfd → allegrolokalnie.pl。填入 likely_intended_urls 陣列。
   - 再根據推測的網站類型（購物、金融、社群等），推薦 2～4 個「同類型、可替代的合法網站」。例如：若仿冒 allegrolokalnie（購物），可推薦蝦皮、Amazon、PChome 等；若仿冒 PayPal，可推薦其他正規支付平台。填入 alternative_recommendations 陣列。

JSON 欄位：
{
  "risk_level": "critical/high/medium/low/inconclusive",
  "confidence": "high/medium/low",
  "risk_score": 0-100,
  "threat_summary": "一句話總結主要威脅",
  "likely_intended_urls": ["網址1", "網址2", ...],
  "intended_url_reason": "簡短說明為何推斷為這些網址（50字內）",
  "alternative_recommendations": [
    {"name": "蝦皮購物", "url": "https://shopee.tw"},
    {"name": "Amazon", "url": "https://www.amazon.com"}
  ],
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
請額外生成一個「創意選擇題」，幫助小朋友學習辨識危險網址或不良內容。
要求：
1. 題目要有趣、不寫死格式（情境題、找不同、排序題等）
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

# ── Content risk prompt (內容適齡) ──

CONTENT_RISK_SYSTEM_PROMPT = """\
你是兒童網路安全輔導員。分析「不適合兒童的網頁內容」（色情、暴力、血腥等）。

**嚴格規則：每個句子只說一次，禁止重複相同語意。why_unsafe 限 150 字以內。evidence_analysis 每條限 30 字。**

用親切口吻，幫助孩子理解為什麼不適合瀏覽。

輸出 JSON：
{
  "risk_level": "high",
  "confidence": "high/medium/low",
  "risk_score": 70-100,
  "threat_summary": "一句話總結，不超過 30 字",
  "evidence_analysis": ["具體證據，每條不同角度，不超過 30 字"],
  "why_unsafe": "解釋為什麼不適合兒童，限 150 字，不得重複語句",
  "technical_details": {"detected_by": ["內容分析"], "threat_types": ["類型"], "indicators": []},
  "content_risk_type": "色情/暴力/其他",
  "user_warnings": ["簡短警告，每條不同"],
  "recommendations": ["具體建議，每條不同"],
  "uncertainties": [],
  "quiz": {
    "question": "情境題",
    "hint": "提示",
    "type": "single_choice",
    "options": [{"id": "A", "text": "選項A"}, {"id": "B", "text": "選項B"}, {"id": "C", "text": "選項C"}, {"id": "D", "text": "選項D"}],
    "correct_answer": "C",
    "explanations": {"A": "說明", "B": "說明", "C": "說明", "D": "說明"},
    "learning_point": "學習重點",
    "difficulty": "easy"
  }
}"""


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
            f"- {f['source']}: {f.get('threat_type') or '未知威脅'}" for f in critical_flags
        ) or "無重大警告"
        warn_text = "\n".join(
            f"- {w['source']}: {str(w.get('reason', '未知原因'))[:100]}" for w in warnings
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

請基於以上資訊，輸出結構化的 JSON 分析結果。
若判定為釣魚網站，請務必填寫 likely_intended_urls、intended_url_reason 與 alternative_recommendations。"""

    @staticmethod
    def _build_content_risk_user_prompt(
        target_url: str, page_content: str, content_classification: dict[str, Any]
    ) -> str:
        labels = content_classification.get("labels", [])
        primary = content_classification.get("primary_label", "不明")
        explanation = content_classification.get("explanation", "")
        content_preview = (page_content[:2000] + "...") if len(page_content) > 2000 else page_content

        return f"""\
請分析以下網頁的「內容適齡性」：

URL: {target_url}

初步內容分類結果：
- 主要標籤：{primary}
- 標籤列表：{', '.join(labels)}
- 說明：{explanation}

網頁內容摘要：
---
{content_preview}
---

請輸出結構化 JSON，包含 why_unsafe、recommendations、quiz 等，用兒童輔導員的語氣。"""

    @staticmethod
    def _fallback_phishing(security_results: dict[str, Any]) -> dict[str, Any]:
        risk = security_results.get("overall_risk", "inconclusive")
        critical = security_results.get("critical_flags", [])
        return {
            "risk_level": risk,
            "confidence": "low",
            "risk_score": security_results.get("risk_score", 50),
            "threat_summary": "無法進行深度分析，請參考原始檢測結果",
            "likely_intended_urls": [],
            "intended_url_reason": None,
            "alternative_recommendations": [],
            "evidence_analysis": [
                f"• {c['source']}: {c.get('threat_type', '未知')}" for c in critical
            ],
            "why_unsafe": "分析服務暫時無法提供詳細說明。建議小朋友先不要點擊這個連結，可以請爸媽或老師幫忙用其他安全工具再檢查一次喔！",
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

    @staticmethod
    def _fallback_content_risk(content_classification: dict[str, Any]) -> dict[str, Any]:
        primary = content_classification.get("primary_label", "不當內容")
        labels = content_classification.get("labels", [primary])
        explanation = content_classification.get("explanation", "")
        label_text = "、".join(labels[:3]) if labels else primary

        evidence = [
            f"網頁內容被標記為「{primary}」類型",
            f"包含以下分類標籤：{label_text}",
        ]
        if explanation:
            evidence.append(f"分析說明：{explanation[:50]}")

        return {
            "risk_level": "high",
            "confidence": "medium",
            "risk_score": 80,
            "threat_summary": f"此網頁含有{primary}內容，不適合兒童瀏覽",
            "evidence_analysis": evidence,
            "why_unsafe": (
                f"這個網站含有「{label_text}」的內容，是專門給大人看的。"
                "小朋友的身心還在成長，看到這些內容可能會感到不舒服或困惑。"
                "網路上有很多好玩又有趣的東西，我們可以一起找更適合的網站！"
                "如果不小心看到，記得馬上關掉，然後跟爸媽或老師說一聲喔。"
            ),
            "technical_details": {
                "detected_by": ["內容分析"],
                "threat_types": labels[:4],
                "indicators": [],
            },
            "content_risk_type": primary,
            "user_warnings": [
                f"此網站含有{primary}等內容，不適合 18 歲以下瀏覽",
                "瀏覽此類網站可能影響身心健康",
            ],
            "recommendations": [
                "立即關閉此網頁，不要繼續瀏覽",
                "告訴爸媽或老師你看到了什麼",
                "使用兒童安全搜尋引擎找有趣的內容",
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
        result["content_risk_type"] = content_classification.get("primary_label", "不當內容")
        return result

    @staticmethod
    def _is_repetitive(text: str, threshold: float = 0.4) -> bool:
        """Detect degenerate repetitive output from small LLMs."""
        if not text or len(text) < 60:
            return False
        sentences = [s.strip() for s in re.split(r'[。！？\.\!\?]', text) if len(s.strip()) > 8]
        if len(sentences) < 2:
            return False
        unique = set(sentences)
        return (len(unique) / len(sentences)) < threshold

    @staticmethod
    def _clean_field(text: str, max_length: int = 300) -> str:
        """Remove repeated sentences and trim to max_length."""
        if not text:
            return text
        sentences = re.split(r'(?<=[。！？\.\!\?])', text)
        seen: set[str] = set()
        cleaned: list[str] = []
        for s in sentences:
            s = s.strip()
            if not s or s in seen:
                continue
            seen.add(s)
            cleaned.append(s)
        result = "".join(cleaned)
        if len(result) > max_length:
            result = result[:max_length - 3] + "..."
        return result

    def _sanitize_output(
        self, analysis: dict[str, Any], fallback_fn: Any
    ) -> dict[str, Any]:
        """Replace repetitive LLM fields with fallback content."""
        why = analysis.get("why_unsafe", "")
        if self._is_repetitive(why):
            logger.warning("Detected repetitive why_unsafe, using fallback")
            fb = fallback_fn()
            analysis["why_unsafe"] = fb.get("why_unsafe", "")
            analysis["user_warnings"] = fb.get("user_warnings", analysis.get("user_warnings", []))

        summary = analysis.get("threat_summary", "")
        if self._is_repetitive(summary):
            fb = fallback_fn()
            analysis["threat_summary"] = fb.get("threat_summary", summary[:80])

        evidence = analysis.get("evidence_analysis", [])
        if isinstance(evidence, list) and len(evidence) > 1:
            unique_evidence: list[str] = []
            seen: set[str] = set()
            for e in evidence:
                e_clean = str(e).strip()
                if e_clean and e_clean not in seen:
                    seen.add(e_clean)
                    unique_evidence.append(e_clean)
            analysis["evidence_analysis"] = unique_evidence or evidence[:1]

        return analysis

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
                frequency_penalty=1.2,
                presence_penalty=0.6,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            analysis: dict[str, Any] = json.loads(content)
            analysis = self._sanitize_output(analysis, fallback_fn)
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
