"""
ReportGeneratorService — kid-friendly JSON report builder.
Supports phishing (with intended URLs + alternatives) and content-risk reports.
Pure dict output, no file I/O.
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import Any

from services.quiz_generator import QuizGenerator

logger = logging.getLogger(__name__)


def simplify_text(text: str, max_length: int = 150) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.strip())
    replacements = {
        "釣魚網站": "騙人的假網站", "惡意軟體": "壞壞的程式",
        "SSL 證書": "安全鎖", "頂級域名": "網址的尾巴",
        "個資": "個人資料", "仿冒": "假裝成", "威脅情報": "安全檢查",
        "色情": "不適合小朋友看的內容", "成人內容": "大人才能看的內容",
        "暴力": "打打殺殺的畫面",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text


class ReportGeneratorService:
    RISK_UI: dict[str, dict[str, str]] = {
        "critical": {"icon": "🔴", "color": "#ef4444", "label": "超級危險"},
        "high":     {"icon": "🔴", "color": "#f97316", "label": "很危險"},
        "medium":   {"icon": "🟠", "color": "#f59e0b", "label": "有點可疑"},
        "low":      {"icon": "🟡", "color": "#eab308", "label": "相對安全"},
        "inconclusive": {"icon": "⚪", "color": "#9ca3af", "label": "無法判斷"},
    }

    CONFIDENCE_UI: dict[str, dict[str, str]] = {
        "high":   {"icon": "✅", "label": "很確定"},
        "medium": {"icon": "⚠️", "label": "大概"},
        "low":    {"icon": "❓", "label": "不太確定"},
    }

    KID_RISK_TEXT: dict[str, str] = {
        "critical":     "🚨 這個網站很可能是騙人的，千萬不要點進去！",
        "high":         "⚠️ 這個網站看起來怪怪的，建議不要訪問",
        "medium":       "🤔 這個網站有點可疑，要多小心一點",
        "low":          "🙂 這個網站看起來還好，但上網還是要保持警覺喔",
        "inconclusive": "❓ 資訊不足，無法判斷，建議用其他工具再檢查",
    }

    KID_CONTENT_RISK_TEXT: dict[str, str] = {
        "critical":     "🚨 這個網站有大人才能看的內容，小朋友不要進去喔！",
        "high":         "⚠️ 這個網站有不適合小朋友的內容，建議不要訪問",
        "medium":       "🤔 這個網站可能有不恰當的內容，要多小心",
        "low":          "🙂 看起來還好，但上網還是要保持警覺喔",
        "inconclusive": "❓ 無法確定內容是否適合，建議不要點擊",
    }

    def __init__(
        self,
        target_url: str,
        analysis_result: dict[str, Any],
        cleaned_results: list[dict[str, Any]],
        risk_source: str = "phishing",
    ) -> None:
        self.target_url = target_url.strip()
        self.analysis = analysis_result
        self.cleaned_results = cleaned_results
        self.risk_source = risk_source
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.target_domain = self._extract_domain(target_url)
        self.target_tld = self._extract_tld(self.target_domain)

    # ── Helpers ──

    @staticmethod
    def _extract_domain(url: str) -> str:
        url = url.strip().rstrip("/")
        url = re.sub(r"^https?://", "", url)
        return url.split("/")[0].split("?")[0]

    @staticmethod
    def _extract_tld(domain: str) -> str:
        parts = domain.split(".")
        return parts[-1] if len(parts) > 1 else ""

    # ── Section generators ──

    def _generate_metadata(self) -> dict[str, Any]:
        risk_level = self.analysis.get("risk_level", "inconclusive")
        risk_ui = self.RISK_UI.get(risk_level, self.RISK_UI["inconclusive"])
        confidence = self.analysis.get("confidence", "low")
        conf_ui = self.CONFIDENCE_UI.get(confidence, self.CONFIDENCE_UI["low"])
        return {
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "target_tld": self.target_tld,
            "timestamp": self.timestamp,
            "risk": {
                "level": risk_level, "score": self.analysis.get("risk_score", 50),
                "icon": risk_ui["icon"], "color": risk_ui["color"], "label": risk_ui["label"],
            },
            "confidence": {"level": confidence, "icon": conf_ui["icon"], "label": conf_ui["label"]},
        }

    def _generate_kid_summary(self) -> dict[str, Any]:
        risk_level = self.analysis.get("risk_level", "inconclusive")
        risk_ui = self.RISK_UI.get(risk_level, self.RISK_UI["inconclusive"])
        risk_texts = self.KID_CONTENT_RISK_TEXT if self.risk_source == "content" else self.KID_RISK_TEXT

        explanation = self.analysis.get("why_unsafe") or self.analysis.get("explanation", "")
        if not explanation or len(explanation) < 50:
            explanation = self._default_kid_explanation()
        return {
            "title": f"{risk_ui['icon']} {risk_ui['label']}！",
            "simple_message": risk_texts.get(risk_level, ""),
            "short_explanation": simplify_text(explanation, 200),
            "emoji_reaction": risk_ui["icon"],
            "action_verb": "不要點" if risk_level in ("critical", "high") else "小心點",
        }

    def _default_kid_explanation(self) -> str:
        risk_level = self.analysis.get("risk_level", "inconclusive")
        content_type = self.analysis.get("content_risk_type", "")
        if self.risk_source == "content" and risk_level in ("critical", "high"):
            return (
                f"這個網站可能有不適合小朋友看的內容（像是{content_type or '大人才能看的東西'}）：\n"
                "1. 網路上有些內容是設計給大人看的\n"
                "2. 小朋友看到可能會有不好的影響\n"
                "3. 如果不小心點進去，要馬上關掉，並告訴爸媽或老師喔！"
            )
        if risk_level in ("critical", "high"):
            return (
                f"這個網址有幾個「紅燈信號」🚦：\n"
                f"1. 網址的尾巴 (.{self.target_tld}) 很少見，很多騙人的網站喜歡用\n"
                "2. 域名長長又複雜，正規網站通常簡單好記\n"
                "3. 看起來很像知名品牌，但其實不是真的\n"
                "所以我們要特別小心，不要隨便點進去或輸入個人資料喔！"
            )
        return "這個網址看起來沒有明顯危險，但上網時還是要保持警覺，不要隨便輸入個人資料喔！"

    def _generate_evidence_cards(self) -> list[dict[str, Any]]:
        evidence = self.analysis.get("evidence_summary") or self.analysis.get("evidence_analysis", [])
        cards: list[dict[str, Any]] = []
        for i, ev in enumerate(evidence[:4]):
            clean_ev = re.sub(r"^[-•\d.\s]+", "", str(ev)).strip()
            if not clean_ev:
                continue
            severity, icon = "medium", "🔍"
            lower = clean_ev.lower()
            if any(kw in lower for kw in ("critical", "惡意", "threat", "danger")):
                severity, icon = "high", "🚨"
            elif any(kw in lower for kw in ("suspicious", "可疑", "warning")):
                icon = "⚠️"
            elif any(kw in lower for kw in ("tld", "尾巴", "cfd", "xyz")):
                icon = "🌐"
            elif any(kw in lower for kw in ("brand", "品牌", "paypal", "allegro")):
                icon = "🏷️"
            cards.append({
                "id": f"evidence_{i + 1}", "icon": icon,
                "title": self._extract_evidence_title(clean_ev),
                "content": simplify_text(clean_ev, 120),
                "severity": severity, "expandable": len(clean_ev) > 80,
            })
        if not cards:
            cards.append({
                "id": "evidence_default", "icon": "💡", "title": "小提醒",
                "content": "這個網址沒有明顯危險信號，但上網時還是要保持警覺喔！",
                "severity": "low", "expandable": False,
            })
        return cards

    @staticmethod
    def _extract_evidence_title(text: str) -> str:
        patterns: list[tuple[str, str]] = [
            (r"威脅類型[:：]", "🚨 偵測到威脅"), (r"分類[:：]", "🏷️ 分類標籤"),
            (r"惡意[:：]?\s*\d+", "🔴 惡意偵測"), (r"品牌", "🏷️ 品牌相似度"),
            (r"域名.*?複雜", "🔤 域名結構"),
        ]
        for pattern, title in patterns:
            if re.search(pattern, text, re.I):
                return title
        return text[:10] + "..." if len(text) > 10 else text

    def _generate_pattern_analysis(self) -> dict[str, Any]:
        high_risk_tlds = {"cfd", "top", "rest", "xyz", "loan", "click", "work"}
        is_high_risk = self.target_tld.lower() in high_risk_tlds
        domain_len = len(self.target_domain)
        has_numbers = any(c.isdigit() for c in self.target_domain)
        has_hyphens = "-" in self.target_domain
        return {
            "tld_analysis": {
                "tld": self.target_tld,
                "is_common": self.target_tld.lower() in {"com", "tw", "org", "net", "edu"},
                "is_high_risk": is_high_risk,
                "kid_message": f"網址的尾巴 `.{self.target_tld}` "
                               + ("很少見，要特別小心" if is_high_risk else "是常見的，比較放心"),
            },
            "domain_structure": {
                "length": domain_len, "has_numbers": has_numbers, "has_hyphens": has_hyphens,
                "kid_message": (
                    f"域名{'長長又複雜' if domain_len > 30 or has_numbers or has_hyphens else '簡單好記'}，"
                    + ("正規網站通常簡單喔" if domain_len > 30 else "")
                ),
            },
            "visual_summary": {
                "url_parts": [
                    {"part": "https://", "label": "協定", "safe": True},
                    {"part": self.target_domain, "label": "域名",
                     "safe": not (is_high_risk or domain_len > 30)},
                    {"part": "/" + self.target_url.split(self.target_domain)[-1]
                     if "/" in self.target_url else "", "label": "路徑", "safe": True},
                ],
            },
        }

    def _generate_interactive_quiz(self) -> dict[str, Any]:
        qg = QuizGenerator(
            analysis=self.analysis,
            risk_source=self.risk_source,
            target_domain=self.target_domain,
            target_tld=self.target_tld,
        )
        return qg.generate()

    def _generate_safety_tips(self) -> list[dict[str, Any]]:
        recommendations = self.analysis.get("recommendations", [])
        if self.risk_source == "content":
            templates = [
                {"icon": "🚫", "tip": "不點開奇怪的連結", "why": "可能連到不適合小朋友的網站"},
                {"icon": "👀", "tip": "看到不舒服的內容要馬上關掉", "why": "保護自己的眼睛和心情"},
                {"icon": "👨‍👩‍👧", "tip": "遇到不清楚的網站告訴爸媽或老師", "why": "大人可以幫你判斷"},
                {"icon": "📱", "tip": "用網路時保持警覺", "why": "不是所有網站都適合小朋友"},
            ]
        else:
            templates = [
                {"icon": "🔍", "tip": "不隨便點陌生連結", "why": "陌生連結可能帶你到騙人的網站"},
                {"icon": "🔐", "tip": "不在不明網站輸入密碼", "why": "騙人的網站會偷走你的帳號"},
                {"icon": "👨‍👩‍👧", "tip": "有疑問時問爸媽或老師", "why": "大人經驗多，可以幫你判斷"},
                {"icon": "🔖", "tip": "把常用網站加入書籤", "why": "避免打錯網址跑到假網站"},
                {"icon": "🔄", "tip": "定期更新密碼", "why": "不同網站用不同密碼更安全"},
            ]
        tips: list[dict[str, Any]] = []
        for i, rec in enumerate(recommendations[:3]):
            clean = re.sub(r"^[-•\d.\s]+", "", str(rec)).strip()
            if clean:
                t = templates[i % len(templates)]
                tips.append({"id": f"tip_{i + 1}", "icon": t["icon"],
                             "tip": simplify_text(clean, 60), "why": t["why"], "action_text": "記住囉！"})
        while len(tips) < 4:
            t = templates[len(tips) % len(templates)]
            tips.append({"id": f"tip_{len(tips) + 1}", "icon": t["icon"],
                         "tip": t["tip"], "why": t["why"], "action_text": "記住囉！"})
        return tips

    def _generate_next_steps(self) -> list[dict[str, Any]]:
        risk = self.analysis.get("risk_level", "inconclusive")
        if risk in ("critical", "high"):
            return [
                {"action": "❌ 不要點擊此連結", "priority": "high", "icon": "🚫"},
                {"action": "🔍 用 VirusTotal 再檢查一次", "priority": "medium", "icon": "🔎", "link": "https://www.virustotal.com"},
                {"action": "👨‍👩‍👧 問爸媽或老師", "priority": "high", "icon": "🗣️"},
                {"action": "🌐 直接輸入官方網址訪問", "priority": "medium", "icon": "✅"},
            ]
        return [
            {"action": "🔍 保持警覺，仔細看網址", "priority": "medium", "icon": "👀"},
            {"action": "🔐 不要在不明網站輸入個資", "priority": "high", "icon": "🔒"},
            {"action": "📚 學習更多網路安全知識", "priority": "low", "icon": "🎓", "link": "https://phishingquiz.withgoogle.com"},
        ]

    # ── Public entry ──

    def generate(self) -> dict[str, Any]:
        return {
            "report_metadata": self._generate_metadata(),
            "kid_friendly_summary": self._generate_kid_summary(),
            "evidence_cards": self._generate_evidence_cards(),
            "pattern_analysis": self._generate_pattern_analysis(),
            "interactive_quiz": self._generate_interactive_quiz(),
            "safety_tips": self._generate_safety_tips(),
            "next_steps": self._generate_next_steps(),
            "raw_analysis": self.analysis,
        }
