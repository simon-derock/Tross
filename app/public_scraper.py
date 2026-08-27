"""
app/public_scraper.py
─────────────────────
Anonymous Public LinkedIn Guest Profile Scraper.

Uses curl_cffi with Chrome 131 TLS impersonation WITHOUT session cookies.
Fetches https://www.linkedin.com/in/{vanity_slug}/ and parses:
  • Schema.org JSON-LD (<script type="application/ld+json">)
  • OpenGraph & standard HTML meta tags (og:title, og:description, og:image, etc.)

Returns structured ProfileResponse populated with public profile data.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from app.logging_config import get_logger, new_trace_id
from app.network import (
    CHROME_131_USER_AGENT,
    ProfileNotFoundError,
    RateLimitError,
)
from app.schemas import DateRange, EducationItem, ExperienceItem, ProfileResponse

logger = get_logger(__name__)


class ScraperError(Exception):
    """Base exception for scraping orchestration and public scraping errors."""


def parse_public_html(
    html: str,
    vanity_slug: str,
    trace_id: str | None = None,
) -> ProfileResponse:
    """
    Parse LinkedIn public / guest profile HTML into a structured ProfileResponse.

    Extracts Schema.org JSON-LD (`@type: Person` or `@graph`) and supplements
    any missing attributes using OpenGraph and standard HTML meta tags.
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── 1. Locate and parse Schema.org JSON-LD ─────────────────────────────────
    person_data: dict[str, Any] = {}
    for script in soup.find_all(
        "script", type=lambda t: t and "application/ld+json" in t
    ):
        text = script.string or script.get_text()
        if not text:
            continue
        try:
            parsed = json.loads(text.strip())
        except Exception:
            continue

        if isinstance(parsed, dict):
            t = parsed.get("@type")
            if t == "Person" or (isinstance(t, list) and "Person" in t):
                person_data = parsed
                break
            graph = parsed.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict) and (
                        item.get("@type") == "Person"
                        or (
                            isinstance(item.get("@type"), list)
                            and "Person" in item.get("@type")
                        )
                    ):
                        person_data = item
                        break
                if person_data:
                    break
            main_entity = parsed.get("mainEntity")
            if isinstance(main_entity, dict) and (
                main_entity.get("@type") == "Person"
                or (
                    isinstance(main_entity.get("@type"), list)
                    and "Person" in main_entity.get("@type")
                )
            ):
                person_data = main_entity
                break
            if "name" in parsed and (
                "jobTitle" in parsed or "worksFor" in parsed or "alumniOf" in parsed
            ):
                person_data = parsed
                break

        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and (
                    item.get("@type") == "Person"
                    or (
                        isinstance(item.get("@type"), list)
                        and "Person" in item.get("@type")
                    )
                ):
                    person_data = item
                    break
            if person_data:
                break

    # ── 2. Extract OpenGraph & HTML Meta tags ──────────────────────────────────
    og_title: str | None = None
    og_desc: str | None = None
    og_image: str | None = None
    meta_desc: str | None = None
    page_title: str | None = None

    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or "").lower()
        name = (meta.get("name") or "").lower()
        content = (meta.get("content") or "").strip()
        if not content:
            continue
        if prop == "og:title":
            og_title = content
        elif prop == "og:description":
            og_desc = content
        elif prop == "og:image":
            og_image = content
        elif name == "description":
            meta_desc = content

    if soup.title and soup.title.string:
        page_title = soup.title.string.strip()

    # ── 3. Parse Name ─────────────────────────────────────────────────────────
    full_name: str | None = person_data.get("name")
    first_name: str | None = person_data.get("givenName")
    last_name: str | None = person_data.get("familyName")

    if full_name and not first_name and not last_name:
        parts = full_name.strip().split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else None
    elif not full_name and (first_name or last_name):
        full_name = f"{first_name or ''} {last_name or ''}".strip() or None

    if not full_name:
        title_source = og_title or page_title
        if title_source:
            clean_title = title_source.split("| LinkedIn")[0].split("|")[0].strip()
            name_parts = [p.strip() for p in clean_title.split(" - ") if p.strip()]
            if name_parts:
                full_name = name_parts[0]
                parts = full_name.split(maxsplit=1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else None

    # ── 4. Parse Headline ─────────────────────────────────────────────────────
    headline: str | None = None
    job_title_val = person_data.get("jobTitle")
    if isinstance(job_title_val, list):
        headline = ", ".join(str(j) for j in job_title_val if j)
    elif isinstance(job_title_val, str) and job_title_val.strip():
        headline = job_title_val.strip()

    if not headline:
        headline = person_data.get("disambiguatingDescription")

    if not headline and (og_title or page_title):
        title_source = og_title or page_title
        clean_title = title_source.split("| LinkedIn")[0].split("|")[0].strip()
        name_parts = [p.strip() for p in clean_title.split(" - ") if p.strip()]
        if len(name_parts) > 1:
            headline = " - ".join(name_parts[1:])

    # ── 5. Parse About / Summary ──────────────────────────────────────────────
    about: str | None = person_data.get("description")
    if (
        not about
        and meta_desc
        and not ("View " in meta_desc and "profile on LinkedIn" in meta_desc)
    ):
        about = meta_desc
    if (
        not about
        and og_desc
        and not ("View " in og_desc and "profile on LinkedIn" in og_desc)
    ):
        about = og_desc

    # ── 6. Parse Profile Photo ────────────────────────────────────────────────
    profile_image_url: str | None = None
    image_val = person_data.get("image")
    if isinstance(image_val, str) and image_val.strip():
        profile_image_url = image_val.strip()
    elif isinstance(image_val, dict):
        profile_image_url = image_val.get("contentUrl") or image_val.get("url")
    elif isinstance(image_val, list) and image_val:
        first_img = image_val[0]
        profile_image_url = (
            first_img.get("contentUrl") or first_img.get("url")
            if isinstance(first_img, dict)
            else str(first_img)
        )

    if not profile_image_url and og_image:
        profile_image_url = og_image

    # ── 7. Parse Location ─────────────────────────────────────────────────────
    location: str | None = None
    country: str | None = None
    addr_val = person_data.get("address")
    if isinstance(addr_val, str) and addr_val.strip():
        location = addr_val.strip()
    elif isinstance(addr_val, dict):
        loc_parts: list[str] = []
        for k in ["addressLocality", "addressRegion", "addressCountry"]:
            v = addr_val.get(k)
            if isinstance(v, dict):
                v = v.get("name")
            if v and isinstance(v, str):
                loc_parts.append(v.strip())
        if loc_parts:
            location = ", ".join(loc_parts)
        country_val = addr_val.get("addressCountry")
        if isinstance(country_val, dict):
            country = country_val.get("name")
        elif isinstance(country_val, str):
            country = country_val

    # ── 8. Parse Experience (worksFor & hasOccupation) ────────────────────────
    experience_list: list[ExperienceItem] = []
    works_for = person_data.get("worksFor")
    if works_for:
        raw_works = works_for if isinstance(works_for, list) else [works_for]
        for w in raw_works:
            if isinstance(w, dict):
                comp_name = w.get("name")
                comp_url = w.get("url") or w.get("sameAs")
                loc = w.get("location")
                if isinstance(loc, dict):
                    loc = loc.get("name") or loc.get("addressLocality")
                title = w.get("jobTitle") or headline
                desc = w.get("description")
                date_range = None
                if "startDate" in w or "endDate" in w:
                    date_range = DateRange(
                        start_date=str(w.get("startDate"))
                        if w.get("startDate")
                        else None,
                        end_date=str(w.get("endDate")) if w.get("endDate") else None,
                    )
                experience_list.append(
                    ExperienceItem(
                        title=title,
                        company=comp_name,
                        company_url=comp_url,
                        location=loc if isinstance(loc, str) else None,
                        description=desc,
                        date_range=date_range,
                    )
                )
            elif isinstance(w, str) and w.strip():
                experience_list.append(
                    ExperienceItem(
                        company=w.strip(),
                        title=headline,
                    )
                )

    has_occupation = person_data.get("hasOccupation")
    if has_occupation:
        raw_occ = (
            has_occupation if isinstance(has_occupation, list) else [has_occupation]
        )
        for occ in raw_occ:
            if isinstance(occ, dict):
                occ_title = (
                    occ.get("name")
                    or occ.get("roleName")
                    or occ.get("hasOccupationRoleName")
                )
                org = occ.get("organization") or occ.get("worksFor")
                comp_name = (
                    org.get("name")
                    if isinstance(org, dict)
                    else (org if isinstance(org, str) else None)
                )
                comp_url = org.get("url") if isinstance(org, dict) else None
                loc = occ.get("hasOccupationLocation")
                if isinstance(loc, dict):
                    loc = loc.get("name") or loc.get("addressLocality")
                experience_list.append(
                    ExperienceItem(
                        title=occ_title,
                        company=comp_name,
                        company_url=comp_url,
                        location=loc if isinstance(loc, str) else None,
                    )
                )

    # ── 9. Parse Education (alumniOf) ─────────────────────────────────────────
    education_list: list[EducationItem] = []
    alumni_of = person_data.get("alumniOf")
    if alumni_of:
        raw_alumni = alumni_of if isinstance(alumni_of, list) else [alumni_of]
        for a in raw_alumni:
            if isinstance(a, dict):
                school_name = a.get("name")
                school_url = a.get("url") or a.get("sameAs")
                degree = a.get("award") or a.get("degree")
                desc = a.get("description")
                education_list.append(
                    EducationItem(
                        school=school_name,
                        school_url=school_url,
                        degree=degree,
                        description=desc,
                    )
                )
            elif isinstance(a, str) and a.strip():
                education_list.append(EducationItem(school=a.strip()))

    canonical_url = f"https://www.linkedin.com/in/{vanity_slug}"
    now_iso = datetime.now(tz=UTC).isoformat()

    return ProfileResponse(
        linkedin_url=canonical_url,
        profile_id=vanity_slug,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        headline=headline,
        location=location,
        country=country,
        industry=person_data.get("knowsAbout")
        if isinstance(person_data.get("knowsAbout"), str)
        else None,
        about=about,
        profile_image_url=profile_image_url,
        experience=experience_list,
        education=education_list,
        scraped_at=now_iso,
        trace_id=trace_id,
    )


async def scrape_public_profile(
    vanity_slug: str, proxy_url: str | None = None
) -> ProfileResponse:
    """
    Scrape a public LinkedIn profile anonymously without cookies using curl_cffi Chrome 131.
    """
    clean_slug = vanity_slug.strip().strip("/")
    url = f"https://www.linkedin.com/in/{clean_slug}/"
    trace_id = new_trace_id()

    logger.info(
        "public_scraper.start",
        url=url,
        vanity_slug=clean_slug,
        trace_id=trace_id,
    )

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": CHROME_131_USER_AGENT,
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }

    try:
        async with AsyncSession(impersonate="chrome131", proxy=proxy_url) as session:
            response = await session.get(url, headers=headers)

        if response.status_code == 404:
            raise ProfileNotFoundError(
                f"LinkedIn public profile not found for vanity slug '{clean_slug}' (HTTP 404)."
            )

        if response.status_code in (429, 999):
            raise RateLimitError(
                f"LinkedIn rate limit exceeded on public profile for '{clean_slug}' (HTTP {response.status_code})."
            )

        if response.status_code != 200:
            raise ScraperError(
                f"LinkedIn public profile request failed with HTTP {response.status_code} for '{clean_slug}'."
            )

        profile = parse_public_html(
            html=response.text,
            vanity_slug=clean_slug,
            trace_id=trace_id,
        )

        logger.info(
            "public_scraper.complete",
            name=profile.full_name,
            vanity_slug=clean_slug,
            trace_id=trace_id,
            experience_count=len(profile.experience),
            education_count=len(profile.education),
        )
        return profile

    except (ProfileNotFoundError, RateLimitError):
        raise
    except ScraperError:
        raise
    except Exception as exc:
        logger.error(
            "public_scraper.unexpected_error",
            error=str(exc),
            vanity_slug=clean_slug,
            trace_id=trace_id,
        )
        raise ScraperError(f"Unexpected public scraping error: {exc}") from exc
