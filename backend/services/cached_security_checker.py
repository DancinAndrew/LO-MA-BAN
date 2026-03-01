"""Cached wrapper for SecurityCheckerService."""
from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any

from cachetools import TTLCache

from services.security_checker import SecurityCheckerService

logger = logging.getLogger("services.security_checker")


class CachedSecurityChecker:
    def __init__(
        self,
        checker: SecurityCheckerService,
        *,
        ttl_seconds: int,
        max_size: int,
    ) -> None:
        self._checker = checker
        self._cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self._cache_lock = asyncio.Lock()
        self._inflight_locks: dict[str, asyncio.Lock] = {}
        self._inflight_locks_guard = asyncio.Lock()

    async def _read_cache(self, key: str) -> dict[str, Any] | None:
        async with self._cache_lock:
            cached = self._cache.get(key)
            return deepcopy(cached) if cached is not None else None

    async def _write_cache(self, key: str, value: dict[str, Any]) -> None:
        async with self._cache_lock:
            self._cache[key] = deepcopy(value)

    async def _get_inflight_lock(self, key: str) -> asyncio.Lock:
        async with self._inflight_locks_guard:
            lock = self._inflight_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._inflight_locks[key] = lock
            return lock

    async def check_all(self, target_url: str) -> dict[str, Any]:
        key = target_url
        logger.info("Security check started: %s", target_url)

        cached = await self._read_cache(key)
        if cached is not None:
            logger.info("Security check cache hit: %s", target_url)
            cached["cached"] = True
            return cached

        logger.info("Security check cache miss: %s", target_url)
        inflight = await self._get_inflight_lock(key)
        async with inflight:
            cached = await self._read_cache(key)
            if cached is not None:
                logger.info("Security check cache hit (after wait): %s", target_url)
                cached["cached"] = True
                return cached

            fresh = await self._checker.check_all(target_url)
            base_result = deepcopy(fresh)
            base_result.pop("cached", None)
            await self._write_cache(key, base_result)

        result = deepcopy(base_result)
        result["cached"] = False
        return result

    async def invalidate(self, target_url: str) -> None:
        key = target_url
        async with self._cache_lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        async with self._cache_lock:
            self._cache.clear()
