"""POST /api/v1/second-stage/analyze — persuasion + education for users who insist on visiting."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from schemas.requests import SecondStageRequest
from schemas.responses import SecondStageResponse
from services.second_stage_analyzer import SecondStageAnalyzerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/second-stage", tags=["second_stage"])


@router.post("/analyze", response_model=SecondStageResponse)
async def second_stage_analyze(body: SecondStageRequest) -> SecondStageResponse:
    """
    第二階段分析：使用者明知有害仍想進入的理由勸阻。

    需要提供：
    - user_input: 使用者的理由文字
    - first_stage_report: 第一階段產出的完整報告 JSON
    """
    try:
        svc = SecondStageAnalyzerService()
        result = await svc.analyze(body.user_input, body.first_stage_report)
        return SecondStageResponse(**result)
    except Exception as exc:
        logger.error("Second stage analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"分析失敗：{exc}") from exc
