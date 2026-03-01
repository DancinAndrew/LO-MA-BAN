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

from config import (
    HIGH_RISK_TLDS, COMMON_TLDS, SUSPICIOUS_DOMAIN_LENGTH,
    KID_FRIENDLY_REPLACEMENTS,
)
from services.quiz_generator import QuizGenerator

logger = logging.getLogger(__name__)


def simplify_text(text: str, max_length: int = 150) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.strip())
    for old, new in KID_FRIENDLY_REPLACEMENTS.items():
        text = text.replace(old, new)
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text


class ReportGeneratorService:
    RISK_UI: dict[str, dict[str, str]] = {
        "critical": {"icon": "🔴", "color": "#ef4444", "label": "Extremely Dangerous"},
        "high":     {"icon": "🔴", "color": "#f97316", "label": "Very Dangerous"},
        "medium":   {"icon": "🟠", "color": "#f59e0b", "label": "Somewhat Suspicious"},
        "low":      {"icon": "🟡", "color": "#eab308", "label": "Relatively Safe"},
        "inconclusive": {"icon": "⚪", "color": "#9ca3af", "label": "Inconclusive"},
    }

    CONFIDENCE_UI: dict[str, dict[str, str]] = {
        "high":   {"icon": "✅", "label": "Very confident"},
        "medium": {"icon": "⚠️", "label": "Somewhat confident"},
        "low":    {"icon": "❓", "label": "Not very confident"},
    }

    KID_RISK_TEXT: dict[str, str] = {
        "critical":     "🚨 This website is very likely a scam — do NOT click!",
        "high":         "⚠️ This website looks suspicious — we recommend not visiting it",
        "medium":       "🤔 This website is a bit suspicious — be extra careful",
        "low":          "🙂 This website seems okay, but always stay alert online",
        "inconclusive": "❓ Not enough info to decide — try checking with another tool",
    }

    KID_CONTENT_RISK_TEXT: dict[str, str] = {
        "critical":     "🚨 This website has adults-only content — kids should NOT visit!",
        "high":         "⚠️ This website has content not suitable for kids — we recommend not visiting",
        "medium":       "🤔 This website may have inappropriate content — be careful",
        "low":          "🙂 Seems okay, but always stay alert online",
        "inconclusive": "❓ Can't tell if the content is appropriate — we recommend not clicking",
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
            "title": f"{risk_ui['icon']} {risk_ui['label']}!",
            "simple_message": risk_texts.get(risk_level, ""),
            "short_explanation": simplify_text(explanation, 200),
            "emoji_reaction": risk_ui["icon"],
            "action_verb": "Don't click" if risk_level in ("critical", "high") else "Be careful",
        }

    def _default_kid_explanation(self) -> str:
        risk_level = self.analysis.get("risk_level", "inconclusive")
        content_type = self.analysis.get("content_risk_type", "")
        if self.risk_source == "content" and risk_level in ("critical", "high"):
            return (
                f"This website may contain content not suitable for kids (such as {content_type or 'adults-only material'}):\n"
                "1. Some online content is designed only for adults\n"
                "2. Seeing it could have a negative effect on kids\n"
                "3. If you accidentally open it, close it right away and tell a parent or teacher!"
            )
        if risk_level in ("critical", "high"):
            return (
                f"This URL has several red flags 🚦:\n"
                f"1. The domain ending (.{self.target_tld}) is uncommon — scam sites love to use these\n"
                "2. The domain name is long and complex — legitimate sites are usually short and easy to remember\n"
                "3. It looks similar to a well-known brand, but it's not the real one\n"
                "So be extra careful — don't click or enter any personal information!"
            )
        return "This URL doesn't show obvious dangers, but always stay alert and don't enter personal information on unfamiliar sites!"

    def _generate_evidence_cards(self) -> list[dict[str, Any]]:
        evidence = self.analysis.get("evidence_summary") or self.analysis.get("evidence_analysis", [])
        cards: list[dict[str, Any]] = []
        for i, ev in enumerate(evidence[:4]):
            clean_ev = re.sub(r"^[-•\d.\s]+", "", str(ev)).strip()
            if not clean_ev:
                continue
            severity, icon = "medium", "🔍"
            lower = clean_ev.lower()
            if any(kw in lower for kw in ("critical", "malicious", "threat", "danger")):
                severity, icon = "high", "🚨"
            elif any(kw in lower for kw in ("suspicious", "warning")):
                icon = "⚠️"
            elif any(kw in lower for kw in ("tld", "ending", "cfd", "xyz")):
                icon = "🌐"
            elif any(kw in lower for kw in ("brand", "paypal", "allegro")):
                icon = "🏷️"
            cards.append({
                "id": f"evidence_{i + 1}", "icon": icon,
                "title": self._extract_evidence_title(clean_ev),
                "content": simplify_text(clean_ev, 120),
                "severity": severity, "expandable": len(clean_ev) > 80,
            })
        if not cards:
            cards.append({
                "id": "evidence_default", "icon": "💡", "title": "Reminder",
                "content": "No obvious danger signs for this URL, but always stay alert online!",
                "severity": "low", "expandable": False,
            })
        return cards

    @staticmethod
    def _extract_evidence_title(text: str) -> str:
        patterns: list[tuple[str, str]] = [
            (r"[Tt]hreat\s*type[:：]", "🚨 Threat Detected"), (r"[Cc]ategor(y|ies)[:：]", "🏷️ Category Tags"),
            (r"[Mm]alicious[:：]?\s*\d+", "🔴 Malicious Detection"), (r"[Bb]rand", "🏷️ Brand Similarity"),
            (r"[Dd]omain.*?complex", "🔤 Domain Structure"),
        ]
        for pattern, title in patterns:
            if re.search(pattern, text, re.I):
                return title
        return text[:10] + "..." if len(text) > 10 else text

    def _generate_pattern_analysis(self) -> dict[str, Any]:
        is_high_risk = self.target_tld.lower() in HIGH_RISK_TLDS
        domain_len = len(self.target_domain)
        has_numbers = any(c.isdigit() for c in self.target_domain)
        has_hyphens = "-" in self.target_domain
        return {
            "tld_analysis": {
                "tld": self.target_tld,
                "is_common": self.target_tld.lower() in COMMON_TLDS,
                "is_high_risk": is_high_risk,
                "kid_message": f"The domain ending `.{self.target_tld}` "
                               + ("is uncommon — be extra careful" if is_high_risk else "is common — that's reassuring"),
            },
            "domain_structure": {
                "length": domain_len, "has_numbers": has_numbers, "has_hyphens": has_hyphens,
                "kid_message": (
                    f"The domain is {'long and complex' if domain_len > SUSPICIOUS_DOMAIN_LENGTH or has_numbers or has_hyphens else 'short and easy to remember'}"
                    + (" — legitimate sites are usually simple" if domain_len > SUSPICIOUS_DOMAIN_LENGTH else "")
                ),
            },
            "visual_summary": {
                "url_parts": [
                    {"part": "https://", "label": "Protocol", "safe": True},
                    {"part": self.target_domain, "label": "Domain",
                     "safe": not (is_high_risk or domain_len > SUSPICIOUS_DOMAIN_LENGTH)},
                    {"part": "/" + self.target_url.split(self.target_domain)[-1]
                     if "/" in self.target_url else "", "label": "Path", "safe": True},
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
                {"icon": "🚫", "tip": "Don't open suspicious links", "why": "They might lead to sites not suitable for kids"},
                {"icon": "👀", "tip": "Close the page immediately if something feels wrong", "why": "Protect your eyes and your mood"},
                {"icon": "👨‍👩‍👧", "tip": "Tell a parent or teacher about unfamiliar sites", "why": "Adults can help you decide"},
                {"icon": "📱", "tip": "Stay alert when browsing", "why": "Not all websites are suitable for kids"},
            ]
        else:
            templates = [
                {"icon": "🔍", "tip": "Don't click unfamiliar links", "why": "Unknown links may lead to scam sites"},
                {"icon": "🔐", "tip": "Never enter passwords on unknown sites", "why": "Scam sites can steal your account"},
                {"icon": "👨‍👩‍👧", "tip": "Ask a parent or teacher when in doubt", "why": "Adults have more experience and can help"},
                {"icon": "🔖", "tip": "Bookmark your favorite sites", "why": "Avoid typos that lead to fake sites"},
                {"icon": "🔄", "tip": "Update your passwords regularly", "why": "Use different passwords for different sites"},
            ]
        tips: list[dict[str, Any]] = []
        for i, rec in enumerate(recommendations[:3]):
            clean = re.sub(r"^[-•\d.\s]+", "", str(rec)).strip()
            if clean:
                t = templates[i % len(templates)]
                tips.append({"id": f"tip_{i + 1}", "icon": t["icon"],
                             "tip": simplify_text(clean, 60), "why": t["why"], "action_text": "Got it!"})
        while len(tips) < 4:
            t = templates[len(tips) % len(templates)]
            tips.append({"id": f"tip_{len(tips) + 1}", "icon": t["icon"],
                         "tip": t["tip"], "why": t["why"], "action_text": "Got it!"})
        return tips

    def _generate_next_steps(self) -> list[dict[str, Any]]:
        risk = self.analysis.get("risk_level", "inconclusive")
        if risk in ("critical", "high"):
            return [
                {"action": "❌ Do NOT click this link", "priority": "high", "icon": "🚫"},
                {"action": "🔍 Double-check with VirusTotal", "priority": "medium", "icon": "🔎", "link": "https://www.virustotal.com"},
                {"action": "👨‍👩‍👧 Ask a parent or teacher", "priority": "high", "icon": "🗣️"},
                {"action": "🌐 Visit the official site directly", "priority": "medium", "icon": "✅"},
            ]
        return [
            {"action": "🔍 Stay alert and inspect the URL carefully", "priority": "medium", "icon": "👀"},
            {"action": "🔐 Don't enter personal info on unknown sites", "priority": "high", "icon": "🔒"},
            {"action": "📚 Learn more about internet safety", "priority": "low", "icon": "🎓", "link": "https://phishingquiz.withgoogle.com"},
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
