"""POST /api/v1/scan/persuade — persuasion endpoint for second-stage input."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_persuasion_service
from schemas.requests import PersuasionRequest
from schemas.responses import PersuasionResponse
from services.persuasion import PersuasionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/scan", tags=["persuasion"])


@router.post("/persuade", response_model=PersuasionResponse)
async def persuade_user(
    body: PersuasionRequest,
    svc: Annotated[PersuasionService, Depends(get_persuasion_service)],
) -> PersuasionResponse:
    try:
        result = await svc.analyze(
            body.user_input,
            body.first_stage_report.model_dump(),
        )
        return PersuasionResponse(**result)
    except Exception:
        logger.exception("Persuasion analysis failed")
        raise HTTPException(
            status_code=500,
            detail="分析失敗，請稍後再試",
        )
