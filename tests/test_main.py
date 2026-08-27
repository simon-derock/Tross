"""
tests/test_main.py
──────────────────
FastAPI endpoint tests via httpx AsyncClient.
Tests all endpoints, security headers, auth guards, response codes, and exception handlers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.network import (
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
)
from app.schemas import ProfileResponse
from app.scraper import ScraperError

VALID_KEY = "test-internal-api-key-12345"
VALID_URL = "https://www.linkedin.com/in/satyanadella"

FAKE_PROFILE = ProfileResponse(
    linkedin_url=VALID_URL,
    profile_id="satyanadella",
    full_name="Satya Nadella",
    headline="Chairman and CEO at Microsoft",
    location="Greater Seattle Area",
    trace_id="abc123def456",
)


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
    """Patch get_settings across all modules."""
    with (
        patch("app.main.get_settings", return_value=FakeSettings()),
        patch("app.config.get_settings", return_value=FakeSettings()),
        patch("app.scraper.get_settings", return_value=FakeSettings()),
    ):
        yield


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── 1. /health Endpoint Tests ─────────────────────────────────────────────────


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "tross"

    @pytest.mark.asyncio
    async def test_health_requires_no_auth(self, client):
        response = await client.get("/health")
        assert response.status_code != status.HTTP_401_UNAUTHORIZED


# ── 2. /api/scrape Security & Auth Tests ──────────────────────────────────────


class TestScrapeAuth:
    @pytest.mark.asyncio
    async def test_missing_api_key_header_returns_422(self, client):
        response = await client.post("/api/scrape", json={"linkedin_url": VALID_URL})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, client):
        response = await client.post(
            "/api/scrape",
            json={"linkedin_url": VALID_URL},
            headers={"X-API-Key": "invalid_wrong_key"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or missing X-API-Key" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_url_payload_returns_422(self, client):
        response = await client.post(
            "/api/scrape",
            json={"linkedin_url": "https://google.com/not-linkedin"},
            headers={"X-API-Key": VALID_KEY},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── 3. /api/scrape Endpoint Success & Exception Handling Tests ────────────────


class TestScrapeEndpointResponses:
    @pytest.mark.asyncio
    async def test_successful_scrape_returns_200_and_profile_payload(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE

            response = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Satya Nadella"
        assert data["profile_id"] == "satyanadella"
        assert data["headline"] == "Chairman and CEO at Microsoft"
        assert data["trace_id"] is not None

    @pytest.mark.asyncio
    async def test_auth_error_returns_401_json(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = AuthenticationError("Session cookies expired")

            response = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Session cookies expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_profile_not_found_returns_404_json(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = ProfileNotFoundError("Member not found")

            response = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Member not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rate_limit_error_returns_429_json(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = RateLimitError("Rate limit triggered")

            response = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit triggered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upstream_scraper_error_returns_502_json(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = ScraperError("Network drop 502")

            response = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Network drop 502" in response.json()["detail"]
