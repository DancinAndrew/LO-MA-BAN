# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv(Path(__file__).parent / ".env")

class Config:
    # ========== API 金鑰 ==========
    FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "")
    
    # ========== Featherless 設定 ==========
    FEATHERLESS_API_URL = "https://api.featherless.ai/v1/chat/completions"
    FEATHERLESS_MODEL = os.getenv("FEATHERLESS_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    FEATHERLESS_TEMPERATURE = float(os.getenv("FEATHERLESS_TEMPERATURE", "0.1"))
    FEATHERLESS_MAX_TOKENS = int(os.getenv("FEATHERLESS_MAX_TOKENS", "1000"))
    
    # ========== 輸出設定 ==========
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
    SAVE_INTERMEDIATE = os.getenv("SAVE_INTERMEDIATE", "true").lower() == "true"
    
    # ========== 預設值 ==========
    DEFAULT_TARGET_URL = os.getenv("DEFAULT_TARGET_URL", "")

    # === Security API Settings ===
    API_TIMEOUT: int = 30
    
    # VirusTotal API v3
    VIRUSTOTAL_API_KEY: str = os.getenv("VIRUSTOTAL_API_KEY", "")
    VIRUSTOTAL_BASE_URL: str = "https://www.virustotal.com/api/v3"
    
    # URLhaus API
    URLHAUS_BASE_URL: str = "https://urlhaus-api.abuse.ch/v1"
    URLHAUS_AUTH_KEY: str = os.getenv("URLHAUS_AUTH_KEY", "")
    
    # PhishTank API
    PHISHTANK_API_KEY: str = os.getenv("PHISHTANK_API_KEY", "")
    PHISHTANK_BASE_URL: str = "https://checkurl.phishtank.com/checkurl"
    
    # Google Safe Browsing API v4
    GOOGLE_SAFE_BROWSING_API_KEY: str = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    GOOGLE_SAFE_BROWSING_BASE_URL: str = "https://safebrowsing.googleapis.com/v4"
    
    # === Featherless AI Settings ===
    FEATHERLESS_API_URL: str = os.getenv("FEATHERLESS_API_URL", "https://api.featherless.ai/v1/chat/completions")
    FEATHERLESS_API_KEY: str = os.getenv("FEATHERLESS_API_KEY", "")
    FEATHERLESS_MODEL: str = os.getenv("FEATHERLESS_MODEL", "Qwen2.5-7B-Instruct")
    FEATHERLESS_TEMPERATURE: float = 0.1
    FEATHERLESS_MAX_TOKENS: int = 2000
    
    @classmethod
    def setup_output_dir(cls):
        """建立輸出資料夾（若不存在）"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return cls.OUTPUT_DIR
    
    @classmethod
    def validate(cls):
        """驗證必要設定"""
        errors = []
        if not cls.EXA_API_KEY:
            errors.append("EXA_API_KEY not set in .env")
        if not cls.FEATHERLESS_API_KEY:
            errors.append("FEATHERLESS_API_KEY not set in .env")
        return errors