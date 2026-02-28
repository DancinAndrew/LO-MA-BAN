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
    
    # 🎨 UI 圖示映射（前端可直接使用）
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
    
    # 🧒 兒童友善風險描述
    KID_RISK_TEXT = {
        "critical": "🚨 這個網站很可能是騙人的，千萬不要點進去！",
        "high": "⚠️ 這個網站看起來怪怪的，建議不要訪問",
        "medium": "🤔 這個網站有點可疑，要多小心一點",
        "low": "🙂 這個網站看起來還好，但上網還是要保持警覺喔",
        "inconclusive": "❓ 資訊不足，無法判斷，建議用其他工具再檢查"
    }
    
    def __init__(self, target_url: str, analysis_result: Dict, cleaned_results: List[Dict]):
        self.target_url = target_url.strip()
        self.analysis = analysis_result
        self.cleaned_results = cleaned_results
        self.timestamp = datetime.now().isoformat()
        
        # 提取域名特徵
        self.target_domain = self._extract_domain(target_url)
        self.target_tld = self._extract_tld(self.target_domain)
    
    def _extract_domain(self, url: str) -> str:
        """從 URL 提取域名"""
        url = url.strip().rstrip('/')
        url = re.sub(r'^https?://', '', url)
        return url.split('/')[0].split('?')[0]
    
    def _extract_tld(self, domain: str) -> str:
        """提取頂級域名"""
        parts = domain.split('.')
        return parts[-1] if len(parts) > 1 else ""
    
    def _simplify_text(self, text: str, max_length: int = 150) -> str:
        """簡化文字，適合兒童閱讀"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        # 替換專業術語為兒童友善用語
        replacements = {
            "釣魚網站": "騙人的假網站",
            "惡意軟體": "壞壞的程式",
            "SSL 證書": "安全鎖",
            "頂級域名": "網址的尾巴",
            "個資": "個人資料",
            "仿冒": "假裝成",
            "威脅情報": "安全檢查"
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        return text
    
    def generate_report(self, output_path: Path) -> Path:
        """生成 JSON 格式報告（前端可直接使用）"""
        report = {
            "report_metadata": self._generate_metadata(),
            "kid_friendly_summary": self._generate_kid_summary(),
            "evidence_cards": self._generate_evidence_cards(),
            "pattern_analysis": self._generate_pattern_analysis(),
            "interactive_quiz": self._generate_interactive_quiz(),
            "safety_tips": self._generate_safety_tips(),
            "next_steps": self._generate_next_steps(),
            "raw_analysis": self.analysis  # 保留原始分析供除錯
        }
        
        # 寫入 JSON 檔案
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📦 JSON 報告已儲存：{output_path}")
        return output_path
    
    def _generate_metadata(self) -> Dict:
        """生成報告基本資訊"""
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
        """生成兒童友善的風險摘要"""
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        risk_ui = self.RISK_UI.get(risk_level, self.RISK_UI['inconclusive'])
        
        # 提取或生成簡化解釋
        explanation = self.analysis.get('why_unsafe') or self.analysis.get('explanation', '')
        if not explanation or len(explanation) < 50:
            explanation = self._generate_default_kid_explanation()
        
        return {
            "title": f"{risk_ui['icon']} {risk_ui['label']}！",
            "simple_message": self.KID_RISK_TEXT.get(risk_level, ""),
            "short_explanation": self._simplify_text(explanation, 200),
            "emoji_reaction": risk_ui['icon'],
            "action_verb": "不要點" if risk_level in ['critical', 'high'] else "小心點"
        }
    
    def _generate_default_kid_explanation(self) -> str:
        """預設兒童版解釋（當 LLM 沒提供時）"""
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        if risk_level in ['critical', 'high']:
            return f"""這個網址有幾個「紅燈信號」🚦：
1. 網址的尾巴 (.{self.target_tld}) 很少見，很多騙人的網站喜歡用
2. 域名長長又複雜，正規網站通常簡單好記
3. 看起來很像知名品牌，但其實不是真的
所以我們要特別小心，不要隨便點進去或輸入個人資料喔！"""
        return "這個網址看起來沒有明顯危險，但上網時還是要保持警覺，不要隨便輸入個人資料喔！"
    
    def _generate_evidence_cards(self) -> List[Dict]:
        """生成證據卡片（前端可輪播顯示）"""
        evidence = self.analysis.get('evidence_summary') or self.analysis.get('evidence_analysis', [])
        cards = []
        
        # 證據圖示映射
        evidence_icons = {
            "域名": "🔤", "尾巴": "🌐", "品牌": "🏷️", 
            "可疑": "⚠️", "威脅": "🚨", "統計": "📊"
        }
        
        for i, ev in enumerate(evidence[:4]):
            clean_ev = re.sub(r'^[-•\d.\s]+', '', str(ev)).strip()
            if not clean_ev:
                continue
            
            # 自動判斷嚴重程度和圖示
            severity = "medium"
            icon = "🔍"
            if any(kw in clean_ev.lower() for kw in ["critical", "惡意", "threat", "danger"]):
                severity = "high"
                icon = "🚨"
            elif any(kw in clean_ev.lower() for kw in ["suspicious", "可疑", "warning"]):
                severity = "medium"
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
        """從證據文字提取簡短標題"""
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
        """生成域名模式分析（簡化版供前端顯示）"""
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
        """生成互動式選擇題（LLM 創意生成 + fallback）"""
        # 嘗試從 LLM 結果提取題目
        quiz_data = self.analysis.get('quiz') or self.analysis.get('interactive_quiz')
        
        # ✅ 防禦性檢查：確保 quiz_data 是 dict 且有 question
        if quiz_data and isinstance(quiz_data, dict) and quiz_data.get('question'):
            try:
                return self._render_llm_quiz(quiz_data)
            except Exception as e:
                logger.warning(f"⚠️ LLM 題目渲染失敗: {e}，使用 fallback 題目")
                return self._generate_fallback_quiz()
        
        # Fallback：根據域名特徵生成基礎題目
        return self._generate_fallback_quiz()
    
    def _render_llm_quiz(self, quiz_data: Dict) -> Dict:
        """渲染 LLM 生成的創意題目（含類型安全檢查）"""
        options = quiz_data.get('options', [])
        explanations = quiz_data.get('explanations', {})
        correct_answer = quiz_data.get('correct_answer', '')
        
        formatted_options = []
        option_ids = ['A', 'B', 'C', 'D']
        
        for i, opt in enumerate(options[:4]):
            # ✅ 處理 options 可能是 dict 或 string 的情況
            if isinstance(opt, dict):
                opt_id = opt.get('id', option_ids[i] if i < len(option_ids) else str(i+1))
                opt_text = opt.get('text', str(opt))
            else:
                opt_id = option_ids[i] if i < len(option_ids) else str(i+1)
                opt_text = str(opt)
            
            # ✅ 判斷是否為正確答案（支援 ID 或文字比對）
            is_correct = (str(opt_text) == str(correct_answer)) or (str(opt_id) == str(correct_answer))
            
            # ✅ 安全提取解釋（避免 unhashable type 錯誤）
            explanation = "再想想看～"
            if isinstance(explanations, dict):
                # 只使用 string 類型的 key 來查詢
                if isinstance(opt_id, str) and opt_id in explanations:
                    explanation = explanations[opt_id]
                elif isinstance(opt_text, str) and opt_text in explanations:
                    explanation = explanations[opt_text]
                # 嘗試轉換 key 為 string 再查詢
                elif str(opt_id) in explanations:
                    explanation = explanations[str(opt_id)]
            
            formatted_options.append({
                "id": str(opt_id),
                "text": self._simplify_text(str(opt_text), 100),
                "is_correct": is_correct,
                "explanation": self._simplify_text(str(explanation), 150),
                "feedback_icon": "✅" if is_correct else "❌"
            })
        
        # ✅ 安全提取正確答案 ID
        correct_answer_id = None
        if correct_answer:
            # 如果 correct_answer 是選項 ID（A/B/C/D）
            if str(correct_answer) in option_ids:
                correct_answer_id = str(correct_answer)
            else:
                # 嘗試從 formatted_options 中找到匹配的文字
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
        """Fallback 題目生成器（當 LLM 沒提供時）"""
        if any(brand in self.target_domain.lower() for brand in ['paypa', 'amazn', 'app1e', 'g0ogle', 'allegro']):
            return self._generate_brand_impersonation_quiz()
        elif self.target_tld.lower() in ['cfd', 'xyz', 'top', 'rest']:
            return self._generate_tld_quiz()
        else:
            return self._generate_generic_safety_quiz()
    
    def _generate_brand_impersonation_quiz(self) -> Dict:
        """品牌仿冒風格題目"""
        return {
            "enabled": True,
            "question": f"🔍 你覺得 `{self.target_domain}` 這個網址，哪裡「怪怪的」？",
            "hint": "仔細看每個字母喔，騙子喜歡用數字代替字母！",
            "type": "single_choice",
            "options": [
                {
                    "id": "A",
                    "text": "它跟真正的品牌網址長得好像，但有些地方不太一樣",
                    "is_correct": False,
                    "explanation": "只注意到「像」還不夠，要學會「逐字檢查每個字母」喔！",
                    "feedback_icon": "❌"
                },
                {
                    "id": "B",
                    "text": f"它的「尾巴」是 .{self.target_tld}，但正規網站通常是 .com",
                    "is_correct": False,
                    "explanation": f".{self.target_tld} 確實可疑，但騙子也會用 .com，不能只看尾巴",
                    "feedback_icon": "❌"
                },
                {
                    "id": "C",
                    "text": "它用數字或符號代替字母（例如用 1 代替 l，0 代替 o）",
                    "is_correct": True,
                    "explanation": "答對啦！騙人的網站常用數字代替字母來混淆你，要逐字檢查！",
                    "feedback_icon": "✅"
                },
                {
                    "id": "D",
                    "text": "以上都是！🎉",
                    "is_correct": False,
                    "explanation": "D 看起來很誘人，但這題要選「最關鍵」的那個喔！",
                    "feedback_icon": "❌"
                }
            ],
            "correct_answer_id": "C",
            "learning_point": "看到很像知名品牌的網址，一定要「逐字檢查」＋「確認官方網址」！",
            "difficulty": "medium"
        }
    
    def _generate_tld_quiz(self) -> Dict:
        """頂級域名風格題目"""
        return {
            "enabled": True,
            "question": f"🌐 網址的「尾巴」`.{self.target_tld}`，代表什麼意思呢？",
            "hint": "想想看，你常看到的網站尾巴是什麼？",
            "type": "single_choice",
            "options": [
                {
                    "id": "A",
                    "text": "這是一個很常見、很安全的尾巴，可以放心點",
                    "is_correct": False,
                    "explanation": f".{self.target_tld} 雖然合法，但因為註冊便宜，常被騙子利用，要小心！",
                    "feedback_icon": "❌"
                },
                {
                    "id": "B",
                    "text": f"這是一個比較少見的尾巴，要特別小心",
                    "is_correct": True,
                    "explanation": f"答對啦！.com、.tw 是常見的尾巴，但像 .{self.target_tld} 這種比較少見的，要特別小心！",
                    "feedback_icon": "✅"
                },
                {
                    "id": "C",
                    "text": "尾巴不重要，只要網站有🔒小鎖頭就安全",
                    "is_correct": False,
                    "explanation": "🔒小鎖頭只代表「連線有加密」，不代表「網站內容是真的」，騙人的網站也可以有鎖頭",
                    "feedback_icon": "❌"
                },
                {
                    "id": "D",
                    "text": "所有尾巴都一樣，不用在意",
                    "is_correct": False,
                    "explanation": "不同的尾巴代表不同的註冊規則，學會分辨很重要喔！",
                    "feedback_icon": "❌"
                }
            ],
            "correct_answer_id": "B",
            "learning_point": f"不確定時，可以搜尋「.{self.target_tld} 域名 安全嗎」，或直接輸入「品牌名 + .com」訪問官方網站！",
            "difficulty": "easy"
        }
    
    def _generate_generic_safety_quiz(self) -> Dict:
        """通用安全意識題目"""
        return {
            "enabled": True,
            "question": "🤔 如果你收到一個陌生連結，第一步應該做什麼？",
            "hint": "記住口訣：停、看、聽！",
            "type": "single_choice",
            "options": [
                {
                    "id": "A",
                    "text": "馬上點進去看看是什麼",
                    "is_correct": False,
                    "explanation": "直接點進去可能會中病毒、被騙個資，千萬不要！",
                    "feedback_icon": "❌"
                },
                {
                    "id": "B",
                    "text": "先複製網址，用安全工具檢查一下",
                    "is_correct": True,
                    "explanation": "答對啦！先用安全工具檢查，是最保險的做法！",
                    "feedback_icon": "✅"
                },
                {
                    "id": "C",
                    "text": "直接刪除，不管它",
                    "is_correct": False,
                    "explanation": "刪除是安全的，但如果這是重要通知，可能會錯過重要資訊",
                    "feedback_icon": "❌"
                },
                {
                    "id": "D",
                    "text": "轉發給朋友一起看",
                    "is_correct": False,
                    "explanation": "轉發可能讓更多人遇到危險，要先確認安全再分享",
                    "feedback_icon": "❌"
                }
            ],
            "correct_answer_id": "B",
            "learning_point": "安全口訣：「陌生連結不亂點，先查再按最安全」🔐",
            "difficulty": "easy"
        }
    
    def _generate_safety_tips(self) -> List[Dict]:
        """生成安全小撇步（前端可卡片輪播）"""
        recommendations = self.analysis.get('recommendations', [])
        
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
        """生成下一步行動建議"""
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


# ========== 相容性函數（供舊版 main.py 呼叫）==========
def generate_report_from_json(
    target_url: str,
    analysis_json_path: Path,
    cleaned_results_path: Path,
    output_path: Path
) -> Path:
    """從 JSON 檔案生成報告（相容舊版介面）"""
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