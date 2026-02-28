"""Centralised application settings from environment (python-dotenv + os.environ)."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env next to this file
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path, encoding="utf-8")

# ── Module-level constants (not env-backed, but centralised) ──

UNSUITABLE_LABELS: frozenset[str] = frozenset([
    "色情", "成人", "暴力", "血腥", "gore", "porn", "nsfw", "explicit",
    "裸露", "不雅", "極端暴力", "恐怖",
])

KID_FRIENDLY_REPLACEMENTS: dict[str, str] = {
    "釣魚網站": "騙人的假網站",
    "惡意軟體": "壞壞的程式",
    "SSL 證書": "安全鎖",
    "頂級域名": "網址的尾巴",
    "個資": "個人資料",
    "仿冒": "假裝成",
    "威脅情報": "安全檢查",
    "色情": "不適合小朋友看的內容",
    "成人內容": "大人才能看的內容",
    "暴力": "打打殺殺的畫面",
}

HIGH_RISK_TLDS: frozenset[str] = frozenset(
    {"cfd", "top", "rest", "xyz", "loan", "click", "work"}
)
COMMON_TLDS: frozenset[str] = frozenset({"com", "tw", "org", "net", "edu"})
SUSPICIOUS_DOMAIN_LENGTH: int = 30
KNOWN_BRAND_PATTERNS: tuple[str, ...] = (
    "paypa", "amazn", "app1e", "g0ogle", "allegro",
)
RISK_WEIGHTS: dict[str, int] = {
    "critical": 3, "warning": 2, "caution": 1, "safe": 0,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Featherless AI (OpenAI-compatible) ---
    featherless_base_url: str = "https://api.featherless.ai/v1"
    featherless_api_key: str = ""
    featherless_model: str = "Qwen/Qwen3-0.6B"
    featherless_temperature: float = 0.1
    featherless_max_tokens: int = 800
    featherless_top_p: float = 0.9

    # --- LLM per-task overrides ---
    content_classify_temperature: float = 0.1
    content_classify_max_tokens: int = 400
    persuasion_temperature: float = 0.1
    persuasion_max_tokens: int = 800

        # --- Exa AI ---
        self.exa_api_key = _env("EXA_API_KEY", "")
        self.exa_base_url = _env("EXA_BASE_URL", "https://api.exa.ai")
        self.exa_timeout = _env_int("EXA_TIMEOUT", 60)
        self.exa_max_age_hours = _env_int("EXA_MAX_AGE_HOURS", 24)
        self.exa_livecrawl_timeout_ms = _env_int("EXA_LIVECRAWL_TIMEOUT_MS", 25000)
        self.exa_search_num_results = _env_int("EXA_SEARCH_NUM_RESULTS", 5)

        # --- Content analysis ---
        self.content_max_chars = _env_int("CONTENT_MAX_CHARS", 8000)

        # --- Security APIs ---
        self.api_timeout = _env_int("API_TIMEOUT", 30)
        self.virustotal_api_key = _env("VIRUSTOTAL_API_KEY", "")
        self.virustotal_base_url = _env("VIRUSTOTAL_BASE_URL", "https://www.virustotal.com/api/v3")
        self.urlhaus_auth_key = _env("URLHAUS_AUTH_KEY", "")
        self.urlhaus_base_url = _env("URLHAUS_BASE_URL", "https://urlhaus-api.abuse.ch/v1")
        self.phishtank_api_key = _env("PHISHTANK_API_KEY", "")
        self.phishtank_base_url = _env("PHISHTANK_BASE_URL", "https://api.phishtank.com/v2/phishtank")
        self.google_safe_browsing_api_key = _env("GOOGLE_SAFE_BROWSING_API_KEY", "")
        self.google_safe_browsing_base_url = _env(
            "GOOGLE_SAFE_BROWSING_BASE_URL", "https://safebrowsing.googleapis.com/v4"
        )

        # --- VirusTotal thresholds ---
        self.vt_malicious_critical = _env_int("VT_MALICIOUS_CRITICAL", 3)
        self.vt_total_critical = _env_int("VT_TOTAL_CRITICAL", 5)
        self.vt_suspicious_warning = _env_int("VT_SUSPICIOUS_WARNING", 2)

        # --- Security aggregation ---
        self.agg_critical_score = _env_int("AGG_CRITICAL_SCORE", 6)
        self.agg_critical_flags = _env_int("AGG_CRITICAL_FLAGS", 2)
        self.agg_high_score = _env_int("AGG_HIGH_SCORE", 3)
        self.agg_high_flags = _env_int("AGG_HIGH_FLAGS", 1)
        self.agg_medium_score = _env_int("AGG_MEDIUM_SCORE", 1)
        self.risk_score_multiplier = _env_int("RISK_SCORE_MULTIPLIER", 25)
        self.risk_score_max = _env_int("RISK_SCORE_MAX", 100)

        # --- App metadata ---
        self.app_title = _env("APP_TITLE", "ScoutNet API")
        self.app_version = _env("APP_VERSION", "2.0.0")
        self.user_agent = _env("USER_AGENT", "ScamAnalyzer/2.0")
        self.safebrowsing_client_id = _env("SAFEBROWSING_CLIENT_ID", "scamanalyzer")
        self.safebrowsing_client_version = _env("SAFEBROWSING_CLIENT_VERSION", "2.0.0")

        # --- Server (lowercase for compatibility with main.py) ---
        self.HOST = _env("HOST", "0.0.0.0")
        self.PORT = _env_int("PORT", 8001)
        self.host = self.HOST
        self.port = self.PORT

        # --- CORS ---
        self.cors_origins = _parse_cors_origins(_env("CORS_ORIGINS", "*"))

    def validate_required(self) -> list[str]:
        errors: list[str] = []
        if not self.featherless_api_key:
            errors.append("FEATHERLESS_API_KEY not set")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
