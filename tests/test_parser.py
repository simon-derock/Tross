"""
tests/test_parser.py
─────────────────────
Unit tests for LinkedIn Voyager API JSON and HTML parsing engine.

Test coverage:
  • Full profileView JSON payload mapping against ProfileResponse schema
  • Nested position groups (multiple roles at same company)
  • Start/end date formatting and active role "Present" resolution
  • Education with school universal URLs
  • Skills, certifications with license IDs/URLs, languages with proficiency
  • Highest resolution vectorImage artifact selection (800x800 vs 100x100)
  • Minimal/partial profileView JSON payloads (graceful null tolerance)
  • Unicode / Arabic RTL / Chinese / Emoji parsing
  • Restli / Dash included entity array extraction
  • Backward-compatible HTML embedded <code> and BS4 fallback parsing
  • Pydantic schema validation and round-trip JSON serialization
"""

from __future__ import annotations

import json

import pytest

from app.parser import (
    _extract_best_image_url,
    _format_date,
    _format_date_range,
    parse_profile,
    parse_voyager_profile,
)
from app.schemas import ProfileResponse
from tests.fixtures.voyager_payloads import (
    FULL_VOYAGER_PROFILE_VIEW_PAYLOAD,
    INCLUDED_ENTITIES_VOYAGER_PAYLOAD,
    MINIMAL_VOYAGER_PROFILE_VIEW_PAYLOAD,
    UNICODE_VOYAGER_PROFILE_VIEW_PAYLOAD,
)

LINKEDIN_URL = "https://www.linkedin.com/in/satyanadella"


# ── 1. Full ProfileView Parsing Tests ─────────────────────────────────────────


class TestParseVoyagerProfileFull:
    @pytest.fixture
    def profile(self) -> ProfileResponse:
        return parse_voyager_profile(
            FULL_VOYAGER_PROFILE_VIEW_PAYLOAD,
            linkedin_url=LINKEDIN_URL,
            vanity_slug="satyanadella",
        )

    def test_identity_fields(self, profile: ProfileResponse):
        assert profile.first_name == "Satya"
        assert profile.last_name == "Nadella"
        assert profile.full_name == "Satya Nadella"
        assert profile.profile_id == "satyanadella"
        assert profile.headline == "Chairman and CEO at Microsoft"
        assert profile.location == "Greater Seattle Area"
        assert profile.country == "United States"
        assert profile.industry == "Computer Software"
        assert profile.followers == 10500000
        assert profile.connections == 500
        assert "Chairman and Chief Executive Officer" in (profile.about or "")

    def test_image_extraction(self, profile: ProfileResponse):
        assert profile.profile_image_url is not None
        assert "shrink_800_800" in profile.profile_image_url
        assert profile.background_image_url is not None
        assert "banner.jpg" in profile.background_image_url

    def test_experience_extraction(self, profile: ProfileResponse):
        assert len(profile.experience) == 3

        # CEO position (active)
        ceo_pos = profile.experience[0]
        assert ceo_pos.title == "Chairman and CEO"
        assert ceo_pos.company == "Microsoft"
        assert ceo_pos.company_url == "https://www.linkedin.com/company/microsoft"
        assert ceo_pos.date_range is not None
        assert ceo_pos.date_range.start_date == "Feb 2014"
        assert ceo_pos.date_range.end_date == "Present"

        # Prior Microsoft position
        evp_pos = profile.experience[1]
        assert evp_pos.title == "Executive Vice President, Cloud and Enterprise"
        assert evp_pos.date_range is not None
        assert evp_pos.date_range.start_date == "Jan 2011"
        assert evp_pos.date_range.end_date == "Feb 2014"

        # Sun Microsystems position
        sun_pos = profile.experience[2]
        assert sun_pos.company == "Sun Microsystems"
        assert sun_pos.title == "Member of Technology Staff"
        assert sun_pos.date_range is not None
        assert sun_pos.date_range.start_date == "Jun 1990"
        assert sun_pos.date_range.end_date == "Dec 1992"

    def test_education_extraction(self, profile: ProfileResponse):
        assert len(profile.education) == 3

        mba = profile.education[0]
        assert "Chicago Booth" in (mba.school or "")
        assert "MBA" in (mba.degree or "")
        assert mba.date_range is not None
        assert mba.date_range.start_date == "1995"
        assert mba.date_range.end_date == "1997"

    def test_skills_extraction(self, profile: ProfileResponse):
        assert len(profile.skills) == 5
        assert "Cloud Computing" in profile.skills
        assert "Distributed Systems" in profile.skills

    def test_certifications_extraction(self, profile: ProfileResponse):
        assert len(profile.certifications) == 1
        cert = profile.certifications[0]
        assert cert.name == "Advanced Executive Leadership"
        assert (
            cert.issuing_organization == "Harvard Business School Executive Education"
        )
        assert cert.credential_id == "EXEC-9921"
        assert cert.issue_date == "May 2005"

    def test_languages_extraction(self, profile: ProfileResponse):
        assert len(profile.languages) == 3
        langs = {item.name: item.proficiency for item in profile.languages}
        assert "English" in langs
        assert "Telugu" in langs
        assert "Hindi" in langs


# ── 2. Minimal / Partial ProfileView Tests ────────────────────────────────────


class TestParseVoyagerProfileMinimal:
    def test_minimal_profile_does_not_raise(self):
        profile = parse_voyager_profile(
            MINIMAL_VOYAGER_PROFILE_VIEW_PAYLOAD,
            linkedin_url="https://www.linkedin.com/in/johndoe",
        )
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.full_name == "John Doe"
        assert profile.profile_id == "johndoe"
        assert profile.headline is None
        assert profile.experience == []
        assert profile.education == []
        assert profile.skills == []
        assert profile.certifications == []
        assert profile.languages == []

    def test_empty_dict_returns_empty_profile(self):
        profile = parse_voyager_profile(
            {}, linkedin_url="https://www.linkedin.com/in/unknown"
        )
        assert profile.full_name is None
        assert profile.profile_id == "unknown"
        assert profile.experience == []


# ── 3. Unicode and Internationalization Tests ─────────────────────────────────


class TestParseVoyagerProfileUnicode:
    def test_arabic_and_emoji_profile(self):
        profile = parse_voyager_profile(
            UNICODE_VOYAGER_PROFILE_VIEW_PAYLOAD,
            linkedin_url="https://www.linkedin.com/in/mohammed-alotaibi",
        )
        assert profile.first_name == "محمد"
        assert profile.last_name == "العتيبي"
        assert profile.full_name == "محمد العتيبي"
        assert "🚀" in (profile.headline or "")
        assert "الرياض" in (profile.location or "")
        assert len(profile.experience) == 1
        assert "شركة التقنية المتقدمة" in (profile.experience[0].company or "")
        assert "Kubernetes 🐳" in profile.skills


# ── 4. Restli / Dash Included Entities Tests ──────────────────────────────────


class TestParseVoyagerProfileIncluded:
    def test_parses_included_entities_structure(self):
        profile = parse_voyager_profile(
            INCLUDED_ENTITIES_VOYAGER_PAYLOAD,
            linkedin_url="https://www.linkedin.com/in/alice-smith",
        )
        assert profile.full_name == "Alice Smith"
        assert profile.headline == "VP of AI Research"
        assert len(profile.experience) == 1
        assert profile.experience[0].title == "VP AI Research"
        assert len(profile.education) == 1
        assert profile.education[0].school == "University of Oxford"
        assert "Machine Learning" in profile.skills


# ── 5. Helper Function Tests ──────────────────────────────────────────────────


class TestHelperFunctions:
    def test_format_date(self):
        assert _format_date({"month": 1, "year": 2024}) == "Jan 2024"
        assert _format_date({"year": 2020}) == "2020"
        assert _format_date(None) is None
        assert _format_date({}) is None

    def test_format_date_range(self):
        dr = _format_date_range(
            {
                "startDate": {"month": 5, "year": 2019},
                "endDate": {"month": 8, "year": 2022},
            }
        )
        assert dr is not None
        assert dr.start_date == "May 2019"
        assert dr.end_date == "Aug 2022"

    def test_format_date_range_ongoing(self):
        dr = _format_date_range({"startDate": {"year": 2021}})
        assert dr is not None
        assert dr.start_date == "2021"
        assert dr.end_date == "Present"

    def test_extract_best_image_url_highest_resolution(self):
        pic = {
            "displayImageReference": {
                "vectorImage": {
                    "rootUrl": "https://media.licdn.com/dms/image/",
                    "artifacts": [
                        {
                            "width": 100,
                            "height": 100,
                            "fileIdentifyingUrlPathSegment": "100.jpg",
                        },
                        {
                            "width": 400,
                            "height": 400,
                            "fileIdentifyingUrlPathSegment": "400.jpg",
                        },
                        {
                            "width": 200,
                            "height": 200,
                            "fileIdentifyingUrlPathSegment": "200.jpg",
                        },
                    ],
                }
            }
        }
        url = _extract_best_image_url(pic)
        assert url == "https://media.licdn.com/dms/image/400.jpg"


# ── 6. HTML Backward Compatibility Tests ──────────────────────────────────────


class TestParseProfileHtmlFallback:
    def test_embedded_code_tag_voyager_json(self):
        html = f"""
        <html><body>
        <code data-delayed-url="/foo">{json.dumps(FULL_VOYAGER_PROFILE_VIEW_PAYLOAD)}</code>
        </body></html>
        """
        profile = parse_profile(html, LINKEDIN_URL)
        assert profile.full_name == "Satya Nadella"
        assert len(profile.experience) == 3

    def test_plain_html_bs4_fallback(self):
        html = """
        <html><body>
        <h1 class="text-heading-xlarge">Jane Doe</h1>
        <div class="text-body-medium break-words">Principal Engineer</div>
        <span class="text-body-small inline t-black--light break-words">San Francisco, CA</span>
        </body></html>
        """
        profile = parse_profile(html, "https://www.linkedin.com/in/janedoe")
        assert profile.full_name == "Jane Doe"
        assert profile.headline == "Principal Engineer"
        assert profile.location == "San Francisco, CA"


# ── 7. Serialization and Round-Trip Tests ─────────────────────────────────────


class TestSchemaValidationAndRoundTrip:
    def test_json_round_trip(self):
        profile = parse_voyager_profile(
            FULL_VOYAGER_PROFILE_VIEW_PAYLOAD,
            linkedin_url=LINKEDIN_URL,
            vanity_slug="satyanadella",
        )
        json_str = profile.model_dump_json()
        restored = ProfileResponse.model_validate_json(json_str)
        assert restored.full_name == profile.full_name
        assert len(restored.experience) == len(profile.experience)
        assert len(restored.skills) == len(profile.skills)


# ── 8. Dash Parser Tests ──────────────────────────────────────────────────────


class TestParseDashProfile:
    def test_parse_dash_profile_with_included_parameter(self):
        from app.parser import parse_dash_profile

        profile = parse_dash_profile(
            data={"data": {}},
            included=INCLUDED_ENTITIES_VOYAGER_PAYLOAD["included"],
            linkedin_url=LINKEDIN_URL,
            vanity_slug="alice-smith",
        )
        assert profile.full_name == "Alice Smith"
        assert profile.headline == "VP of AI Research"
        assert len(profile.experience) == 1
        assert profile.experience[0].title == "VP AI Research"
        assert profile.experience[0].company == "DeepBio Labs"
        assert len(profile.education) == 1
        assert profile.education[0].school == "University of Oxford"
        assert "Machine Learning" in profile.skills
