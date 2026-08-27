"""
app/session.py
──────────────
Upstash Redis session cache for LinkedIn cookies.
Persists li_at / JSESSIONID across stateless Vercel invocations,
preventing repeated re-authentication and reducing account flag risk.
"""

from __future__ import annotations

import json

import redis.asyncio as aioredis

from app.logging_config import get_logger

logger = get_logger(__name__)

_SESSION_KEY = "tross:linkedin:session"
_TTL_SECONDS = 60 * 60 * 20  # 20 hours — LinkedIn sessions typically last 24h


class SessionCache:
    """Async Redis client wrapper for cookie persistence."""

    def __init__(self, redis_url: str) -> None:
        self._client: aioredis.Redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

    async def get_cookies(self) -> dict[str, str] | None:
        """
        Retrieve cached cookies.
        Returns None if cache miss or Redis unavailable.
        """
        try:
            raw = await self._client.get(_SESSION_KEY)
            if raw:
                logger.info("session.cache_hit")
                return json.loads(raw)
            logger.info("session.cache_miss")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("session.redis_read_error", error=str(exc))
            return None

    async def set_cookies(self, cookies: dict[str, str]) -> None:
        """Persist cookies with TTL. Fails silently to not block scraping."""
        try:
            await self._client.setex(_SESSION_KEY, _TTL_SECONDS, json.dumps(cookies))
            logger.info("session.cache_written", ttl=_TTL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.warning("session.redis_write_error", error=str(exc))

    async def invalidate(self) -> None:
        """Delete cached session (call after a 401/403 from LinkedIn)."""
        try:
            await self._client.delete(_SESSION_KEY)
            logger.info("session.cache_invalidated")
        except Exception as exc:  # noqa: BLE001
            logger.warning("session.redis_delete_error", error=str(exc))

    async def close(self) -> None:
        await self._client.aclose()
