from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class Config:
    # --- Featherless AI (OpenAI-compatible) ---
    FEATHERLESS_BASE_URL: str = os.getenv(
        "FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"
    )
    FEATHERLESS_API_KEY: str = os.getenv("FEATHERLESS_API_KEY", "")
    FEATHERLESS_MODEL: str = os.getenv(
        "FEATHERLESS_MODEL", "Qwen/Qwen2.5-7B-Instruct"
    )
    FEATHERLESS_TEMPERATURE: float = float(
        os.getenv("FEATHERLESS_TEMPERATURE", "0.1")
    )
    FEATHERLESS_MAX_TOKENS: int = int(os.getenv("FEATHERLESS_MAX_TOKENS", "2000"))

    # --- Exa AI ---
    EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")

    # --- Security API keys ---
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))

    VIRUSTOTAL_API_KEY: str = os.getenv("VIRUSTOTAL_API_KEY", "")
    VIRUSTOTAL_BASE_URL: str = "https://www.virustotal.com/api/v3"

    URLHAUS_BASE_URL: str = "https://urlhaus-api.abuse.ch/v1"
    URLHAUS_AUTH_KEY: str = os.getenv("URLHAUS_AUTH_KEY", "")

    PHISHTANK_API_KEY: str = os.getenv("PHISHTANK_API_KEY", "")

    GOOGLE_SAFE_BROWSING_API_KEY: str = os.getenv(
        "GOOGLE_SAFE_BROWSING_API_KEY", ""
    )

    # --- Server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def validate(cls) -> list[str]:
        errors: list[str] = []
        if not cls.FEATHERLESS_API_KEY:
            errors.append("FEATHERLESS_API_KEY not set in .env")
        return errors
