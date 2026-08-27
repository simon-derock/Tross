"""
tests/test_config.py
────────────────────
Tests for pydantic-settings environment validation.
Ensures the app fails fast on missing/malformed secrets
and accepts correct values without side effects.
"""

import pytest
from pydantic import ValidationError

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

    def test_missing_li_at_raises(self):
        data = _valid_overrides()
        del data["li_at"]
        with pytest.raises(ValidationError, match="li_at"):
            Settings(_env_file=None, **data)

    def test_short_li_at_raises(self):
        with pytest.raises(ValidationError, match="li_at"):
            Settings(_env_file=None, **_valid_overrides(li_at="short"))

    def test_missing_jsessionid_raises(self):
        data = _valid_overrides()
        del data["jsessionid"]
        with pytest.raises(ValidationError, match="jsessionid"):
            Settings(_env_file=None, **data)

    def test_short_jsessionid_raises(self):
        with pytest.raises(ValidationError, match="jsessionid"):
            Settings(_env_file=None, **_valid_overrides(jsessionid="short"))

    def test_missing_api_key_raises(self):
        data = _valid_overrides()
        del data["internal_api_key"]
        with pytest.raises(ValidationError, match="internal_api_key"):
            Settings(_env_file=None, **data)

    def test_short_api_key_raises(self):
        with pytest.raises(ValidationError, match="internal_api_key"):
            Settings.model_validate(_valid_overrides(internal_api_key="tooshort"))

    def test_jsessionid_quotes_stripped(self):
        s = Settings.model_validate(_valid_overrides(jsessionid='"' + "b" * 20 + '"'))
        assert not s.jsessionid.startswith('"')
        assert not s.jsessionid.endswith('"')
        assert s.jsessionid == "b" * 20

    def test_proxy_url_optional(self):
        s = Settings.model_validate(_valid_overrides(proxy_url=None))
        assert s.proxy_url is None

        s_with_proxy = Settings.model_validate(
            _valid_overrides(proxy_url="http://proxy:8080")
        )
        assert s_with_proxy.proxy_url == "http://proxy:8080"

    def test_invalid_log_level_raises(self):
        with pytest.raises(ValidationError, match="log_level"):
            Settings.model_validate(_valid_overrides(log_level="VERBOSE"))

    def test_valid_log_levels(self):
        for lvl in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            s = Settings.model_validate(_valid_overrides(log_level=lvl))
            assert s.log_level == lvl

    def test_max_retries_bounds(self):
        with pytest.raises(ValidationError, match="max_retries"):
            Settings.model_validate(_valid_overrides(max_retries=0))
        with pytest.raises(ValidationError, match="max_retries"):
            Settings.model_validate(_valid_overrides(max_retries=11))

    def test_retry_backoff_bounds(self):
        with pytest.raises(ValidationError, match="retry_backoff_seconds"):
            Settings.model_validate(_valid_overrides(retry_backoff_seconds=0.1))
        with pytest.raises(ValidationError, match="retry_backoff_seconds"):
            Settings.model_validate(_valid_overrides(retry_backoff_seconds=35.0))
