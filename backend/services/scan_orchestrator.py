"""ScanOrchestrator — first-stage URL scan orchestration logic."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import HTTPException

from schemas.responses import ScanResponse
from services.content_checker import ContentCheckerService, is_unsuitable_for_children
from services.report_generator import ReportGeneratorService
from services.security_checker import SecurityCheckerService
from services.threat_analysis import ThreatAnalysisService

logger = logging.getLogger(__name__)


class ScanOrchestrator:
    def __init__(
        self,
        security_checker: SecurityCheckerService,
        threat_analyzer: ThreatAnalysisService,
        content_checker: ContentCheckerService,
        report_generator_factory: Callable[..., ReportGeneratorService],
    ) -> None:
        self._security_checker = security_checker
        self._threat_analyzer = threat_analyzer
        self._content_checker = content_checker
        self._report_generator_factory = report_generator_factory

    async def execute(
        self,
        target_url: str,
        quick_scan: bool,
        force_deep_analysis: bool,
    ) -> ScanResponse:
        # Run security check and content fetch in parallel to save time.
        security_task = asyncio.create_task(
            self._security_checker.check_all(target_url)
        )
        content_task = asyncio.create_task(
            self._content_checker.fetch_content(target_url)
        )

        try:
            security_results = await security_task
        except Exception:
            content_task.cancel()
            logger.exception("Security check failed")
            raise HTTPException(status_code=502, detail="Security API check failed")

        overall_risk = security_results.get("overall_risk", "inconclusive")
        if quick_scan and not force_deep_analysis:
            content_task.cancel()
            return ScanResponse(
                target_url=target_url,
                risk_source="none",
                security_check=security_results,
                final_risk_level=overall_risk,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        llm_analysis: dict[str, Any] | None = None
        content_classification: dict[str, Any] | None = None
        risk_source = "none"

        should_call_phishing_llm = (
            overall_risk in ("critical", "high", "medium") or force_deep_analysis
        )

        if should_call_phishing_llm:
            content_task.cancel()
            risk_source = "phishing"
            try:
                llm_analysis = await self._threat_analyzer.analyze_phishing(
                    target_url, security_results
                )
            except Exception:
                logger.exception("LLM phishing analysis failed")
                llm_analysis = ThreatAnalysisService._fallback_phishing(security_results)
        else:
            try:
                content, content_err = await content_task
            except Exception:
                content, content_err = None, "Content fetch failed"

            if content:
                content_classification = await self._content_checker.classify_safety(
                    target_url, content
                )
                unsuitable = (
                    content_classification.get("is_unsuitable_for_children")
                    or is_unsuitable_for_children(content_classification)
                )
                if unsuitable:
                    risk_source = "content"
                    try:
                        llm_analysis = await self._threat_analyzer.analyze_content_risk(
                            target_url, content, content_classification
                        )
                    except Exception:
                        logger.exception("LLM content analysis failed")
                        llm_analysis = ThreatAnalysisService._fallback_content_risk(
                            content_classification
                        )
            else:
                logger.info("Could not fetch content: %s", content_err)

        final_risk = llm_analysis.get("risk_level", overall_risk) if llm_analysis else overall_risk
        analysis_data = llm_analysis

        if not analysis_data and final_risk == "low":
            analysis_data = {
                "risk_level": "low",
                "confidence": "medium",
                "risk_score": 20,
                "threat_summary": "未偵測到釣魚或明顯不良內容",
                "why_unsafe": "此網址在資安與內容檢查中未發現明顯風險，但仍建議上網時保持警覺喔！",
                "evidence_analysis": [],
                "recommendations": ["保持警覺", "不隨便點陌生連結", "有疑問問爸媽或老師"],
            }
        if not analysis_data:
            analysis_data = security_results

        cleaned_results = security_results.get("raw_results", [])
        report_svc = self._report_generator_factory(
            target_url=target_url,
            analysis_result=analysis_data,
            cleaned_results=cleaned_results,
            risk_source=risk_source,
        )
        report = report_svc.generate()

        return ScanResponse(
            target_url=target_url,
            risk_source=risk_source,
            security_check=security_results,
            llm_analysis=llm_analysis,
            content_classification=content_classification,
            report=report,
            final_risk_level=final_risk,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
