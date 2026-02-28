"""Centralised application settings backed by pydantic-settings."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    exa_api_key: str = ""
    exa_base_url: str = "https://api.exa.ai"
    exa_timeout: int = 60
    exa_max_age_hours: int = 24
    exa_livecrawl_timeout_ms: int = 25000
    exa_search_num_results: int = 5

    # --- Content analysis ---
    content_max_chars: int = 8000

    # --- Security APIs ---
    api_timeout: int = 30

    virustotal_api_key: str = ""
    virustotal_base_url: str = "https://www.virustotal.com/api/v3"

    urlhaus_auth_key: str = ""
    urlhaus_base_url: str = "https://urlhaus-api.abuse.ch/v1"

    phishtank_api_key: str = ""
    phishtank_base_url: str = "https://api.phishtank.com/v2/phishtank"

    google_safe_browsing_api_key: str = ""
    google_safe_browsing_base_url: str = "https://safebrowsing.googleapis.com/v4"

    # --- VirusTotal classification thresholds ---
    vt_malicious_critical: int = 3
    vt_total_critical: int = 5
    vt_suspicious_warning: int = 2

    # --- Security aggregation thresholds ---
    agg_critical_score: int = 6
    agg_critical_flags: int = 2
    agg_high_score: int = 3
    agg_high_flags: int = 1
    agg_medium_score: int = 1
    risk_score_multiplier: int = 25
    risk_score_max: int = 100

    # --- App metadata ---
    app_title: str = "ScoutNet API"
    app_version: str = "2.0.0"
    user_agent: str = "ScamAnalyzer/2.0"
    safebrowsing_client_id: str = "scamanalyzer"
    safebrowsing_client_version: str = "2.0.0"

    # --- Server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
# --- CORS ---
    cors_origins: list[str] = Field(default=["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    def validate_required(self) -> list[str]:
        errors: list[str] = []
        if not self.featherless_api_key:
            errors.append("FEATHERLESS_API_KEY not set")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
