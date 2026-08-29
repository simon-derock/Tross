"""
app/schemas.py
──────────────
Pydantic v2 schemas for LinkedIn profile data extraction.
Designed to capture comprehensive profile attributes:
name, headline, location, about, experience, education, skills,
certifications, languages, and media.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AliasChoices, BaseModel, Field, field_validator

# ── Sub-models ────────────────────────────────────────────────────────────────


class DateRange(BaseModel):
    """Represents a start/end date pair (month/year granularity)."""

    start_date: str | None = Field(
        default=None, description="Start date (e.g. 'Feb 2014' or '1995')"
    )
    end_date: str | None = Field(
        default=None,
        description="End date (e.g. 'Present', 'Dec 2020', or '1997')",
    )


class ExperienceItem(BaseModel):
    """Single work experience entry."""

    title: str | None = Field(default=None, description="Job title or role")
    company: str | None = Field(
        default=None, description="Company or organization name"
    )
    company_url: str | None = Field(
        default=None, description="LinkedIn company page URL"
    )
    location: str | None = Field(
        default=None, description="Geographic location of the role"
    )
    description: str | None = Field(
        default=None,
        description="Description of role responsibilities and achievements",
    )
    date_range: DateRange | None = Field(
        default=None, description="Start and end dates"
    )
    duration: str | None = Field(
        default=None, description="Duration string (e.g. '5 yrs 2 mos')"
    )


class EducationItem(BaseModel):
    """Single education entry."""

    school: str | None = Field(
        default=None, description="School, university, or institution name"
    )
    school_url: str | None = Field(default=None, description="LinkedIn school page URL")
    degree: str | None = Field(default=None, description="Degree or qualification name")
    field_of_study: str | None = Field(
        default=None, description="Field of study or major"
    )
    date_range: DateRange | None = Field(
        default=None, description="Start and end years/dates"
    )
    description: str | None = Field(
        default=None, description="Activities, honors, or notes"
    )


class CertificationItem(BaseModel):
    """Professional certification or license entry."""

    name: str | None = Field(default=None, description="Certification or license name")
    issuing_organization: str | None = Field(
        default=None, description="Issuing organization or authority"
    )
    issue_date: str | None = Field(default=None, description="Date issued")
    expiration_date: str | None = Field(
        default=None, description="Date expired (if applicable)"
    )
    credential_id: str | None = Field(
        default=None, description="Credential license number or ID"
    )
    credential_url: str | None = Field(default=None, description="Verification URL")


class LanguageItem(BaseModel):
    """Language proficiency entry."""

    name: str | None = Field(default=None, description="Language name")
    proficiency: str | None = Field(
        default=None,
        description="Proficiency level (e.g. 'Native or bilingual', 'Professional working')",
    )


# ── Primary Request / Response models ────────────────────────────────────────


class ScrapeRequest(BaseModel):
    """
    Inbound request body for profile scraping.
    Supports aliases: 'linkedin_url', 'url', 'profile_url', 'link'.
    """

    linkedin_url: Annotated[
        str,
        Field(
            ...,
            validation_alias=AliasChoices("linkedin_url", "url", "profile_url", "link"),
            description="LinkedIn profile URL or member vanity slug",
            examples=["https://www.linkedin.com/in/satyanadella/"],
        ),
    ]

    @field_validator("linkedin_url")
    @classmethod
    def normalize_and_validate_url(cls, v: str) -> str:
        clean = v.strip().rstrip("/")
        if not clean:
            raise ValueError("LinkedIn profile URL cannot be empty.")
        return clean


class ProfileResponse(BaseModel):
    """
    Complete structured LinkedIn profile payload.
    All fields are nullable to tolerate partial data gracefully.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    linkedin_url: str | None = Field(
        default=None, description="Full LinkedIn profile URL"
    )
    profile_id: str | None = Field(
        default=None, description="Member vanity slug or public identifier"
    )
    first_name: str | None = Field(default=None, description="First / given name")
    last_name: str | None = Field(default=None, description="Last / family name")
    full_name: str | None = Field(default=None, description="Full formatted name")
    headline: str | None = Field(
        default=None, description="Professional headline or title"
    )
    location: str | None = Field(
        default=None, description="Geographic location (city, state, region)"
    )
    country: str | None = Field(default=None, description="Country or territory")
    industry: str | None = Field(default=None, description="Industry sector")

    # ── About ─────────────────────────────────────────────────────────────────
    about: str | None = Field(default=None, description="Summary or About section text")
    followers: int | None = Field(default=None, description="Number of followers")
    connections: int | None = Field(default=None, description="Number of connections")

    # ── Media ─────────────────────────────────────────────────────────────────
    profile_image_url: str | None = Field(
        default=None, description="Highest-resolution profile avatar photo URL"
    )
    background_image_url: str | None = Field(
        default=None, description="Background banner image URL"
    )

    # ── Structured Sections ───────────────────────────────────────────────────
    experience: list[ExperienceItem] = Field(
        default_factory=list, description="Work experience history"
    )
    education: list[EducationItem] = Field(
        default_factory=list, description="Education history"
    )
    skills: list[str] = Field(
        default_factory=list, description="List of endorsed/listed skills"
    )
    certifications: list[CertificationItem] = Field(
        default_factory=list, description="Professional licenses and certifications"
    )
    languages: list[LanguageItem] = Field(
        default_factory=list, description="Languages and spoken proficiencies"
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    scraped_at: str | None = Field(
        default=None, description="ISO-8601 UTC timestamp of scraping execution"
    )
    trace_id: str | None = Field(
        default=None, description="Unique trace identifier for this request"
    )

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    detail: str = Field(description="Descriptive error explanation")
    status_code: int = Field(description="HTTP status code")
    trace_id: str | None = Field(default=None, description="Trace ID for debugging")


# ── Aliases ───────────────────────────────────────────────────────────────────
ProfileRequest = ScrapeRequest
