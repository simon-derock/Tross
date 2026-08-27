"""
app/scraper.py
──────────────
High-level LinkedIn Scraping Orchestrator.

Flow:
  1. Extract vanity slug from any LinkedIn profile URL or identifier.
  2. Instantiate VoyagerClient using session credentials (LI_AT / JSESSIONID) from Settings.
  3. Fetch raw Voyager profileView JSON via curl_cffi Chrome 131 session.
  4. Parse and normalize JSON into structured ProfileResponse model.
  5. Attach per-request trace_id and return.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.config import get_settings
from app.logging_config import get_logger, new_trace_id
from app.network import (
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
    VoyagerAPIError,
    VoyagerClient,
)
from app.parser import parse_voyager_profile
from app.schemas import ProfileResponse

logger = get_logger(__name__)


class ScraperError(Exception):
    """Base exception for scraping orchestration errors."""


def extract_vanity_slug(raw_input: str) -> str:
    """
    Extract the vanity identifier / username from a LinkedIn profile URL or raw string.

    Supported formats:
      • https://www.linkedin.com/in/satyanadella/ -> satyanadella
      • https://linkedin.com/in/john-doe-123?miniProfileUrn=... -> john-doe-123
      • http://www.linkedin.com/in/jane-doe#experience -> jane-doe
      • linkedin.com/in/williamhgates -> williamhgates
      • in/satyanadella -> satyanadella
      • satyanadella -> satyanadella

    Raises:
      ValueError: If the string is completely empty or cannot be parsed.
    """
    clean = raw_input.strip()
    if not clean:
        raise ValueError("Profile input cannot be empty.")

    # Remove trailing fragments or query parameters
    clean = clean.split("#")[0].split("?")[0].rstrip("/")

    # Pattern 1: Contains /in/<slug>
    match = re.search(r"/in/([^/?#]+)", clean)
    if match:
        slug = match.group(1).strip()
        if slug:
            return slug

    # Pattern 2: Starts with in/<slug>
    if clean.startswith("in/"):
        slug = clean[3:].strip()
        if slug:
            return slug

    # Pattern 3: Full URL without /in/ (e.g. invalid company or school URL passed)
    if (
        clean.startswith("http://")
        or clean.startswith("https://")
        or "linkedin.com" in clean
    ):
        parsed = urlparse(clean if "://" in clean else f"https://{clean}")
        path_parts = [p for p in parsed.path.split("/") if p]
        if "in" in path_parts:
            idx = path_parts.index("in")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
        raise ValueError(
            f"Invalid LinkedIn profile URL '{raw_input}'. Expected format 'https://www.linkedin.com/in/<username>'."
        )

    # Pattern 4: Raw vanity slug (e.g. 'satyanadella')
    slug = clean.strip()
    if re.match(r"^[a-zA-Z0-9_\-%]+$", slug):
        return slug

    raise ValueError(
        f"Unable to extract LinkedIn vanity slug from input '{raw_input}'."
    )


async def scrape_profile(linkedin_url: str) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL using reverse-engineered Voyager API endpoints.

    Args:
        linkedin_url: Validated LinkedIn profile URL or vanity slug.

    Returns:
        ProfileResponse populated with all extracted profile fields.

    Raises:
        AuthenticationError: If backend session cookies (li_at / JSESSIONID) are invalid or expired.
        ProfileNotFoundError: If the target LinkedIn profile does not exist (HTTP 404).
        RateLimitError: If LinkedIn rate limits the request (HTTP 429 / 999).
        ScraperError: On other upstream API or network failures.
    """
    trace_id = new_trace_id()
    settings = get_settings()

    vanity_slug = extract_vanity_slug(linkedin_url)
    canonical_url = (
        linkedin_url
        if linkedin_url.startswith("http")
        else f"https://www.linkedin.com/in/{vanity_slug}"
    )

    logger.info(
        "scraper.start",
        url=canonical_url,
        vanity_slug=vanity_slug,
        trace_id=trace_id,
    )

    try:
        async with VoyagerClient(
            li_at=settings.li_at,
            jsessionid=settings.jsessionid,
            proxy_url=settings.proxy_url,
            max_retries=settings.max_retries,
            backoff_seconds=settings.retry_backoff_seconds,
        ) as client:
            raw_data = await client.get_profile_view(vanity_slug)

        profile = parse_voyager_profile(
            data=raw_data,
            linkedin_url=canonical_url,
            vanity_slug=vanity_slug,
        )
        profile.trace_id = trace_id

        logger.info(
            "scraper.complete",
            name=profile.full_name,
            vanity_slug=vanity_slug,
            trace_id=trace_id,
            experience_count=len(profile.experience),
            skills_count=len(profile.skills),
        )
        return profile

    except (AuthenticationError, ProfileNotFoundError, RateLimitError):
        # Re-raise domain exceptions to be handled by FastAPI exception handlers
        raise

    except VoyagerAPIError as exc:
        logger.error("scraper.voyager_error", error=str(exc), vanity_slug=vanity_slug)
        raise ScraperError(f"LinkedIn Voyager API error: {exc}") from exc

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "scraper.unexpected_error", error=str(exc), vanity_slug=vanity_slug
        )
        raise ScraperError(f"Unexpected scraping error: {exc}") from exc
