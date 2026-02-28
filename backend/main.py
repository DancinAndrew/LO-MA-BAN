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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

app = FastAPI(
    title="ScoutNet API",
    description="Backend proxy for ScoutNet Chrome Extension — security check + AI analysis",
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


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=True,
    )
