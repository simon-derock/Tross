"""
tests/test_failover.py
──────────────────────
Comprehensive tests for 4-Tier Anti-Fragile Failover Architecture:
  1. Automatic fallback from 401/403 Voyager error to Public Guest scraper.
  2. In-Memory LRU Cache hit (<5ms response time).
  3. Custom X-Li-At and X-JSESSIONID header override support in FastAPI endpoints.
  4. Public Guest scraper Schema.org JSON-LD and OpenGraph metadata parsing.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.network import AuthenticationError
from app.public_scraper import parse_public_html
from app.schemas import ProfileResponse
from app.scraper import (
    clear_cache,
    get_cached_profile,
    scrape_profile,
    set_cached_profile,
)

VALID_KEY = "test-internal-api-key-12345"
VALID_URL = "https://www.linkedin.com/in/satyanadella"
VANITY_SLUG = "satyanadella"

SAMPLE_PUBLIC_HTML_JSON_LD = """
<!DOCTYPE html>
<html>
<head>
    <title>Satya Nadella - Chairman and CEO - Microsoft | LinkedIn</title>
    <meta property="og:title" content="Satya Nadella - Chairman and CEO - Microsoft | LinkedIn" />
    <meta property="og:description" content="View Satya Nadella's profile on LinkedIn" />
    <meta property="og:image" content="https://media.licdn.com/dms/image/v2/test_avatar.jpg" />
    <meta name="description" content="Satya Nadella is the Chairman and Chief Executive Officer of Microsoft." />
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Person",
                "name": "Satya Nadella",
                "givenName": "Satya",
                "familyName": "Nadella",
                "jobTitle": ["Chairman and CEO"],
                "description": "Satya Nadella is the Chairman and Chief Executive Officer of Microsoft.",
                "image": {
                    "@type": "ImageObject",
                    "contentUrl": "https://media.licdn.com/dms/image/v2/satya_headshot.jpg"
                },
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Redmond",
                    "addressRegion": "Washington",
                    "addressCountry": "United States"
                },
                "worksFor": [
                    {
                        "@type": "Organization",
                        "name": "Microsoft",
                        "url": "https://www.linkedin.com/company/microsoft",
                        "location": "Redmond, WA",
                        "jobTitle": "Chairman and CEO"
                    }
                ],
                "alumniOf": [
                    {
                        "@type": "EducationalOrganization",
                        "name": "University of Chicago Booth School of Business",
                        "url": "https://www.linkedin.com/school/uchicagobooth/",
                        "award": "MBA"
                    }
                ]
            }
        ]
    }
    </script>
</head>
<body><h1>Satya Nadella</h1></body>
</html>
"""

SAMPLE_OG_ONLY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Satya Nadella - Chairman and CEO at Microsoft | LinkedIn</title>
    <meta property="og:title" content="Satya Nadella - Chairman and CEO at Microsoft | LinkedIn" />
    <meta property="og:description" content="Satya Nadella is Chairman and CEO of Microsoft Corporation." />
    <meta property="og:image" content="https://media.licdn.com/dms/image/og_image.jpg" />
</head>
<body></body>
</html>
"""


class FakeSettings:
    internal_api_key = VALID_KEY
    li_at = "AQEDAT..." + "x" * 50
    jsessionid = '"ajax:1234567890123456789"'
    proxy_url = None
    log_level = "INFO"
    max_retries = 3
    retry_backoff_seconds = 0.01


@pytest.fixture(autouse=True)
def reset_state():
    clear_cache()
    with (
        patch("app.main.get_settings", return_value=FakeSettings()),
        patch("app.config.get_settings", return_value=FakeSettings()),
        patch("app.scraper.get_settings", return_value=FakeSettings()),
    ):
        yield
    clear_cache()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestPublicScraperParsing:
    def test_parse_public_html_with_schema_org_json_ld(self):
        profile = parse_public_html(SAMPLE_PUBLIC_HTML_JSON_LD, vanity_slug=VANITY_SLUG)
        assert profile.full_name == "Satya Nadella"
        assert profile.first_name == "Satya"
        assert profile.last_name == "Nadella"
        assert profile.headline == "Chairman and CEO"
        assert "Chief Executive Officer" in (profile.about or "")
        assert profile.location == "Redmond, Washington, United States"
        assert (
            profile.profile_image_url
            == "https://media.licdn.com/dms/image/v2/satya_headshot.jpg"
        )
        assert len(profile.experience) == 1
        assert profile.experience[0].company == "Microsoft"
        assert profile.experience[0].title == "Chairman and CEO"
        assert len(profile.education) == 1
        assert "Chicago Booth" in (profile.education[0].school or "")
        assert profile.education[0].degree == "MBA"

    def test_parse_public_html_og_tags_fallback(self):
        profile = parse_public_html(SAMPLE_OG_ONLY_HTML, vanity_slug=VANITY_SLUG)
        assert profile.full_name == "Satya Nadella"
        assert profile.headline == "Chairman and CEO at Microsoft"
        assert (
            profile.profile_image_url
            == "https://media.licdn.com/dms/image/og_image.jpg"
        )
        assert "Microsoft Corporation" in (profile.about or "")


class TestFailoverOrchestration:
    @pytest.mark.asyncio
    async def test_automatic_fallback_from_401_to_public_scraper(self):
        with (
            patch("app.scraper.VoyagerClient") as mock_client_cls,
            patch(
                "app.scraper.scrape_public_profile", new_callable=AsyncMock
            ) as mock_public,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get_profile_view.side_effect = AuthenticationError(
                "LinkedIn session expired (HTTP 401)"
            )
            mock_client_cls.return_value = mock_client

            fallback_profile = ProfileResponse(
                linkedin_url=VALID_URL,
                profile_id=VANITY_SLUG,
                full_name="Satya Nadella (Guest)",
                headline="Chairman and CEO at Microsoft",
            )
            mock_public.return_value = fallback_profile

            result = await scrape_profile(VALID_URL)

            assert result.full_name == "Satya Nadella (Guest)"
            mock_public.assert_awaited_once_with(
                vanity_slug=VANITY_SLUG, proxy_url=None
            )

    @pytest.mark.asyncio
    async def test_failover_when_no_credentials_configured(self, monkeypatch):
        class EmptySettings:
            internal_api_key = VALID_KEY
            li_at = ""
            jsessionid = ""
            proxy_url = None
            log_level = "INFO"
            max_retries = 1
            retry_backoff_seconds = 0.01

        monkeypatch.setattr("app.scraper.get_settings", lambda: EmptySettings())

        with patch(
            "app.scraper.scrape_public_profile", new_callable=AsyncMock
        ) as mock_public:
            mock_public.return_value = ProfileResponse(
                linkedin_url=VALID_URL,
                profile_id=VANITY_SLUG,
                full_name="Satya Nadella",
            )
            result = await scrape_profile(VALID_URL)
            assert result.full_name == "Satya Nadella"
            mock_public.assert_awaited_once_with(
                vanity_slug=VANITY_SLUG, proxy_url=None
            )


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_cache_hit_under_5ms(self):
        cached_data = ProfileResponse(
            linkedin_url=VALID_URL,
            profile_id=VANITY_SLUG,
            full_name="Satya Nadella Cached",
            headline="Chairman and CEO at Microsoft",
        )
        set_cached_profile(VANITY_SLUG, cached_data)

        start = time.perf_counter()
        result = await scrape_profile(VALID_URL)
        duration_ms = (time.perf_counter() - start) * 1000

        assert result.full_name == "Satya Nadella Cached"
        assert duration_ms < 5.0, f"Cache lookup took {duration_ms:.2f}ms (> 5ms)"

    def test_cache_expiration(self):
        cached_data = ProfileResponse(
            linkedin_url=VALID_URL,
            profile_id=VANITY_SLUG,
            full_name="Old Profile",
        )
        set_cached_profile(VANITY_SLUG, cached_data, ttl_seconds=-1.0)
        assert get_cached_profile(VANITY_SLUG) is None


class TestHeaderOverrides:
    @pytest.mark.asyncio
    async def test_post_with_x_li_at_header_override(self, client):
        custom_li_at = "AQEDA_CUSTOM_COOKIE_OVERRIDE"
        custom_jsessionid = "ajax:999888777666"

        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = ProfileResponse(
                linkedin_url=VALID_URL,
                profile_id=VANITY_SLUG,
                full_name="Satya Nadella",
            )

            response = await client.post(
                "/api/scrape",
                json={"url": VALID_URL},
                headers={
                    "X-API-Key": VALID_KEY,
                    "X-Li-At": custom_li_at,
                    "X-JSESSIONID": custom_jsessionid,
                },
            )

            assert response.status_code == status.HTTP_200_OK
            mock_scrape.assert_awaited_once_with(
                VALID_URL,
                override_cookies={
                    "li_at": custom_li_at,
                    "JSESSIONID": custom_jsessionid,
                },
            )

    @pytest.mark.asyncio
    async def test_get_with_x_li_at_header_override(self, client):
        custom_li_at = "AQEDA_CUSTOM_GET_COOKIE"

        with patch("app.main.scrape_profile", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = ProfileResponse(
                linkedin_url=VALID_URL,
                profile_id=VANITY_SLUG,
                full_name="Satya Nadella",
            )

            response = await client.get(
                f"/api/scrape?url={VALID_URL}",
                headers={
                    "X-API-Key": VALID_KEY,
                    "X-Li-At": custom_li_at,
                },
            )

            assert response.status_code == status.HTTP_200_OK
            mock_scrape.assert_awaited_once_with(
                VALID_URL,
                override_cookies={"li_at": custom_li_at},
            )
