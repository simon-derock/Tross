"""
app/scraper.py
──────────────
High-level scraping orchestrator.
Ties together: SessionCache → LinkedInClient → parse_profile.

Flow:
  1. Load cookies from Redis (or fall back to env-configured cookies).
  2. Fetch LinkedIn profile page via HTTPX with proxy + retries.
  3. On 401/403 → invalidate Redis cache, raise AuthenticationError.
  4. Parse HTML into ProfileResponse via parser.py.
  5. Return structured ProfileResponse.
"""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.logging_config import get_logger, new_trace_id
from app.network import LinkedInClient
from app.parser import parse_profile
from app.schemas import ProfileResponse
from app.session import SessionCache

logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when LinkedIn returns 401/403 — cookies are expired."""


class ScraperError(Exception):
    """Raised on non-retryable scraping failure."""


async def scrape_profile(linkedin_url: str) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL and return a structured ProfileResponse.

    Args:
        linkedin_url: Validated LinkedIn profile URL (from ScrapeRequest).

    Returns:
        ProfileResponse populated with all extractable fields.

    Raises:
        AuthenticationError: If LinkedIn responds 401/403.
        ScraperError: On permanent fetch failure (404, bad HTML, etc.).
    """
    trace_id = new_trace_id()
    settings = get_settings()

    logger.info("scraper.start", url=linkedin_url, trace_id=trace_id)

    # ── 1. Resolve cookies (Redis cache → env fallback) ───────────────────────
    cache = SessionCache(str(settings.upstash_redis_url))
    cookies = await cache.get_cookies()

    if cookies is None:
        cookies = {
            "li_at": settings.li_at,
            "JSESSIONID": f'"{settings.jsessionid}"',
        }
        logger.info("scraper.using_env_cookies")
    else:
        logger.info("scraper.using_cached_cookies")

    # ── 2. Fetch profile page ─────────────────────────────────────────────────
    try:
        async with LinkedInClient(
            cookies=cookies,
            proxy_url=settings.proxy_url,
            max_retries=settings.max_retries,
            backoff_seconds=settings.retry_backoff_seconds,
        ) as client:
            response = await client.get(linkedin_url)

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.error("scraper.http_error", status=status, url=linkedin_url)
        if status in (401, 403):
            await cache.invalidate()
            raise AuthenticationError(
                f"LinkedIn rejected cookies (HTTP {status}). "
                "Please refresh li_at / JSESSIONID."
            ) from exc
        raise ScraperError(f"HTTP {status} fetching {linkedin_url}") from exc

    except Exception as exc:  # noqa: BLE001
        logger.error("scraper.network_error", error=str(exc))
        raise ScraperError(f"Network failure: {exc}") from exc

    finally:
        await cache.close()

    # ── 3. Guard non-200 ──────────────────────────────────────────────────────
    if response.status_code == 404:
        raise ScraperError(f"Profile not found: {linkedin_url}")
    if response.status_code != 200:
        raise ScraperError(
            f"Unexpected HTTP {response.status_code} from {linkedin_url}"
        )

    # ── 4. Cache successful cookies for future requests ───────────────────────
    cache2 = SessionCache(str(settings.upstash_redis_url))
    await cache2.set_cookies(cookies)
    await cache2.close()

    # ── 5. Parse and return ───────────────────────────────────────────────────
    html = response.text
    profile = parse_profile(html, linkedin_url)
    profile.trace_id = trace_id

    logger.info(
        "scraper.complete",
        name=profile.full_name,
        trace_id=trace_id,
        exp_count=len(profile.experience),
    )
    return profile
