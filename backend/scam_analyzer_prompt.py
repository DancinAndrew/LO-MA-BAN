#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScamAdviser 搜索結果清理器
轉換為 Featherless API (Qwen2.5-7B-Instruct) 可用的 prompt 格式
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional


def extract_domain(url: str) -> str:
    """從完整 URL 提取純域名"""
    # 移除前後空白和可能的多餘字元
    url = url.strip().rstrip('/')
    # 移除 http(s)://
    url = re.sub(r'^https?://', '', url)
    # 移除路徑，只保留域名
    domain = url.split('/')[0]
    return domain


def parse_trust_score(summary: str) -> Optional[str]:
    """從 summary 中提取信任評分相關資訊"""
    if not summary:
        return None
    
    # 常見信任評分關鍵字
    patterns = [
        r'trust score of (\d+)%',
        r'trust score[:\s]+(\d+)[/\s]+100',
        r'rating.*?(\d+)[/\s]+100',
        r'very low trust',
        r'low trust',
        r'high trust',
        r'100/100',
    ]
    
    summary_lower = summary.lower()
    
    if 'very low trust' in summary_lower or 'trust score 0' in summary_lower:
        return "very_low"
    elif 'low trust' in summary_lower:
        return "low"
    elif 'high trust' in summary_lower or '100/100' in summary_lower:
        return "high"
    elif '75%' in summary or 'medium' in summary_lower:
        return "medium"
    
    # 嘗試提取數字分數
    match = re.search(r'(\d+)[/\s]+100', summary)
    if match:
        score = int(match.group(1))
        if score >= 80:
            return "high"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "low"
        else:
            return "very_low"
    
    return None


def extract_key_risks(summary: str) -> list[str]:
    """從 summary 中提取關鍵風險指標"""
    if not summary:
        return []
    
    risks = []
    summary_lower = summary.lower()
    
    # 定義風險關鍵字映射
    risk_keywords = {
        "newly registered domain": ["newly registered", "very young", "domain age.*?[0-3] months", "young domain"],
        "hidden owner/WHOIS": ["whois.*?hidden", "owner.*?hide", "identity.*?conceal", "redacted for privacy"],
        "suspicious domain pattern": ["suspicious domain", "random string", "complex domain", "numeric structure"],
        "fake login forms risk": ["fake login", "capture.*?credential", "deceptive.*?form"],
        "low traffic/ranking": ["low tranco", "few visitor", "low rank", "not many visitor"],
        "high-risk hosting": ["high-risk location", "suspicious.*?server", "same server.*?scam"],
        "invalid/weak SSL": ["ssl.*?invalid", "no ssl", "certificate.*?problem"],
        "brand impersonation": ["similarity.*?legitimate", "mimic.*?allegro", "impersonat"],
        "gambling/spam association": ["gambling", "spam", "fraud.*?site"],
    }
    
    for risk_name, patterns in risk_keywords.items():
        for pattern in patterns:
            if re.search(pattern, summary_lower):
                if risk_name not in risks:
                    risks.append(risk_name)
                break
    
    return risks


def clean_search_result(result: dict) -> dict:
    """清理單個搜索結果，提取標準化欄位"""
    url = result.get('url', '').strip()
    domain = extract_domain(url) if url else result.get('id', '').strip()
    
    # 優先使用 summary，其次嘗試從 highlights 重建
    summary = result.get('summary', '')
    if not summary and result.get('highlights'):
        # 嘗試從 highlights 提取文字內容
        highlights = result['highlights']
        if isinstance(highlights, list) and highlights:
            summary = ' '.join(str(h) for h in highlights[:3])  # 取前3個
    
    cleaned = {
        "domain": domain,
        "url": url,
        "title": result.get('title', '').strip(),
        "trust_score": parse_trust_score(summary),
        "key_risks": extract_key_risks(summary),
        "summary_snippet": summary[:300] + "..." if len(summary) > 300 else summary,
        "published_date": result.get('publishedDate', result.get('published_date', '')),
    }
    
    return cleaned


def load_search_data(file_path: str) -> dict:
    """載入搜索結果檔案（支援 JSON 或含 JSON 的 TXT）"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # 如果檔案內容是純 JSON
    if content.startswith('{'):
        return json.loads(content)
    
    # 如果檔案包含 JSON 區塊，嘗試提取
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        return json.loads(json_match.group())
    
    raise ValueError(f"無法解析檔案格式: {file_path}")


def build_featherless_prompt(
    target_url: str,
    cleaned_results: list[dict],
    instruction: Optional[str] = None
) -> list[dict]:
    """
    建構 Featherless API 可用的 messages 格式
    
    Args:
        target_url: 要分析的目標網址
        cleaned_results: 清理後的搜索結果列表
        instruction: 自訂分析指令（可選）
    
    Returns:
        messages 陣列，可直接用於 API 呼叫
    """
    
    # 預設系統提示詞
    system_prompt = instruction or """你是一位專業的網路安全分析助手，專門協助判斷網站是否為釣魚或詐騙網站。
請嚴格基於用戶提供的 ScamAdviser 搜索結果進行推理，不要自行搜尋或假設額外資訊。
輸出時請使用結構化格式，包含：風險結論、關鍵證據、不確定性說明、實務建議。"""

    # 建構證據摘要（精簡版，節省 token）
    evidence_lines = []
    for r in cleaned_results:
        risk_str = ", ".join(r['key_risks'][:3]) if r['key_risks'] else "無明顯風險"
        score_str = r['trust_score'] or "未知"
        evidence_lines.append(f"- {r['domain']}: 信任={score_str}, 風險=[{risk_str}]")
    
    evidence_text = "\n".join(evidence_lines)
    
    # 用戶提示詞
    user_prompt = f"""請幫我分析以下網站是否為釣魚網站或不安全：

🎯 目標網址：{target_url}

📊 提供的 ScamAdviser 搜索結果摘要（共 {len(cleaned_results)} 筆）：
{evidence_text}

⚠️ 重要提醒：
1. 目標網址可能不在上述搜索結果中，請基於「相似域名模式」和「風險特徵」進行間接推論
2. .cfd/.top/.rest 等非常規頂級域名通常風險較高
3. SSL 證書有效 ≠ 網站安全，釣魚網站也可取得 SSL
4. 請明確指出推理的不確定性

請輸出結構化分析結果（JSON 格式優先）：
{{
  "risk_conclusion": "高風險/中風險/低風險/無法判斷",
  "confidence": "高/中/低",
  "evidence_summary": ["證據1", "證據2", ...],
  "uncertainties": ["不確定因素1", ...],
  "recommendations": ["建議1", "建議2", ...]
}}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def main():
    """主函數：命令行介面"""
    import argparse
    
    parser = argparse.ArgumentParser(description='轉換 ScamAdviser 搜索結果為 Featherless API 格式')
    parser.add_argument('input_file', help='輸入檔案路徑（含搜索結果的 JSON/TXT）')
    parser.add_argument('-t', '--target', required=True, help='要分析的目標網址')
    parser.add_argument('-o', '--output', help='輸出檔案路徑（預設：stdout）')
    parser.add_argument('--raw', action='store_true', help='輸出原始 cleaned results JSON（而非 messages）')
    
    args = parser.parse_args()
    
    try:
        # 1. 載入原始數據
        raw_data = load_search_data(args.input_file)
        
        # 2. 清理搜索結果
        cleaned_results = [
            clean_search_result(r) 
            for r in raw_data.get('results', [])
            if r.get('url') or r.get('id')
        ]
        
        # 3. 根據需求輸出
        if args.raw:
            # 輸出清理後的結果（用於除錯或進一步處理）
            output_data = {
                "target_url": args.target,
                "cleaned_results": cleaned_results,
                "total_processed": len(cleaned_results)
            }
            output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
        else:
            # 輸出 Featherless API 可用的 messages
            messages = build_featherless_prompt(args.target, cleaned_results)
            output_json = json.dumps({"messages": messages}, ensure_ascii=False, indent=2)
        
        # 4. 寫入檔案或輸出到 stdout
        if args.output:
            Path(args.output).write_text(output_json, encoding='utf-8')
            print(f"✅ 已輸出至: {args.output}", file=sys.stderr)
        else:
            print(output_json)
            
    except Exception as e:
        print(f"❌ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()