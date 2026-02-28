# exa_query.py
from exa_py import Exa
from typing import Optional, List, Dict
import logging
from pathlib import Path
from config import Config
from utils import save_json, step_marker

logger = logging.getLogger(__name__)

class ExaQuery:
    """Exa AI 安全資訊查詢器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.EXA_API_KEY
        if not self.api_key:
            raise ValueError("Exa API key is required")
        self.client = Exa(self.api_key)
    
    def search_and_save(
        self,
        target_url: str,
        output_path: Optional[Path] = None,
        **search_params
    ) -> Dict:
        """
        查詢並自動儲存結果到 JSON
        
        Args:
            target_url: 要分析的目標網址
            output_path: 輸出路徑（預設: Config.OUTPUT_DIR / "01_exa_raw.json"）
            **search_params: 額外搜尋參數
        
        Returns:
            Exa API 原始回應字典
        """
        # 設定預設輸出路徑
        if output_path is None:
            output_path = Config.OUTPUT_DIR / "01_exa_raw.json"
        
        # 合併參數
        params = {
            "query": target_url,
            "type": "auto",
            "num_results": search_params.get("num_results", Config.EXA_MAX_RESULTS),
            "include_domains": search_params.get("include_domains", Config.SECURITY_DOMAINS),
            "contents": {
                "highlights": {
                    "query": search_params.get("highlights_query", Config.HIGHLIGHTS_QUERY),
                    "max_characters": 4000
                },
                "summary": True,
                "max_age_hours": search_params.get("max_age_hours", Config.EXA_MAX_AGE_HOURS),
                "livecrawl_timeout": search_params.get("livecrawl_timeout", Config.EXA_LIVECRAWL_TIMEOUT)
            }
        }
        
        logger.info(step_marker(1, f"Exa 查詢: {target_url}"))
        logger.debug(f"Exa params: {params}")
        
        try:
            # 執行查詢
            result = self.client.search(**params)
            raw_data = self._serialize_result(result)
            
            # 自動儲存
            if Config.SAVE_INTERMEDIATE:
                save_json(raw_data, output_path)
            
            logger.info(step_marker(1, "Exa 查詢完成", "done"))
            return raw_data
            
        except Exception as e:
            logger.error(step_marker(1, f"Exa 查詢失敗: {e}", "error"))
            raise
    
    def _serialize_result(self, result) -> Dict:
        """將 Exa 結果物件轉換為純字典"""
        if hasattr(result, '__dict__'):
            data = {}
            for key, value in result.__dict__.items():
                if isinstance(value, list):
                    data[key] = [self._serialize_result(item) for item in value]
                elif hasattr(value, '__dict__'):
                    data[key] = self._serialize_result(value)
                else:
                    data[key] = value
            return data
        return result