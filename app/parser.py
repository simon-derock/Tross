"""
app/parser.py
─────────────
LinkedIn profile data extraction engine.

Primary strategy:
  Parse the embedded Voyager JSON state injected into <code> tags by LinkedIn's
  SSR renderer. These tags contain the raw GraphQL/Restli response payloads.

Fallback strategy:
  BeautifulSoup4 CSS selectors against the rendered HTML for fields not found
  in the Voyager payload (older profile layouts, A/B variants).

All extracted data is mapped into the ProfileResponse Pydantic schema.
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

# ── Voyager JSON extraction regex ─────────────────────────────────────────────
_CODE_TAG_RE = re.compile(r"<code[^>]*data-delayed-url[^>]*>(.*?)</code>", re.DOTALL)
# LinkedIn Voyager profile entity types
_PROFILE_TYPE = "com.linkedin.voyager.dash.identity.profile.Profile"
_POSITION_TYPE = "com.linkedin.voyager.dash.identity.profile.Position"
_EDUCATION_TYPE = "com.linkedin.voyager.dash.identity.profile.Education"
_SKILL_TYPE = "com.linkedin.voyager.dash.identity.profile.Skill"
_CERT_TYPE = "com.linkedin.voyager.dash.identity.profile.Certification"
_LANG_TYPE = "com.linkedin.voyager.dash.identity.profile.Language"


def _safe_str(obj: Any, *keys: str, default: str | None = None) -> str | None:
    """Safely navigate nested dict/list structures."""
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key)
    if obj is None:
        return default
    return str(obj)


def _extract_date_range(item: dict[str, Any]) -> DateRange | None:
    """Extract start/end date from a Voyager dateRange sub-object."""
    dr = item.get("dateRange")
    if not dr:
        return None

    def _fmt(d: dict | None) -> str | None:
        if not d:
            return None
        month_map = {
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
        m = d.get("month")
        y = d.get("year")
        if m and y:
            return f"{month_map.get(m, str(m))} {y}"
        if y:
            return str(y)
        return None

    start = _fmt(dr.get("start"))
    end_raw = dr.get("end")
    end = _fmt(end_raw) if end_raw else "Present"
    return DateRange(start_date=start, end_date=end)


# ── Primary: Voyager JSON parser ──────────────────────────────────────────────


def _parse_voyager(html: str) -> dict[str, Any]:
    """
    Extract all <code data-delayed-url> JSON blobs from the page and
    merge them into a flat entity map keyed by Voyager entity URN.
    """
    entities: dict[str, Any] = {}
    for match in re.finditer(r"<code[^>]*>(.*?)</code>", html, re.DOTALL):
        blob = match.group(1).strip()
        try:
            data = json.loads(blob)
        except (json.JSONDecodeError, ValueError):
            continue

        # Voyager wraps data in {"data": {"*elements": [...], "included": [...]}}
        included = None
        if isinstance(data, dict):
            included = data.get("included") or data.get("data", {}).get("included")

        if isinstance(included, list):
            for entity in included:
                if isinstance(entity, dict) and "$type" in entity:
                    urn = entity.get("entityUrn", "")
                    entities[urn] = entity

    return entities


def _build_profile_from_voyager(
    entities: dict[str, Any], linkedin_url: str
) -> ProfileResponse | None:
    """Map Voyager entities into a ProfileResponse. Returns None on total miss."""
    profile_entity = next(
        (e for e in entities.values() if e.get("$type") == _PROFILE_TYPE), None
    )
    if not profile_entity:
        return None

    first = _safe_str(profile_entity, "firstName", "text") or _safe_str(
        profile_entity, "firstName"
    )
    last = _safe_str(profile_entity, "lastName", "text") or _safe_str(
        profile_entity, "lastName"
    )
    full = f"{first or ''} {last or ''}".strip() or None

    # Experience
    experience: list[ExperienceItem] = []
    for ent in entities.values():
        if ent.get("$type") != _POSITION_TYPE:
            continue
        experience.append(
            ExperienceItem(
                title=_safe_str(ent, "title", "text") or _safe_str(ent, "title"),
                company=_safe_str(ent, "companyName", "text")
                or _safe_str(ent, "companyName"),
                location=_safe_str(ent, "locationName"),
                description=_safe_str(ent, "description", "text"),
                date_range=_extract_date_range(ent),
            )
        )

    # Education
    education: list[EducationItem] = []
    for ent in entities.values():
        if ent.get("$type") != _EDUCATION_TYPE:
            continue
        education.append(
            EducationItem(
                school=_safe_str(ent, "schoolName"),
                degree=_safe_str(ent, "degreeName"),
                field_of_study=_safe_str(ent, "fieldOfStudy"),
                date_range=_extract_date_range(ent),
                description=_safe_str(ent, "description", "text"),
            )
        )

    # Skills
    skills: list[str] = []
    for ent in entities.values():
        if ent.get("$type") != _SKILL_TYPE:
            continue
        name = _safe_str(ent, "name", "text") or _safe_str(ent, "name")
        if name:
            skills.append(name)

    # Certifications
    certifications: list[CertificationItem] = []
    for ent in entities.values():
        if ent.get("$type") != _CERT_TYPE:
            continue
        certifications.append(
            CertificationItem(
                name=_safe_str(ent, "name"),
                issuing_organization=_safe_str(ent, "authority"),
                credential_id=_safe_str(ent, "licenseNumber"),
                credential_url=_safe_str(ent, "url"),
            )
        )

    # Languages
    languages: list[LanguageItem] = []
    for ent in entities.values():
        if ent.get("$type") != _LANG_TYPE:
            continue
        languages.append(
            LanguageItem(
                name=_safe_str(ent, "name"),
                proficiency=_safe_str(ent, "proficiency"),
            )
        )

    photo = (
        profile_entity.get("profilePicture", {})
        .get("displayImageReference", {})
        .get("vectorImage", {})
    )
    image_url: str | None = None
    if isinstance(photo, dict):
        artifacts = photo.get("artifacts", [])
        if artifacts:
            root = photo.get("rootUrl", "")
            image_url = root + artifacts[-1].get("fileIdentifyingUrlPathSegment", "")

    return ProfileResponse(
        linkedin_url=linkedin_url,
        profile_id=profile_entity.get("publicIdentifier"),
        first_name=first,
        last_name=last,
        full_name=full,
        headline=_safe_str(profile_entity, "headline", "text")
        or _safe_str(profile_entity, "headline"),
        location=_safe_str(profile_entity, "locationName"),
        industry=_safe_str(profile_entity, "industryName"),
        about=_safe_str(profile_entity, "summary", "text")
        or _safe_str(profile_entity, "summary"),
        followers=profile_entity.get("followersCount"),
        connections=profile_entity.get("connectionsCount"),
        profile_image_url=image_url or None,
        experience=experience,
        education=education,
        skills=skills,
        certifications=certifications,
        languages=languages,
        scraped_at=datetime.now(tz=UTC).isoformat(),
    )


# ── Fallback: BeautifulSoup4 CSS parser ───────────────────────────────────────


def _build_profile_from_html(html: str, linkedin_url: str) -> ProfileResponse:
    """
    Minimal CSS-selector extraction when Voyager JSON is absent.
    Captures top-level profile card fields only.
    """
    soup = BeautifulSoup(html, "html.parser")

    def _text(selector: str) -> str | None:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    full_name = _text("h1.text-heading-xlarge") or _text("h1")
    headline = _text(".text-body-medium.break-words")
    location = _text(".text-body-small.inline.t-black--light.break-words")

    img_tag = soup.select_one("img.pv-top-card-profile-picture__image--show")
    image_url = img_tag.get("src") if img_tag else None

    about_el = soup.select_one("#about ~ div .inline-show-more-text")
    about = about_el.get_text(strip=True) if about_el else None

    logger.warning("parser.fallback_html_used", url=linkedin_url)

    return ProfileResponse(
        linkedin_url=linkedin_url,
        full_name=full_name,
        headline=headline,
        location=location,
        about=about,
        profile_image_url=image_url,
        scraped_at=datetime.now(tz=UTC).isoformat(),
    )


# ── Public entry point ────────────────────────────────────────────────────────


def parse_profile(html: str, linkedin_url: str) -> ProfileResponse:
    """
    Parse a LinkedIn profile HTML page into a ProfileResponse.

    Strategy:
      1. Attempt Voyager JSON extraction (rich, structured).
      2. Fall back to BS4 CSS parsing if Voyager yields no profile entity.
    """
    logger.info("parser.start", url=linkedin_url, html_len=len(html))

    try:
        entities = _parse_voyager(html)
        profile = _build_profile_from_voyager(entities, linkedin_url)
        if profile:
            logger.info(
                "parser.voyager_success",
                name=profile.full_name,
                exp_count=len(profile.experience),
            )
            return profile
    except Exception as exc:  # noqa: BLE001
        logger.warning("parser.voyager_error", error=str(exc))

    return _build_profile_from_html(html, linkedin_url)
