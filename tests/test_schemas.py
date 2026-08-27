"""
tests/test_schemas.py
─────────────────────
Strict schema tests for Phase 3.
Covers: field presence, type validation, LinkedIn URL guard,
JSON round-trip fidelity, and partial-data tolerance.
"""

import json

import pytest
from pydantic import ValidationError

from app.schemas import (
    ErrorResponse,
    ProfileResponse,
    ScrapeRequest,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

FULL_PROFILE_FIXTURE = {
    "linkedin_url": "https://www.linkedin.com/in/jane-doe-123",
    "profile_id": "jane-doe-123",
    "first_name": "Jane",
    "last_name": "Doe",
    "full_name": "Jane Doe",
    "headline": "Senior Software Engineer @ FAANG",
    "location": "San Francisco, CA",
    "country": "United States",
    "industry": "Computer Software",
    "about": "Passionate about building scalable systems.",
    "followers": 5000,
    "connections": 500,
    "profile_image_url": "https://media.licdn.com/dms/image/foo.jpg",
    "background_image_url": None,
    "experience": [
        {
            "title": "Senior SWE",
            "company": "BigCo",
            "company_url": "https://www.linkedin.com/company/bigco",
            "location": "Remote",
            "description": "Built stuff.",
            "date_range": {"start_date": "Jan 2021", "end_date": "Present"},
            "duration": "3 yrs",
        }
    ],
    "education": [
        {
            "school": "MIT",
            "school_url": "https://www.linkedin.com/school/mit",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science",
            "date_range": {"start_date": "Sep 2014", "end_date": "Jun 2018"},
            "description": None,
        }
    ],
    "skills": ["Python", "FastAPI", "Docker"],
    "certifications": [
        {
            "name": "AWS Solutions Architect",
            "issuing_organization": "Amazon",
            "issue_date": "Jan 2022",
            "expiration_date": None,
            "credential_id": "ABC123",
            "credential_url": "https://aws.amazon.com/verify/ABC123",
        }
    ],
    "languages": [
        {"name": "English", "proficiency": "Native"},
        {"name": "Spanish", "proficiency": "Professional Working"},
    ],
    "scraped_at": "2024-01-15T10:30:00Z",
    "trace_id": "abc123def456",
}


# ── ScrapeRequest tests ───────────────────────────────────────────────────────


class TestScrapeRequest:
    def test_valid_linkedin_url(self):
        r = ScrapeRequest(linkedin_url="https://www.linkedin.com/in/john-doe/")
        assert r.linkedin_url == "https://www.linkedin.com/in/john-doe"

    def test_trailing_slash_stripped(self):
        r = ScrapeRequest(linkedin_url="https://www.linkedin.com/in/john-doe/")
        assert not r.linkedin_url.endswith("/")

    def test_non_linkedin_url_raises(self):
        with pytest.raises(ValidationError, match="'/in/'"):
            ScrapeRequest(linkedin_url="https://example.com/profile/john")

    def test_company_url_rejected(self):
        with pytest.raises(ValidationError):
            ScrapeRequest(linkedin_url="https://www.linkedin.com/company/google/")

    def test_missing_url_raises(self):
        with pytest.raises(ValidationError):
            ScrapeRequest()


# ── ProfileResponse tests ─────────────────────────────────────────────────────


class TestProfileResponse:
    def test_full_fixture_parses(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        assert p.full_name == "Jane Doe"
        assert p.headline == "Senior Software Engineer @ FAANG"

    def test_empty_profile_is_valid(self):
        """All fields nullable — partial data must not raise."""
        p = ProfileResponse()
        assert p.full_name is None
        assert p.experience == []
        assert p.skills == []

    def test_experience_parses_correctly(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        exp = p.experience[0]
        assert exp.title == "Senior SWE"
        assert exp.date_range.end_date == "Present"

    def test_education_parses_correctly(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        edu = p.education[0]
        assert edu.school == "MIT"
        assert edu.degree == "Bachelor of Science"

    def test_skills_list(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        assert "Python" in p.skills
        assert len(p.skills) == 3

    def test_certifications_parse(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        cert = p.certifications[0]
        assert cert.name == "AWS Solutions Architect"
        assert cert.credential_id == "ABC123"

    def test_languages_parse(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        assert p.languages[0].proficiency == "Native"

    def test_followers_and_connections_are_int(self):
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        assert isinstance(p.followers, int)
        assert isinstance(p.connections, int)

    def test_json_round_trip(self):
        """Serialize → deserialize must be lossless."""
        p1 = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        json_str = p1.model_dump_json()
        p2 = ProfileResponse.model_validate_json(json_str)
        assert p1 == p2

    def test_json_output_matches_phantombuster_keys(self):
        """Spot-check critical PhantomBuster field names exist in output."""
        p = ProfileResponse.model_validate(FULL_PROFILE_FIXTURE)
        data = json.loads(p.model_dump_json())
        required_keys = {
            "full_name",
            "headline",
            "location",
            "about",
            "experience",
            "education",
            "skills",
            "certifications",
            "languages",
            "profile_image_url",
        }
        assert required_keys.issubset(data.keys())


# ── ErrorResponse tests ───────────────────────────────────────────────────────


class TestErrorResponse:
    def test_error_response_valid(self):
        e = ErrorResponse(detail="Not found", status_code=404, trace_id="xyz")
        assert e.status_code == 404
        assert e.detail == "Not found"

    def test_error_response_no_trace(self):
        e = ErrorResponse(detail="Internal error", status_code=500)
        assert e.trace_id is None
