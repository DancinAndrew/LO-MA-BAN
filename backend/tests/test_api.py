#!/usr/bin/env python3
"""
端對端 API 測試：自動呼叫 first_stage + second_stage，儲存結果至 tests/output/
用法：先啟動 server，再執行 python tests/test_api.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import httpx

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path(__file__).parent / "output"

SCENARIOS = {
    "phishing": {
        "url": "https://allegrolokalnie.pl-oferta-id-133457-kategorie-id-192876.cfd",
        "user_input": (
            "我知道你們說這是釣魚網站，但我覺得你們可能分析錯了。"
            "我之前有在 Allegro Lokalnie 上買過東西，這個連結是賣家傳給我的，"
            "我怕錯過訂單的確認頁面。而且我覺得光是點進去看一下應該不會怎樣吧？"
            "我又不會輸入密碼，就看看頁面長什麼樣子而已。"
            "如果真的是假的我馬上關掉就好了，應該來得及吧？"
        ),
    },
    "violence": {
        "url": "http://theync.com/media.php?name=15644-beheading",
        "user_input": (
            "我同學傳給我這個連結，說裡面有一段很誇張的影片，大家都在討論。"
            "我知道可能有暴力的畫面，但我覺得既然新聞都會報導這些事情，"
            "我看一下應該也沒什麼大不了的吧？而且我已經快要成年了，"
            "我覺得我可以自己判斷要不要繼續看。"
            "我只是好奇大家到底在討論什麼，不想被同學覺得我什麼都不知道。"
        ),
    },
    "porn": {
        "url": "https://cn.pornhub.com/",
        "user_input": (
            "我在網路上不小心看到這個網址，然後被你們的系統攔下來了。"
            "但說實話我就是有點好奇，想知道那個網站到底有什麼。"
            "我覺得現在很多人都會看這些東西，也沒有什麼大不了的吧？"
            "而且我有聽說這個網站很有名，我就是想確認一下它到底是什麼樣的網站。"
            "我保證我只是看一下就關掉，不會沉迷。"
        ),
    },
}


def check_server():
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"✅ Server is running: {r.json()}")
        return True
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        return False


def run_first_stage(scenario_name: str, url: str) -> Optional[dict]:
    out_dir = OUTPUT_DIR / "first_stage" / scenario_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🔍 [First Stage] {scenario_name}: {url}")
    print(f"{'='*60}")

    try:
        r = httpx.post(
            f"{BASE_URL}/api/v1/scan",
            json={"url": url},
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        return None

    print(f"  ✅ risk_source={data.get('risk_source')}  final_risk={data.get('final_risk_level')}")

    _save(data.get("security_check", {}), out_dir / "01_security_check.json")
    _save(data, out_dir / "02_full_response.json")

    report = data.get("report")
    if report:
        _save(report, out_dir / "03_final_report.json")
    else:
        print("  ⚠️  No report generated (quick_scan or low risk)")

    return data


def run_second_stage(scenario_name: str, user_input: str, first_stage_report: dict):
    out_dir = OUTPUT_DIR / "second_stage" / scenario_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🗣️ [Second Stage] {scenario_name}")
    print(f"{'='*60}")

    request_body = {
        "user_input": user_input,
        "first_stage_report": first_stage_report,
    }
    _save(request_body, out_dir / "simulate_user_input.json")

    try:
        r = httpx.post(
            f"{BASE_URL}/api/v1/scan/persuade",
            json=request_body,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        return

    result = data.get("second_stage_result", {})
    ra = result.get("reason_analysis", {})
    print(f"  ✅ reasonable={ra.get('is_reasonable')}")
    print(f"  💬 {ra.get('empathy_note', '')[:80]}...")

    _save(data, out_dir / "second_stage_result.json")


def _save(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 {path.relative_to(OUTPUT_DIR)}")


def main():
    if not check_server():
        print("\n請先啟動 server：cd backend && python main.py")
        sys.exit(1)

    first_stage_results: Dict[str, dict] = {}

    # ── First Stage ──
    for name, cfg in SCENARIOS.items():
        result = run_first_stage(name, cfg["url"])
        if result:
            first_stage_results[name] = result

    # ── Second Stage ──
    for name, cfg in SCENARIOS.items():
        fs = first_stage_results.get(name)
        if not fs:
            print(f"\n⚠️  Skipping second stage for {name} — no first stage result")
            continue

        report = fs.get("report", {})
        run_second_stage(name, cfg["user_input"], report)

    # ── Summary ──
    print(f"\n{'='*60}")
    print("📋 測試結果總覽")
    print(f"{'='*60}")
    for name in SCENARIOS:
        fs_dir = OUTPUT_DIR / "first_stage" / name
        ss_dir = OUTPUT_DIR / "second_stage" / name
        fs_files = list(fs_dir.glob("*.json")) if fs_dir.exists() else []
        ss_files = list(ss_dir.glob("*.json")) if ss_dir.exists() else []
        print(f"  {name:12s}  first_stage: {len(fs_files)} files  second_stage: {len(ss_files)} files")

    print(f"\n📁 所有結果儲存在：{OUTPUT_DIR}")
    print("✅ 測試完成")


if __name__ == "__main__":
    main()
