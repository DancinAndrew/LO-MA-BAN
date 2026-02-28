from __future__ import annotations

from pydantic import BaseModel, HttpUrl, Field

from schemas.responses import ReportResponse


class ScanRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target URL to analyze")
    quick_scan: bool = Field(
        False,
        description="Only run security API checks and skip deep analysis",
    )
    force_deep_analysis: bool = Field(
        False,
        description="Force deep analysis even when risk is low",
    )


class PersuasionRequest(BaseModel):
    user_input: str = Field(
        ...,
        description="使用者解釋為什麼仍想進入有害網站的理由",
        min_length=1,
    )
    first_stage_report: ReportResponse = Field(
        ...,
        description="第一階段產出的完整報告 JSON",
    )
