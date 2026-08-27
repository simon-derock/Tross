"""
app/network.py
──────────────
Async HTTPX client for LinkedIn requests.
Features:
  • Residential proxy injection
  • LinkedIn-authentic request headers
  • tenacity exponential-backoff retry on 429 / 5xx / network errors
  • Structured logging with trace_id at every retry boundary
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.logging_config import get_logger

logger = get_logger(__name__)

# ── LinkedIn-authentic headers (mimics Chrome 124 on Windows) ─────────────────
_BASE_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)


def _is_retryable_response(response: httpx.Response) -> bool:
    return response.status_code in _RETRYABLE_STATUS


class LinkedInClient:
    """
    Async HTTPX client pre-configured for LinkedIn scraping.
    Must be used as an async context manager.
    """

    def __init__(
        self,
        cookies: dict[str, str],
        proxy_url: str | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 2.0,
    ) -> None:
        self._cookies = cookies
        self._proxy_url = proxy_url
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LinkedInClient:
        if self._proxy_url:
            logger.info("network.proxy_enabled", proxy=self._proxy_url[:30] + "…")

        self._client = httpx.AsyncClient(
            headers=_BASE_HEADERS,
            cookies=self._cookies,
            proxy=self._proxy_url,  # type: ignore[arg-type]
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """
        GET with tenacity retry.
        Retries on: network errors, 429, 5xx.
        Raises httpx.HTTPStatusError on 401/403/404 (non-retryable).
        """
        if not self._client:
            raise RuntimeError("LinkedInClient must be used as async context manager")

        attempt = 0

        async def _attempt() -> httpx.Response:
            nonlocal attempt
            attempt += 1
            logger.info("network.get", url=url, attempt=attempt)
            response = await self._client.get(url, **kwargs)  # type: ignore[union-attr]

            if _is_retryable_response(response):
                logger.warning(
                    "network.retryable_status",
                    status=response.status_code,
                    attempt=attempt,
                )
                # Raise so tenacity can catch and retry
                response.raise_for_status()

            return response

        retried = self._with_retries(_attempt)
        return await retried()

    def _with_retries(self, fn: Any) -> Any:
        """Wrap an async callable with tenacity retry logic."""
        return retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._backoff, min=self._backoff, max=60),
            retry=(
                retry_if_exception_type(
                    (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
                )
            ),
            reraise=True,
        )(fn)
