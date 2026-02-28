# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv(Path(__file__).parent / ".env")

class Config:
    # ========== API 金鑰 ==========
    EXA_API_KEY = os.getenv("EXA_API_KEY", "")
    FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "")
    
    # ========== Exa 設定 ==========
    EXA_MAX_RESULTS = int(os.getenv("EXA_MAX_RESULTS", "20"))
    EXA_MAX_AGE_HOURS = int(os.getenv("EXA_MAX_AGE_HOURS", "168"))
    EXA_LIVECRAWL_TIMEOUT = int(os.getenv("EXA_LIVECRAWL_TIMEOUT", "5000"))
    
    SECURITY_DOMAINS = [
        "virustotal.com", "phishtank.com", "urlhaus.abuse.ch",
        "threatcrowd.org", "alienvault.com", "scamadviser.com", "whois.com"
    ]
    HIGHLIGHTS_QUERY = "phishing detection, security verdict, malware analysis, scam report, domain reputation"
    
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