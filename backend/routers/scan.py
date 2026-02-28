"""POST /api/v1/scan — first-stage URL scanning endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies import get_scan_orchestrator
from schemas.requests import ScanRequest
from schemas.responses import ScanResponse
from services.scan_orchestrator import ScanOrchestrator

router = APIRouter(prefix="/api/v1", tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
async def scan_url(
    body: ScanRequest,
    orchestrator: Annotated[ScanOrchestrator, Depends(get_scan_orchestrator)],
) -> ScanResponse:
    return await orchestrator.execute(
        target_url=str(body.url),
        quick_scan=body.quick_scan,
        force_deep_analysis=body.force_deep_analysis,
    )
