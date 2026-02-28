"""ScoutNet Backend — FastAPI entry point."""
from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from schemas.responses import HealthResponse
from routers.analyze import router as analyze_router
from routers.second_stage import router as second_stage_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

app = FastAPI(
    title="ScoutNet API",
    description="兒童網路安全網址分析 API — 資安檢查 + AI 內容適齡分析",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(second_stage_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    return HealthResponse()


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None, help="Port to bind (default: from PORT env or 8000)")
    parser.add_argument("--host", type=str, default=None, help="Host to bind (default: from HOST env or 0.0.0.0)")
    args = parser.parse_args()
    port = args.port if args.port is not None else Config.PORT
    host = args.host if args.host is not None else Config.HOST

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
    )
