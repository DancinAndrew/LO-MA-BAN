"""
QuizGenerator — interactive quiz builder extracted from ReportGeneratorService.
Generates kid-friendly quizzes for phishing awareness and content-safety education.
"""
from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _simplify_text(text: str, max_length: int = 150) -> str:
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
            explanation = "再想想看～"
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
        brands = ("paypa", "amazn", "app1e", "g0ogle", "allegro")
        if any(b in self.target_domain.lower() for b in brands):
            return self._brand_quiz()
        if self.target_tld.lower() in {"cfd", "xyz", "top", "rest"}:
            return self._tld_quiz()
        return self._generic_quiz()

    @staticmethod
    def _content_risk_quiz() -> dict[str, Any]:
        return {
            "enabled": True,
            "question": "🤔 如果你不小心點進了一個「不適合小朋友看」的網站，第一步應該做什麼？",
            "hint": "記得：不要慌張，找大人幫忙！", "type": "single_choice",
            "options": [
                {"id": "A", "text": "繼續看下去，反正都點進來了", "is_correct": False, "explanation": "這樣會看到更多不適當的內容，要趕快關掉喔！", "feedback_icon": "❌"},
                {"id": "B", "text": "馬上關掉網頁，然後告訴爸媽或老師", "is_correct": True, "explanation": "答對啦！關掉並告訴大人是最好的做法！", "feedback_icon": "✅"},
                {"id": "C", "text": "偷偷存起來，不要讓別人知道", "is_correct": False, "explanation": "遇到這種情況要勇敢求助，大人會幫忙你的！", "feedback_icon": "❌"},
                {"id": "D", "text": "分享給同學一起看", "is_correct": False, "explanation": "不適當的內容不應該分享，要保護自己也保護同學喔！", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": "遇到不適當的網站：關掉 → 告訴大人 → 不要害怕求助！",
            "difficulty": "easy",
        }

    def _brand_quiz(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "question": f"🔍 你覺得 `{self.target_domain}` 這個網址，哪裡「怪怪的」？",
            "hint": "仔細看每個字母喔，騙子喜歡用數字代替字母！", "type": "single_choice",
            "options": [
                {"id": "A", "text": "它跟真正的品牌網址長得好像，但有些地方不太一樣", "is_correct": False, "explanation": "只注意到「像」還不夠，要學會「逐字檢查每個字母」喔！", "feedback_icon": "❌"},
                {"id": "B", "text": f"它的「尾巴」是 .{self.target_tld}，但正規網站通常是 .com", "is_correct": False, "explanation": f".{self.target_tld} 確實可疑，但騙子也會用 .com，不能只看尾巴", "feedback_icon": "❌"},
                {"id": "C", "text": "它用數字或符號代替字母（例如用 1 代替 l，0 代替 o）", "is_correct": True, "explanation": "答對啦！騙人的網站常用數字代替字母來混淆你，要逐字檢查！", "feedback_icon": "✅"},
                {"id": "D", "text": "以上都是！🎉", "is_correct": False, "explanation": "D 看起來很誘人，但這題要選「最關鍵」的那個喔！", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "C",
            "learning_point": "看到很像知名品牌的網址，一定要「逐字檢查」＋「確認官方網址」！",
            "difficulty": "medium",
        }

    def _tld_quiz(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "question": f"🌐 網址的「尾巴」`.{self.target_tld}`，代表什麼意思呢？",
            "hint": "想想看，你常看到的網站尾巴是什麼？", "type": "single_choice",
            "options": [
                {"id": "A", "text": "這是一個很常見、很安全的尾巴，可以放心點", "is_correct": False, "explanation": f".{self.target_tld} 雖然合法，但因為註冊便宜，常被騙子利用，要小心！", "feedback_icon": "❌"},
                {"id": "B", "text": "這是一個比較少見的尾巴，要特別小心", "is_correct": True, "explanation": f"答對啦！.com、.tw 是常見的尾巴，但像 .{self.target_tld} 這種比較少見的，要特別小心！", "feedback_icon": "✅"},
                {"id": "C", "text": "尾巴不重要，只要網站有🔒小鎖頭就安全", "is_correct": False, "explanation": "🔒小鎖頭只代表「連線有加密」，不代表「網站內容是真的」", "feedback_icon": "❌"},
                {"id": "D", "text": "所有尾巴都一樣，不用在意", "is_correct": False, "explanation": "不同的尾巴代表不同的註冊規則，學會分辨很重要喔！", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": f"不確定時，可以搜尋「.{self.target_tld} 域名 安全嗎」，或直接輸入「品牌名 + .com」訪問官方網站！",
            "difficulty": "easy",
        }

    @staticmethod
    def _generic_quiz() -> dict[str, Any]:
        return {
            "enabled": True,
            "question": "🤔 如果你收到一個陌生連結，第一步應該做什麼？",
            "hint": "記住口訣：停、看、聽！", "type": "single_choice",
            "options": [
                {"id": "A", "text": "馬上點進去看看是什麼", "is_correct": False, "explanation": "直接點進去可能會中病毒、被騙個資，千萬不要！", "feedback_icon": "❌"},
                {"id": "B", "text": "先複製網址，用安全工具檢查一下", "is_correct": True, "explanation": "答對啦！先用安全工具檢查，是最保險的做法！", "feedback_icon": "✅"},
                {"id": "C", "text": "直接刪除，不管它", "is_correct": False, "explanation": "刪除是安全的，但如果這是重要通知，可能會錯過重要資訊", "feedback_icon": "❌"},
                {"id": "D", "text": "轉發給朋友一起看", "is_correct": False, "explanation": "轉發可能讓更多人遇到危險，要先確認安全再分享", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": "安全口訣：「陌生連結不亂點，先查再按最安全」🔐",
            "difficulty": "easy",
        }
