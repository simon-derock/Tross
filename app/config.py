"""
app/config.py
─────────────
Strict environment validation using pydantic-settings.
Application boot validates backend credentials if provided,
with safe defaults for open public API access.
"""

from functools import lru_cache
from typing import Any, Literal

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

    @field_validator("jsessionid", mode="before")
    @classmethod
    def strip_jsessionid_quotes(cls, v: Any) -> str:
        """LinkedIn wraps JSESSIONID in quotes — clean outer quotes while preserving value."""
        if not v:
            return ""
        return str(v).strip('"').strip()

    @field_validator("log_level", mode="before")
    @classmethod
    def default_log_level_if_empty(cls, v: Any) -> str:
        if not v or str(v).strip() == "":
            return "INFO"
        val = str(v).strip().upper()
        return val if val in ("DEBUG", "INFO", "WARNING", "ERROR") else "INFO"

    @field_validator("max_retries", mode="before")
    @classmethod
    def default_max_retries_if_empty(cls, v: Any) -> int:
        if v is None or str(v).strip() == "":
            return 3
        try:
            return int(v)
        except (ValueError, TypeError):
            return 3

    @field_validator("retry_backoff_seconds", mode="before")
    @classmethod
    def default_backoff_if_empty(cls, v: Any) -> float:
        if v is None or str(v).strip() == "":
            return 2.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 2.0

    @field_validator("proxy_url", mode="before")
    @classmethod
    def default_proxy_if_empty(cls, v: Any) -> str | None:
        if not v or str(v).strip() == "":
            return None
        return str(v).strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the validated Settings singleton.
    Cached so .env is parsed exactly once per process.
    """
    return Settings()
