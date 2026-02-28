#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網頁爬取 + AI 標籤分類
1. 使用 Exa API 爬取指定 URL 的網頁內容
2. 將內容送至 Featherless AI 判斷網頁屬於什麼標籤

使用方式：
  python -m tools.url_crawl_and_classify "https://example.com"
"""
import json
import sys
import requests
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from shared.config import Config


# ========== 方法一：Exa API 直接抓取 URL 內容 ==========
def _fetch_exa_contents(
    target_url: str,
    max_age_hours: Optional[int] = 24,
    livecrawl_timeout_ms: Optional[int] = 25000,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    呼叫 Exa /contents，回傳 (內容, 錯誤訊息, 錯誤 tag)
    """
    api_url = "https://api.exa.ai/contents"
    api_key = Config.EXA_API_KEY

    payload = {
        "urls": [target_url],
        "text": True,
        "highlights": True,
    }
    if max_age_hours is not None:
        payload["maxAgeHours"] = max_age_hours
    if livecrawl_timeout_ms is not None:
        payload["livecrawlTimeout"] = livecrawl_timeout_ms

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if results:
        return _merge_exa_results(results), None, None

    statuses = data.get("statuses", [])
    for s in statuses:
        if s.get("status") == "error":
            err = s.get("error", {})
            return None, f"Exa 爬取失敗: {err.get('tag', 'unknown')}", err.get("tag")
    return None, "Exa 未回傳任何內容", None


def _merge_exa_results(results: list) -> str:
    parts = []
    for r in results:
        if r.get("text"):
            parts.append(r["text"])
        if r.get("highlights"):
            for h in r["highlights"] if isinstance(r["highlights"], list) else [r["highlights"]]:
                if isinstance(h, str):
                    parts.append(h)
                elif isinstance(h, dict):
                    parts.append(h.get("text", h.get("snippet", str(h))))
    content = "\n\n".join(parts).strip()
    return content if content else ""


def fetch_url_content_exa(target_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    使用 Exa API /contents 端點抓取網頁全文
    - 預設 maxAgeHours=24：livecrawl 超時時會 fallback 至快取
    - 若仍 CRAWL_LIVECRAWL_TIMEOUT，改以 maxAgeHours=-1（僅快取）重試
    回傳 (合併後的文字內容, 錯誤訊息)
    """
    if not Config.EXA_API_KEY:
        return None, "EXA_API_KEY 未設定，請在 .env 中設定"

    try:
        content, err, tag = _fetch_exa_contents(
            target_url, max_age_hours=24, livecrawl_timeout_ms=25000,
        )
        if content:
            return content, None
        if tag != "CRAWL_LIVECRAWL_TIMEOUT":
            return None, err or "Exa 爬取失敗"

        content, retry_err, _ = _fetch_exa_contents(
            target_url, max_age_hours=-1, livecrawl_timeout_ms=None,
        )
        if content:
            return content, None
        return None, err or retry_err
    except requests.RequestException as e:
        return None, f"Exa API 請求失敗: {e}"


# ========== 方法二：Exa API 搜尋網路上關於此 URL 的討論 ==========
def search_url_context_exa(target_url: str, num_results: int = 5) -> Tuple[Optional[str], Optional[str]]:
    """
    使用 Exa API /search 端點搜尋關於此 URL 的討論
    回傳 (合併後的搜尋結果文字, 錯誤訊息)
    """
    api_url = "https://api.exa.ai/search"
    api_key = Config.EXA_API_KEY

    if not api_key:
        return None, "EXA_API_KEY 未設定"

    payload = {
        "query": target_url,
        "type": "auto",
        "numResults": num_results,
        "contents": {"text": True, "summary": True},
    }
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return None, "Exa 搜尋無結果"

        parts = []
        for r in results:
            if r.get("text"):
                parts.append(r["text"])
            if r.get("summary"):
                parts.append(f"[摘要] {r['summary']}")

        return "\n\n".join(parts).strip() or None, None
    except requests.RequestException as e:
        return None, f"Exa 搜尋請求失敗: {e}"


# ========== Featherless AI 標籤分類 ==========
def classify_with_featherless(url: str, page_content: str) -> dict:
    api_url = Config.FEATHERLESS_API_URL
    api_key = Config.FEATHERLESS_API_KEY
    model = Config.FEATHERLESS_MODEL

    if not api_key:
        raise ValueError("FEATHERLESS_API_KEY 未設定，請在 .env 中設定")

    max_chars = 8000
    if len(page_content) > max_chars:
        page_content = page_content[:max_chars] + "\n\n[... 內容已截斷 ...]"

    system_prompt = """你是一位專業的網頁內容分類專家。請根據提供的網頁 URL 與內容，判斷這個網頁屬於什麼標籤。

請輸出結構化 JSON，格式如下：
{
  "labels": ["標籤1", "標籤2", "標籤3"],
  "primary_label": "主要標籤",
  "confidence": "high/medium/low",
  "explanation": "簡短說明為什麼歸類為這些標籤（50–100字）"
}

標籤範例（可依實際內容自訂）：
- 詐騙 / 釣魚 / 惡意
- 購物 / 電商 / 拍賣
- 新聞 / 媒體 / 部落格
- 社交 / 論壇 / 討論區
- 金融 / 銀行 / 投資
- 政府 / 官方
- 教育 / 學術
- 娛樂 / 遊戲
- 不明 / 可疑
"""

    user_content = f"""
請分析以下網頁並判斷其標籤：

URL: {url}

網頁內容：
---
{page_content}
---

請輸出 JSON 格式的分類結果。
"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    resp = requests.post(api_url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()

    if "choices" not in result:
        raise ValueError(f"Featherless API 回傳格式異常: {result}")

    content = result["choices"][0]["message"]["content"]
    classification = json.loads(content)
    classification["llm_metadata"] = {
        "model": model,
        "usage": result.get("usage", {}),
    }
    return classification


# ========== Main ==========
def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    target_url = target_url.strip()
    use_search = "--search" in sys.argv

    print(f"🎯 目標網址: {target_url}")
    print()

    content = None
    err = None
    if use_search:
        print("📡 使用 Exa 搜尋模式...")
        content, err = search_url_context_exa(target_url)
    else:
        print("📡 使用 Exa 直接抓取網頁內容...")
        content, err = fetch_url_content_exa(target_url)
        if err and ("CRAWL_LIVECRAWL_TIMEOUT" in str(err) or "CRAWL_NOT_FOUND" in str(err)):
            print(f"   ⚠️ 直接抓取失敗 ({err})，改以 Exa 搜尋模式嘗試...")
            content, err = search_url_context_exa(target_url)

    if err or not content:
        print(f"❌ {err or '未能取得內容'}")
        sys.exit(1)

    print(f"✅ 取得內容，共 {len(content)} 字")
    print()

    print("🤖 呼叫 Featherless AI 進行標籤分類...")
    try:
        classification = classify_with_featherless(target_url, content)
    except Exception as e:
        print(f"❌ Featherless API 錯誤: {e}")
        sys.exit(1)

    output = {
        "target_url": target_url,
        "content_length": len(content),
        "content_preview": content[:500] + "..." if len(content) > 500 else content,
        "classification": classification,
    }

    out_path = Path(__file__).parent / "url_classification_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 結果已儲存至: {out_path}")
    print()
    print("=" * 50)
    print("📋 分類結果")
    print("=" * 50)
    print(f"  主要標籤: {classification.get('primary_label', 'N/A')}")
    print(f"  標籤列表: {', '.join(classification.get('labels', []))}")
    print(f"  信心程度: {classification.get('confidence', 'N/A')}")
    print(f"  說明: {classification.get('explanation', 'N/A')}")


if __name__ == "__main__":
    main()
