#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
互動式教學報告生成器（JSON 輸出版）
專為 18 歲以下學習者設計：兒童友善內容 + 創意選擇題 + 前端可直接使用
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """生成前端可用的 JSON 格式教學報告"""
    
    RISK_UI = {
        "critical": {"icon": "🔴", "color": "#ef4444", "label": "超級危險"},
        "high": {"icon": "🔴", "color": "#f97316", "label": "很危險"},
        "medium": {"icon": "🟠", "color": "#f59e0b", "label": "有點可疑"},
        "low": {"icon": "🟡", "color": "#eab308", "label": "相對安全"},
        "inconclusive": {"icon": "⚪", "color": "#9ca3af", "label": "無法判斷"}
    }
    
    CONFIDENCE_UI = {
        "high": {"icon": "✅", "label": "很確定"},
        "medium": {"icon": "⚠️", "label": "大概"},
        "low": {"icon": "❓", "label": "不太確定"}
    }
    
    KID_RISK_TEXT = {
        "critical": "🚨 這個網站很可能是騙人的，千萬不要點進去！",
        "high": "⚠️ 這個網站看起來怪怪的，建議不要訪問",
        "medium": "🤔 這個網站有點可疑，要多小心一點",
        "low": "🙂 這個網站看起來還好，但上網還是要保持警覺喔",
        "inconclusive": "❓ 資訊不足，無法判斷，建議用其他工具再檢查"
    }

    KID_CONTENT_RISK_TEXT = {
        "critical": "🚨 這個網站有大人才能看的內容，小朋友不要進去喔！",
        "high": "⚠️ 這個網站有不適合小朋友的內容，建議不要訪問",
        "medium": "🤔 這個網站可能有不恰當的內容，要多小心",
        "low": "🙂 看起來還好，但上網還是要保持警覺喔",
        "inconclusive": "❓ 無法確定內容是否適合，建議不要點擊"
    }
    
    def __init__(
        self,
        target_url: str,
        analysis_result: Dict,
        cleaned_results: List[Dict],
        risk_source: str = "phishing",
    ):
        self.target_url = target_url.strip()
        self.analysis = analysis_result
        self.cleaned_results = cleaned_results
        self.risk_source = risk_source
        self.timestamp = datetime.now().isoformat()
        self.target_domain = self._extract_domain(target_url)
        self.target_tld = self._extract_tld(self.target_domain)
    
    def _extract_domain(self, url: str) -> str:
        url = url.strip().rstrip('/')
        url = re.sub(r'^https?://', '', url)
        return url.split('/')[0].split('?')[0]
    
    def _extract_tld(self, domain: str) -> str:
        parts = domain.split('.')
        return parts[-1] if len(parts) > 1 else ""
    
    def _simplify_text(self, text: str, max_length: int = 150) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        replacements = {
            "釣魚網站": "騙人的假網站",
            "惡意軟體": "壞壞的程式",
            "SSL 證書": "安全鎖",
            "頂級域名": "網址的尾巴",
            "個資": "個人資料",
            "仿冒": "假裝成",
            "威脅情報": "安全檢查",
            "色情": "不適合小朋友看的內容",
            "成人內容": "大人才能看的內容",
            "暴力": "打打殺殺的畫面",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        return text
    
    def generate_report(self, output_path: Path) -> Path:
        report = {
            "report_metadata": self._generate_metadata(),
            "kid_friendly_summary": self._generate_kid_summary(),
            "evidence_cards": self._generate_evidence_cards(),
            "pattern_analysis": self._generate_pattern_analysis(),
            "interactive_quiz": self._generate_interactive_quiz(),
            "safety_tips": self._generate_safety_tips(),
            "next_steps": self._generate_next_steps(),
            "raw_analysis": self.analysis
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"📦 JSON 報告已儲存：{output_path}")

        md_path = output_path.with_suffix('.md')
        self._write_markdown_report(report, md_path)
        logger.info(f"📄 Markdown 報告已儲存：{md_path}")
        return output_path

    def _write_markdown_report(self, report: Dict, md_path: Path) -> None:
        meta = report.get("report_metadata", {})
        kid = report.get("kid_friendly_summary", {})
        risk = meta.get("risk", {})
        conf = meta.get("confidence", {})

        raw = report.get("raw_analysis", {})
        intended_urls = raw.get("likely_intended_urls") or []
        if not intended_urls and raw.get("likely_intended_url"):
            intended_urls = [raw["likely_intended_url"]]
        intended_reason = raw.get("intended_url_reason", "")
        alternatives = raw.get("alternative_recommendations") or []

        lines = [
            "# 網址安全分析報告",
            "",
            f"**目標網址**：{meta.get('target_url', '')}",
            f"**分析時間**：{meta.get('timestamp', '')}",
            "",
        ]
        if intended_urls:
            lines.append("**你可能想去的正確網址**：")
            for u in intended_urls:
                lines.append(f"- {u}")
            if intended_reason:
                lines.extend(["", f"*{intended_reason}*", ""])
            else:
                lines.append("")
        if alternatives:
            lines.append("**可替代的合法網站推薦**：")
            for a in alternatives:
                name = a.get("name", "")
                url = a.get("url", "")
                lines.append(f"- **{name}**：{url}")
            lines.append("")
        lines.extend([
            "---", "",
            f"## {kid.get('title', '')}", "",
            kid.get("simple_message", ""), "",
            f"**簡要說明**：{kid.get('short_explanation', '')}", "",
            "### 風險資訊",
            f"- 風險等級：{risk.get('label', '')}（分數 {risk.get('score', 'N/A')}/100）",
            f"- 信心程度：{conf.get('label', '')}", "",
            "---", "", "## 證據摘要", "",
        ])
        for card in report.get("evidence_cards", []):
            lines.append(f"- **{card.get('icon', '')} {card.get('title', '')}**：{card.get('content', '')}")
        lines.extend(["", "---", "", "## 安全小撇步", ""])
        for tip in report.get("safety_tips", []):
            lines.append(f"- **{tip.get('icon', '')} {tip.get('tip', '')}** — {tip.get('why', '')}")
        lines.extend(["", "---", "", "## 下一步建議", ""])
        for step in report.get("next_steps", []):
            lines.append(f"- {step.get('icon', '')} {step.get('action', '')}")
        lines.extend(["", "---", "", "## 互動問答", ""])
        quiz = report.get("interactive_quiz", {})
        if quiz.get("enabled") and quiz.get("question"):
            lines.extend([f"**題目**：{quiz.get('question', '')}", ""])
            for opt in quiz.get("options", []):
                lines.append(f"- **{opt.get('id', '')}** {opt.get('text', '')} {opt.get('feedback_icon', '')}")
            if quiz.get("learning_point"):
                lines.extend(["", f"**學習重點**：{quiz.get('learning_point', '')}", ""])
        lines.append("")
        md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    def _generate_metadata(self) -> Dict:
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        risk_ui = self.RISK_UI.get(risk_level, self.RISK_UI['inconclusive'])
        confidence = self.analysis.get('confidence', 'low')
        confidence_ui = self.CONFIDENCE_UI.get(confidence, self.CONFIDENCE_UI['low'])
        
        return {
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "target_tld": self.target_tld,
            "timestamp": self.timestamp,
            "risk": {
                "level": risk_level,
                "score": self.analysis.get('risk_score', 50),
                "icon": risk_ui['icon'],
                "color": risk_ui['color'],
                "label": risk_ui['label']
            },
            "confidence": {
                "level": confidence,
                "icon": confidence_ui['icon'],
                "label": confidence_ui['label']
            }
        }
    
    def _generate_kid_summary(self) -> Dict:
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        risk_ui = self.RISK_UI.get(risk_level, self.RISK_UI['inconclusive'])
        risk_texts = self.KID_CONTENT_RISK_TEXT if self.risk_source == "content" else self.KID_RISK_TEXT

        explanation = self.analysis.get('why_unsafe') or self.analysis.get('explanation', '')
        if not explanation or len(explanation) < 50:
            explanation = self._generate_default_kid_explanation()

        return {
            "title": f"{risk_ui['icon']} {risk_ui['label']}！",
            "simple_message": risk_texts.get(risk_level, risk_texts.get("inconclusive", "")),
            "short_explanation": self._simplify_text(explanation, 200),
            "emoji_reaction": risk_ui['icon'],
            "action_verb": "不要點" if risk_level in ['critical', 'high'] else "小心點"
        }
    
    def _generate_default_kid_explanation(self) -> str:
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        content_type = self.analysis.get('content_risk_type', '')

        if self.risk_source == "content" and risk_level in ['critical', 'high']:
            return f"""這個網站可能有不適合小朋友看的內容（像是{content_type or '大人才能看的東西'}）：
1. 網路上有些內容是設計給大人看的
2. 小朋友看到可能會有不好的影響
3. 如果不小心點進去，要馬上關掉，並告訴爸媽或老師喔！"""
        if risk_level in ['critical', 'high']:
            return f"""這個網址有幾個「紅燈信號」🚦：
1. 網址的尾巴 (.{self.target_tld}) 很少見，很多騙人的網站喜歡用
2. 域名長長又複雜，正規網站通常簡單好記
3. 看起來很像知名品牌，但其實不是真的
所以我們要特別小心，不要隨便點進去或輸入個人資料喔！"""
        return "這個網址看起來沒有明顯危險，但上網時還是要保持警覺，不要隨便輸入個人資料喔！"
    
    def _generate_evidence_cards(self) -> List[Dict]:
        evidence = self.analysis.get('evidence_summary') or self.analysis.get('evidence_analysis', [])
        cards = []
        
        for i, ev in enumerate(evidence[:4]):
            clean_ev = re.sub(r'^[-•\d.\s]+', '', str(ev)).strip()
            if not clean_ev:
                continue
            severity = "medium"
            icon = "🔍"
            if any(kw in clean_ev.lower() for kw in ["critical", "惡意", "threat", "danger"]):
                severity = "high"
                icon = "🚨"
            elif any(kw in clean_ev.lower() for kw in ["suspicious", "可疑", "warning"]):
                icon = "⚠️"
            elif any(kw in clean_ev.lower() for kw in ["tld", "尾巴", "cfd", "xyz"]):
                icon = "🌐"
            elif any(kw in clean_ev.lower() for kw in ["brand", "品牌", "paypal", "allegro"]):
                icon = "🏷️"
            
            cards.append({
                "id": f"evidence_{i+1}",
                "icon": icon,
                "title": self._extract_evidence_title(clean_ev),
                "content": self._simplify_text(clean_ev, 120),
                "severity": severity,
                "expandable": len(clean_ev) > 80
            })
        
        if not cards:
            cards.append({
                "id": "evidence_default",
                "icon": "💡",
                "title": "小提醒",
                "content": "這個網址沒有明顯危險信號，但上網時還是要保持警覺喔！",
                "severity": "low",
                "expandable": False
            })
        
        return cards
    
    def _extract_evidence_title(self, evidence_text: str) -> str:
        patterns = [
            (r"威脅類型[:：]\s*(.+?)(?:[，。]|$)", "🚨 偵測到威脅"),
            (r"分類[:：]\s*(.+?)(?:[，。]|$)", "🏷️ 分類標籤"),
            (r"惡意[:：]?\s*\d+", "🔴 惡意偵測"),
            (r"\.(\w+)\s*域名", lambda m: f"🌐 .{m.group(1)} 域名風險"),
            (r"品牌", "🏷️ 品牌相似度"),
            (r"域名.*?複雜", "🔤 域名結構"),
        ]
        for pattern, title in patterns:
            match = re.search(pattern, evidence_text, re.I)
            if match:
                return title if isinstance(title, str) else title(match)
        return evidence_text[:10] + "..." if len(evidence_text) > 10 else evidence_text
    
    def _generate_pattern_analysis(self) -> Dict:
        high_risk_tlds = ['cfd', 'top', 'rest', 'xyz', 'loan', 'click', 'work']
        is_high_risk_tld = self.target_tld.lower() in high_risk_tlds
        domain_len = len(self.target_domain)
        has_numbers = any(c.isdigit() for c in self.target_domain)
        has_hyphens = '-' in self.target_domain
        
        return {
            "tld_analysis": {
                "tld": self.target_tld,
                "is_common": self.target_tld.lower() in ['com', 'tw', 'org', 'net', 'edu'],
                "is_high_risk": is_high_risk_tld,
                "kid_message": f"網址的尾巴 `.{self.target_tld}` {'很少見，要特別小心' if is_high_risk_tld else '是常見的，比較放心'}"
            },
            "domain_structure": {
                "length": domain_len,
                "has_numbers": has_numbers,
                "has_hyphens": has_hyphens,
                "kid_message": f"域名{'長長又複雜' if domain_len > 30 or has_numbers or has_hyphens else '簡單好記'}，{'正規網站通常簡單喔' if domain_len > 30 else ''}"
            },
            "visual_summary": {
                "url_parts": [
                    {"part": "https://", "label": "協定", "safe": True},
                    {"part": self.target_domain, "label": "域名", "safe": not (is_high_risk_tld or domain_len > 30)},
                    {"part": "/" + self.target_url.split(self.target_domain)[-1] if '/' in self.target_url else "", "label": "路徑", "safe": True}
                ]
            }
        }
        
    def _generate_interactive_quiz(self) -> Dict:
        quiz_data = self.analysis.get('quiz') or self.analysis.get('interactive_quiz')
        if quiz_data and isinstance(quiz_data, dict) and quiz_data.get('question'):
            try:
                return self._render_llm_quiz(quiz_data)
            except Exception as e:
                logger.warning(f"⚠️ LLM 題目渲染失敗: {e}，使用 fallback 題目")
                return self._generate_fallback_quiz()
        return self._generate_fallback_quiz()
    
    def _render_llm_quiz(self, quiz_data: Dict) -> Dict:
        options = quiz_data.get('options', [])
        explanations = quiz_data.get('explanations', {})
        correct_answer = quiz_data.get('correct_answer', '')
        
        formatted_options = []
        option_ids = ['A', 'B', 'C', 'D']
        
        for i, opt in enumerate(options[:4]):
            if isinstance(opt, dict):
                opt_id = opt.get('id', option_ids[i] if i < len(option_ids) else str(i+1))
                opt_text = opt.get('text', str(opt))
            else:
                opt_id = option_ids[i] if i < len(option_ids) else str(i+1)
                opt_text = str(opt)
            
            is_correct = (str(opt_text) == str(correct_answer)) or (str(opt_id) == str(correct_answer))
            
            explanation = "再想想看～"
            if isinstance(explanations, dict):
                if isinstance(opt_id, str) and opt_id in explanations:
                    explanation = explanations[opt_id]
                elif isinstance(opt_text, str) and opt_text in explanations:
                    explanation = explanations[opt_text]
                elif str(opt_id) in explanations:
                    explanation = explanations[str(opt_id)]
            
            formatted_options.append({
                "id": str(opt_id),
                "text": self._simplify_text(str(opt_text), 100),
                "is_correct": is_correct,
                "explanation": self._simplify_text(str(explanation), 150),
                "feedback_icon": "✅" if is_correct else "❌"
            })
        
        correct_answer_id = None
        if correct_answer:
            if str(correct_answer) in option_ids:
                correct_answer_id = str(correct_answer)
            else:
                for opt in formatted_options:
                    if opt['text'] == str(correct_answer):
                        correct_answer_id = opt['id']
                        break
        
        return {
            "enabled": True,
            "question": self._simplify_text(str(quiz_data.get('question', '你覺得這個網址哪裡怪怪的？')), 120),
            "hint": self._simplify_text(str(quiz_data.get('hint', '')), 80) if quiz_data.get('hint') else None,
            "type": quiz_data.get('type', 'single_choice'),
            "options": formatted_options,
            "correct_answer_id": correct_answer_id,
            "learning_point": self._simplify_text(str(quiz_data.get('learning_point', '')), 150),
            "difficulty": quiz_data.get('difficulty', 'easy')
        }

    def _generate_fallback_quiz(self) -> Dict:
        if self.risk_source == "content":
            return self._generate_content_risk_quiz()
        if any(brand in self.target_domain.lower() for brand in ['paypa', 'amazn', 'app1e', 'g0ogle', 'allegro']):
            return self._generate_brand_impersonation_quiz()
        elif self.target_tld.lower() in ['cfd', 'xyz', 'top', 'rest']:
            return self._generate_tld_quiz()
        else:
            return self._generate_generic_safety_quiz()

    def _generate_content_risk_quiz(self) -> Dict:
        return {
            "enabled": True,
            "question": "🤔 如果你不小心點進了一個「不適合小朋友看」的網站，第一步應該做什麼？",
            "hint": "記得：不要慌張，找大人幫忙！",
            "type": "single_choice",
            "options": [
                {"id": "A", "text": "繼續看下去，反正都點進來了", "is_correct": False, "explanation": "這樣會看到更多不適當的內容，要趕快關掉喔！", "feedback_icon": "❌"},
                {"id": "B", "text": "馬上關掉網頁，然後告訴爸媽或老師", "is_correct": True, "explanation": "答對啦！關掉並告訴大人是最好的做法！", "feedback_icon": "✅"},
                {"id": "C", "text": "偷偷存起來，不要讓別人知道", "is_correct": False, "explanation": "遇到這種情況要勇敢求助，大人會幫忙你的！", "feedback_icon": "❌"},
                {"id": "D", "text": "分享給同學一起看", "is_correct": False, "explanation": "不適當的內容不應該分享，要保護自己也保護同學喔！", "feedback_icon": "❌"},
            ],
            "correct_answer_id": "B",
            "learning_point": "遇到不適當的網站：關掉 → 告訴大人 → 不要害怕求助！",
            "difficulty": "easy"
        }
    
    def _generate_brand_impersonation_quiz(self) -> Dict:
        return {
            "enabled": True,
            "question": f"🔍 你覺得 `{self.target_domain}` 這個網址，哪裡「怪怪的」？",
            "hint": "仔細看每個字母喔，騙子喜歡用數字代替字母！",
            "type": "single_choice",
            "options": [
                {"id": "A", "text": "它跟真正的品牌網址長得好像，但有些地方不太一樣", "is_correct": False, "explanation": "只注意到「像」還不夠，要學會「逐字檢查每個字母」喔！", "feedback_icon": "❌"},
                {"id": "B", "text": f"它的「尾巴」是 .{self.target_tld}，但正規網站通常是 .com", "is_correct": False, "explanation": f".{self.target_tld} 確實可疑，但騙子也會用 .com，不能只看尾巴", "feedback_icon": "❌"},
                {"id": "C", "text": "它用數字或符號代替字母（例如用 1 代替 l，0 代替 o）", "is_correct": True, "explanation": "答對啦！騙人的網站常用數字代替字母來混淆你，要逐字檢查！", "feedback_icon": "✅"},
                {"id": "D", "text": "以上都是！🎉", "is_correct": False, "explanation": "D 看起來很誘人，但這題要選「最關鍵」的那個喔！", "feedback_icon": "❌"}
            ],
            "correct_answer_id": "C",
            "learning_point": "看到很像知名品牌的網址，一定要「逐字檢查」＋「確認官方網址」！",
            "difficulty": "medium"
        }
    
    def _generate_tld_quiz(self) -> Dict:
        return {
            "enabled": True,
            "question": f"🌐 網址的「尾巴」`.{self.target_tld}`，代表什麼意思呢？",
            "hint": "想想看，你常看到的網站尾巴是什麼？",
            "type": "single_choice",
            "options": [
                {"id": "A", "text": "這是一個很常見、很安全的尾巴，可以放心點", "is_correct": False, "explanation": f".{self.target_tld} 雖然合法，但因為註冊便宜，常被騙子利用，要小心！", "feedback_icon": "❌"},
                {"id": "B", "text": f"這是一個比較少見的尾巴，要特別小心", "is_correct": True, "explanation": f"答對啦！.com、.tw 是常見的尾巴，但像 .{self.target_tld} 這種比較少見的，要特別小心！", "feedback_icon": "✅"},
                {"id": "C", "text": "尾巴不重要，只要網站有🔒小鎖頭就安全", "is_correct": False, "explanation": "🔒小鎖頭只代表「連線有加密」，不代表「網站內容是真的」，騙人的網站也可以有鎖頭", "feedback_icon": "❌"},
                {"id": "D", "text": "所有尾巴都一樣，不用在意", "is_correct": False, "explanation": "不同的尾巴代表不同的註冊規則，學會分辨很重要喔！", "feedback_icon": "❌"}
            ],
            "correct_answer_id": "B",
            "learning_point": f"不確定時，可以搜尋「.{self.target_tld} 域名 安全嗎」，或直接輸入「品牌名 + .com」訪問官方網站！",
            "difficulty": "easy"
        }
    
    def _generate_generic_safety_quiz(self) -> Dict:
        return {
            "enabled": True,
            "question": "🤔 如果你收到一個陌生連結，第一步應該做什麼？",
            "hint": "記住口訣：停、看、聽！",
            "type": "single_choice",
            "options": [
                {"id": "A", "text": "馬上點進去看看是什麼", "is_correct": False, "explanation": "直接點進去可能會中病毒、被騙個資，千萬不要！", "feedback_icon": "❌"},
                {"id": "B", "text": "先複製網址，用安全工具檢查一下", "is_correct": True, "explanation": "答對啦！先用安全工具檢查，是最保險的做法！", "feedback_icon": "✅"},
                {"id": "C", "text": "直接刪除，不管它", "is_correct": False, "explanation": "刪除是安全的，但如果這是重要通知，可能會錯過重要資訊", "feedback_icon": "❌"},
                {"id": "D", "text": "轉發給朋友一起看", "is_correct": False, "explanation": "轉發可能讓更多人遇到危險，要先確認安全再分享", "feedback_icon": "❌"}
            ],
            "correct_answer_id": "B",
            "learning_point": "安全口訣：「陌生連結不亂點，先查再按最安全」🔐",
            "difficulty": "easy"
        }
    
    def _generate_safety_tips(self) -> List[Dict]:
        recommendations = self.analysis.get('recommendations', [])
        if self.risk_source == "content":
            kid_tips_templates = [
                {"icon": "🚫", "tip": "不點開奇怪的連結", "why": "可能連到不適合小朋友的網站"},
                {"icon": "👀", "tip": "看到不舒服的內容要馬上關掉", "why": "保護自己的眼睛和心情"},
                {"icon": "👨‍👩‍👧", "tip": "遇到不清楚的網站告訴爸媽或老師", "why": "大人可以幫你判斷"},
                {"icon": "📱", "tip": "用網路時保持警覺", "why": "不是所有網站都適合小朋友"},
            ]
        else:
            kid_tips_templates = [
                {"icon": "🔍", "tip": "不隨便點陌生連結", "why": "陌生連結可能帶你到騙人的網站"},
                {"icon": "🔐", "tip": "不在不明網站輸入密碼", "why": "騙人的網站會偷走你的帳號"},
                {"icon": "👨‍👩‍👧", "tip": "有疑問時問爸媽或老師", "why": "大人經驗多，可以幫你判斷"},
                {"icon": "🔖", "tip": "把常用網站加入書籤", "why": "避免打錯網址跑到假網站"},
                {"icon": "🔄", "tip": "定期更新密碼", "why": "不同網站用不同密碼更安全"}
            ]
        
        tips = []
        for i, rec in enumerate(recommendations[:3]):
            clean_rec = re.sub(r'^[-•\d.\s]+', '', str(rec)).strip()
            if clean_rec:
                template = kid_tips_templates[i % len(kid_tips_templates)]
                tips.append({
                    "id": f"tip_{i+1}",
                    "icon": template["icon"],
                    "tip": self._simplify_text(clean_rec, 60),
                    "why": template["why"],
                    "action_text": "記住囉！"
                })
        
        while len(tips) < 4:
            template = kid_tips_templates[len(tips) % len(kid_tips_templates)]
            tips.append({
                "id": f"tip_{len(tips)+1}",
                "icon": template["icon"],
                "tip": template["tip"],
                "why": template["why"],
                "action_text": "記住囉！"
            })
        
        return tips
    
    def _generate_next_steps(self) -> List[Dict]:
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        if risk_level in ['critical', 'high']:
            return [
                {"action": "❌ 不要點擊此連結", "priority": "high", "icon": "🚫"},
                {"action": "🔍 用 VirusTotal 再檢查一次", "priority": "medium", "icon": "🔎", "link": "https://www.virustotal.com"},
                {"action": "👨‍👩‍👧 問爸媽或老師", "priority": "high", "icon": "🗣️"},
                {"action": "🌐 直接輸入官方網址訪問", "priority": "medium", "icon": "✅"}
            ]
        else:
            return [
                {"action": "🔍 保持警覺，仔細看網址", "priority": "medium", "icon": "👀"},
                {"action": "🔐 不要在不明網站輸入個資", "priority": "high", "icon": "🔒"},
                {"action": "📚 學習更多網路安全知識", "priority": "low", "icon": "🎓", "link": "https://phishingquiz.withgoogle.com"}
            ]


def generate_report_from_json(
    target_url: str,
    analysis_json_path: Path,
    cleaned_results_path: Path,
    output_path: Path
) -> Path:
    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    if 'choices' in raw_data:
        content = raw_data['choices'][0]['message']['content']
        analysis_result = json.loads(content)
    elif 'llm_analysis' in raw_data:
        analysis_result = raw_data['llm_analysis'] or raw_data
    else:
        analysis_result = raw_data
    with open(cleaned_results_path, 'r', encoding='utf-8') as f:
        cleaned_data = json.load(f)
    cleaned_results = cleaned_data.get('results', cleaned_data.get('cleaned_results', []))
    generator = ReportGenerator(target_url, analysis_result, cleaned_results)
    return generator.generate_report(output_path)
