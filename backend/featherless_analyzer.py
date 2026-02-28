#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Featherless AI Analyzer: 將安全 API 的警告結果送給 LLM 進行深度分析
"""
import json
import requests
import logging
from typing import Dict, List, Optional
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)

class FeatherlessAnalyzer:
    """將安全警告送給 Featherless AI 進行解釋與建議生成"""
    
    def __init__(self):
        self.api_url = Config.FEATHERLESS_API_URL
        self.api_key = Config.FEATHERLESS_API_KEY
        self.model = Config.FEATHERLESS_MODEL
        self.timeout = 120
    
    def build_analysis_prompt(self, target_url: str, security_results: Dict) -> List[Dict]:
        """
        建構給 LLM 的分析 prompt（含安全檢查）
        """
        # 提取關鍵警告資訊
        critical_flags = security_results.get('critical_flags', [])
        warnings = security_results.get('warnings', [])
        raw_results = security_results.get('raw_results', [])
        
        # 🔧 安全提取證據（避免 unhashable type 錯誤）
        evidence_items = []
        for result in raw_results:
            if not result.get('found'):
                continue
            source = result['source']
            
            # threat_type
            if result.get('threat_type'):
                evidence_items.append(f"• [{source}] 威脅類型: {result['threat_type']}")
            
            # categories（關鍵修正）
            categories = result.get('categories')
            if categories:
                if isinstance(categories, list):
                    cats = categories[:3]
                    evidence_items.append(f"• [{source}] 分類: {', '.join(cats)}")
                elif isinstance(categories, dict):
                    cats = list(categories.keys())[:3]
                    evidence_items.append(f"• [{source}] 分類: {', '.join(cats)}")
            
            # stats
            stats = result.get('stats')
            if stats and isinstance(stats, dict):
                mal = stats.get('malicious', 0)
                sus = stats.get('suspicious', 0)
                if mal > 0 or sus > 0:
                    evidence_items.append(f"• [{source}] 惡意:{mal} 可疑:{sus}")
            
            # tags
            tags = result.get('tags')
            if tags:
                tag_list = tags if isinstance(tags, list) else [str(tags)]
                evidence_items.append(f"• [{source}] 標籤: {', '.join(tag_list[:3])}")
        
        # 系統提示（18 歲以下兒童輔導員視角）
        system_prompt = """你是一位關心 18 歲以下兒童網路安全的輔導員，用親切、易懂的方式幫助孩子理解網路風險。

        請基於提供的威脅情報平台檢測結果，分析目標網址的風險。用「小朋友聽得懂」的語言解釋，避免太多專業術語。

        輸出要求：
        1. 使用結構化 JSON 格式
        2. 用簡單的話解釋為什麼這個網址有危險
        3. 提供具體、實用的建議（適合兒童與家長）
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
        
        # 用戶提示
        critical_text = "\n".join(f"- {f['source']}: {f.get('threat_type') or '未知威脅'}" for f in critical_flags) or "無重大警告"
        warning_text = "\n".join(f"- {w['source']}: {str(w.get('reason', '未知原因'))[:100]}" for w in warnings) or "無次要警告"
        evidence_text = "\n".join(evidence_items) or "• 未偵測到具體威脅指標"
        
        user_content = f"""請分析以下網址的安全性：

    🎯 目標網址: {target_url}

    📊 威脅情報平台檢測結果:
    - 整體風險評估: {security_results.get('overall_risk', 'unknown')}
    - 信心程度: {security_results.get('confidence', 'unknown')}
    - 風險分數: {security_results.get('risk_score', 'N/A')}/100
    - 已檢查來源數: {security_results.get('checked_sources', 0)}

    🚨 關鍵警告 ({len(critical_flags)} 項):
    {critical_text}

    ⚠️ 次要警告 ({len(warnings)} 項):
    {warning_text}

    🔍 詳細證據:
    {evidence_text}

    請基於以上資訊，輸出結構化的 JSON 分析結果。"""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    
    def analyze(self, target_url: str, security_results: Dict) -> Dict:
        """
        呼叫 Featherless API 進行深度分析
        """
        logger.info("🤖 開始 Featherless AI 深度分析...")
        
        messages = self.build_analysis_prompt(target_url, security_results)
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # 低溫度確保輸出穩定
            "max_tokens": 800,
            "top_p": 0.9,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stream": False,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 解析 LLM 回應
            if 'choices' in result:
                content = result['choices'][0]['message']['content']
                analysis = json.loads(content)
                analysis['llm_metadata'] = {
                    "model": self.model,
                    "usage": result.get('usage', {})
                }
                logger.info("✅ Featherless 分析完成")
                return analysis
            else:
                logger.error(f"Unexpected response format: {result}")
                return self._fallback_analysis(security_results)
                
        except requests.RequestException as e:
            logger.error(f"Featherless API request failed: {e}")
            return self._fallback_analysis(security_results)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._fallback_analysis(security_results)

    def build_content_risk_prompt(
        self, target_url: str, page_content: str, content_classification: Dict
    ) -> List[Dict]:
        """
        建構「內容風險」（情色、暴力等不適合兒童）的分析 prompt
        輸出格式與 build_analysis_prompt 一致，供 ReportGenerator 使用
        """
        labels = content_classification.get("labels", [])
        primary = content_classification.get("primary_label", "不明")
        explanation = content_classification.get("explanation", "")

        system_prompt = """你是一位關心 18 歲以下兒童網路安全的輔導員。這次要分析的是「不適合兒童的網頁內容」（如色情、暴力、血腥等），而非釣魚詐騙。

請用親切、易懂的方式，幫助孩子理解為什麼某些網站不適合他們瀏覽，以及如何保護自己。避免嚇唬，用正面、教育的口吻。

輸出 JSON 格式（與資安分析相同結構）：
{
  "risk_level": "high",
  "confidence": "high/medium/low",
  "risk_score": 70-100,
  "threat_summary": "一句話總結（例如：此網頁包含不適合兒童的內容）",
  "evidence_analysis": ["內容證據1", "內容證據2", ...],
  "why_unsafe": "詳細解釋為什麼不適合兒童（200-300字，用小朋友聽得懂的語言）",
  "technical_details": {
    "detected_by": ["內容分析"],
    "threat_types": ["色情", "暴力", ...],
    "indicators": []
  },
  "content_risk_type": "色情/暴力/其他不當內容",
  "user_warnings": ["警告1", "警告2", ...],
  "recommendations": ["建議1", "建議2", ...],
  "uncertainties": []
}

並生成創意選擇題（quiz 欄位），幫助小朋友學習「如何分辨不適當的網站」或「遇到不當內容該怎麼辦」。格式與資安分析相同。"""

        content_preview = (page_content[:2000] + "...") if len(page_content) > 2000 else page_content

        user_content = f"""請分析以下網頁的「內容適齡性」：

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

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def analyze_content_risk(
        self, target_url: str, page_content: str, content_classification: Dict
    ) -> Dict:
        """
        針對「內容風險」（情色、暴力等）呼叫 Featherless 進行深度分析
        回傳與 analyze() 相同的 JSON 結構，供 ReportGenerator 使用
        """
        logger.info("🤖 開始 Featherless 內容風險分析（兒童輔導員模式）...")
        messages = self.build_content_risk_prompt(target_url, page_content, content_classification)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1000,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.post(
                self.api_url, headers=headers, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
                analysis = json.loads(content)
                analysis["llm_metadata"] = {"model": self.model, "usage": result.get("usage", {})}
                analysis["content_risk_type"] = content_classification.get("primary_label", "不當內容")
                logger.info("✅ Featherless 內容風險分析完成")
                return analysis
        except Exception as e:
            logger.error(f"Featherless 內容風險分析失敗: {e}")
        return self._fallback_content_risk(content_classification)

    def _fallback_content_risk(self, content_classification: Dict) -> Dict:
        """內容風險分析的降級輸出"""
        primary = content_classification.get("primary_label", "不當內容")
        return {
            "risk_level": "high",
            "confidence": "medium",
            "risk_score": 80,
            "threat_summary": f"此網頁可能包含不適合兒童的內容（{primary}）",
            "evidence_analysis": [f"內容分類：{primary}"],
            "why_unsafe": f"根據分析，這個網頁可能含有{primary}等內容，不適合 18 歲以下的兒童與青少年瀏覽。建議不要點擊，如有疑問可與家長或老師討論。",
            "technical_details": {
                "detected_by": ["內容分析"],
                "threat_types": content_classification.get("labels", [primary]),
                "indicators": [],
            },
            "content_risk_type": primary,
            "user_warnings": ["此網站可能含有不適合兒童的內容"],
            "recommendations": [
                "不要點擊或瀏覽此連結",
                "如不小心點進去，請立即關閉並告訴家長或老師",
                "使用網路時保持警覺，遇到奇怪內容要及時求助",
            ],
            "uncertainties": [],
            "fallback_mode": True,
        }

    def _fallback_analysis(self, security_results: Dict) -> Dict:
        """
        當 LLM 呼叫失敗時的降級處理
        """
        risk = security_results.get('overall_risk', 'inconclusive')
        critical = security_results.get('critical_flags', [])
        
        return {
            "risk_level": risk,
            "confidence": "low",
            "risk_score": security_results.get('risk_score', 50),
            "threat_summary": "無法進行深度分析，請參考原始檢測結果",
            "evidence_analysis": [f"• {c['source']}: {c.get('threat_type', '未知')}" for c in critical],
            "why_unsafe": "分析服務暫時無法提供詳細說明。建議小朋友先不要點擊這個連結，可以請爸媽或老師幫忙用其他安全工具再檢查一次喔！",
            "technical_details": {
                "detected_by": [c['source'] for c in critical],
                "threat_types": [c.get('threat_type') for c in critical if c.get('threat_type')],
                "indicators": []
            },
            "user_warnings": ["⚠️ 分析服務暫時不可用，請謹慎訪問此網址"],
            "recommendations": [
                "避免在此網站輸入任何個人資訊",
                "使用其他安全工具進行二次驗證",
                "如已輸入敏感資料，立即更改密碼"
            ],
            "uncertainties": ["LLM 分析服務呼叫失敗"],
            "fallback_mode": True
        }