from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------- Security check sub-models ----------

class CriticalFlag(BaseModel):
    source: str
    threat_type: Optional[Any] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class Warning(BaseModel):
    source: str
    reason: Optional[Any] = None


class SecurityCheckResult(BaseModel, extra="allow"):
    overall_risk: str = "inconclusive"
    confidence: str = "low"
    risk_score: int = 0
    checked_sources: int = 0
    critical_flags: List[CriticalFlag] = Field(default_factory=list)
    warnings: List[Warning] = Field(default_factory=list)
    raw_results: List[Dict[str, Any]] = Field(default_factory=list)
    target_url: str = ""
    timestamp: str = ""


# ---------- LLM analysis ----------

class LLMAnalysisResult(BaseModel, extra="allow"):
    risk_level: str = "inconclusive"
    confidence: str = "low"
    risk_score: int = 50
    threat_summary: str = ""
    fallback_mode: bool = False


# ---------- Report ----------

class ReportResponse(BaseModel, extra="allow"):
    report_metadata: Dict[str, Any] = Field(default_factory=dict)
    kid_friendly_summary: Dict[str, Any] = Field(default_factory=dict)
    evidence_cards: List[Dict[str, Any]] = Field(default_factory=list)
    pattern_analysis: Dict[str, Any] = Field(default_factory=dict)
    interactive_quiz: Dict[str, Any] = Field(default_factory=dict)
    safety_tips: List[Dict[str, Any]] = Field(default_factory=list)
    next_steps: List[Dict[str, Any]] = Field(default_factory=list)
    raw_analysis: Dict[str, Any] = Field(default_factory=dict)


# ---------- Top-level responses ----------

class AnalyzeResponse(BaseModel):
    target_url: str
    risk_source: str = "phishing"
    security_check: Dict[str, Any] = Field(default_factory=dict)
    llm_analysis: Optional[Dict[str, Any]] = None
    content_classification: Optional[Dict[str, Any]] = None
    report: Optional[ReportResponse] = None
    final_risk_level: str = "inconclusive"
    timestamp: str = ""


class SecondStageResponse(BaseModel):
    user_input: str
    first_stage_report_summary: Dict[str, Any] = Field(default_factory=dict)
    second_stage_result: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
