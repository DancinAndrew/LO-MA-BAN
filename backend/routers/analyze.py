"""POST /api/v1/analyze — orchestrates security check → LLM analysis → report."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from schemas.requests import AnalyzeRequest
from schemas.responses import AnalyzeResponse
from services.security_checker import SecurityCheckerService
from services.llm_analyzer import LLMAnalyzerService
from services.report_generator import ReportGeneratorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(body: AnalyzeRequest) -> AnalyzeResponse:
    target_url = str(body.url)

    # Step 1 — Security check (4 APIs in parallel)
    security_svc = SecurityCheckerService()
    try:
        security_results = await security_svc.check_all(target_url)
    except Exception as exc:
        logger.error("Security check failed: %s", exc)
        raise HTTPException(status_code=502, detail="Security API check failed") from exc

    overall_risk = security_results.get("overall_risk", "inconclusive")

    # Step 2 — LLM deep analysis when risk is notable
    llm_analysis: dict | None = None
    should_call_llm = overall_risk in ("critical", "high", "medium")

    if should_call_llm:
        llm_svc = LLMAnalyzerService()
        try:
            llm_analysis = await llm_svc.analyze(target_url, security_results)
        except Exception as exc:
            logger.error("LLM analysis failed: %s", exc)
            llm_analysis = LLMAnalyzerService._fallback(security_results)

    final_risk = (
        llm_analysis.get("risk_level", overall_risk) if llm_analysis else overall_risk
    )

    # Step 3 — Generate kid-friendly report
    analysis_data = llm_analysis or security_results
    cleaned_results = security_results.get("raw_results", [])
    report_svc = ReportGeneratorService(
        target_url=target_url,
        analysis_result=analysis_data,
        cleaned_results=cleaned_results,
    )
    report = report_svc.generate()

    return AnalyzeResponse(
        target_url=target_url,
        security_check=security_results,
        llm_analysis=llm_analysis,
        report=report,
        final_risk_level=final_risk,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
