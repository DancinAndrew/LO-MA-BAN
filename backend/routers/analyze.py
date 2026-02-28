"""POST /api/v1/analyze — first-stage: security check → content check → LLM → report."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from schemas.requests import AnalyzeRequest
from schemas.responses import AnalyzeResponse
from services.security_checker import SecurityCheckerService
from services.llm_analyzer import LLMAnalyzerService
from services.content_checker import ContentCheckerService, is_unsuitable_for_children
from services.report_generator import ReportGeneratorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(body: AnalyzeRequest) -> AnalyzeResponse:
    """
    完整第一階段分析流程：

    1. 安全平台 API 檢查（VirusTotal / URLhaus / PhishTank / Google SB）
    2. 分流：
       - 路徑 A：偵測到釣魚/資安風險 → Featherless AI 深度分析（含預測正確網址 + 推薦替代）
       - 路徑 B：資安無風險 → Exa 取得網頁內容 → 內容適齡檢查 → 若不適當 → LLM 分析
    3. 生成兒童友善報告
    """
    target_url = str(body.url)

    # ── Step 1: Security check ──
    security_svc = SecurityCheckerService()
    try:
        security_results = await security_svc.check_all(target_url)
    except Exception as exc:
        logger.error("Security check failed: %s", exc)
        raise HTTPException(status_code=502, detail="Security API check failed") from exc

    overall_risk = security_results.get("overall_risk", "inconclusive")

    if body.skip_llm and not body.force_llm:
        return AnalyzeResponse(
            target_url=target_url,
            risk_source="none",
            security_check=security_results,
            final_risk_level=overall_risk,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # ── Step 2: Branching ──
    llm_svc = LLMAnalyzerService()
    llm_analysis: dict[str, Any] | None = None
    content_classification: dict[str, Any] | None = None
    risk_source = "none"

    should_call_phishing_llm = overall_risk in ("critical", "high", "medium") or body.force_llm

    if should_call_phishing_llm:
        # Path A: phishing / security risk
        risk_source = "phishing"
        try:
            llm_analysis = await llm_svc.analyze_phishing(target_url, security_results)
        except Exception as exc:
            logger.error("LLM phishing analysis failed: %s", exc)
            llm_analysis = LLMAnalyzerService._fallback_phishing(security_results)
    else:
        # Path B: content suitability check
        content_svc = ContentCheckerService()
        content, content_err = await content_svc.fetch_content(target_url)

        if content:
            content_classification = await content_svc.classify_safety(target_url, content)
            unsuitable = (
                content_classification.get("is_unsuitable_for_children")
                or is_unsuitable_for_children(content_classification)
            )
            if unsuitable:
                risk_source = "content"
                try:
                    llm_analysis = await llm_svc.analyze_content_risk(
                        target_url, content, content_classification
                    )
                except Exception as exc:
                    logger.error("LLM content analysis failed: %s", exc)
                    llm_analysis = LLMAnalyzerService._fallback_content_risk(content_classification)
        else:
            logger.info("Could not fetch content: %s", content_err)

    # ── Step 3: Report ──
    final_risk = (
        llm_analysis.get("risk_level", overall_risk) if llm_analysis else overall_risk
    )

    analysis_data = llm_analysis
    if not analysis_data and final_risk == "low":
        analysis_data = {
            "risk_level": "low", "confidence": "medium", "risk_score": 20,
            "threat_summary": "未偵測到釣魚或明顯不良內容",
            "why_unsafe": "此網址在資安與內容檢查中未發現明顯風險，但仍建議上網時保持警覺喔！",
            "evidence_analysis": [],
            "recommendations": ["保持警覺", "不隨便點陌生連結", "有疑問問爸媽或老師"],
        }
    if not analysis_data:
        analysis_data = security_results

    cleaned_results = security_results.get("raw_results", [])
    report_svc = ReportGeneratorService(
        target_url=target_url,
        analysis_result=analysis_data,
        cleaned_results=cleaned_results,
        risk_source=risk_source,
    )
    report = report_svc.generate()

    return AnalyzeResponse(
        target_url=target_url,
        risk_source=risk_source,
        security_check=security_results,
        llm_analysis=llm_analysis,
        content_classification=content_classification,
        report=report,
        final_risk_level=final_risk,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
