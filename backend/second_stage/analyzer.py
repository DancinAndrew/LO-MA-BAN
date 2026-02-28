#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二階段分析：針對「明知連結有害仍想點擊」的用戶理由進行勸阻與教育
組合 user_input + first_stage_report，呼叫 Featherless API 取得勸阻結果
輸出 JSON + Markdown
"""
import json
import sys
import requests
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from shared.config import Config


def build_second_stage_prompt(user_input: str, first_stage_report: dict) -> List[dict]:
    target_url = first_stage_report.get("report_metadata", {}).get("target_url", "未知網址")
    risk_info = first_stage_report.get("report_metadata", {}).get("risk", {})
    kid_summary = first_stage_report.get("kid_friendly_summary", {})
    raw_analysis = first_stage_report.get("raw_analysis", {})

    risk_source = "phishing"
    content_type = raw_analysis.get("content_risk_type", "")
    threat_types = raw_analysis.get("technical_details", {}).get("threat_types", [])
    if content_type or any(t in str(threat_types) for t in ["色情", "暴力", "血腥", "成人"]):
        risk_source = "content"

    system_prompt = """你是一位關心 18 歲以下兒童的網路安全輔導員。當使用者已經被告知某個連結有風險（可能是釣魚詐騙、色情、暴力等），但仍說出想進去的理由時，你要用溫暖但堅定的方式勸阻並教育。

請基於「第一階段安全報告」與「用戶自述的理由」，輸出結構化 JSON：

{
  "behavior_consequence_warning": "具體說明執意進入的後果（2–4 句，語氣嚴謹但友善）",
  "reason_analysis": {
    "is_reasonable": false,
    "analysis": "分析用戶理由，說明為什麼這種心態仍有風險",
    "empathy_note": "先同理用戶的心情，再解釋風險（例如：我理解你的好奇心，但是...）"
  },
  "general_warnings": [
    "提醒1",
    "提醒2",
    "提醒3"
  ],
  "recommended_actions": [
    "具體建議1（例如：和爸媽討論你看到的東西）",
    "具體建議2（例如：用安全工具查詢）",
    "具體建議3"
  ],
  "encouraging_message": "一句鼓勵的話（讓使用者覺得被理解，而不是被責備）"
}

注意：
- 用小朋友聽得懂的語言
- 先表達理解（同理心），再說明風險
- 不要恐嚇，而是引導
- 根據風險類型調整語氣（釣魚 → 強調個資安全；色情 → 強調身心影響；暴力 → 強調心理健康）
"""

    report_summary = f"""
【第一階段安全報告摘要】
• 目標網址：{target_url}
• 風險等級：{risk_info.get('label', '未知')}（分數 {risk_info.get('score', 'N/A')}/100）
• 風險來源：{'釣魚/資安' if risk_source == 'phishing' else f'不適合兒童的內容（{content_type}）'}
• 簡要說明：{kid_summary.get('short_explanation', raw_analysis.get('why_unsafe', ''))}
• 威脅類型：{', '.join(threat_types) if threat_types else '未知'}
"""

    user_content = f"""以下是使用者「明知有風險」仍想點擊的自述理由：

---
{user_input}
---

第一階段安全報告摘要：
{report_summary}

請輸出結構化 JSON（包含 behavior_consequence_warning、reason_analysis、general_warnings、recommended_actions、encouraging_message）。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def call_featherless_api(messages: List[dict]) -> dict:
    payload = {
        "model": Config.FEATHERLESS_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1000,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.FEATHERLESS_API_KEY}",
    }
    response = requests.post(
        Config.FEATHERLESS_API_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    if "choices" in result:
        return json.loads(result["choices"][0]["message"]["content"])
    raise ValueError(f"Unexpected API response: {result}")


def write_markdown(output: dict, md_path: Path) -> None:
    r = output.get("second_stage_result", {})
    summary = output.get("first_stage_report_summary", {})
    ra = r.get("reason_analysis", {})

    lines = [
        "# 第二階段分析報告：使用者理由勸阻",
        "",
        f"**目標網址**：{summary.get('target_url', '未知')}",
        f"**風險等級**：{summary.get('risk_level', '未知')}",
        f"**風險來源**：{summary.get('risk_source', '未知')}",
        "",
        "---",
        "",
        "## 使用者自述理由",
        "",
        f"> {output.get('user_input', '')}",
        "",
        "---",
        "",
        "## 行為後果警告",
        "",
        r.get("behavior_consequence_warning", "(無)"),
        "",
        "---",
        "",
        "## 理由分析",
        "",
        f"**合理？** {'是' if ra.get('is_reasonable') else '否'}",
        "",
        ra.get("empathy_note", ""),
        "",
        ra.get("analysis", ""),
        "",
        "---",
        "",
        "## 一般性安全提醒",
        "",
    ]
    for w in r.get("general_warnings", []):
        lines.append(f"- {w}")
    lines.extend(["", "---", "", "## 建議行動", ""])
    for a in r.get("recommended_actions", []):
        lines.append(f"- {a}")
    enc = r.get("encouraging_message", "")
    if enc:
        lines.extend(["", "---", "", "## 鼓勵", "", f"*{enc}*", ""])
    lines.append("")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="第二階段分析：對明知有害仍想點擊的用戶進行勸阻")
    parser.add_argument("input", nargs="?", help="simulate_user_input.json 路徑")
    parser.add_argument("--first-stage", help="03_final_report.json 路徑")
    parser.add_argument("-o", "--output-dir", help="輸出目錄（預設：與 input 同目錄）")
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else Path(__file__).parent / "simulate_user_input.json"
    if not input_path.exists():
        print(f"❌ 找不到輸入檔：{input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_input = data.get("user_input", "")
    first_stage_report = data.get("first_stage_report", {})

    if args.first_stage:
        stage_path = Path(args.first_stage)
        if stage_path.exists():
            with open(stage_path, "r", encoding="utf-8") as f:
                first_stage_report = json.load(f)
            print(f"📂 已從 {stage_path} 載入第一階段報告")
    elif first_stage_report == "__LOAD_FROM_FILE__" or not first_stage_report:
        print("❌ 需指定 --first-stage 03_final_report.json")
        sys.exit(1)

    if not user_input:
        print("❌ 輸入檔需包含 user_input")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🎯 網址：{first_stage_report.get('report_metadata', {}).get('target_url', '未知')}")
    print("🔧 建構 prompt...")
    messages = build_second_stage_prompt(user_input, first_stage_report)

    print("📡 呼叫 Featherless API...")
    result = call_featherless_api(messages)

    risk_meta = first_stage_report.get("report_metadata", {}).get("risk", {})
    raw = first_stage_report.get("raw_analysis", {})
    content_type = raw.get("content_risk_type", "")
    risk_source = "content" if content_type else "phishing"

    full_output = {
        "user_input": user_input,
        "first_stage_report_summary": {
            "target_url": first_stage_report.get("report_metadata", {}).get("target_url"),
            "risk_level": risk_meta.get("level"),
            "risk_label": risk_meta.get("label"),
            "risk_score": risk_meta.get("score"),
            "risk_source": risk_source,
        },
        "second_stage_result": result,
    }

    json_path = output_dir / "second_stage_result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 已儲存：{json_path}")

    md_path = output_dir / "second_stage_result.md"
    write_markdown(full_output, md_path)
    print(f"📄 Markdown 已儲存：{md_path}")

    print("\n" + "=" * 50)
    print("📋 第二階段分析結果摘要")
    print("=" * 50)
    print(f"\n🚨 行為後果警告：\n{result.get('behavior_consequence_warning', '(無)')}")
    ra = result.get("reason_analysis", {})
    print(f"\n📊 理由合理？ {'是' if ra.get('is_reasonable') else '否'}")
    print(f"💬 {ra.get('empathy_note', '')}")
    print(f"📝 {ra.get('analysis', '')}")
    enc = result.get("encouraging_message", "")
    if enc:
        print(f"\n💪 {enc}")


if __name__ == "__main__":
    main()
