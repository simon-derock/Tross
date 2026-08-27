"""
tests/test_schemas.py
─────────────────────
Unit tests for Pydantic v2 schemas in app/schemas.py.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    ErrorResponse,
    ProfileResponse,
    ScrapeRequest,
)

LINKEDIN_URL = "https://www.linkedin.com/in/satyanadella"


class TestScrapeRequest:
    def test_valid_url_standard(self):
        req = ScrapeRequest(linkedin_url="https://www.linkedin.com/in/satyanadella/")
        assert req.linkedin_url == "https://www.linkedin.com/in/satyanadella"

    def test_alias_url(self):
        req = ScrapeRequest.model_validate(
            {"url": "https://www.linkedin.com/in/satyanadella"}
        )
        assert req.linkedin_url == "https://www.linkedin.com/in/satyanadella"

    def test_alias_profile_url(self):
        req = ScrapeRequest.model_validate(
            {"profile_url": "https://www.linkedin.com/in/satyanadella"}
        )
        assert req.linkedin_url == "https://www.linkedin.com/in/satyanadella"

    def test_empty_url_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ScrapeRequest(linkedin_url="   ")


class TestProfileResponse:
    def test_empty_profile_valid(self):
        p = ProfileResponse()
        assert p.full_name is None
        assert p.experience == []
        assert p.education == []
        assert p.skills == []
        assert p.certifications == []
        assert p.languages == []

    def test_json_round_trip(self):
        p = ProfileResponse(
            full_name="Satya Nadella",
            headline="CEO at Microsoft",
            location="Redmond, WA",
            skills=["Leadership", "Cloud"],
        )
        json_data = p.model_dump_json()
        restored = ProfileResponse.model_validate_json(json_data)
        assert restored.full_name == "Satya Nadella"
        assert restored.skills == ["Leadership", "Cloud"]


class TestErrorResponse:
    def test_error_response_structure(self):
        err = ErrorResponse(detail="Unauthorized", status_code=401, trace_id="trace123")
        assert err.status_code == 401
        assert err.detail == "Unauthorized"
        assert err.trace_id == "trace123"
