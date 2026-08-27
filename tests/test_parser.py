"""
tests/test_parser.py
─────────────────────
Tests for the extraction engine (parser.py).
Uses inline HTML fixtures to test both Voyager JSON and BS4 fallback paths.
No real network calls.
"""

from __future__ import annotations

import json

from app.parser import (
    _build_profile_from_html,
    _build_profile_from_voyager,
    _extract_date_range,
    _parse_voyager,
    parse_profile,
)
from app.schemas import ProfileResponse

LINKEDIN_URL = "https://www.linkedin.com/in/jane-doe"

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_voyager_html(included: list[dict]) -> str:
    """Wrap a list of Voyager entities in a minimal LinkedIn-like HTML page."""
    blob = json.dumps({"included": included})
    return f"""
    <html><body>
    <code data-delayed-url="/voyager/api/identity/profiles/jane-doe/profileView">
    {blob}
    </code>
    </body></html>
    """


PROFILE_ENTITY = {
    "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
    "entityUrn": "urn:li:fsd_profile:ABC123",
    "publicIdentifier": "jane-doe",
    "firstName": "Jane",
    "lastName": "Doe",
    "headline": "Senior SWE @ BigCo",
    "locationName": "San Francisco, CA",
    "industryName": "Computer Software",
    "summary": "I build scalable systems.",
    "followersCount": 4200,
    "connectionsCount": 500,
    "profilePicture": {
        "displayImageReference": {
            "vectorImage": {
                "rootUrl": "https://media.licdn.com/dms/image/",
                "artifacts": [
                    {"fileIdentifyingUrlPathSegment": "foo_100.jpg"},
                    {"fileIdentifyingUrlPathSegment": "foo_400.jpg"},
                ],
            }
        }
    },
}

POSITION_ENTITY = {
    "$type": "com.linkedin.voyager.dash.identity.profile.Position",
    "entityUrn": "urn:li:fsd_position:POS1",
    "title": "Senior Software Engineer",
    "companyName": "BigCo",
    "locationName": "Remote",
    "description": "Built distributed systems.",
    "dateRange": {
        "start": {"month": 3, "year": 2021},
        "end": None,
    },
}

EDUCATION_ENTITY = {
    "$type": "com.linkedin.voyager.dash.identity.profile.Education",
    "entityUrn": "urn:li:fsd_education:EDU1",
    "schoolName": "MIT",
    "degreeName": "Bachelor of Science",
    "fieldOfStudy": "Computer Science",
    "dateRange": {
        "start": {"month": 9, "year": 2014},
        "end": {"month": 6, "year": 2018},
    },
}

SKILL_ENTITY = {
    "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
    "entityUrn": "urn:li:fsd_skill:SK1",
    "name": "Python",
}

CERT_ENTITY = {
    "$type": "com.linkedin.voyager.dash.identity.profile.Certification",
    "entityUrn": "urn:li:fsd_cert:CERT1",
    "name": "AWS Solutions Architect",
    "authority": "Amazon Web Services",
    "licenseNumber": "ABC-123",
}

LANG_ENTITY = {
    "$type": "com.linkedin.voyager.dash.identity.profile.Language",
    "entityUrn": "urn:li:fsd_lang:LANG1",
    "name": "Spanish",
    "proficiency": "Professional Working",
}

ALL_ENTITIES = [
    PROFILE_ENTITY,
    POSITION_ENTITY,
    EDUCATION_ENTITY,
    SKILL_ENTITY,
    CERT_ENTITY,
    LANG_ENTITY,
]

FULL_HTML = _make_voyager_html(ALL_ENTITIES)


# ── _parse_voyager tests ──────────────────────────────────────────────────────


class TestParseVoyager:
    def test_extracts_entities_from_code_tag(self):
        entities = _parse_voyager(FULL_HTML)
        assert len(entities) > 0

    def test_skips_invalid_json_blobs(self):
        bad_html = "<code>NOT JSON</code>" + FULL_HTML
        entities = _parse_voyager(bad_html)
        assert len(entities) > 0  # still gets the good one

    def test_empty_html_returns_empty(self):
        assert _parse_voyager("<html><body></body></html>") == {}


# ── _extract_date_range tests ─────────────────────────────────────────────────


class TestExtractDateRange:
    def test_start_and_end(self):
        dr = _extract_date_range(
            {
                "dateRange": {
                    "start": {"month": 1, "year": 2020},
                    "end": {"month": 6, "year": 2023},
                }
            }
        )
        assert dr.start_date == "Jan 2020"
        assert dr.end_date == "Jun 2023"

    def test_no_end_means_present(self):
        dr = _extract_date_range(
            {"dateRange": {"start": {"month": 3, "year": 2021}, "end": None}}
        )
        assert dr.end_date == "Present"

    def test_no_date_range_returns_none(self):
        assert _extract_date_range({}) is None

    def test_year_only(self):
        dr = _extract_date_range(
            {"dateRange": {"start": {"year": 2019}, "end": {"year": 2022}}}
        )
        assert dr.start_date == "2019"
        assert dr.end_date == "2022"


# ── _build_profile_from_voyager tests ────────────────────────────────────────


class TestBuildProfileFromVoyager:
    def _entities(self) -> dict:
        return {e["entityUrn"]: e for e in ALL_ENTITIES}

    def test_full_profile_built(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert p is not None
        assert p.full_name == "Jane Doe"
        assert p.headline == "Senior SWE @ BigCo"
        assert p.location == "San Francisco, CA"

    def test_experience_extracted(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert len(p.experience) == 1
        assert p.experience[0].title == "Senior Software Engineer"
        assert p.experience[0].date_range.end_date == "Present"

    def test_education_extracted(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert len(p.education) == 1
        assert p.education[0].school == "MIT"
        assert p.education[0].field_of_study == "Computer Science"

    def test_skills_extracted(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert "Python" in p.skills

    def test_certifications_extracted(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert p.certifications[0].name == "AWS Solutions Architect"

    def test_languages_extracted(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert p.languages[0].name == "Spanish"

    def test_profile_image_extracted(self):
        p = _build_profile_from_voyager(self._entities(), LINKEDIN_URL)
        assert p.profile_image_url is not None
        assert "foo_400.jpg" in p.profile_image_url

    def test_returns_none_without_profile_entity(self):
        entities = {e["entityUrn"]: e for e in [POSITION_ENTITY]}
        result = _build_profile_from_voyager(entities, LINKEDIN_URL)
        assert result is None


# ── _build_profile_from_html tests (BS4 fallback) ────────────────────────────


class TestBuildProfileFromHtml:
    BS4_HTML = """
    <html><body>
    <h1 class="text-heading-xlarge">Alice Smith</h1>
    <div class="text-body-medium break-words">ML Engineer at Startup</div>
    <span class="text-body-small inline t-black--light break-words">London, UK</span>
    </body></html>
    """

    def test_extracts_name(self):
        p = _build_profile_from_html(self.BS4_HTML, LINKEDIN_URL)
        assert p.full_name == "Alice Smith"

    def test_extracts_headline(self):
        p = _build_profile_from_html(self.BS4_HTML, LINKEDIN_URL)
        assert p.headline == "ML Engineer at Startup"

    def test_extracts_location(self):
        p = _build_profile_from_html(self.BS4_HTML, LINKEDIN_URL)
        assert p.location == "London, UK"

    def test_returns_profile_response(self):
        p = _build_profile_from_html(self.BS4_HTML, LINKEDIN_URL)
        assert isinstance(p, ProfileResponse)


# ── parse_profile integration tests ──────────────────────────────────────────


class TestParseProfile:
    def test_uses_voyager_when_available(self):
        p = parse_profile(FULL_HTML, LINKEDIN_URL)
        assert p.full_name == "Jane Doe"
        assert len(p.experience) == 1

    def test_falls_back_to_bs4_on_no_voyager(self):
        plain_html = """
        <html><body>
        <h1 class="text-heading-xlarge">Bob Jones</h1>
        </body></html>
        """
        p = parse_profile(plain_html, LINKEDIN_URL)
        assert p.full_name == "Bob Jones"

    def test_scraped_at_is_set(self):
        p = parse_profile(FULL_HTML, LINKEDIN_URL)
        assert p.scraped_at is not None

    def test_linkedin_url_preserved(self):
        p = parse_profile(FULL_HTML, LINKEDIN_URL)
        assert p.linkedin_url == LINKEDIN_URL
