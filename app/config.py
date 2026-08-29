"""
app/config.py
─────────────
Strict environment validation using pydantic-settings.
Application boot validates backend credentials if provided,
with safe defaults for open public API access.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application configuration, validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LinkedIn Session Cookies (optional backend secrets) ───────────────────
    li_at: str = Field(
        default="",
        validation_alias=AliasChoices("li_at", "li_at_cookie", "li-at"),
        description="LinkedIn li_at session cookie",
    )
    jsessionid: str = Field(
        default="",
        validation_alias=AliasChoices("jsessionid", "jsession_id"),
        description="LinkedIn JSESSIONID cookie",
    )

    # ── Internal API Security (optional) ──────────────────────────────────────
    internal_api_key: str = Field(
        default="",
        description="Optional internal API key",
    )

    # ── Proxy Rotation (optional) ─────────────────────────────────────────────
    proxy_url: str | None = Field(
        default=None, description="Residential proxy URI (http:// or socks5://)"
    )

    # ── App Tuning (optional with safe defaults) ──────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_backoff_seconds: float = Field(default=2.0, ge=0.5, le=30.0)

    @field_validator("jsessionid")
    @classmethod
    def strip_jsessionid_quotes(cls, v: str) -> str:
        """LinkedIn sometimes wraps JSESSIONID in quotes or prefixes with ajax: — clean it."""
        return v.replace("ajax:", "").strip('"').strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the validated Settings singleton.
    Cached so .env is parsed exactly once per process.
    """
    return Settings()
