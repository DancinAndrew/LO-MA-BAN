from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ---------- Security check sub-models ----------


class CriticalFlag(BaseModel):
    source: str
    threat_type: Optional[Any] = None
    details: Dict[str, Any] | list[Any] = Field(default_factory=dict)


class Warning(BaseModel):
    source: str
    reason: Optional[Any] = None


class SecurityCheckResult(BaseModel, extra="allow"):
    overall_risk: str = "inconclusive"
    confidence: str = "low"
    risk_score: int = 0
    checked_sources: int = 0
    critical_flags: list[CriticalFlag] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    raw_results: list[Dict[str, Any]] = Field(default_factory=list)
    target_url: str = ""
    timestamp: str = ""


# ---------- LLM analysis ----------


class LLMAnalysisResult(BaseModel, extra="allow"):
    risk_level: str = "inconclusive"
    confidence: str = "low"
    risk_score: int = 50
    threat_summary: str = ""
    fallback_mode: bool = False


# ---------- Content classification ----------


class ContentClassification(BaseModel, extra="allow"):
    labels: list[str] = Field(default_factory=list)
    primary_label: str = "不明"
    confidence: str = "low"
    explanation: str = ""
    is_unsuitable_for_children: bool = False


# ---------- Report sub-models ----------


class RiskInfo(BaseModel, extra="allow"):
    level: str = "inconclusive"
    score: int = 50
    icon: str = ""
    color: str = ""
    label: str = ""


class ConfidenceInfo(BaseModel, extra="allow"):
    level: str = "low"
    icon: str = ""
    label: str = ""


class ReportMetadata(BaseModel, extra="allow"):
    target_url: str = ""
    target_domain: str = ""
    target_tld: str = ""
    timestamp: str = ""
    risk: RiskInfo = Field(default_factory=RiskInfo)
    confidence: ConfidenceInfo = Field(default_factory=ConfidenceInfo)


class KidFriendlySummary(BaseModel, extra="allow"):
    title: str = ""
    simple_message: str = ""
    short_explanation: str = ""
    emoji_reaction: str = ""
    action_verb: str = ""


class EvidenceCard(BaseModel, extra="allow"):
    id: str = ""
    icon: str = ""
    title: str = ""
    content: str = ""
    severity: str = "medium"
    expandable: bool = False


class QuizOption(BaseModel, extra="allow"):
    id: str
    text: str
    is_correct: bool = False
    explanation: str = ""
    feedback_icon: str = ""


class InteractiveQuiz(BaseModel, extra="allow"):
    enabled: bool = True
    question: str = ""
    hint: Optional[str] = None
    type: str = "single_choice"
    options: list[QuizOption] = Field(default_factory=list)
    correct_answer_id: Optional[str] = None
    learning_point: str = ""
    difficulty: str = "easy"


class SafetyTip(BaseModel, extra="allow"):
    id: str = ""
    icon: str = ""
    tip: str = ""
    why: str = ""
    action_text: str = ""


class NextStep(BaseModel, extra="allow"):
    action: str = ""
    priority: str = "medium"
    icon: str = ""
    link: Optional[str] = None


class ReportResponse(BaseModel, extra="allow"):
    report_metadata: ReportMetadata = Field(default_factory=ReportMetadata)
    kid_friendly_summary: KidFriendlySummary = Field(default_factory=KidFriendlySummary)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
    pattern_analysis: Dict[str, Any] = Field(default_factory=dict)
    interactive_quiz: InteractiveQuiz = Field(default_factory=InteractiveQuiz)
    safety_tips: list[SafetyTip] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)
    raw_analysis: Dict[str, Any] = Field(default_factory=dict)


# ---------- Second stage ----------


class ReasonAnalysis(BaseModel, extra="allow"):
    is_reasonable: bool = False
    analysis: str = ""
    empathy_note: str = ""


class PersuasionResult(BaseModel, extra="allow"):
    behavior_consequence_warning: str = ""
    reason_analysis: ReasonAnalysis = Field(default_factory=ReasonAnalysis)
    general_warnings: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    encouraging_message: str = ""


class FirstStageSummary(BaseModel, extra="allow"):
    target_url: Optional[str] = None
    risk_level: Optional[str] = None
    risk_label: Optional[str] = None
    risk_score: Optional[int] = None
    risk_source: Optional[str] = None


# ---------- Top-level responses ----------


class ScanResponse(BaseModel):
    target_url: str
    risk_source: str = "phishing"
    security_check: SecurityCheckResult = Field(default_factory=SecurityCheckResult)
    llm_analysis: Optional[LLMAnalysisResult] = None
    content_classification: Optional[ContentClassification] = None
    report: Optional[ReportResponse] = None
    final_risk_level: str = "inconclusive"
    timestamp: str = ""


class PersuasionResponse(BaseModel):
    user_input: str
    first_stage_report_summary: FirstStageSummary = Field(
        default_factory=FirstStageSummary
    )
    second_stage_result: PersuasionResult = Field(default_factory=PersuasionResult)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
