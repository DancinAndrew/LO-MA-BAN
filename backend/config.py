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


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _parse_cors_origins(v: str) -> list[str]:
    if not v:
        return ["*"]
    if v.strip().startswith("["):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            pass
    return [s.strip() for s in v.split(",") if s.strip()]


class Settings:
    """Settings loaded from environment (no pydantic_settings dependency)."""

    def __init__(self) -> None:
        # --- Featherless AI (OpenAI-compatible) ---
        self.featherless_base_url = _env("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
        self.featherless_api_key = _env("FEATHERLESS_API_KEY", "")
        self.featherless_model = _env("FEATHERLESS_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        self.featherless_temperature = _env_float("FEATHERLESS_TEMPERATURE", "0.1")
        self.featherless_max_tokens = _env_int("FEATHERLESS_MAX_TOKENS", 2000)
        self.featherless_top_p = _env_float("FEATHERLESS_TOP_P", "0.9")

        # --- LLM per-task overrides ---
        self.content_classify_temperature = _env_float("CONTENT_CLASSIFY_TEMPERATURE", "0.1")
        self.content_classify_max_tokens = _env_int("CONTENT_CLASSIFY_MAX_TOKENS", 400)
        self.persuasion_temperature = _env_float("PERSUASION_TEMPERATURE", "0.1")
        self.persuasion_max_tokens = _env_int("PERSUASION_MAX_TOKENS", 1000)

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
