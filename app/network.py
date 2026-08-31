"""
app/network.py
──────────────
Reverse-engineered LinkedIn Voyager Network Client using curl_cffi Chrome 131 impersonation.

Features:
  • curl_cffi.requests.AsyncSession with Chrome 131 fingerprint
  • Dynamic CSRF header derived from JSESSIONID (strips surrounding quotes)
  • Authentic Chrome 131 HTTP request headers matching LinkedIn Voyager web client
  • Dynamic page instance URN generation per request
  • Tenacity exponential backoff retries for 429, 500, 502, 503, 504, 999
  • Custom domain exceptions: AuthenticationError, ProfileNotFoundError, RateLimitError, VoyagerAPIError
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from curl_cffi.requests import AsyncSession, Response, Session
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.logging_config import get_logger

logger = get_logger(__name__)

# ── Status codes eligible for tenacity retry ──────────────────────────────────
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504, 999}

# ── Default Chrome 131 User-Agent string ──────────────────────────────────────
CHROME_131_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ── Base Voyager tracking payload ─────────────────────────────────────────────
DEFAULT_TRACKING_PAYLOAD = {
    "clientVersion": "1.13.19790",
    "osName": "web",
    "timezoneOffset": 0,
    "deviceFormFactor": "DESKTOP",
    "mpName": "voyager-web",
}


# ── Domain Exceptions ─────────────────────────────────────────────────────────


class VoyagerError(Exception):
    """Base exception for all LinkedIn Voyager network and client errors."""


class AuthenticationError(VoyagerError):
    """Raised on HTTP 401 or 403 when LinkedIn session credentials are invalid or expired."""


class ProfileNotFoundError(VoyagerError):
    """Raised on HTTP 404 when the requested LinkedIn profile does not exist."""


class RateLimitError(VoyagerError):
    """Raised on HTTP 429 or 999 when LinkedIn rate limits/throttles requests after retries."""


class VoyagerAPIError(VoyagerError):
    """Raised on unexpected HTTP status codes or unparseable API responses."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class _RetryableStatusError(Exception):
    """Internal exception to signal tenacity to retry on transient HTTP status codes."""

    def __init__(self, status_code: int, response: Response | None = None) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(f"Retryable HTTP status: {status_code}")


# ── Header Builder ────────────────────────────────────────────────────────────


def build_voyager_headers(
    vanity_slug: str,
    csrf_token: str,
    tracking_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Build complete, authentic Chrome 131 headers for LinkedIn Voyager API requests.

    Args:
        vanity_slug: LinkedIn member vanity slug (e.g. 'satyanadella').
        csrf_token: Clean CSRF token (unquoted JSESSIONID value).
        tracking_payload: Optional custom tracking metadata dict.

    Returns:
        Dictionary of HTTP request headers.
    """
    payload = tracking_payload or DEFAULT_TRACKING_PAYLOAD
    return {
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": CHROME_131_USER_AGENT,
        "x-restli-protocol-version": "2.0.0",
        "x-li-lang": "en_US",
        "x-li-track": json.dumps(payload),
        "x-li-page-instance": f"urn:li:page:d_flagship3_profile_view_base;{uuid.uuid4()}",
        # Mobile SDK headers: decouples session from desktop browser lifecycle
        "x-li-src": "msdk",
        "x-li-device-id": "urn:li:device:vercel-serverless-001",
        "csrf-token": csrf_token,
        "Referer": f"https://www.linkedin.com/in/{vanity_slug}/",
        "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }


# ── Voyager Client ────────────────────────────────────────────────────────────


class VoyagerClient:
    """
    LinkedIn Voyager API client using curl_cffi with Chrome 131 TLS impersonation.
    Must be used as an async context manager.
    """

    def __init__(
        self,
        li_at: str | None = None,
        jsessionid: str | None = None,
        *,
        cookies: dict[str, str] | None = None,
        proxy_url: str | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        impersonate: str = "chrome131",
    ) -> None:
        """
        Initialize VoyagerClient with session credentials and configuration.

        Args:
            li_at: LinkedIn 'li_at' session cookie value.
            jsessionid: LinkedIn 'JSESSIONID' session cookie value (quotes stripped automatically).
            cookies: Optional dictionary containing 'li_at' and 'JSESSIONID'.
            proxy_url: Optional residential/datacenter proxy URI (e.g. 'http://user:pass@host:port').
            max_retries: Maximum number of tenacity retry attempts on transient failures.
            backoff_seconds: Base multiplier in seconds for exponential backoff.
            impersonate: Browser profile for curl_cffi impersonation (defaults to 'chrome131').
        """
        if cookies:
            self.li_at = cookies.get("li_at", "")
            self.jsessionid = cookies.get("JSESSIONID", cookies.get("jsessionid", ""))
        else:
            self.li_at = li_at or ""
            self.jsessionid = jsessionid or ""

        self.proxy_url = proxy_url
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.impersonate = impersonate
        self._session: AsyncSession | None = None

    @property
    def csrf_token(self) -> str:
        """Derive CSRF token from JSESSIONID by stripping surrounding quotes while preserving prefix."""
        return self.jsessionid.strip('"').strip()

    @property
    def cookies(self) -> dict[str, str]:
        """Format cookie jar required by LinkedIn."""
        return {
            "li_at": self.li_at,
            "JSESSIONID": f'"{self.csrf_token}"'
            if not self.csrf_token.startswith('"')
            else self.csrf_token,
        }

    def build_headers(self, vanity_slug: str) -> dict[str, str]:
        """Construct request headers for a specific vanity slug profile request."""
        return build_voyager_headers(
            vanity_slug=vanity_slug,
            csrf_token=self.csrf_token,
        )

    async def __aenter__(self) -> VoyagerClient:
        """Open curl_cffi AsyncSession with Chrome 131 impersonation and cookies."""
        if self.proxy_url:
            logger.info("network.proxy_enabled", proxy=self.proxy_url[:30] + "…")

        self._session = AsyncSession(
            impersonate=self.impersonate,
            cookies=self.cookies,
            proxy=self.proxy_url,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close underlying curl_cffi AsyncSession."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_profile_view(
        self,
        vanity_slug: str,
        decoration_id: str = "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-118",
    ) -> dict[str, Any]:
        """
        Fetch and parse the Voyager profile view endpoint for a given vanity slug.

        Endpoint:
          https://www.linkedin.com/voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={vanity_slug}&decorationId={decoration_id}

        Retries:
          Retries on HTTP 429, 500, 502, 503, 504, 999 with exponential backoff.

        Raises:
          AuthenticationError: If response is HTTP 401 or 403.
          ProfileNotFoundError: If response is HTTP 404.
          RateLimitError: If HTTP 429 or 999 persists after all retries.
          VoyagerAPIError: If HTTP 5xx persists or on unexpected response / parsing failure.
          RuntimeError: If called outside an async context manager.
        """
        if self._session is None:
            raise RuntimeError(
                "VoyagerClient must be used as an async context manager."
            )

        clean_slug = vanity_slug.strip().strip("/")
        url = (
            f"https://www.linkedin.com/voyager/api/identity/dash/profiles"
            f"?q=memberIdentity&memberIdentity={clean_slug}"
            f"&decorationId={decoration_id}"
        )
        headers = self.build_headers(clean_slug)
        attempt_count = 0

        async def _fetch() -> Response:
            nonlocal attempt_count
            attempt_count += 1
            logger.info(
                "network.voyager_get",
                vanity_slug=clean_slug,
                attempt=attempt_count,
            )
            try:
                response = await self._session.get(
                    url,
                    headers=headers,
                    allow_redirects=False,
                )
            except Exception as err:
                logger.warning("network.async_fallback_to_sync", error=str(err))

                def _sync_fetch() -> Response:
                    with Session(
                        impersonate=self.impersonate,
                        cookies=self.cookies,
                        proxy=self.proxy_url,
                    ) as sync_session:
                        return sync_session.get(
                            url, headers=headers, allow_redirects=False
                        )

                response = await asyncio.to_thread(_sync_fetch)

            # Redirects to login/authwall mean session is invalid or expired
            if response.status_code in (301, 302, 303, 307, 308, 401, 403):
                raise AuthenticationError(
                    "LinkedIn rejected the server's session (IP flagged). "
                    "Open Swagger UI (/docs) and provide your own fresh 'X-Li-At' and 'X-JSESSIONID' headers to bypass this."
                )

            if response.status_code in RETRYABLE_STATUS_CODES:
                logger.warning(
                    "network.voyager_retryable_status",
                    status=response.status_code,
                    attempt=attempt_count,
                    vanity_slug=clean_slug,
                )
                raise _RetryableStatusError(response.status_code, response)

            if response.status_code == 404:
                raise ProfileNotFoundError(
                    f"LinkedIn profile not found for vanity slug '{clean_slug}' (HTTP 404)."
                )

            if response.status_code != 200:
                raise VoyagerAPIError(
                    f"Unexpected HTTP {response.status_code} from LinkedIn Voyager API.",
                    status_code=response.status_code,
                )

            return response

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(
                    multiplier=self.backoff_seconds,
                    min=self.backoff_seconds,
                    max=60,
                ),
                retry=retry_if_exception_type(_RetryableStatusError),
                reraise=True,
            ):
                with attempt:
                    resp = await _fetch()
        except _RetryableStatusError as exc:
            if exc.status_code in (429, 999):
                raise RateLimitError(
                    f"LinkedIn rate limit exceeded (HTTP {exc.status_code}) "
                    f"for '{clean_slug}' after {self.max_retries} attempts."
                ) from exc
            raise VoyagerAPIError(
                f"LinkedIn Voyager API server error (HTTP {exc.status_code}) "
                f"for '{clean_slug}' after {self.max_retries} attempts.",
                status_code=exc.status_code,
            ) from exc

        try:
            data = resp.json()
            if not isinstance(data, dict):
                raise VoyagerAPIError(
                    "LinkedIn Voyager API returned non-dictionary JSON response.",
                    status_code=200,
                )
            return data
        except Exception as exc:
            if isinstance(exc, VoyagerAPIError):
                raise
            raise VoyagerAPIError(
                f"Failed to decode JSON from LinkedIn Voyager API response: {exc}",
                status_code=200,
            ) from exc


# ── Backwards compatibility alias ─────────────────────────────────────────────
LinkedInClient = VoyagerClient
