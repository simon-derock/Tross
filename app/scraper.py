"""
app/scraper.py
──────────────
High-level LinkedIn Scraping Orchestrator with 4-Tier Anti-Fragile Failover:
  1. In-Memory LRU Cache (24-hour TTL) for sub-millisecond repeated lookups.
  2. Authenticated Voyager API client with custom or configured session cookies.
  3. Automatic Failover to Anonymous Public Guest scraper on 401/403/Challenge.
  4. Trace ID tagging and cache propagation.
"""

from __future__ import annotations

import re
import time
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
from app.public_scraper import scrape_public_profile
from app.schemas import ProfileResponse

logger = get_logger(__name__)


class ScraperError(Exception):
    """Base exception for scraping orchestration errors."""


# ── In-Memory LRU Cache with 24-hour TTL ──────────────────────────────────────
CACHE_TTL_SECONDS: float = 24 * 60 * 60  # 86,400 seconds (24 hours)
MAX_CACHE_SIZE: int = 1000

# Mapping: normalized vanity_slug -> (expires_at_timestamp, ProfileResponse)
_PROFILE_CACHE: dict[str, tuple[float, ProfileResponse]] = {}


def get_cached_profile(vanity_slug: str) -> ProfileResponse | None:
    """Retrieve profile from in-memory cache if present and not expired."""
    key = vanity_slug.lower().strip()
    if key in _PROFILE_CACHE:
        expires_at, profile = _PROFILE_CACHE[key]
        if time.time() < expires_at:
            _PROFILE_CACHE.pop(key)
            _PROFILE_CACHE[key] = (expires_at, profile)
            return profile
        _PROFILE_CACHE.pop(key, None)
    return None


def set_cached_profile(
    vanity_slug: str,
    profile: ProfileResponse,
    ttl_seconds: float = CACHE_TTL_SECONDS,
) -> None:
    """Store profile in in-memory cache with TTL and LRU eviction."""
    key = vanity_slug.lower().strip()
    if len(_PROFILE_CACHE) >= MAX_CACHE_SIZE and key not in _PROFILE_CACHE:
        oldest_key = next(iter(_PROFILE_CACHE))
        _PROFILE_CACHE.pop(oldest_key, None)
    _PROFILE_CACHE[key] = (time.time() + ttl_seconds, profile)


def clear_cache() -> None:
    """Clear all entries from in-memory profile cache."""
    _PROFILE_CACHE.clear()


def extract_vanity_slug(raw_input: str) -> str:
    """
    Extract the vanity identifier / username from a LinkedIn profile URL or raw string.

    Supported formats:
      • https://www.linkedin.com/in/satyanadella/ -> satyanadella
      • https://linkedin.com/in/john-doe-123?miniProfileUrn=... -> john-doe-123
      • http://www.linkedin.com/in/jane-doe#experience -> jane-doe
      • linkedin.com/in/williamhgates -> williamhgates
      • in/reidhoffman -> reidhoffman
      • satyanadella -> satyanadella
    """
    clean = raw_input.strip()
    if not clean:
        raise ValueError("Profile input cannot be empty.")

    clean = clean.split("#")[0].split("?")[0].rstrip("/")

    match = re.search(r"/in/([^/?#]+)", clean)
    if match:
        slug = match.group(1).strip()
        if slug:
            return slug

    if clean.startswith("in/"):
        slug = clean[3:].strip()
        if slug:
            return slug

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

    slug = clean.strip()
    if re.match(r"^[a-zA-Z0-9_\-%]+$", slug):
        return slug

    raise ValueError(
        f"Unable to extract LinkedIn vanity slug from input '{raw_input}'."
    )


async def scrape_profile(
    linkedin_url: str,
    override_cookies: dict[str, str] | None = None,
) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL using reverse-engineered Voyager API endpoints
    with automatic failover to anonymous public scraper and in-memory LRU cache.
    """
    trace_id = new_trace_id()
    settings = get_settings()

    vanity_slug = extract_vanity_slug(linkedin_url)
    canonical_url = (
        linkedin_url
        if linkedin_url.startswith("http")
        else f"https://www.linkedin.com/in/{vanity_slug}"
    )

    # ── a. Check In-Memory LRU Cache ──────────────────────────────────────────
    cached_profile = get_cached_profile(vanity_slug)
    if cached_profile is not None:
        logger.info(
            "scraper.cache_hit",
            vanity_slug=vanity_slug,
            trace_id=trace_id,
        )
        response_copy = cached_profile.model_copy()
        response_copy.trace_id = trace_id
        return response_copy

    logger.info(
        "scraper.start",
        url=canonical_url,
        vanity_slug=vanity_slug,
        trace_id=trace_id,
    )

    # ── b. Resolve Credentials ────────────────────────────────────────────────
    li_at: str | None = None
    jsessionid: str | None = None

    if override_cookies:
        li_at = (
            override_cookies.get("li_at")
            or override_cookies.get("X-Li-At")
            or override_cookies.get("x-li-at")
        )
        jsessionid = (
            override_cookies.get("JSESSIONID")
            or override_cookies.get("jsessionid")
            or override_cookies.get("X-JSESSIONID")
            or override_cookies.get("x-jsessionid")
        )
    else:
        li_at = settings.li_at
        jsessionid = settings.jsessionid

    profile: ProfileResponse | None = None

    # ── c. Authenticated Voyager Scraping or Failover ──────────────────────────
    if li_at:
        try:
            async with VoyagerClient(
                li_at=li_at,
                jsessionid=jsessionid,
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

        except AuthenticationError as exc:
            logger.warning(
                "scraper.auth_failed_fallback_to_public",
                error=str(exc),
                vanity_slug=vanity_slug,
                trace_id=trace_id,
            )
            profile = await scrape_public_profile(
                vanity_slug=vanity_slug,
                proxy_url=settings.proxy_url,
            )

        except VoyagerAPIError as exc:
            err_msg = str(exc).lower()
            if (
                exc.status_code in (401, 403)
                or "auth" in err_msg
                or "challenge" in err_msg
                or "checkpoint" in err_msg
            ):
                logger.warning(
                    "scraper.voyager_challenge_fallback_to_public",
                    error=str(exc),
                    vanity_slug=vanity_slug,
                    trace_id=trace_id,
                )
                profile = await scrape_public_profile(
                    vanity_slug=vanity_slug,
                    proxy_url=settings.proxy_url,
                )
            else:
                logger.error(
                    "scraper.voyager_error", error=str(exc), vanity_slug=vanity_slug
                )
                raise ScraperError(f"LinkedIn Voyager API error: {exc}") from exc

        except (ProfileNotFoundError, RateLimitError):
            raise

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "scraper.unexpected_error", error=str(exc), vanity_slug=vanity_slug
            )
            raise ScraperError(f"Unexpected scraping error: {exc}") from exc
    else:
        # No credentials configured — directly use anonymous public guest scraper
        logger.info(
            "scraper.no_credentials_using_public",
            vanity_slug=vanity_slug,
            trace_id=trace_id,
        )
        profile = await scrape_public_profile(
            vanity_slug=vanity_slug,
            proxy_url=settings.proxy_url,
        )

    # ── d. Cache & Attach Trace ID ────────────────────────────────────────────
    profile.trace_id = trace_id
    set_cached_profile(vanity_slug, profile)

    logger.info(
        "scraper.complete",
        name=profile.full_name,
        vanity_slug=vanity_slug,
        trace_id=trace_id,
        experience_count=len(profile.experience),
        skills_count=len(profile.skills),
    )
    return profile
