"""
tests/test_config.py
────────────────────
Tests for pydantic-settings environment validation (Phase 2).
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
        "upstash_redis_url": "rediss://default:pass@host.upstash.io:6380",
        "proxy_url": None,
    }
    base.update(kwargs)
    return base


class TestSettingsValidation:
    def test_valid_settings_instantiate(self):
        s = Settings.model_validate(_valid_overrides())
        assert s.li_at == "a" * 20
        assert s.max_retries == 3

    def test_missing_li_at_raises(self):
        data = _valid_overrides()
        del data["li_at"]
        with pytest.raises(ValidationError, match="li_at"):
            Settings.model_validate(data)

    def test_missing_jsessionid_raises(self):
        data = _valid_overrides()
        del data["jsessionid"]
        with pytest.raises(ValidationError, match="jsessionid"):
            Settings.model_validate(data)

    def test_missing_api_key_raises(self):
        data = _valid_overrides()
        del data["internal_api_key"]
        with pytest.raises(ValidationError, match="internal_api_key"):
            Settings.model_validate(data)

    def test_short_api_key_raises(self):
        with pytest.raises(ValidationError):
            Settings.model_validate(_valid_overrides(internal_api_key="tooshort"))

    def test_invalid_redis_scheme_raises(self):
        with pytest.raises(ValidationError, match="redis"):
            Settings.model_validate(
                _valid_overrides(upstash_redis_url="http://not-redis.com")
            )

    def test_jsessionid_quotes_stripped(self):
        s = Settings.model_validate(_valid_overrides(jsessionid='"' + "b" * 20 + '"'))
        assert not s.jsessionid.startswith('"')

    def test_proxy_url_optional(self):
        s = Settings.model_validate(_valid_overrides(proxy_url=None))
        assert s.proxy_url is None

    def test_invalid_log_level_raises(self):
        with pytest.raises(ValidationError):
            Settings.model_validate(_valid_overrides(log_level="VERBOSE"))

    def test_max_retries_bounds(self):
        with pytest.raises(ValidationError):
            Settings.model_validate(_valid_overrides(max_retries=0))
        with pytest.raises(ValidationError):
            Settings.model_validate(_valid_overrides(max_retries=11))
