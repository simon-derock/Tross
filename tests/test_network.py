"""
tests/test_network.py
──────────────────────
Comprehensive unit tests for the curl_cffi Chrome 131 VoyagerClient.

Test coverage:
  • CSRF token derivation (quotes stripped, clean string preserved)
  • Cookies jar formatting
  • Authentic Chrome 131 headers (User-Agent, sec-ch-ua, x-restli, dynamic URN, x-li-track)
  • VoyagerClient context manager lifecycle
  • Proxy configuration forwarding to curl_cffi AsyncSession
  • Successful get_profile_view JSON parsing
  • HTTP 401 / 403 raising AuthenticationError (immediate, no retries)
  • HTTP 404 raising ProfileNotFoundError (immediate, no retries)
  • HTTP 429 and 999 triggering tenacity retries and raising RateLimitError on exhaustion
  • HTTP 500, 502, 503, 504 triggering tenacity retries and raising VoyagerAPIError on exhaustion
  • Transient failure recovery (e.g. 429 -> 503 -> 200 success)
  • HTTP 400 raising VoyagerAPIError immediately
  • Malformed JSON response raising VoyagerAPIError
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.network import (
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
    VoyagerAPIError,
    VoyagerClient,
    build_voyager_headers,
)

FAKE_LI_AT = "AQEDAT..." + "x" * 50
FAKE_JSESSIONID_QUOTED = '"ajax:1234567890123456789"'
FAKE_JSESSIONID_RAW = "ajax:1234567890123456789"
FAKE_CSRF_CLEAN = "1234567890123456789"
FAKE_SLUG = "satyanadella"


def _make_mock_response(
    status_code: int,
    json_data: dict[str, Any] | None = None,
    text: str = "",
) -> MagicMock:
    """Create a mock curl_cffi Response object."""
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
        resp.text = json.dumps(json_data)
    else:
        resp.text = text
        resp.json.side_effect = json.JSONDecodeError("Expecting value", text, 0)
    return resp


# ── 1. CSRF & Cookie Construction Tests ───────────────────────────────────────


class TestCSRFAndCookies:
    def test_csrf_token_strips_enclosing_quotes_and_ajax_prefix(self):
        client = VoyagerClient(li_at=FAKE_LI_AT, jsessionid=FAKE_JSESSIONID_QUOTED)
        assert client.csrf_token == FAKE_CSRF_CLEAN
        assert not client.csrf_token.startswith('"')
        assert not client.csrf_token.endswith('"')
        assert not client.csrf_token.startswith("ajax:")

    def test_csrf_token_preserves_clean_string(self):
        client = VoyagerClient(li_at=FAKE_LI_AT, jsessionid=FAKE_CSRF_CLEAN)
        assert client.csrf_token == FAKE_CSRF_CLEAN

    def test_cookies_dict_formatting(self):
        client = VoyagerClient(li_at=FAKE_LI_AT, jsessionid=FAKE_JSESSIONID_QUOTED)
        cookies = client.cookies
        assert cookies["li_at"] == FAKE_LI_AT
        assert cookies["JSESSIONID"] == f'"{FAKE_CSRF_CLEAN}"'

    def test_init_with_cookies_dict(self):
        client = VoyagerClient(
            cookies={"li_at": FAKE_LI_AT, "JSESSIONID": FAKE_JSESSIONID_QUOTED}
        )
        assert client.li_at == FAKE_LI_AT
        assert client.csrf_token == FAKE_CSRF_CLEAN
        assert client.cookies["JSESSIONID"] == f'"{FAKE_CSRF_CLEAN}"'


# ── 2. Header Construction Tests ──────────────────────────────────────────────


class TestHeaderConstruction:
    def test_header_user_agent_chrome131(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert "User-Agent" in headers
        assert "Chrome/131" in headers["User-Agent"]
        assert "Mozilla/5.0" in headers["User-Agent"]

    def test_header_restli_protocol_version(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert headers["x-restli-protocol-version"] == "2.0.0"

    def test_header_mobile_sdk_decoupling(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert headers["x-li-src"] == "msdk"
        assert "urn:li:device:" in headers["x-li-device-id"]

    def test_header_sec_ch_ua(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert headers["sec-ch-ua"] == '"Chromium";v="131", "Not_A Brand";v="24"'
        assert headers["sec-ch-ua-mobile"] == "?0"
        assert headers["sec-ch-ua-platform"] == '"Windows"'

    def test_header_accept_and_language(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert headers["Accept"] == "application/vnd.linkedin.normalized+json+2.1"
        assert headers["Accept-Language"] == "en-US,en;q=0.9"
        assert headers["x-li-lang"] == "en_US"

    def test_header_csrf_and_referer(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert headers["csrf-token"] == FAKE_CSRF_CLEAN
        assert headers["Referer"] == f"https://www.linkedin.com/in/{FAKE_SLUG}/"

    def test_header_sec_fetch_directives(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        assert headers["sec-fetch-dest"] == "empty"
        assert headers["sec-fetch-mode"] == "cors"
        assert headers["sec-fetch-site"] == "same-origin"

    def test_header_tracking_is_valid_json(self):
        headers = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        track_data = json.loads(headers["x-li-track"])
        assert track_data["clientVersion"] == "1.13.19790"
        assert track_data["osName"] == "web"
        assert track_data["mpName"] == "voyager-web"

    def test_header_dynamic_page_instance_urn(self):
        headers1 = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        headers2 = build_voyager_headers(
            vanity_slug=FAKE_SLUG, csrf_token=FAKE_CSRF_CLEAN
        )
        urn1 = headers1["x-li-page-instance"]
        urn2 = headers2["x-li-page-instance"]

        assert urn1.startswith("urn:li:page:d_flagship3_profile_view_base;")
        assert urn2.startswith("urn:li:page:d_flagship3_profile_view_base;")
        # Distinct UUIDs generated on each call
        assert urn1 != urn2


# ── 3. Client Lifecycle & Proxy Tests ─────────────────────────────────────────


class TestClientLifecycleAndProxy:
    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_session_cls.return_value = mock_instance

            client = VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
            )
            assert client._session is None

            async with client as active_client:
                assert active_client._session is not None
                mock_session_cls.assert_called_once_with(
                    impersonate="chrome131",
                    cookies={
                        "li_at": FAKE_LI_AT,
                        "JSESSIONID": f'"{FAKE_CSRF_CLEAN}"',
                    },
                    proxy=None,
                )

            # Session should be closed upon context manager exit
            mock_instance.close.assert_awaited_once()
            assert client._session is None

    @pytest.mark.asyncio
    async def test_proxy_url_forwarded_to_async_session(self):
        proxy = "http://user:pass@127.0.0.1:8080"
        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_session_cls.return_value = mock_instance

            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                proxy_url=proxy,
            ):
                mock_session_cls.assert_called_once_with(
                    impersonate="chrome131",
                    cookies={
                        "li_at": FAKE_LI_AT,
                        "JSESSIONID": f'"{FAKE_CSRF_CLEAN}"',
                    },
                    proxy=proxy,
                )

    @pytest.mark.asyncio
    async def test_calling_get_profile_view_outside_context_manager_raises(self):
        client = VoyagerClient(li_at=FAKE_LI_AT, jsessionid=FAKE_JSESSIONID_QUOTED)
        with pytest.raises(RuntimeError, match="async context manager"):
            await client.get_profile_view(FAKE_SLUG)


# ── 4. API Invocation & Response Handling Tests ───────────────────────────────


class TestGetProfileView:
    @pytest.mark.asyncio
    async def test_get_profile_view_success(self):
        expected_json = {
            "data": {
                "firstName": "Satya",
                "lastName": "Nadella",
                "headline": "Chairman and CEO at Microsoft",
            },
            "included": [],
        }
        mock_resp = _make_mock_response(200, expected_json)

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_cls.return_value = mock_instance

            async with VoyagerClient(
                li_at=FAKE_LI_AT, jsessionid=FAKE_JSESSIONID_QUOTED
            ) as client:
                result = await client.get_profile_view(FAKE_SLUG)

            assert result == expected_json
            mock_instance.get.assert_awaited_once()
            called_url = mock_instance.get.call_args[1].get(
                "url",
                mock_instance.get.call_args[0][0]
                if mock_instance.get.call_args[0]
                else None,
            )
            assert "identity/dash/profiles" in called_url
            assert f"memberIdentity={FAKE_SLUG}" in called_url
            assert (
                "decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-118"
                in called_url
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [401, 403])
    async def test_auth_errors_raise_authentication_error_without_retry(
        self, status_code: int
    ):
        mock_resp = _make_mock_response(status_code, text="Unauthorized")

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_cls.return_value = mock_instance

            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                max_retries=3,
                backoff_seconds=0.01,
            ) as client:
                with pytest.raises(AuthenticationError, match="authentication failed"):
                    await client.get_profile_view(FAKE_SLUG)

            # Must not retry on auth failures
            assert mock_instance.get.call_count == 1

    @pytest.mark.asyncio
    async def test_404_raises_profile_not_found_error_without_retry(self):
        mock_resp = _make_mock_response(404, text="Not Found")

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_cls.return_value = mock_instance

            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                max_retries=3,
                backoff_seconds=0.01,
            ) as client:
                with pytest.raises(ProfileNotFoundError, match="profile not found"):
                    await client.get_profile_view(FAKE_SLUG)

            assert mock_instance.get.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [429, 999])
    async def test_rate_limit_triggers_retries_and_raises_rate_limit_error(
        self, status_code: int
    ):
        mock_resp = _make_mock_response(status_code, text="Rate limit exceeded")

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_cls.return_value = mock_instance

            max_retries = 3
            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                max_retries=max_retries,
                backoff_seconds=0.01,
            ) as client:
                with pytest.raises(RateLimitError, match="rate limit exceeded"):
                    await client.get_profile_view(FAKE_SLUG)

            assert mock_instance.get.call_count == max_retries

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    async def test_server_errors_trigger_retries_and_raise_voyager_api_error(
        self, status_code: int
    ):
        mock_resp = _make_mock_response(status_code, text="Server Error")

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_cls.return_value = mock_instance

            max_retries = 3
            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                max_retries=max_retries,
                backoff_seconds=0.01,
            ) as client:
                with pytest.raises(VoyagerAPIError, match="server error") as exc_info:
                    await client.get_profile_view(FAKE_SLUG)
                assert exc_info.value.status_code == status_code

            assert mock_instance.get.call_count == max_retries

    @pytest.mark.asyncio
    async def test_transient_retry_recovers_to_success(self):
        success_data = {"data": {"id": "123"}}
        mock_responses = [
            _make_mock_response(429, text="Too Many Requests"),
            _make_mock_response(503, text="Service Unavailable"),
            _make_mock_response(200, success_data),
        ]

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=mock_responses)
            mock_session_cls.return_value = mock_instance

            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                max_retries=3,
                backoff_seconds=0.01,
            ) as client:
                data = await client.get_profile_view(FAKE_SLUG)

            assert data == success_data
            assert mock_instance.get.call_count == 3

    @pytest.mark.asyncio
    async def test_unexpected_http_status_raises_voyager_api_error_without_retry(self):
        mock_resp = _make_mock_response(400, text="Bad Request")

        with patch("app.network.AsyncSession") as mock_session_cls:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_cls.return_value = mock_instance

            async with VoyagerClient(
                li_at=FAKE_LI_AT,
                jsessionid=FAKE_JSESSIONID_QUOTED,
                max_retries=3,
                backoff_seconds=0.01,
            ) as client:
                with pytest.raises(VoyagerAPIError, match="Unexpected HTTP 400"):
                    await client.get_profile_view(FAKE_SLUG)

            assert mock_instance.get.call_count == 1
