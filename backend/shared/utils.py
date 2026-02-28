import json
from pathlib import Path
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

def save_json(data: Any, filepath: Path, indent: int = 2, ensure_ascii: bool = False) -> Path:
    """
    儲存資料為 JSON 檔案

    Args:
        data: 要儲存的資料（dict/list/任何可序列化物件）
        filepath: 輸出檔案路徑
        indent: JSON 縮排數
        ensure_ascii: 是否轉義非 ASCII 字元

    Returns:
        實際儲存的檔案路徑
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    
    logger.info(f"💾 已儲存: {filepath} ({filepath.stat().st_size:,} bytes)")
    return filepath

def load_json(filepath: Path) -> Dict:
    """載入 JSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def step_marker(step_num: int, step_name: str, status: str = "start") -> str:
    """產生步驟標記訊息"""
    icons = {"start": "🔄", "done": "✅", "error": "❌"}
    return f"{icons.get(status, '📍')} [Step {step_num}] {step_name}"
