from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.cached_security_checker import CachedSecurityChecker


class StubSecurityChecker:
    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls = 0

    async def check_all(self, target_url: str) -> dict:
        self.calls += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return {
            "target_url": target_url,
            "overall_risk": "low",
            "call_number": self.calls,
        }


@pytest.mark.asyncio
async def test_cache_miss_then_hit() -> None:
    stub = StubSecurityChecker()
    checker = CachedSecurityChecker(stub, ttl_seconds=60, max_size=128)

    first = await checker.check_all("http://example.com")
    second = await checker.check_all("http://example.com")

    assert stub.calls == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["call_number"] == 1


@pytest.mark.asyncio
async def test_ttl_expired_calls_backend_again() -> None:
    stub = StubSecurityChecker()
    checker = CachedSecurityChecker(stub, ttl_seconds=1, max_size=128)

    await checker.check_all("http://example.com")
    await asyncio.sleep(1.1)
    second = await checker.check_all("http://example.com")

    assert stub.calls == 2
    assert second["cached"] is False
    assert second["call_number"] == 2


@pytest.mark.asyncio
async def test_different_urls_use_different_cache_keys() -> None:
    stub = StubSecurityChecker()
    checker = CachedSecurityChecker(stub, ttl_seconds=60, max_size=128)

    await checker.check_all("http://example.com")
    await checker.check_all("http://another.com")

    assert stub.calls == 2


@pytest.mark.asyncio
async def test_url_is_case_sensitive_cache_key() -> None:
    stub = StubSecurityChecker()
    checker = CachedSecurityChecker(stub, ttl_seconds=60, max_size=128)

    await checker.check_all("http://Example.com/")
    await checker.check_all("http://example.com/")

    assert stub.calls == 2


@pytest.mark.asyncio
async def test_invalidate_removes_single_url() -> None:
    stub = StubSecurityChecker()
    checker = CachedSecurityChecker(stub, ttl_seconds=60, max_size=128)

    await checker.check_all("http://example.com")
    await checker.invalidate("http://example.com")
    second = await checker.check_all("http://example.com")

    assert stub.calls == 2
    assert second["cached"] is False


@pytest.mark.asyncio
async def test_clear_removes_all_cache() -> None:
    stub = StubSecurityChecker()
    checker = CachedSecurityChecker(stub, ttl_seconds=60, max_size=128)

    await checker.check_all("http://example.com")
    await checker.check_all("http://another.com")
    await checker.clear()
    await checker.check_all("http://example.com")
    await checker.check_all("http://another.com")

    assert stub.calls == 4


@pytest.mark.asyncio
async def test_concurrent_requests_same_url_only_call_backend_once() -> None:
    stub = StubSecurityChecker(delay=0.05)
    checker = CachedSecurityChecker(stub, ttl_seconds=60, max_size=128)
    url = "http://example.com"

    results = await asyncio.gather(*[checker.check_all(url) for _ in range(10)])

    assert stub.calls == 1
    assert any(r["cached"] is False for r in results)
    assert any(r["cached"] is True for r in results)
