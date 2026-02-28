#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
報告生成器：將 LLM 分析結果轉換為人類可讀的 Markdown 報告
通用模板，不寫死特定品牌或域名特徵
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """生成通用風格的 Markdown 分析報告"""
    
    RISK_ICONS = {
        "critical": "🔴",
        "high": "🔴",
        "medium": "🟠",
        "low": "🟡",
        "inconclusive": "⚪"
    }
    
    CONFIDENCE_ICONS = {
        "high": "✅",
        "medium": "⚠️",
        "low": "❓"
    }
    
    def __init__(self, target_url: str, analysis_result: Dict, cleaned_results: List[Dict]):
        self.target_url = target_url
        self.analysis = analysis_result
        self.cleaned_results = cleaned_results
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 動態提取目標網址特徵
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
    
    def _get_risk_level_text(self, risk_level: str) -> str:
        """根據風險等級返回描述文字"""
        texts = {
            "critical": "極高風險 - 強烈建議避免訪問",
            "high": "高風險 - 建議避免訪問",
            "medium": "中等風險 - 需謹慎對待",
            "low": "低風險 - 相對安全但仍需留意",
            "inconclusive": "無法判斷 - 證據不足"
        }
        return texts.get(risk_level, "風險等級未知")
    
    def generate_report(self, output_path: Path) -> Path:
        """生成完整 Markdown 報告"""
        report = []
        
        # ========== 標題 ==========
        report.append("# 🔍 網站安全分析報告\n")
        report.append(f"**分析時間**: {self.timestamp}\n")
        report.append(f"**目標網址**: `{self.target_url}`\n")
        report.append(f"**目標域名**: `{self.target_domain}`\n")
        report.append(f"**頂級域名**: `.{self.target_tld}`\n")
        
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        confidence = self.analysis.get('confidence', 'low')
        risk_score = self.analysis.get('risk_score', 'N/A')
        
        report.append(f"**風險等級**: {self.RISK_ICONS.get(risk_level, '⚪')} {risk_level.upper()}\n")
        report.append(f"**信心程度**: {self.CONFIDENCE_ICONS.get(confidence, '❓')} {confidence}\n")
        report.append(f"**風險分數**: {risk_score}/100\n")
        report.append("\n---\n")
        
        # ========== 風險警告（僅高風險時顯示）==========
        if risk_level in ['critical', 'high']:
            report.append(self._generate_warning_section())
            report.append("\n---\n")
        
        # ========== 證據摘要 ==========
        report.append(self._generate_evidence_section())
        report.append("\n---\n")
        
        # ========== 域名模式分析 ==========
        report.append(self._generate_pattern_section())
        report.append("\n---\n")
        
        # ========== 相似案例對比 ==========
        report.append(self._generate_similarities_section())
        report.append("\n---\n")
        
        # ========== 詳細解釋 ==========
        report.append(self._generate_explanation_section())
        report.append("\n---\n")
        
        # ========== 實務建議 ==========
        report.append(self._generate_recommendations_section())
        
        # 寫入檔案
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(report)
        output_path.write_text(content, encoding='utf-8')
        
        logger.info(f"💾 報告已儲存至：{output_path}")
        return output_path
    
    def _generate_warning_section(self) -> str:
        """生成風險警告區塊"""
        warnings = self.analysis.get('warnings', [])
        
        section = [
            "## 🚨 風險警告",
            "",
            "> ⚠️ **該網址具備「多重高風險指標」，應視為「極可能為釣魚或詐騙網站」處理。**",
            "",
            "### 請避免：",
        ]
        
        if warnings:
            for warning in warnings[:5]:
                # 清理警告文字，移除重複的「目標網址」
                clean_warning = warning.replace("目標網址", "此網站").strip()
                if clean_warning.startswith('-'):
                    clean_warning = clean_warning[1:].strip()
                section.append(f"- ❌ {clean_warning}")
        else:
            # 預設警告
            section.extend([
                "- ❌ 點擊此連結",
                "- ❌ 在此網站輸入帳號、密碼、信用卡或個人資料",
                "- ❌ 掃描此網站提供的 QR Code 或下載附件",
                "- ❌ 允許此網站的通知權限",
            ])
        
        return "\n".join(section)
    
    def _generate_evidence_section(self) -> str:
        """生成證據摘要區塊"""
        evidence = self.analysis.get('evidence_summary', [])
        
        section = [
            "## 📊 關鍵證據",
            "",
        ]
        
        if evidence:
            for i, ev in enumerate(evidence[:5], 1):
                # 清理證據文字
                clean_ev = ev.strip()
                if clean_ev.startswith('- ') or clean_ev.startswith('• '):
                    clean_ev = clean_ev[2:]
                section.append(f"{i}. {clean_ev}")
        else:
            section.append("⚠️ 未提供具體證據摘要")
        
        return "\n".join(section)
    
    def _generate_pattern_section(self) -> str:
        """生成域名模式分析區塊（通用版，不寫死特定品牌）"""
        
        # 統計同 TLD 域名風險
        same_tld_sites = [r for r in self.cleaned_results if r.get('tld') == self.target_tld]
        same_tld_low_trust = len([r for r in same_tld_sites if r['trust_indicator'] in ['very_low', 'low']])
        
        # 已知高風險 TLD 列表
        high_risk_tlds = ['cfd', 'top', 'rest', 'xyz', 'loan', 'click', 'work', 'date', 'racing']
        is_high_risk_tld = self.target_tld.lower() in high_risk_tlds
        
        section = [
            "## 📈 域名風險模式分析",
            "",
        ]
        
        # 如果有同 TLD 的搜索結果，顯示表格
        if same_tld_sites:
            section.extend([
                f"### `.{self.target_tld}` 域名在安全資料庫的風險模式",
                "",
                "| 網站範例 | 信任評級 | 關鍵風險指標 |",
                "|----------|----------|--------------|",
            ])
            
            for r in same_tld_sites[:5]:
                trust_icon = "🔴" if r['trust_indicator'] in ['very_low', 'low'] else "🟢"
                risks = ", ".join(r['key_risks'][:3]) if r['key_risks'] else "無明顯風險"
                section.append(f"| `{r['domain']}` | {trust_icon} {r['trust_indicator']} | {risks} |")
            
            section.append("")
        
        # 動態生成特徵分析表格
        section.extend([
            "### 🎯 目標網址特徵分析",
            "",
            "| 特徵 | 分析結果 | 風險推論 |",
            "|------|----------|----------|",
        ])
        
        # TLD 風險
        if same_tld_sites:
            tld_evidence = f"{same_tld_low_trust}/{len(same_tld_sites)} 個 .{self.target_tld} 案例被標記為低信任"
            tld_risk = "🔴 高度可疑" if same_tld_low_trust > len(same_tld_sites) * 0.5 else "⚠️ 需留意"
        elif is_high_risk_tld:
            tld_evidence = f".{self.target_tld} 是已知高風險頂級域名"
            tld_risk = "🔴 高度可疑"
        else:
            tld_evidence = f".{self.target_tld} 是較少見的頂級域名"
            tld_risk = "⚠️ 需留意"
        
        section.append(f"| **頂級域名 (.TLD)** | {tld_evidence} | {tld_risk} |")
        
        # 域名長度/複雜度
        domain_complexity = "複雜" if len(self.target_domain) > 30 else "正常"
        has_numbers = any(c.isdigit() for c in self.target_domain)
        has_hyphens = '-' in self.target_domain
        complexity_risk = "⚠️ 需留意" if (has_numbers or has_hyphens or len(self.target_domain) > 30) else "🟢 正常"
        section.append(f"| **域名結構** | 長度={len(self.target_domain)}, 含數字={has_numbers}, 含連字號={has_hyphens} | {complexity_risk} |")
        
        # 短連結服務
        shortener_services = ['t.co', 'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly']
        is_shortener = any(s in self.target_url for s in shortener_services)
        if is_shortener:
            section.append(f"| **短連結服務** | 使用短連結服務（真實目標網址被隱藏） | 🔴 高度可疑 |")
        
        # 品牌仿冒（動態檢測，不寫死特定品牌）
        known_brands = ['allegro', 'amazon', 'paypal', 'apple', 'google', 'microsoft', 'facebook', 'netflix', 'spotify']
        brand_matches = [b for b in known_brands if b in self.target_domain.lower()]
        if brand_matches:
            section.append(f"| **品牌相似度** | 域名包含知名品牌關鍵字：{', '.join(brand_matches)} | 🔴 高度可疑 |")
        else:
            section.append(f"| **品牌相似度** | 未發現與知名品牌的直接相似性 | 🟢 正常 |")
        
        # SSL/HTTPS
        is_https = self.target_url.startswith('https://')
        ssl_risk = "🟢 正常" if is_https else "⚠️ 需留意（無 HTTPS）"
        section.append(f"| **HTTPS 加密** | {'有' if is_https else '無'} | {ssl_risk} |")
        
        return "\n".join(section)
    
    def _generate_similarities_section(self) -> str:
        """生成相似案例對比區塊（通用版）"""
        similarities = self.analysis.get('similarities', [])
        
        section = [
            "## 🔗 與已知釣魚網站的相似處",
            "",
        ]
        
        if similarities:
            for sim in similarities[:5]:
                clean_sim = sim.strip()
                if clean_sim.startswith('- '):
                    clean_sim = clean_sim[2:]
                section.append(f"- {clean_sim}")
        else:
            # 根據實際特徵生成預設內容
            section.append("**分析結果未提供具體相似處，以下為基於域名特徵的推論：**")
            section.append("")
            
            if self.target_tld.lower() in ['cfd', 'top', 'rest', 'xyz']:
                section.append(f"- 使用非常規頂級域名 (.{self.target_tld})，此類域名常見於釣魚網站")
            
            if len(self.target_domain) > 30:
                section.append("- 域名長度較長，可能用於混淆視聽")
            
            if 't.co' in self.target_url or 'bit.ly' in self.target_url:
                section.append("- 使用短連結服務，隱藏真實目標網址")
            
            if not section[-1].startswith('-'):
                section.append("- 暫未發現與已知釣魚網站的直接相似處")
        
        return "\n".join(section)
    
    def _generate_explanation_section(self) -> str:
        """生成詳細解釋區塊"""
        explanation = self.analysis.get('explanation', '')
        
        section = [
            "## 📝 詳細分析解釋",
            "",
        ]
        
        if explanation:
            # 清理解釋文字
            clean_explanation = explanation.strip()
            # 如果解釋太短，補充預設內容
            if len(clean_explanation) < 50:
                section.append(self._generate_default_explanation())
            else:
                section.append(clean_explanation)
        else:
            section.append(self._generate_default_explanation())
        
        return "\n".join(section)
    
    def _generate_default_explanation(self) -> str:
        """生成預設解釋（當 LLM 未提供時）"""
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        
        if risk_level in ['critical', 'high']:
            return f"""根據提供的安全搜尋結果和目標網址的特徵分析，我們得出以下結論：

1. **頂級域名風險**：.{self.target_tld} 是非常規頂級域名，在安全資料庫中多數同類域名被標記為低信任或不安全。

2. **域名結構**：目標域名的結構特徵（長度、數字、連字號等）與典型釣魚網站模式相符。

3. **間接證據**：雖然目標網址本身可能不在搜索結果中，但基於相似域名模式和風險特徵的間接推論，我們認為風險等級較高。

建議用戶在訪問此網站前保持警惕，並通過官方渠道驗證網站的真實性。"""
        
        elif risk_level == 'inconclusive':
            return f"""根據提供的安全搜尋結果，我們無法對目標網址做出明確的風險判斷：

1. **證據不足**：搜索結果中缺乏與目標網址直接相關的數據。

2. **頂級域名**：.{self.target_tld} 是較少見的頂級域名，但不足以單獨作為風險判斷依據。

3. **建議**：建議用戶通過其他安全工具（如 VirusTotal、ScamAdviser）進行二次驗證，或直接通過官方渠道訪問相關服務。"""
        
        else:
            return f"""根據分析結果，目標網址的風險等級為{risk_level}。建議用戶保持基本的安全意識，避免在不明網站輸入敏感信息。"""
    
    def _generate_recommendations_section(self) -> str:
        """生成實務建議區塊（通用版）"""
        recommendations = self.analysis.get('recommendations', [])
        risk_level = self.analysis.get('risk_level', 'inconclusive')
        
        section = [
            "## 🛡️ 實務建議",
            "",
            "### 建議行動：",
            "",
        ]
        
        if recommendations:
            for rec in recommendations[:5]:
                clean_rec = rec.strip()
                if clean_rec.startswith('- '):
                    clean_rec = clean_rec[2:]
                section.append(f"- ✅ {clean_rec}")
        else:
            # 根據風險等級生成預設建議
            if risk_level in ['critical', 'high']:
                section.extend([
                    "- ✅ 避免點擊此連結或訪問此網站",
                    "- ✅ 不要在此網站輸入任何敏感信息（帳號、密碼、信用卡等）",
                    "- ✅ 如已輸入個資，立即更改密碼並聯絡相關機構",
                    "- ✅ 通過官方渠道驗證網站真實性",
                    "- ✅ 向相關機構報告此可疑網址",
                ])
            elif risk_level == 'medium':
                section.extend([
                    "- ✅ 謹慎對待此網站，避免輸入敏感信息",
                    "- ✅ 通過其他安全工具進行二次驗證",
                    "- ✅ 優先使用官方渠道進行交易或溝通",
                ])
            else:
                section.extend([
                    "- ✅ 保持基本安全意識",
                    "- ✅ 定期更新密碼和安全設定",
                    "- ✅ 使用安全軟體保護設備",
                ])
        
        section.extend([
            "",
            "### 如需進一步驗證：",
            "",
            "- [ScamAdviser](https://www.scamadviser.com)",
            "- [VirusTotal](https://www.virustotal.com)",
            "- [PhishTank](https://www.phishtank.com)",
            "- [Google Safe Browsing](https://transparencyreport.google.com/safe-browsing/search)",
        ])
        
        return "\n".join(section)


def generate_report_from_json(
    target_url: str,
    analysis_json_path: Path,
    cleaned_results_path: Path,
    output_path: Path
) -> Path:
    """從 JSON 檔案生成報告"""
    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    # 提取 LLM 回應內容
    if 'choices' in analysis_data:
        content = analysis_data['choices'][0]['message']['content']
        analysis_result = json.loads(content)
    else:
        analysis_result = analysis_data
    
    with open(cleaned_results_path, 'r', encoding='utf-8') as f:
        cleaned_data = json.load(f)
        cleaned_results = cleaned_data.get('results', [])
    
    generator = ReportGenerator(target_url, analysis_result, cleaned_results)
    return generator.generate_report(output_path)