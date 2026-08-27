"""
app/schemas.py
──────────────
PhantomBuster-compliant Pydantic output schemas for LinkedIn profile data.
All fields mirror the PhantomBuster "LinkedIn Profile Scraper" output exactly.
Strict validation ensures downstream consumers receive clean, typed data.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# ── Sub-models ────────────────────────────────────────────────────────────────


class DateRange(BaseModel):
    """Represents a start/end date pair (month/year granularity)."""

    start_date: str | None = None  # e.g. "Jan 2020"
    end_date: str | None = None  # e.g. "Mar 2023" or "Present"


class ExperienceItem(BaseModel):
    """Single work experience entry."""

    title: str | None = None
    company: str | None = None
    company_url: str | None = None
    location: str | None = None
    description: str | None = None
    date_range: DateRange | None = None
    duration: str | None = None  # e.g. "3 yrs 2 mos"


class EducationItem(BaseModel):
    """Single education entry."""

    school: str | None = None
    school_url: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    date_range: DateRange | None = None
    description: str | None = None


class CertificationItem(BaseModel):
    """Professional certification entry."""

    name: str | None = None
    issuing_organization: str | None = None
    issue_date: str | None = None
    expiration_date: str | None = None
    credential_id: str | None = None
    credential_url: str | None = None


class LanguageItem(BaseModel):
    """Language proficiency entry."""

    name: str | None = None
    proficiency: str | None = None  # e.g. "Native", "Professional Working"


# ── Primary Request / Response models ────────────────────────────────────────


class ScrapeRequest(BaseModel):
    """Inbound request body for POST /api/scrape."""

    linkedin_url: Annotated[
        str,
        Field(
            ...,
            description="Full LinkedIn profile URL",
            examples=["https://www.linkedin.com/in/username/"],
        ),
    ]

    @field_validator("linkedin_url")
    @classmethod
    def must_be_linkedin_profile(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if "linkedin.com/in/" not in v:
            raise ValueError("URL must be a LinkedIn profile URL containing '/in/'")
        return v


class ProfileResponse(BaseModel):
    """
    PhantomBuster-compliant LinkedIn profile payload.
    All fields are nullable — partial data is better than a hard failure.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    linkedin_url: str | None = None
    profile_id: str | None = None  # vanity slug, e.g. "john-doe-123"
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    headline: str | None = None
    location: str | None = None
    country: str | None = None
    industry: str | None = None

    # ── About ─────────────────────────────────────────────────────────────────
    about: str | None = None
    followers: int | None = None
    connections: int | None = None

    # ── Media ─────────────────────────────────────────────────────────────────
    profile_image_url: str | None = None
    background_image_url: str | None = None

    # ── Structured sections ───────────────────────────────────────────────────
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)

    # ── Meta ──────────────────────────────────────────────────────────────────
    scraped_at: str | None = None  # ISO-8601 timestamp
    trace_id: str | None = None

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    detail: str
    trace_id: str | None = None
    status_code: int
