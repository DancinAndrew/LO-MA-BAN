"""ScoutNet Backend — FastAPI entry point."""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_settings
from schemas.responses import HealthResponse
from routers.scan import router as scan_router
from routers.persuade import router as persuade_router
from middleware import RequestIDMiddleware, RequestIDFilter
from exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

# ── Structured logging with request_id ──

_rid_filter = RequestIDFilter()
_formatter = logging.Formatter(
    "%(asctime)s [%(request_id)s] %(levelname)s %(name)s — %(message)s"
)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(_formatter)
_handler.addFilter(_rid_filter)
logging.basicConfig(level=logging.INFO, handlers=[_handler])


# ── Lifespan: validate config on startup ──


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    errors = settings.validate_required()
    if errors:
        for e in errors:
            logging.getLogger(__name__).warning("Config warning: %s", e)
    yield


# ── App factory ──

settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    description="兒童網路安全網址分析 API — 資安檢查 + AI 內容適齡分析",
    version=settings.app_version,
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

# Routers
app.include_router(scan_router)
app.include_router(persuade_router)


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
    _s = get_settings()
    port = args.port if args.port is not None else _s.port
    host = args.host if args.host is not None else _s.host

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
    )
