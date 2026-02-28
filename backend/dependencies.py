"""Centralised FastAPI dependency providers — one place to override in tests."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from config import Settings, get_settings
from services.security_checker import SecurityCheckerService
from services.content_checker import ContentCheckerService
from services.persuasion import PersuasionService
from services.report_generator import ReportGeneratorService
from services.scan_orchestrator import ScanOrchestrator
from services.threat_analysis import ThreatAnalysisService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_security_checker(settings: SettingsDep) -> SecurityCheckerService:
    return SecurityCheckerService(settings)


def get_threat_analyzer(settings: SettingsDep) -> ThreatAnalysisService:
    return ThreatAnalysisService(settings)


def get_content_checker(settings: SettingsDep) -> ContentCheckerService:
    return ContentCheckerService(settings)


def get_persuasion_service(settings: SettingsDep) -> PersuasionService:
    return PersuasionService(settings)


def get_report_generator_factory() -> type[ReportGeneratorService]:
    return ReportGeneratorService


def get_scan_orchestrator(
    security_checker: Annotated[SecurityCheckerService, Depends(get_security_checker)],
    threat_analyzer: Annotated[ThreatAnalysisService, Depends(get_threat_analyzer)],
    content_checker: Annotated[ContentCheckerService, Depends(get_content_checker)],
    report_generator_factory: Annotated[
        type[ReportGeneratorService], Depends(get_report_generator_factory)
    ],
) -> ScanOrchestrator:
    return ScanOrchestrator(
        security_checker=security_checker,
        threat_analyzer=threat_analyzer,
        content_checker=content_checker,
        report_generator_factory=report_generator_factory,
    )
