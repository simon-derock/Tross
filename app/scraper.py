"""
app/scraper.py
──────────────
High-level LinkedIn Scraping Orchestrator.

Flow:
  1. Extract vanity slug from LinkedIn profile URL (e.g. 'satyanadella').
  2. Instantiate VoyagerClient using session credentials (LI_AT / JSESSIONID) from Settings.
  3. Fetch raw Voyager profileView JSON via curl_cffi Chrome 131 session.
  4. Parse and normalize JSON into PhantomBuster-compliant ProfileResponse model.
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


def extract_vanity_slug(linkedin_url: str) -> str:
    """
    Extract the vanity identifier / username from a LinkedIn profile URL.

    Examples:
      • https://www.linkedin.com/in/satyanadella/ -> satyanadella
      • https://linkedin.com/in/john-doe-123?miniProfileUrn=... -> john-doe-123
      • https://www.linkedin.com/in/jane-doe#experience -> jane-doe

    Raises:
      ValueError: If the URL does not contain a valid /in/ vanity slug.
    """
    clean_url = linkedin_url.strip()
    parsed = urlparse(clean_url)
    path = parsed.path.rstrip("/")

    match = re.search(r"/in/([^/?#]+)", path)
    if not match:
        raise ValueError(
            f"Invalid LinkedIn profile URL '{linkedin_url}'. Expected path format '/in/<username>'."
        )

    slug = match.group(1).strip()
    if not slug:
        raise ValueError(f"Empty member vanity slug extracted from '{linkedin_url}'.")

    return slug


async def scrape_profile(linkedin_url: str) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL using reverse-engineered Voyager API endpoints.

    Args:
        linkedin_url: Validated LinkedIn profile URL.

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
    logger.info(
        "scraper.start",
        url=linkedin_url,
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
            linkedin_url=linkedin_url,
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
