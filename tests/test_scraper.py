"""
tests/test_scraper.py
──────────────────────
Unit and integration tests for the scraper orchestrator (app/scraper.py).

Test coverage:
  • Vanity slug extraction from all URL formats (http/https, with/without www, query params, fragments, raw slugs)
  • Error handling on invalid/empty inputs
  • End-to-end scrape execution with mocked VoyagerClient
  • Exception propagation (AuthenticationError, ProfileNotFoundError, RateLimitError, VoyagerAPIError)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.network import (
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
    VoyagerAPIError,
)
from app.schemas import ProfileResponse
from app.scraper import ScraperError, extract_vanity_slug, scrape_profile
from tests.fixtures.voyager_payloads import FULL_VOYAGER_PROFILE_VIEW_PAYLOAD

VALID_LINKEDIN_URL = "https://www.linkedin.com/in/satyanadella"


# ── 1. Vanity Slug Extraction Tests ───────────────────────────────────────────


class TestExtractVanitySlug:
    def test_standard_https_url(self):
        assert (
            extract_vanity_slug("https://www.linkedin.com/in/satyanadella")
            == "satyanadella"
        )

    def test_url_with_trailing_slash(self):
        assert (
            extract_vanity_slug("https://www.linkedin.com/in/satyanadella/")
            == "satyanadella"
        )

    def test_url_with_query_params(self):
        assert (
            extract_vanity_slug(
                "https://www.linkedin.com/in/john-doe-123?miniProfileUrn=urn%3Ali%3Afs_miniProfile"
            )
            == "john-doe-123"
        )

    def test_url_with_hash_fragment(self):
        assert (
            extract_vanity_slug("https://www.linkedin.com/in/jane-doe#experience")
            == "jane-doe"
        )

    def test_url_without_protocol_or_www(self):
        assert extract_vanity_slug("linkedin.com/in/williamhgates") == "williamhgates"

    def test_prefix_in_slash(self):
        assert extract_vanity_slug("in/satyanadella") == "satyanadella"

    def test_raw_vanity_slug_directly(self):
        assert extract_vanity_slug("satyanadella") == "satyanadella"

    def test_empty_input_raises_value_error(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            extract_vanity_slug("   ")


# ── 2. Scrape Profile Orchestration Tests ─────────────────────────────────────


class TestScrapeProfileOrchestration:
    @pytest.fixture(autouse=True)
    def mock_settings(self, monkeypatch):
        class FakeSettings:
            li_at = "AQEDAT..." + "x" * 50
            jsessionid = '"ajax:1234567890123456789"'
            internal_api_key = "test_internal_api_key_12345"
            proxy_url = None
            log_level = "INFO"
            max_retries = 3
            retry_backoff_seconds = 0.01

        from app import config

        monkeypatch.setattr(config, "get_settings", lambda: FakeSettings())
        monkeypatch.setattr("app.scraper.get_settings", lambda: FakeSettings())

    @pytest.mark.asyncio
    async def test_successful_scrape_profile(self):
        with patch("app.scraper.VoyagerClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_profile_view = AsyncMock(
                return_value=FULL_VOYAGER_PROFILE_VIEW_PAYLOAD
            )
            mock_client_cls.return_value = mock_client

            profile = await scrape_profile(VALID_LINKEDIN_URL)

            assert isinstance(profile, ProfileResponse)
            assert profile.full_name == "Satya Nadella"
            assert profile.profile_id == "satyanadella"
            assert profile.trace_id is not None
            assert len(profile.experience) == 3
            assert len(profile.skills) == 5

            mock_client.get_profile_view.assert_awaited_once_with("satyanadella")

    @pytest.mark.asyncio
    async def test_auth_error_propagates(self):
        with patch("app.scraper.VoyagerClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_profile_view = AsyncMock(
                side_effect=AuthenticationError("Invalid credentials")
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                await scrape_profile(VALID_LINKEDIN_URL)

    @pytest.mark.asyncio
    async def test_profile_not_found_propagates(self):
        with patch("app.scraper.VoyagerClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_profile_view = AsyncMock(
                side_effect=ProfileNotFoundError("Not found")
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProfileNotFoundError, match="Not found"):
                await scrape_profile(VALID_LINKEDIN_URL)

    @pytest.mark.asyncio
    async def test_rate_limit_propagates(self):
        with patch("app.scraper.VoyagerClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_profile_view = AsyncMock(
                side_effect=RateLimitError("Rate limit exceeded")
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                await scrape_profile(VALID_LINKEDIN_URL)

    @pytest.mark.asyncio
    async def test_voyager_api_error_wrapped_in_scraper_error(self):
        with patch("app.scraper.VoyagerClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_profile_view = AsyncMock(
                side_effect=VoyagerAPIError("500 Server Error", status_code=500)
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(ScraperError, match="LinkedIn Voyager API error"):
                await scrape_profile(VALID_LINKEDIN_URL)
