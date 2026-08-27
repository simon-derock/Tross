"""
tests/test_diverse_profiles.py
──────────────────────────────
Tests for diverse real-world LinkedIn profile personas.
Verifies parsing and FastAPI extraction across multiple professions and data configurations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.parser import parse_voyager_profile
from tests.fixtures.dynamic_profiles import (
    PERSONA_REGISTRY,
    generate_dynamic_profile_payload,
)

VALID_KEY = "test-internal-api-key-12345"


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


class TestDiversePersonasParsing:
    @pytest.mark.parametrize("persona", list(PERSONA_REGISTRY.keys()))
    def test_all_dynamic_personas_parse_cleanly(self, persona: str):
        payload = generate_dynamic_profile_payload(persona)
        profile = parse_voyager_profile(
            payload,
            linkedin_url=f"https://www.linkedin.com/in/{persona}",
            vanity_slug=persona,
        )

        assert profile.full_name is not None
        assert len(profile.full_name) > 0
        assert profile.linkedin_url == f"https://www.linkedin.com/in/{persona}"

    def test_custom_fields_override(self):
        payload = generate_dynamic_profile_payload(
            "software_engineer",
            profile={"firstName": "CustomAlex", "lastName": "CustomChen"},
        )
        profile = parse_voyager_profile(
            payload,
            linkedin_url="https://www.linkedin.com/in/custom-alex",
            vanity_slug="custom-alex",
        )
        assert profile.first_name == "CustomAlex"
        assert profile.last_name == "CustomChen"
        assert profile.full_name == "CustomAlex CustomChen"


class TestDiversePersonasApiIntegration:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("persona", list(PERSONA_REGISTRY.keys()))
    async def test_api_scrape_dynamic_personas(self, persona: str):
        payload = generate_dynamic_profile_payload(persona)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            with patch("app.scraper.VoyagerClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get_profile_view = AsyncMock(return_value=payload)
                mock_client_cls.return_value = mock_client

                response = await client.post(
                    "/api/scrape",
                    json={"url": f"https://www.linkedin.com/in/{persona}"},
                    headers={"X-API-Key": VALID_KEY},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["full_name"] is not None
                assert data["trace_id"] is not None
