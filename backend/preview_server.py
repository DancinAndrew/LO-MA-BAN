#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preview image API: POST /api/preview-url — uses Playwright to screenshot the target URL and return base64 image.
Run: cd backend && pip install -r requirements-preview.txt && python -m playwright install chromium && uvicorn preview_server:app --host 0.0.0.0 --port 8001
"""
import base64
import logging
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ScoutNet Preview API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PreviewRequest(BaseModel):
    url: str


def is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


@app.get("/")
def root():
    return {"message": "ScoutNet Preview API", "preview": "POST /api/preview-url with body {\"url\": \"https://...\"}"}


@app.post("/api/preview-url")
async def preview_url(req: PreviewRequest):
    url = (req.url or "").strip()
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL: only http/https allowed")
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && python -m playwright install chromium")
        raise HTTPException(
            status_code=503,
            detail="Preview service unavailable: Playwright not installed",
        )
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(1500)
            raw = await page.screenshot(type="png")
            await browser.close()
        b64 = base64.b64encode(raw).decode("ascii")
        return {"image": b64}
    except Exception as e:
        logger.exception("Preview failed for %s", url)
        raise HTTPException(status_code=502, detail=f"Preview failed: {e!s}")
