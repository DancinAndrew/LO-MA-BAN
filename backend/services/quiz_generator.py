"""
QuizGenerator — interactive quiz builder extracted from ReportGeneratorService.
Generates kid-friendly quizzes for phishing awareness and content-safety education.
"""
from __future__ import annotations

import re
import logging
from typing import Any

from config import KID_FRIENDLY_REPLACEMENTS, KNOWN_BRAND_PATTERNS

logger = logging.getLogger(__name__)


def _simplify_text(text: str, max_length: int = 150) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text.strip())
    for old, new in KID_FRIENDLY_REPLACEMENTS.items():
        text = text.replace(old, new)
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text


class QuizGenerator:
    """Build an interactive quiz dict from LLM output or fallback templates."""

    def __init__(
        self,
        analysis: dict[str, Any],
        risk_source: str,
        target_domain: str,
        target_tld: str,
    ) -> None:
        self.analysis = analysis
        self.risk_source = risk_source
        self.target_domain = target_domain
        self.target_tld = target_tld

    def generate(self) -> dict[str, Any]:
        quiz_data = self.analysis.get("quiz") or self.analysis.get("interactive_quiz")
        if quiz_data and isinstance(quiz_data, dict) and quiz_data.get("question"):
            try:
                return self._render_llm_quiz(quiz_data)
            except Exception as exc:
                logger.warning("LLM quiz render failed: %s — using fallback", exc)
        return self._fallback_quiz()

    # ── LLM quiz rendering ──

    def _render_llm_quiz(self, quiz_data: dict[str, Any]) -> dict[str, Any]:
        options = quiz_data.get("options", [])
        explanations = quiz_data.get("explanations", {})
        correct = quiz_data.get("correct_answer", "")
        ids = ["A", "B", "C", "D"]
        fmt: list[dict[str, Any]] = []
        for i, opt in enumerate(options[:4]):
            if isinstance(opt, dict):
                oid = opt.get("id", ids[i] if i < 4 else str(i + 1))
                otxt = opt.get("text", str(opt))
            else:
                oid = ids[i] if i < 4 else str(i + 1)
                otxt = str(opt)
            is_correct = str(oid) == str(correct) or str(otxt) == str(correct)
            explanation = "Think again~"
            if isinstance(explanations, dict):
                explanation = explanations.get(str(oid), explanations.get(str(otxt), explanation))
            fmt.append({
                "id": str(oid), "text": _simplify_text(str(otxt), 100),
                "is_correct": is_correct,
                "explanation": _simplify_text(str(explanation), 150),
                "feedback_icon": "✅" if is_correct else "❌",
            })
        correct_id = str(correct) if str(correct) in ids else None
        if not correct_id:
            for o in fmt:
                if o["is_correct"]:
                    correct_id = o["id"]
                    break
        return {
            "enabled": True,
            "question": _simplify_text(str(quiz_data.get("question", "")), 120),
            "hint": _simplify_text(str(quiz_data.get("hint", "")), 80) or None,
            "type": quiz_data.get("type", "single_choice"),
            "options": fmt, "correct_answer_id": correct_id,
            "learning_point": _simplify_text(str(quiz_data.get("learning_point", "")), 150),
            "difficulty": quiz_data.get("difficulty", "easy"),
        }

    # ── Fallback quizzes ──

    def _fallback_quiz(self) -> dict[str, Any]:
        if self.risk_source == "content":
            return self._content_risk_quiz()
        if any(b in self.target_domain.lower() for b in KNOWN_BRAND_PATTERNS):
            return self._brand_quiz()
        if self.target_tld.lower() in {"cfd", "xyz", "top", "rest"}:
            return self._tld_quiz()
        return self._generic_quiz()

    @staticmethod
    def _content_risk_quiz() -> dict[str, Any]:
        return {
            "enabled": True,
            "question": "🤔 If you accidentally open a website that's 'not for kids', what should you do first?",
            "hint": "Remember: don't panic — ask an adult for help!", "type": "single_choice",
            "options": [
                {"id": "A", "text": "Keep browsing since you already opened it", "is_correct": False, "explanation": "That would expose you to more inappropriate content — close it right away!", "feedback_icon": "❌"},
                {"id": "B", "text": "Close the page immediately and tell a parent or teacher", "is_correct": True, "explanation": "Correct! Closing it and telling an adult is the best thing to do!", "feedback_icon": "✅"},
                {"id": "C", "text": "Save it secretly and don't tell anyone", "is_correct": False, "explanation": "Be brave and ask for help — adults are there to support you!", "feedback_icon": "❌"},
                {"id": "D", "text": "Share it with your classmates", "is_correct": False, "explanation": "Inappropriate content should not be shared — protect yourself and your friends!", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": "When you find an inappropriate site: close it → tell an adult → don't be afraid to ask for help!",
            "difficulty": "easy",
        }

    def _brand_quiz(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "question": f"🔍 What looks 'off' about the URL `{self.target_domain}`?",
            "hint": "Look at every letter carefully — scammers love to swap letters with numbers!", "type": "single_choice",
            "options": [
                {"id": "A", "text": "It looks similar to the real brand URL, but something is different", "is_correct": False, "explanation": "Noticing the similarity isn't enough — you need to check every single letter!", "feedback_icon": "❌"},
                {"id": "B", "text": f"Its ending is .{self.target_tld}, but legitimate sites usually use .com", "is_correct": False, "explanation": f".{self.target_tld} is indeed suspicious, but scammers can also use .com — don't rely on the ending alone", "feedback_icon": "❌"},
                {"id": "C", "text": "It uses numbers or symbols to replace letters (e.g., 1 for l, 0 for o)", "is_correct": True, "explanation": "Correct! Scam sites often swap numbers for letters to trick you — always check letter by letter!", "feedback_icon": "✅"},
                {"id": "D", "text": "All of the above! 🎉", "is_correct": False, "explanation": "D is tempting, but pick the single most critical clue!", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "C",
            "learning_point": "When a URL looks like a famous brand, always check letter by letter and verify the official URL!",
            "difficulty": "medium",
        }

    def _tld_quiz(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "question": f"🌐 What does the domain ending `.{self.target_tld}` tell us?",
            "hint": "Think about it — what endings do you usually see on websites?", "type": "single_choice",
            "options": [
                {"id": "A", "text": "It's a very common and safe ending — no worries", "is_correct": False, "explanation": f".{self.target_tld} is technically valid, but it's cheap to register and often used by scammers — be careful!", "feedback_icon": "❌"},
                {"id": "B", "text": "It's an uncommon ending — be extra cautious", "is_correct": True, "explanation": f"Correct! .com and .org are common endings, but uncommon ones like .{self.target_tld} deserve extra caution!", "feedback_icon": "✅"},
                {"id": "C", "text": "The ending doesn't matter as long as the site has a 🔒 lock icon", "is_correct": False, "explanation": "The 🔒 lock only means the connection is encrypted — it doesn't mean the site is trustworthy", "feedback_icon": "❌"},
                {"id": "D", "text": "All endings are the same — it doesn't matter", "is_correct": False, "explanation": "Different endings have different registration rules — learning to tell them apart is important!", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": f"When unsure, search 'is .{self.target_tld} safe?' or go directly to the official site by typing 'brand name + .com'!",
            "difficulty": "easy",
        }

    @staticmethod
    def _generic_quiz() -> dict[str, Any]:
        return {
            "enabled": True,
            "question": "🤔 If you receive an unfamiliar link, what should you do first?",
            "hint": "Remember the motto: Stop, Look, Think!", "type": "single_choice",
            "options": [
                {"id": "A", "text": "Click it right away to see what it is", "is_correct": False, "explanation": "Clicking could expose you to viruses or steal your info — never do this!", "feedback_icon": "❌"},
                {"id": "B", "text": "Copy the URL and check it with a safety tool first", "is_correct": True, "explanation": "Correct! Checking with a safety tool first is the safest approach!", "feedback_icon": "✅"},
                {"id": "C", "text": "Delete it and ignore it completely", "is_correct": False, "explanation": "Deleting is safe, but if it's an important notice you might miss something", "feedback_icon": "❌"},
                {"id": "D", "text": "Forward it to your friends", "is_correct": False, "explanation": "Forwarding could put more people at risk — verify safety before sharing", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": "Safety motto: 'Don't click unknown links — check first, click later!' 🔐",
            "difficulty": "easy",
        }
