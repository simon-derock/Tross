"""
tests/test_main.py
──────────────────
FastAPI endpoint tests via httpx AsyncClient.
All external I/O (scraper, Redis) is mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas import ProfileResponse
from app.scraper import AuthenticationError, ScraperError

VALID_KEY = "test-internal-key-1234"
VALID_URL = "https://www.linkedin.com/in/test-user"

FAKE_PROFILE = ProfileResponse(
    linkedin_url=VALID_URL,
    full_name="Test User",
    headline="Software Engineer",
    location="London, UK",
    trace_id="abc123",
)


class FakeSettings:
    internal_api_key = VALID_KEY
    li_at = "a" * 20
    jsessionid = "b" * 20
    upstash_redis_url = "rediss://default:pass@host.upstash.io:6380"
    proxy_url = None
    log_level = "INFO"
    max_retries = 3
    retry_backoff_seconds = 2.0


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch get_settings everywhere in the app stack."""
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


# ── /health tests ─────────────────────────────────────────────────────────────


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        r = await client.get("/health")
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client):
        r = await client.get("/health")
        assert r.status_code != 401


# ── /api/scrape auth tests ────────────────────────────────────────────────────


class TestScrapeAuth:
    @pytest.mark.asyncio
    async def test_missing_api_key_returns_422(self, client):
        r = await client.post("/api/scrape", json={"linkedin_url": VALID_URL})
        # FastAPI returns 422 when required header is missing
        assert r.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_wrong_api_key_returns_401(self, client):
        r = await client.post(
            "/api/scrape",
            json={"linkedin_url": VALID_URL},
            headers={"X-API-Key": "wrong-key"},
        )
        assert r.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_linkedin_url_returns_422(self, client):
        r = await client.post(
            "/api/scrape",
            json={"linkedin_url": "https://example.com/not-linkedin"},
            headers={"X-API-Key": VALID_KEY},
        )
        assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── /api/scrape success + error tests ────────────────────────────────────────


class TestScrapeEndpoint:
    @pytest.mark.asyncio
    async def test_successful_scrape(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            r = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert data["full_name"] == "Test User"
        assert data["linkedin_url"] == VALID_URL

    @pytest.mark.asyncio
    async def test_response_has_phantombuster_keys(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            r = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        data = r.json()
        for key in ["full_name", "headline", "location", "experience", "skills"]:
            assert key in data

    @pytest.mark.asyncio
    async def test_auth_error_returns_401(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = AuthenticationError("Cookies expired")
            r = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert r.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Cookies expired" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_scraper_error_returns_502(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = ScraperError("Network timeout")
            r = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert r.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Network timeout" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_trace_id_in_response(self, client):
        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = FAKE_PROFILE
            r = await client.post(
                "/api/scrape",
                json={"linkedin_url": VALID_URL},
                headers={"X-API-Key": VALID_KEY},
            )
        assert r.json().get("trace_id") is not None
