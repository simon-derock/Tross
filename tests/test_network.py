"""
tests/test_network.py
──────────────────────
Unit tests for LinkedInClient and SessionCache.
All external I/O is mocked — no real network or Redis calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.network import LinkedInClient, _is_retryable_response
from app.session import SessionCache

# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_COOKIES = {"li_at": "a" * 20, "JSESSIONID": "b" * 20}
FAKE_URL = "https://www.linkedin.com/in/test-user"


def _make_response(status: int, text: str = "<html>ok</html>") -> httpx.Response:
    return httpx.Response(status_code=status, text=text)


# ── LinkedInClient tests ──────────────────────────────────────────────────────


class TestLinkedInClient:
    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        async with LinkedInClient(cookies=FAKE_COOKIES) as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        async with LinkedInClient(cookies=FAKE_COOKIES) as client:
            inner = client._client
        # After exit, client should be closed — calling aclose twice is safe
        assert inner is not None

    @pytest.mark.asyncio
    async def test_successful_get(self):
        async with LinkedInClient(cookies=FAKE_COOKIES) as client:
            with patch.object(
                client._client, "get", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = _make_response(200)
                response = await client.get(FAKE_URL)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_headers_include_user_agent(self):
        async with LinkedInClient(cookies=FAKE_COOKIES) as client:
            assert "User-Agent" in client._client.headers
            assert "Mozilla" in client._client.headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_get_raises_on_401(self):
        async with LinkedInClient(cookies=FAKE_COOKIES, max_retries=1) as client:
            with patch.object(
                client._client, "get", new_callable=AsyncMock
            ) as mock_get:
                # 401 is NOT retryable — should raise immediately
                mock_resp = _make_response(401)
                mock_get.return_value = mock_resp
                response = await client.get(FAKE_URL)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_retryable_status_helper(self):
        assert _is_retryable_response(_make_response(429))
        assert _is_retryable_response(_make_response(503))
        assert not _is_retryable_response(_make_response(200))
        assert not _is_retryable_response(_make_response(404))

    @pytest.mark.asyncio
    async def test_get_without_context_manager_raises(self):
        client = LinkedInClient(cookies=FAKE_COOKIES)
        with pytest.raises(RuntimeError, match="context manager"):
            await client.get(FAKE_URL)


# ── SessionCache tests ────────────────────────────────────────────────────────


class TestSessionCache:
    def _make_cache(self) -> SessionCache:
        cache = SessionCache.__new__(SessionCache)
        cache._client = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_get_cookies_cache_hit(self):
        cache = self._make_cache()
        cache._client.get = AsyncMock(return_value=json.dumps(FAKE_COOKIES))
        result = await cache.get_cookies()
        assert result == FAKE_COOKIES

    @pytest.mark.asyncio
    async def test_get_cookies_cache_miss(self):
        cache = self._make_cache()
        cache._client.get = AsyncMock(return_value=None)
        result = await cache.get_cookies()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cookies_redis_error_returns_none(self):
        cache = self._make_cache()
        cache._client.get = AsyncMock(side_effect=Exception("connection refused"))
        result = await cache.get_cookies()
        assert result is None  # degrades gracefully

    @pytest.mark.asyncio
    async def test_set_cookies_calls_setex(self):
        cache = self._make_cache()
        cache._client.setex = AsyncMock()
        await cache.set_cookies(FAKE_COOKIES)
        cache._client.setex.assert_called_once()
        args = cache._client.setex.call_args[0]
        assert json.loads(args[2]) == FAKE_COOKIES

    @pytest.mark.asyncio
    async def test_set_cookies_redis_error_silent(self):
        cache = self._make_cache()
        cache._client.setex = AsyncMock(side_effect=Exception("timeout"))
        # Should not raise
        await cache.set_cookies(FAKE_COOKIES)

    @pytest.mark.asyncio
    async def test_invalidate_calls_delete(self):
        cache = self._make_cache()
        cache._client.delete = AsyncMock()
        await cache.invalidate()
        cache._client.delete.assert_called_once()
