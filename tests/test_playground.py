"""
tests/test_playground.py
────────────────────────
Tests for the Interactive Dark-Mode Web Playground.
Verifies HTML markup generation, route availability at '/', and DOM components.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.playground import get_playground_html


class TestPlaygroundGeneration:
    def test_get_playground_html_returns_valid_markup(self):
        html = get_playground_html()
        assert "<!DOCTYPE html>" in html
        assert "<title>Tross" in html
        assert "Voyager Reverse Engine" in html
        assert "tailwindcss.com" in html
        assert "handleScrape" in html
        assert "fillSample" in html
        assert "satyanadella" in html
        assert "reidhoffman" in html
        assert "copyJson" in html


class TestPlaygroundEndpoint:
    @pytest.mark.asyncio
    async def test_root_route_serves_playground_html(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "TROSS" in response.text
        assert "Scrape Profile" in response.text

    @pytest.mark.asyncio
    async def test_root_route_requires_no_authentication(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/")

        assert response.status_code == 200
