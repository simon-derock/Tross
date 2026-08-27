"""
tests/test_main.py
──────────────────
Comprehensive tests for FastAPI application in app/main.py.

Test coverage:
  • /health endpoint (unauthenticated)
  • POST /api/scrape with X-API-Key header
  • POST /scrape route alias
  • GET /api/scrape with ?url= query parameter
  • GET /scrape route alias
  • Authentication via 'Authorization: Bearer <key>'
  • Authentication via '?api_key=<key>' parameter
  • 401 on missing or invalid API key
  • 404 on profile not found
  • 429 on rate limit
  • 502 on scraper upstream failure
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


# ── 2. Security & Multi-Source Auth Tests ─────────────────────────────────────


class TestScrapeAuth:
    @pytest.mark.asyncio
    async def test_missing_auth_returns_401(self, client):
        response = await client.post("/api/scrape", json={"url": VALID_URL})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, client):
        response = await client.post(
            "/api/scrape",
            json={"url": VALID_URL},
            headers={"X-API-Key": "wrong_key"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_auth_via_bearer_token(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={"Authorization": f"Bearer {VALID_KEY}"},
            )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_auth_via_query_param(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            response = await client.get(
                f"/api/scrape?url={VALID_URL}&api_key={VALID_KEY}"
            )
        assert response.status_code == status.HTTP_200_OK


# ── 3. Route Aliases & Methods (POST / GET) ───────────────────────────────────


class TestRoutesAndMethods:
    @pytest.mark.asyncio
    async def test_post_api_scrape_success(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["full_name"] == "Satya Nadella"

    @pytest.mark.asyncio
    async def test_post_scrape_alias_success(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            response = await client.post(
                "/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["full_name"] == "Satya Nadella"

    @pytest.mark.asyncio
    async def test_get_api_scrape_success(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            response = await client.get(
                f"/api/scrape?url={VALID_URL}",
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["full_name"] == "Satya Nadella"

    @pytest.mark.asyncio
    async def test_get_scrape_alias_success(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            response = await client.get(
                f"/scrape?url={VALID_URL}",
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["full_name"] == "Satya Nadella"


# ── 4. Exception Handling Tests ───────────────────────────────────────────────


class TestExceptionHandling:
    @pytest.mark.asyncio
    async def test_auth_error_returns_401(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = AuthenticationError("LinkedIn session expired")
            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "LinkedIn session expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = ProfileNotFoundError("Profile not found")
            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Profile not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = RateLimitError("Rate limited")
            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limited" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_scraper_error_returns_502(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = ScraperError("Upstream timeout")
            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Upstream timeout" in response.json()["detail"]
