#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
內容風險檢查：使用 Exa 取得網頁內容，以 Featherless AI 判斷是否為情色、暴力等不適合兒童的內容
"""
import json
import requests
from typing import Dict, Tuple, Optional
from shared.config import Config

UNSUITABLE_LABELS = frozenset([
    "色情", "成人", "暴力", "血腥", "gore", "porn", "nsfw", "explicit",
    "裸露", "不雅", "極端暴力", "恐怖"
])


def fetch_content_for_url(target_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    使用 Exa 取得網頁內容，失敗時改用搜尋模式
    回傳 (內容, 錯誤訊息)
    """
    try:
        from tools.url_crawl_and_classify import fetch_url_content_exa, search_url_context_exa
    except ImportError:
        return None, "無法載入 tools.url_crawl_and_classify 模組"

    content, err = fetch_url_content_exa(target_url)
    if err and ("CRAWL_LIVECRAWL_TIMEOUT" in str(err) or "CRAWL_NOT_FOUND" in str(err)):
        content, err = search_url_context_exa(target_url)
    return content, err


def is_unsuitable_for_children(classification: Dict) -> bool:
    """根據分類結果判斷是否不適合兒童"""
    labels = classification.get("labels", []) or []
    primary = (classification.get("primary_label") or "").lower()
    for lbl in labels + [primary]:
        lbl_lower = str(lbl).lower()
        for kw in UNSUITABLE_LABELS:
            if kw in lbl_lower or kw in str(lbl):
                return True
    return False


def classify_content_safety(target_url: str, page_content: str) -> Dict:
    """
    將網頁內容送至 Featherless AI 判斷是否適合 18 歲以下兒童
    """
    api_url = Config.FEATHERLESS_API_URL
    api_key = Config.FEATHERLESS_API_KEY
    model = Config.FEATHERLESS_MODEL

    if not api_key:
        return {"labels": [], "primary_label": "不明", "is_unsuitable_for_children": False, "error": "API 未設定"}

    max_chars = 8000
    if len(page_content) > max_chars:
        page_content = page_content[:max_chars] + "\n\n[... 內容已截斷 ...]"

    system_prompt = """你是一位關心兒童網路安全的專家。請根據提供的網頁 URL 與內容，判斷這個網頁**是否適合 18 歲以下兒童**瀏覽。

重點檢查：色情、成人內容、極端暴力、血腥、恐怖等不適當內容。

請輸出結構化 JSON：
{
  "labels": ["標籤1", "標籤2"],
  "primary_label": "主要標籤",
  "confidence": "high/medium/low",
  "explanation": "簡短說明（50字內）",
  "is_unsuitable_for_children": true 或 false
}

若內容涉及色情、成人、暴力、血腥等，is_unsuitable_for_children 必須為 true。"""

    user_content = f"""請分析以下網頁是否適合兒童：

URL: {target_url}

網頁內容：
---
{page_content}
---

輸出 JSON。"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 400,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        classification = json.loads(content)
        classification["is_unsuitable_for_children"] = classification.get(
            "is_unsuitable_for_children", is_unsuitable_for_children(classification)
        )
        return classification
    except Exception as e:
        return {"labels": [], "primary_label": "不明", "is_unsuitable_for_children": False, "error": str(e)}
