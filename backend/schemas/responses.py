from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------- Security check sub-models ----------

class CriticalFlag(BaseModel):
    source: str
    threat_type: Any | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class Warning(BaseModel):
    source: str
    reason: Any | None = None


class SecurityCheckResult(BaseModel):
    overall_risk: str
    confidence: str
    risk_score: int
    checked_sources: int
    critical_flags: list[CriticalFlag] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    raw_results: list[dict[str, Any]] = Field(default_factory=list)
    target_url: str
    timestamp: str


# ---------- LLM analysis ----------

class LLMAnalysisResult(BaseModel, extra="allow"):
    """LLM response is semi-structured; extra fields are preserved."""
    risk_level: str = "inconclusive"
    confidence: str = "low"
    risk_score: int = 50
    threat_summary: str = ""
    fallback_mode: bool = False


# ---------- Report ----------

class ReportResponse(BaseModel, extra="allow"):
    """Full kid-friendly report; flexible shape forwarded from ReportGenerator."""
    report_metadata: dict[str, Any] = Field(default_factory=dict)
    kid_friendly_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_cards: list[dict[str, Any]] = Field(default_factory=list)
    pattern_analysis: dict[str, Any] = Field(default_factory=dict)
    interactive_quiz: dict[str, Any] = Field(default_factory=dict)
    safety_tips: list[dict[str, Any]] = Field(default_factory=list)
    next_steps: list[dict[str, Any]] = Field(default_factory=list)


# ---------- Top-level response ----------

class AnalyzeResponse(BaseModel):
    target_url: str
    security_check: SecurityCheckResult
    llm_analysis: dict[str, Any] | None = None
    report: ReportResponse
    final_risk_level: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
