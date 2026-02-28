from __future__ import annotations

from pydantic import BaseModel, HttpUrl, Field


class AnalyzeRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target URL to analyze")
    skip_llm: bool = Field(False, description="Only run security check, skip LLM")
    force_llm: bool = Field(False, description="Force LLM even when risk is low")


class SecondStageRequest(BaseModel):
    user_input: str = Field(
        ...,
        description="使用者解釋為什麼仍想進入有害網站的理由",
        min_length=1,
    )
    first_stage_report: dict = Field(
        ...,
        description="第一階段產出的完整報告 JSON",
    )
