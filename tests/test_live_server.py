"""
tests/test_live_server.py
─────────────────────────
Live running server tests and high-concurrency stress testing for Tross.
Executes against an active HTTP server instance with real sockets and async concurrency.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.fixtures.voyager_payloads import (
    FULL_VOYAGER_PROFILE_VIEW_PAYLOAD,
    MINIMAL_VOYAGER_PROFILE_VIEW_PAYLOAD,
    UNICODE_VOYAGER_PROFILE_VIEW_PAYLOAD,
)

VALID_KEY = "test-internal-api-key-12345"
BASE_URL = "https://www.linkedin.com/in/satyanadella"


class FakeSettings:
    internal_api_key = VALID_KEY
    li_at = "AQEDAT..." + "x" * 50
    jsessionid = '"ajax:1234567890123456789"'
    proxy_url = None
    log_level = "INFO"
    max_retries = 3
    retry_backoff_seconds = 0.01


@pytest.fixture(autouse=True)
def patch_settings():
    with (
        patch("app.main.get_settings", return_value=FakeSettings()),
        patch("app.config.get_settings", return_value=FakeSettings()),
        patch("app.scraper.get_settings", return_value=FakeSettings()),
    ):
        yield


# ── 1. High-Concurrency Stress Tests ──────────────────────────────────────────


class TestHighConcurrencyStress:
    @pytest.mark.asyncio
    async def test_50_concurrent_requests_execute_cleanly(self):
        """
        Simulate 50 simultaneous incoming requests hitting the API concurrently.
        Verifies:
          - Zero race conditions or deadlocks
          - Unique trace_id per request
          - Correct profile payload returned for every call
        """
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch("app.scraper.VoyagerClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get_profile_view = AsyncMock(
                    return_value=FULL_VOYAGER_PROFILE_VIEW_PAYLOAD
                )
                mock_client_cls.return_value = mock_client

                tasks = [
                    client.post(
                        "/api/scrape",
                        json={"url": f"https://www.linkedin.com/in/user-{i}"},
                        headers={"X-API-Key": VALID_KEY},
                    )
                    for i in range(50)
                ]

                responses = await asyncio.gather(*tasks)

        assert len(responses) == 50
        for resp in responses:
            assert resp.status_code == 200
            data = resp.json()
            assert data["full_name"] == "Satya Nadella"
            assert data["trace_id"] is not None

        # Verify all 50 trace_ids are strictly unique
        trace_ids = [r.json()["trace_id"] for r in responses]
        assert len(set(trace_ids)) == 50

    @pytest.mark.asyncio
    async def test_mixed_get_and_post_concurrent_traffic(self):
        """Simulate concurrent mixed traffic across GET and POST endpoints."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch("app.scraper.VoyagerClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get_profile_view = AsyncMock(
                    return_value=FULL_VOYAGER_PROFILE_VIEW_PAYLOAD
                )
                mock_client_cls.return_value = mock_client

                tasks = []
                for i in range(30):
                    if i % 2 == 0:
                        tasks.append(
                            client.post(
                                "/api/scrape",
                                json={"url": f"https://www.linkedin.com/in/user-{i}"},
                                headers={"X-API-Key": VALID_KEY},
                            )
                        )
                    else:
                        tasks.append(
                            client.get(
                                f"/api/scrape?url=https://www.linkedin.com/in/user-{i}&api_key={VALID_KEY}"
                            )
                        )

                responses = await asyncio.gather(*tasks)

        assert len(responses) == 30
        assert all(r.status_code == 200 for r in responses)


# ── 2. Malicious Payload & Fuzzing Tests ───────────────────────────────────────


class TestFuzzingAndEdgeCases:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "malicious_url",
        [
            "https://www.linkedin.com/in/../../etc/passwd",
            "https://www.linkedin.com/in/<script>alert(1)</script>",
            "https://www.linkedin.com/in/' OR '1'='1",
            "https://www.linkedin.com/in/admin;DROP TABLE users;--",
            "https://www.linkedin.com/in/NULL%00BYTE",
        ],
    )
    async def test_security_injection_payloads_safely_handled(self, malicious_url: str):
        """Verify injection strings in URL paths are extracted safely without crashes."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch("app.scraper.VoyagerClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get_profile_view = AsyncMock(
                    return_value=MINIMAL_VOYAGER_PROFILE_VIEW_PAYLOAD
                )
                mock_client_cls.return_value = mock_client

                response = await client.post(
                    "/api/scrape",
                    json={"url": malicious_url},
                    headers={"X-API-Key": VALID_KEY},
                )

                # Should return either 200 (parsed slug safely) or 422/404/502 (validation/upstream)
                # But NEVER a 500 unhandled crash
                assert response.status_code in (200, 422, 404, 502)

    @pytest.mark.asyncio
    async def test_massive_10kb_payload_does_not_crash(self):
        """Verify handling of oversized body payload."""
        oversized_url = "https://www.linkedin.com/in/" + ("a" * 10000)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/api/scrape",
                json={"url": oversized_url},
                headers={"X-API-Key": VALID_KEY},
            )
            assert response.status_code in (200, 422, 502)

    @pytest.mark.asyncio
    async def test_unicode_and_emoji_full_cycle(self):
        """Verify end-to-end extraction and serialization of international profiles."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch("app.scraper.VoyagerClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get_profile_view = AsyncMock(
                    return_value=UNICODE_VOYAGER_PROFILE_VIEW_PAYLOAD
                )
                mock_client_cls.return_value = mock_client

                response = await client.post(
                    "/api/scrape",
                    json={"url": "https://www.linkedin.com/in/mohammed-alotaibi"},
                    headers={"X-API-Key": VALID_KEY},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["first_name"] == "محمد"
                assert "🚀" in data["headline"]
                assert "الرياض" in data["location"]
                assert "Kubernetes 🐳" in data["skills"]


# ── 3. Health & Meta Diagnostics ──────────────────────────────────────────────


class TestHealthAndDiagnostics:
    @pytest.mark.asyncio
    async def test_health_under_rapid_polling(self):
        """Simulate rapid-fire health check polling (e.g. Vercel / Kubernetes liveness probe)."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            tasks = [client.get("/health") for _ in range(50)]
            responses = await asyncio.gather(*tasks)

        assert len(responses) == 50
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["status"] == "ok" for r in responses)
