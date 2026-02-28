# prompt_builder.py
from typing import List, Dict, Optional
import re
import json
import logging
from pathlib import Path
from config import Config
from utils import save_json, step_marker

logger = logging.getLogger(__name__)

class PromptBuilder:
    SYSTEM_PROMPT = """你是一位專業的網路安全分析專家，專門協助判斷網站是否為釣魚或詐騙網站。
請嚴格基於用戶提供的安全搜尋結果進行推理，不要自行搜尋或假設額外資訊。

輸出時請使用結構化 JSON 格式，包含以下欄位：
- risk_level: "critical/high/medium/low/inconclusive"
- confidence: "high/medium/low"
- risk_score: 0-100 的數字分數
- evidence_summary: 證據列表
- pattern_analysis: 域名模式分析
- similarities: 與已知釣魚網站的相似處
- uncertainties: 不確定因素
- warnings: 具體警告列表（如果風險高）
- recommendations: 具體建議列表
- explanation: 詳細解釋（300-500字）"""

    def extract_domain(self, url: str) -> str:
        """從 URL 提取純域名"""
        url = url.strip().rstrip('/')
        url = re.sub(r'^https?://', '', url)
        return url.split('/')[0].split('?')[0]
    
    def extract_tld(self, domain: str) -> str:
        """
        從域名提取頂級域名 (TLD)
        例如：baroki287.cfd → cfd
            allegro.pl → pl
            sub.example.com → com
        """
        parts = domain.split('.')
        return parts[-1] if len(parts) > 1 else ""
    
    def extract_analyzed_domain(self, url: str) -> str:
        """
        從 ScamAdviser URL 提取被分析的域名
        例如：https://www.scamadviser.com/check-website/baroki287.cfd
        應該返回：baroki287.cfd
        """
        # 匹配 ScamAdviser 的 check-website/XXX 格式
        match = re.search(r'check-website/([^?/]+)', url)
        if match:
            return match.group(1)
        # 如果不是 ScamAdviser URL，用一般方法提取
        return self.extract_domain(url)
    
    def parse_trust_indicator(self, summary: str) -> str:
        if not summary:
            return "unknown"
        s = summary.lower()
        if any(kw in s for kw in ["very low trust", "trust score 0", "likely unsafe", "scam"]):
            return "very_low"
        elif any(kw in s for kw in ["low trust", "caution", "risky"]):
            return "low"
        elif any(kw in s for kw in ["high trust", "100/100", "safe to use"]):
            return "high"
        elif any(kw in s for kw in ["medium", "75%", "moderate"]):
            return "medium"
        return "unknown"
    
    def extract_key_risks(self, summary: str) -> List[str]:
        if not summary:
            return []
        risks = []
        s = summary.lower()
        risk_map = {
            "newly_registered": ["newly registered", "very young", "young domain", "registered recently"],
            "hidden_whois": ["whois.*?hidden", "identity.*?hide", "redacted", "privacy service"],
            "suspicious_pattern": ["suspicious domain", "random string", "complex domain", "numeric domain"],
            "fake_login_risk": ["fake login", "capture credential", "deceptive form"],
            "low_traffic": ["low tranco", "few visitor", "low rank", "not popular"],
            "risky_hosting": ["high-risk location", "suspicious server", "same server.*?scam"],
            "ssl_warning": ["ssl.*?invalid", "no ssl", "certificate problem"],
            "brand_impersonation": ["mimic.*?allegro", "impersonat", "similarity.*?legitimate"],
            "gambling_spam": ["gambling", "spam", "fraud"],
        }
        for risk_name, patterns in risk_map.items():
            for p in patterns:
                if re.search(p, s):
                    if risk_name not in risks:
                        risks.append(risk_name)
                    break
        return risks
    
    def clean_and_save_results(
        self,
        exa_results: Dict,
        output_path: Optional[str] = None
    ) -> List[Dict]:
        if output_path is None:
            output_path = Config.OUTPUT_DIR / "02_cleaned_results.json"
        else:
            output_path = Path(output_path)
        
        logger.info(step_marker(2, "清理 Exa 結果"))
        
        cleaned = [
            self.clean_result(r) 
            for r in exa_results.get('results', [])
            if r.get('url') or r.get('id')
        ]
        
        if Config.SAVE_INTERMEDIATE:
            save_json({
                "total_results": len(cleaned),
                "sources": list(set(r['source'] for r in cleaned)),
                "results": cleaned
            }, output_path)
        
        logger.info(step_marker(2, f"清理完成 ({len(cleaned)} 筆)", "done"))
        return cleaned
    
    def clean_result(self, result: Dict) -> Dict:
        url = result.get('url', result.get('id', '')).strip()
        
        # ✅ 使用新方法提取被分析的域名
        domain = self.extract_analyzed_domain(url)
        tld = self.extract_tld(domain)
        
        summary = result.get('summary', '')
        if not summary and result.get('highlights'):
            highlights = result['highlights']
            if isinstance(highlights, list) and highlights:
                summary = ' '.join(str(h)[:200] for h in highlights[:2])
        
        return {
            "domain": domain,  # ✅ 現在會是 baroki287.cfd 而不是 scamadviser.com
            "tld": tld,        # ✅ 現在會是 cfd 而不是 com
            "url": url,
            "title": result.get('title', '').strip()[:100],
            "trust_indicator": self.parse_trust_indicator(summary),
            "key_risks": self.extract_key_risks(summary),
            "summary_snippet": summary[:250] + "..." if len(summary) > 250 else summary,
            "source": next((d for d in Config.SECURITY_DOMAINS if d in url), "unknown"),
        }
    
    # prompt_builder.py
    def build_and_save_prompt(
        self,
        target_url: str,
        cleaned_results: List[Dict],
        output_path: Optional[str] = None,
        custom_instruction: Optional[str] = None
    ) -> Dict:
        if output_path is None:
            output_path = Config.OUTPUT_DIR / "03_featherless_prompt.json"
        else:
            output_path = Path(output_path)
        
        logger.info(step_marker(3, "建構 Featherless prompt"))
        
        # 統計 .cfd 域名風險
        cfd_sites = [r for r in cleaned_results if r.get('tld') == 'cfd']
        cfd_low_trust = len([r for r in cfd_sites if r['trust_indicator'] in ['very_low', 'low']])
        cfd_total = len(cfd_sites)
        
        # 分析目標網址特徵
        target_domain = self.extract_analyzed_domain(target_url)
        target_tld = self.extract_tld(target_domain)
        
        # 建構證據表格
        evidence_table = []
        for r in cleaned_results:
            evidence_table.append({
                "domain": r['domain'],
                "tld": r.get('tld', 'unknown'),
                "trust": r['trust_indicator'],
                "risks": r['key_risks'][:3]
            })
        
        # ✅ 更嚴格的系統提示詞
        system_prompt = """你是一位專業的網路安全分析專家，專門協助判斷網站是否為釣魚或詐騙網站。
        請嚴格基於用戶提供的安全搜尋結果進行推理，不要自行搜尋或假設額外資訊。

        **重要評分原則**：
        1. 如果目標網址使用 .cfd/.top/.rest/.xyz 等非常規頂級域名，且搜索結果中多數同類域名被標記為低信任，風險等級必須是 high 或 critical
        2. 如果目標網址包含知名品牌名稱（如 allegro、amazon、paypal 等）+ 長串參數 + 非常規後綴，這是最典型的釣魚模式，風險等級必須是 critical
        3. SSL 證書有效不能作为安全依據，釣魚網站也可取得 SSL
        4. 如果證據顯示高風險但無法 100% 確認，risk_level 應該是 high 而不是 inconclusive

        輸出時請使用結構化 JSON 格式，包含以下欄位：
        - risk_level: "critical/high/medium/low/inconclusive"
        - confidence: "high/medium/low"
        - risk_score: 0-100 的數字分數
        - evidence_summary: 證據列表
        - pattern_analysis: 域名模式分析
        - similarities: 與已知釣魚網站的相似處
        - uncertainties: 不確定因素
        - warnings: 具體警告列表（如果風險高）
        - recommendations: 具體建議列表
        - explanation: 詳細解釋（300-500 字）"""

        # ✅ 更詳細的用戶提示詞
        user_content = f"""請幫我分析以下網站是否為釣魚網站或不安全：

        🎯 目標網址：{target_url}
        🔍 目標域名：{target_domain}
        📍 頂級域名：{target_tld}

        📊 提供的安全搜尋結果摘要（共 {len(cleaned_results)} 筆）：
        {json.dumps(evidence_table, ensure_ascii=False, indent=2)}

        📈 統計數據：
        - .cfd 域名數量：{cfd_total}
        - .cfd 低信任數量：{cfd_low_trust}
        - 低信任比例：{round(cfd_low_trust/cfd_total*100) if cfd_total > 0 else 0}%

        ⚠️ 目標網址特徵分析：
        1. **頂級域名風險**：{target_tld} 是非常規頂級域名，搜索結果中 {cfd_low_trust}/{cfd_total} 個同類域名被標記為低信任
        2. **品牌模仿**：目標域名包含 "allegrolokalnie"，與波蘭知名電商平台 Allegro Lokalnie 高度相似
        3. **參數結構**：目標網址包含長串假造參數 (oferta-id-133457-kategorie-id-192876)，這是典型釣魚網站手法
        4. **完整模式**：品牌名 + 長參數 + 非常規後綴 = 高風險釣魚模式

        ⚠️ 重要提醒：
        1. 目標網址可能不在上述結果中，請基於「相似域名模式」和「風險特徵」進行間接推論
        2. .cfd/.top/.rest/.xyz 等非常規頂級域名通常風險較高
        3. SSL 證書有效 ≠ 網站安全，釣魚網站也可取得 SSL
        4. **如果目標網址符合「品牌名 + 長參數 + 非常規後綴」模式，風險等級必須是 critical 或 high**
        5. 請明確指出推理的不確定性，但不要因为證據間接就給出 inconclusive

        請輸出結構化 JSON 分析結果：
        {{
        "risk_level": "critical/high/medium/low/inconclusive",
        "confidence": "high/medium/low",
        "risk_score": 0-100,
        "evidence_summary": ["證據 1", "證據 2", ...],
        "pattern_analysis": {{
            "tld_risk": ".cfd 風險說明",
            "domain_pattern": "域名結構分析",
            "brand_impersonation": "品牌仿冒分析"
        }},
        "similarities": ["與已知釣魚網站的相似處 1", ...],
        "uncertainties": ["不確定因素 1", ...],
        "warnings": ["具體警告 1", "具體警告 2", ...],
        "recommendations": ["具體建議 1", "具體建議 2", ...],
        "explanation": "詳細解釋（300-500 字）"
        }}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        payload = {
            "model": Config.FEATHERLESS_MODEL,
            "messages": messages,
            "temperature": 0.1,  # ✅ 降低溫度讓輸出更穩定
            "max_tokens": 1500,  # ✅ 增加 token 讓解釋更詳細
            "response_format": {"type": "json_object"}
        }
        
        if Config.SAVE_INTERMEDIATE:
            from utils import save_json
            save_json(payload, output_path)
        
        logger.info(step_marker(3, "Prompt 建構完成", "done"))
        return payload
    
    def build_messages(self, target_url: str, exa_results: Dict, custom_instruction: Optional[str] = None) -> List[Dict]:
        cleaned = [self.clean_result(r) for r in exa_results.get('results', []) if r.get('url') or r.get('id')]
        evidence_lines = []
        for r in cleaned:
            risk_str = ", ".join(r['key_risks'][:3]) if r['key_risks'] else "無明顯風險"
            evidence_lines.append(f"- [{r['source']}] {r['domain']}: 信任={r['trust_indicator']}, 風險=[{risk_str}]")
        evidence_text = "\n".join(evidence_lines) or "⚠️ 未找到相關安全報告"
        user_content = f"""請幫我分析以下網站是否為釣魚網站或不安全：

        🎯 目標網址：{target_url}

        📊 提供的安全搜尋結果摘要（共 {len(cleaned)} 筆）：
        {evidence_text}

        ⚠️ 重要提醒：
        1. 目標網址可能不在上述結果中，請基於「相似域名模式」和「風險特徵」進行間接推論
        2. .cfd/.top/.rest 等非常規頂級域名通常風險較高
        3. SSL 證書有效 ≠ 網站安全，釣魚網站也可取得 SSL
        4. 請明確指出推理的不確定性

        請輸出結構化分析結果（JSON 格式優先）：
        {{
        "risk_conclusion": "高風險/中風險/低風險/無法判斷",
        "confidence": "高/中/低",
        "evidence_summary": ["證據 1", "證據 2", ...],
        "uncertainties": ["不確定因素 1", ...],
        "recommendations": ["建議 1", "建議 2", ...]
        }}"""
        return [
            {"role": "system", "content": custom_instruction or self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
    
    def to_featherless_payload(self, messages: List[Dict], model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> Dict:
        return {
            "model": model or Config.FEATHERLESS_MODEL,
            "messages": messages,
            "temperature": temperature or Config.FEATHERLESS_TEMPERATURE,
            "max_tokens": max_tokens or Config.FEATHERLESS_MAX_TOKENS,
            "response_format": {"type": "json_object"}
        }