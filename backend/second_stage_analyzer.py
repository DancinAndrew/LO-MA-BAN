#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二階段分析：針對「明知連結有害仍想點擊」的用戶理由進行勸阻與教育
組合 user_input + first_stage_report，呼叫 Featherless API 取得勸阻結果
"""
import json
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
from config import Config


def build_second_stage_prompt(user_input: str, first_stage_report: dict) -> list[dict]:
    """
    建構第二階段分析的 system + user prompt
    """
    target_url = first_stage_report.get("report_metadata", {}).get("target_url", "未知網址")
    risk_info = first_stage_report.get("report_metadata", {}).get("risk", {})
    kid_summary = first_stage_report.get("kid_friendly_summary", {})
    raw_analysis = first_stage_report.get("raw_analysis", {})

    system_prompt = """你是一位專業的網路安全教育專家。你的任務是：當使用者已經知道某個連結是有害的，但仍陳述他想點進去的理由時，你要給予適當的勸阻與教育。

你必須基於「第一階段安全報告」與「用戶自述的理由」，輸出結構化 JSON，內容需包含以下三部分：

1. **行為後果警告 (behavior_consequence_warning)**：明確且具體地說明，若用戶仍執意進入該連結，可能導致什麼後果（如：個資外洩、裝置中毒、信用卡被盜刷、被釣魚詐騙等）。用 2–4 句說明，語氣嚴謹但友善。

2. **理由合理性分析 (reason_analysis)**：
   - "is_reasonable": 布林值，判斷用戶理由是否合理
   - "analysis": 簡要分析用戶的理由（例如「好奇」、「想確認」等），說明為什麼這種心態在面對高風險連結時仍不足以防護

3. **一般性安全提醒 (general_warnings)**：提供 3–5 條通用的網路安全建議，例如：
   - 不要在任何可疑網站輸入信用卡號、密碼、OTP
   - 不要因為「只是想看看」就進入高風險連結，因為只要載入頁面就可能觸發惡意程式
   - 防毒軟體無法 100% 阻擋所有威脅
   - 其他你認為重要的提醒

輸出 JSON 格式：
{
  "behavior_consequence_warning": "字串，說明執意進入的具體後果",
  "reason_analysis": {
    "is_reasonable": false,
    "analysis": "分析用戶理由是否合理，以及為什麼"
  },
  "general_warnings": [
    "提醒1：不要輸入信用卡密碼等敏感資訊",
    "提醒2：...",
    "提醒3：..."
  ]
}
"""

    report_summary = f"""
【第一階段安全報告摘要】
• 目標網址：{target_url}
• 風險等級：{risk_info.get('label', '未知')}（分數 {risk_info.get('score', 'N/A')}/100）
• 簡要說明：{kid_summary.get('short_explanation', raw_analysis.get('why_unsafe', ''))}
• 威脅類型：{', '.join(raw_analysis.get('technical_details', {}).get('threat_types', ['未知']))}
• 已標記平台：{', '.join(raw_analysis.get('technical_details', {}).get('detected_by', []))}
"""

    user_content = f"""
以下是「明知連結有害」的用戶自述想點進去的理由：

---
{user_input}
---

以下是針對該連結的第一階段安全報告（摘要）：
{report_summary}

請根據以上資訊，輸出結構化的 JSON，包含：
1. behavior_consequence_warning（行為後果警告）
2. reason_analysis（理由合理性分析）
3. general_warnings（一般性安全提醒，含不要輸入信用卡密碼等）
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]


def call_featherless_api(messages: list[dict]) -> dict:
    """呼叫 Featherless API"""
    payload = {
        "model": Config.FEATHERLESS_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1000,
        "top_p": 0.9,
        "stream": False,
        "response_format": {"type": "json_object"}
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.FEATHERLESS_API_KEY}"
    }
    response = requests.post(
        Config.FEATHERLESS_API_URL,
        headers=headers,
        json=payload,
        timeout=120
    )
    response.raise_for_status()
    result = response.json()
    if "choices" in result:
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
    raise ValueError(f"Unexpected API response: {result}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="第二階段分析：對明知有害仍想點擊的用戶進行勸阻")
    parser.add_argument("input", nargs="?", help="輸入 JSON 檔（預設：test_user_reason_input.json）")
    parser.add_argument("--first-stage", help="可選：直接從 03_final_report.json 載入第一階段報告")
    args = parser.parse_args()

    # 預設使用 test_user_reason_input.json
    input_path = Path(args.input or str(Path(__file__).parent / "test_user_reason_input.json"))

    if not input_path.exists():
        print(f"❌ 找不到輸入檔：{input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_input = data.get("user_input", "")
    first_stage_report = data.get("first_stage_report", {})

    # 若指定 --first-stage，則從該檔載入完整報告
    if args.first_stage:
        stage_path = Path(args.first_stage)
        if stage_path.exists():
            with open(stage_path, "r", encoding="utf-8") as f:
                first_stage_report = json.load(f)
            print(f"📂 已從 {stage_path} 載入第一階段報告")

    if not user_input or not first_stage_report:
        print("❌ 輸入檔需包含 user_input 與 first_stage_report")
        sys.exit(1)

    print("🔧 建構 prompt...")
    messages = build_second_stage_prompt(user_input, first_stage_report)

    print("📡 呼叫 Featherless API...")
    result = call_featherless_api(messages)

    # 儲存結果
    output_path = Path(__file__).parent / "test_second_stage_output.json"
    full_output = {
        "user_input": user_input,
        "first_stage_report_summary": {
            "target_url": first_stage_report.get("report_metadata", {}).get("target_url"),
            "risk_level": first_stage_report.get("report_metadata", {}).get("risk", {}).get("level"),
        },
        "second_stage_result": result
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, ensure_ascii=False, indent=2)

    print(f"✅ 結果已儲存至：{output_path}")
    print("\n" + "=" * 50)
    print("📋 第二階段分析結果摘要")
    print("=" * 50)
    print("\n🚨 行為後果警告：")
    print(result.get("behavior_consequence_warning", "(無)"))
    print("\n📊 理由分析：")
    ra = result.get("reason_analysis", {})
    print(f"  合理？{'是' if ra.get('is_reasonable') else '否'}")
    print(f"  分析：{ra.get('analysis', '(無)')}")
    print("\n⚠️ 一般性安全提醒：")
    for w in result.get("general_warnings", []):
        print(f"  • {w}")


if __name__ == "__main__":
    main()
