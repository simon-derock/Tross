"""
app/config.py
─────────────
Strict environment validation using pydantic-settings.
Application boot will FAIL FAST if any required secret is missing or malformed,
preventing silent runtime crashes on Vercel.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application configuration, validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LinkedIn Session Cookies (required) ───────────────────────────────────
    li_at: str = Field(..., min_length=10, description="LinkedIn li_at session cookie")
    jsessionid: str = Field(
        ..., min_length=10, description="LinkedIn JSESSIONID cookie"
    )

    # ── Internal API Security (required) ──────────────────────────────────────
    internal_api_key: str = Field(
        ..., min_length=16, description="Internal bearer token for /api/scrape"
    )

    # ── Upstash Redis (required) ───────────────────────────────────────────────
    upstash_redis_url: AnyUrl = Field(
        ..., description="Upstash Redis URL (rediss://...)"
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
        """LinkedIn sometimes wraps JSESSIONID in quotes — strip them."""
        return v.strip('"')

    @field_validator("upstash_redis_url", mode="before")
    @classmethod
    def validate_redis_scheme(cls, v: str) -> str:
        if not str(v).startswith(("redis://", "rediss://")):
            raise ValueError("UPSTASH_REDIS_URL must start with redis:// or rediss://")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the validated Settings singleton.
    Cached so .env is parsed exactly once per process.
    Raises ValidationError on startup if any required var is missing.
    """
    return Settings()
