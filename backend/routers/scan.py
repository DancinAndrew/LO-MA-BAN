"""POST /api/v1/scan — first-stage URL scanning endpoint."""
from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from dependencies import get_scan_orchestrator
from schemas.requests import ScanRequest
from schemas.responses import ScanResponse
from services.scan_orchestrator import ScanOrchestrator

router = APIRouter(prefix="/api/v1", tags=["scan"])

_CACHE_TTL = 300  # 5 minutes
_scan_cache: dict[str, tuple[float, ScanResponse]] = {}


def _get_cached(url: str) -> ScanResponse | None:
    entry = _scan_cache.get(url)
    if entry and time.monotonic() - entry[0] < _CACHE_TTL:
        return entry[1]
    if entry:
        _scan_cache.pop(url, None)
    return None


def _set_cached(url: str, resp: ScanResponse) -> None:
    _scan_cache[url] = (time.monotonic(), resp)
    if len(_scan_cache) > 500:
        oldest_key = next(iter(_scan_cache))
        _scan_cache.pop(oldest_key, None)


@router.post("/scan", response_model=ScanResponse)
async def scan_url(
    body: ScanRequest,
    orchestrator: Annotated[ScanOrchestrator, Depends(get_scan_orchestrator)],
) -> ScanResponse:
    url = str(body.url)
    cached = _get_cached(url)
    if cached is not None:
        return cached

    result = await orchestrator.execute(
        target_url=url,
        quick_scan=body.quick_scan,
        force_deep_analysis=body.force_deep_analysis,
    )
    _set_cached(url, result)
    return result
