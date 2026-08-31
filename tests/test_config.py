"""
tests/test_config.py
────────────────────
Tests for pydantic-settings environment validation.
Ensures the app accepts correct values and defaults without side effects.
"""

from app.config import Settings


def _valid_overrides(**kwargs) -> dict:
    """Return a minimal valid env dict, with optional overrides."""
    base = {
        "li_at": "a" * 20,
        "jsessionid": "b" * 20,
        "internal_api_key": "c" * 20,
        "proxy_url": None,
    }
    base.update(kwargs)
    return base


class TestSettingsValidation:
    def test_valid_settings_instantiate(self):
        s = Settings(_env_file=None, **_valid_overrides())
        assert s.li_at == "a" * 20
        assert s.max_retries == 3
        assert s.retry_backoff_seconds == 2.0
        assert s.log_level == "INFO"

    def test_defaults_instantiate_without_error(self):
        s = Settings(_env_file=None)
        assert s.li_at == ""
        assert s.jsessionid == ""
        assert s.max_retries == 3
        assert s.log_level == "INFO"

    def test_quoted_jsessionid_is_stripped(self):
        s = Settings(
            _env_file=None, **_valid_overrides(jsessionid='"ajax:1234567890123456789"')
        )
        assert s.jsessionid == "ajax:1234567890123456789"
        assert '"' not in s.jsessionid

    def test_li_at_cookie_alias(self):
        s = Settings(
            _env_file=None,
            li_at_cookie="my_mobile_li_at_token_12345",
        )
        assert s.li_at == "my_mobile_li_at_token_12345"

    def test_proxy_url_optional(self):
        s = Settings(
            _env_file=None,
            **_valid_overrides(proxy_url="http://user:pass@proxy.com:8080"),
        )
        assert s.proxy_url == "http://user:pass@proxy.com:8080"
