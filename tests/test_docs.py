"""
tests/test_docs.py
──────────────────
Tests for native FastAPI Swagger UI and ReDoc documentation endpoints.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestDocumentationEndpoints:
    @pytest.mark.asyncio
    async def test_root_redirects_to_docs(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "/docs"

    @pytest.mark.asyncio
    async def test_docs_returns_native_swagger_ui(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/docs")

        assert response.status_code == 200
        assert "swagger-ui" in response.text

    @pytest.mark.asyncio
    async def test_redoc_endpoint_returns_200(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/redoc")

        assert response.status_code == 200
        assert "redoc" in response.text
