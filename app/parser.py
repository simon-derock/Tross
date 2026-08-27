"""
app/parser.py
─────────────
LinkedIn profile data extraction and normalization engine.

Primary Strategy:
  Directly parse pure JSON payloads from LinkedIn's internal Voyager REST API
  (e.g. GET /voyager/api/identity/profiles/{slug}/profileView or Dash entities)
  and map them into a PhantomBuster-compliant Pydantic schema (ProfileResponse).

Fallback Strategy:
  BeautifulSoup4 HTML CSS selector parsing when HTML content is passed.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from app.logging_config import get_logger
from app.schemas import (
    CertificationItem,
    DateRange,
    EducationItem,
    ExperienceItem,
    LanguageItem,
    ProfileResponse,
)

logger = get_logger(__name__)

MONTH_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def _format_date(d: dict[str, Any] | None) -> str | None:
    """Convert Voyager date dict (with 'month' and/or 'year') to 'Mon YYYY' or 'YYYY' string."""
    if not isinstance(d, dict):
        return None
    month = d.get("month")
    year = d.get("year")
    if month and year:
        month_str = MONTH_NAMES.get(month, str(month))
        return f"{month_str} {year}"
    if year:
        return str(year)
    return None


def _format_date_range(time_period: dict[str, Any] | None) -> DateRange | None:
    """Format Voyager timePeriod / dateRange object into DateRange model."""
    if not isinstance(time_period, dict):
        return None

    start_raw = time_period.get("startDate") or time_period.get("start")
    end_raw = time_period.get("endDate") or time_period.get("end")

    start_str = _format_date(start_raw)
    end_str = _format_date(end_raw) if end_raw else "Present"

    if not start_str and not end_str:
        return None

    return DateRange(start_date=start_str, end_date=end_str)


def _extract_best_image_url(
    picture_obj: dict[str, Any] | None,
) -> str | None:
    """
    Extract the highest resolution image URL from a Voyager vectorImage reference.
    Selects the artifact with the largest width/height or the last item.
    """
    if not isinstance(picture_obj, dict):
        return None

    vector_image = (
        picture_obj.get("displayImageReference", {}).get("vectorImage")
        or picture_obj.get("vectorImage")
        or picture_obj
    )
    if not isinstance(vector_image, dict):
        return None

    root_url = vector_image.get("rootUrl", "")
    artifacts = vector_image.get("artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        return None

    # Sort artifacts by area (width * height) descending
    def _artifact_size(a: dict[str, Any]) -> int:
        return int(a.get("width", 0)) * int(a.get("height", 0))

    sorted_artifacts = sorted(artifacts, key=_artifact_size, reverse=True)
    best_artifact = sorted_artifacts[0]
    path_segment = best_artifact.get("fileIdentifyingUrlPathSegment", "")

    if root_url and path_segment:
        return f"{root_url}{path_segment}"
    if path_segment.startswith("http"):
        return path_segment
    return None


# ── Primary: Pure Voyager JSON Parser ─────────────────────────────────────────


def parse_voyager_profile(
    data: dict[str, Any],
    linkedin_url: str,
    vanity_slug: str | None = None,
) -> ProfileResponse:
    """
    Parse a raw LinkedIn Voyager API JSON response (profileView or Dash entities)
    into a complete, PhantomBuster-compliant ProfileResponse model.

    Args:
        data: Dict containing parsed JSON from LinkedIn Voyager REST API.
        linkedin_url: Inbound LinkedIn profile URL.
        vanity_slug: Optional profile vanity slug.

    Returns:
        ProfileResponse populated with all available profile details.
    """
    profile_data: dict[str, Any] = {}
    included_entities: list[dict[str, Any]] = []

    # 1. Handle profileView structure: {"profile": {...}, "positionGroupView": {...}, ...}
    if "profile" in data and isinstance(data["profile"], dict):
        profile_data = data["profile"]
    elif "data" in data and isinstance(data["data"], dict):
        profile_data = data["data"].get("profile", data["data"])

    # 2. Handle Restli / Dash included arrays: {"included": [...]}
    if "included" in data and isinstance(data["included"], list):
        included_entities = data["included"]
        if not profile_data:
            profile_data = next(
                (
                    e
                    for e in included_entities
                    if isinstance(e, dict) and e.get("$type", "").endswith(".Profile")
                ),
                {},
            )

    # ── Basic Identification ──────────────────────────────────────────────────
    first_name = profile_data.get("firstName") or None
    last_name = profile_data.get("lastName") or None
    full_name = (
        f"{first_name or ''} {last_name or ''}".strip()
        if (first_name or last_name)
        else None
    )

    slug = (
        profile_data.get("publicIdentifier")
        or vanity_slug
        or (
            linkedin_url.rstrip("/").split("/in/")[-1]
            if "/in/" in linkedin_url
            else None
        )
    )
    headline = profile_data.get("headline") or None
    location = (
        profile_data.get("locationName")
        or profile_data.get("location", {}).get("name")
        or None
    )
    country = (
        profile_data.get("geoCountryName") or profile_data.get("countryCode") or None
    )
    industry = profile_data.get("industryName") or None
    about = (
        profile_data.get("summary")
        or profile_data.get("summaryText")
        or profile_data.get("about")
        or None
    )
    followers = profile_data.get("followersCount")
    connections = profile_data.get("connectionsCount")

    # ── Profile & Background Images ───────────────────────────────────────────
    profile_img = _extract_best_image_url(profile_data.get("profilePicture"))
    background_img = _extract_best_image_url(profile_data.get("backgroundPicture"))

    # ── Experience Extraction ─────────────────────────────────────────────────
    experiences: list[ExperienceItem] = []

    # A. profileView: positionGroupView -> elements
    pos_group_view = data.get("positionGroupView", {})
    if isinstance(pos_group_view, dict):
        elements = pos_group_view.get("elements", [])
        if isinstance(elements, list):
            for group in elements:
                if not isinstance(group, dict):
                    continue
                company_name = (
                    group.get("name")
                    or group.get("miniCompany", {}).get("name")
                    or None
                )
                company_slug = group.get("miniCompany", {}).get("universalName")
                company_url = (
                    f"https://www.linkedin.com/company/{company_slug}"
                    if company_slug
                    else None
                )

                positions = group.get("positions", [])
                if isinstance(positions, list) and positions:
                    for pos in positions:
                        if not isinstance(pos, dict):
                            continue
                        experiences.append(
                            ExperienceItem(
                                title=pos.get("title") or None,
                                company=pos.get("companyName") or company_name,
                                company_url=company_url,
                                location=pos.get("locationName") or None,
                                description=pos.get("description") or None,
                                date_range=_format_date_range(pos.get("timePeriod")),
                            )
                        )
                else:
                    # Single position entry in group
                    experiences.append(
                        ExperienceItem(
                            title=group.get("title") or None,
                            company=company_name,
                            company_url=company_url,
                            location=group.get("locationName") or None,
                            description=group.get("description") or None,
                            date_range=_format_date_range(group.get("timePeriod")),
                        )
                    )

    # B. Restli included entities: com.linkedin.voyager.dash.identity.profile.Position
    if not experiences and included_entities:
        for ent in included_entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("$type", "").endswith(".Position"):
                experiences.append(
                    ExperienceItem(
                        title=ent.get("title") or None,
                        company=ent.get("companyName") or None,
                        location=ent.get("locationName") or None,
                        description=ent.get("description") or None,
                        date_range=_format_date_range(ent.get("dateRange")),
                    )
                )

    # ── Education Extraction ──────────────────────────────────────────────────
    education_items: list[EducationItem] = []

    edu_view = data.get("educationView", {})
    if isinstance(edu_view, dict):
        elements = edu_view.get("elements", [])
        if isinstance(elements, list):
            for edu in elements:
                if not isinstance(edu, dict):
                    continue
                school_slug = edu.get("school", {}).get("universalName")
                school_url = (
                    f"https://www.linkedin.com/school/{school_slug}"
                    if school_slug
                    else None
                )
                education_items.append(
                    EducationItem(
                        school=edu.get("schoolName") or None,
                        school_url=school_url,
                        degree=edu.get("degreeName") or None,
                        field_of_study=edu.get("fieldOfStudy") or None,
                        description=edu.get("description") or None,
                        date_range=_format_date_range(edu.get("timePeriod")),
                    )
                )

    if not education_items and included_entities:
        for ent in included_entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("$type", "").endswith(".Education"):
                education_items.append(
                    EducationItem(
                        school=ent.get("schoolName") or None,
                        degree=ent.get("degreeName") or None,
                        field_of_study=ent.get("fieldOfStudy") or None,
                        description=ent.get("description") or None,
                        date_range=_format_date_range(ent.get("dateRange")),
                    )
                )

    # ── Skills Extraction ─────────────────────────────────────────────────────
    skills_list: list[str] = []

    skill_view = data.get("skillView", {})
    if isinstance(skill_view, dict):
        elements = skill_view.get("elements", [])
        if isinstance(elements, list):
            for skill in elements:
                if isinstance(skill, dict) and skill.get("name"):
                    skills_list.append(str(skill["name"]).strip())

    if not skills_list and included_entities:
        for ent in included_entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("$type", "").endswith(".Skill") and ent.get("name"):
                skills_list.append(str(ent["name"]).strip())

    # ── Certifications Extraction ─────────────────────────────────────────────
    certifications_list: list[CertificationItem] = []

    cert_view = data.get("certificationView", {})
    if isinstance(cert_view, dict):
        elements = cert_view.get("elements", [])
        if isinstance(elements, list):
            for cert in elements:
                if not isinstance(cert, dict):
                    continue
                date_r = _format_date_range(cert.get("timePeriod"))
                certifications_list.append(
                    CertificationItem(
                        name=cert.get("name") or None,
                        issuing_organization=cert.get("authority") or None,
                        credential_id=cert.get("licenseNumber") or None,
                        credential_url=cert.get("url") or None,
                        issue_date=date_r.start_date if date_r else None,
                        expiration_date=date_r.end_date
                        if (date_r and date_r.end_date != "Present")
                        else None,
                    )
                )

    if not certifications_list and included_entities:
        for ent in included_entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("$type", "").endswith(".Certification"):
                certifications_list.append(
                    CertificationItem(
                        name=ent.get("name") or None,
                        issuing_organization=ent.get("authority") or None,
                        credential_id=ent.get("licenseNumber") or None,
                        credential_url=ent.get("url") or None,
                    )
                )

    # ── Languages Extraction ──────────────────────────────────────────────────
    languages_list: list[LanguageItem] = []

    lang_view = data.get("languageView", {})
    if isinstance(lang_view, dict):
        elements = lang_view.get("elements", [])
        if isinstance(elements, list):
            for lang in elements:
                if isinstance(lang, dict) and lang.get("name"):
                    languages_list.append(
                        LanguageItem(
                            name=lang.get("name"),
                            proficiency=lang.get("proficiency") or None,
                        )
                    )

    if not languages_list and included_entities:
        for ent in included_entities:
            if not isinstance(ent, dict):
                continue
            if ent.get("$type", "").endswith(".Language") and ent.get("name"):
                languages_list.append(
                    LanguageItem(
                        name=ent.get("name"),
                        proficiency=ent.get("proficiency") or None,
                    )
                )

    return ProfileResponse(
        linkedin_url=linkedin_url,
        profile_id=slug,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        headline=headline,
        location=location,
        country=country,
        industry=industry,
        about=about,
        followers=followers,
        connections=connections,
        profile_image_url=profile_img,
        background_image_url=background_img,
        experience=experiences,
        education=education_items,
        skills=skills_list,
        certifications=certifications_list,
        languages=languages_list,
        scraped_at=datetime.now(tz=UTC).isoformat(),
    )


# ── Backward Compatibility: HTML Parser ───────────────────────────────────────


def parse_profile(html: str, linkedin_url: str) -> ProfileResponse:
    """
    Backward-compatible entry point for HTML-based parsing.
    Extracts embedded Voyager JSON or falls back to BeautifulSoup CSS selectors.
    """
    for match in re.finditer(r"<code[^>]*>(.*?)</code>", html, re.DOTALL):
        blob = match.group(1).strip()
        try:
            parsed_json = json.loads(blob)
            if isinstance(parsed_json, dict) and (
                "profile" in parsed_json or "included" in parsed_json
            ):
                return parse_voyager_profile(parsed_json, linkedin_url)
        except (json.JSONDecodeError, ValueError):
            continue

    # Fallback to BS4 CSS selectors
    soup = BeautifulSoup(html, "html.parser")

    def _text(sel: str) -> str | None:
        el = soup.select_one(sel)
        return el.get_text(strip=True) if el else None

    img_tag = soup.select_one("img.pv-top-card-profile-picture__image--show")
    img_url = img_tag.get("src") if img_tag else None

    return ProfileResponse(
        linkedin_url=linkedin_url,
        full_name=_text("h1.text-heading-xlarge") or _text("h1"),
        headline=_text(".text-body-medium.break-words"),
        location=_text(".text-body-small.inline.t-black--light.break-words"),
        profile_image_url=img_url,
        scraped_at=datetime.now(tz=UTC).isoformat(),
    )
