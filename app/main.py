"""
app/main.py
───────────
FastAPI application — Production ASGI entry point for Tross.

Endpoints:
  POST /api/scrape   — Scrape a LinkedIn profile (X-API-Key protected)
  GET  /health       — Health check (open)
  GET  /docs         — OpenAPI documentation

Security:
  Inbound POST /api/scrape requires header 'X-API-Key' matching INTERNAL_API_KEY.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import configure_logging, get_logger, new_trace_id
from app.network import (
    AuthenticationError,
    ProfileNotFoundError,
    RateLimitError,
)
from app.schemas import ErrorResponse, ProfileResponse, ScrapeRequest
from app.scraper import ScraperError, scrape_profile

# ── Startup & Lifecycle ───────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    settings = get_settings()
    configure_logging(settings.log_level)
    get_logger(__name__).info("tross.startup", log_level=settings.log_level)
    yield
    get_logger(__name__).info("tross.shutdown")


app = FastAPI(
    title="Tross — LinkedIn Scraper API",
    description=(
        "Production-ready, reverse-engineered LinkedIn profile scraper API. "
        "Accepts a LinkedIn profile URL and returns structured JSON conforming to PhantomBuster schema."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

logger = get_logger(__name__)


# ── Auth Dependency ───────────────────────────────────────────────────────────


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """Validate inbound X-API-Key header against INTERNAL_API_KEY env var."""
    settings = get_settings()
    if x_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )


# ── Exception Handlers ────────────────────────────────────────────────────────


@app.exception_handler(AuthenticationError)
async def auth_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    logger.error("api.auth_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            detail=str(exc),
            status_code=status.HTTP_401_UNAUTHORIZED,
        ).model_dump(),
    )


@app.exception_handler(ProfileNotFoundError)
async def not_found_handler(
    request: Request, exc: ProfileNotFoundError
) -> JSONResponse:
    logger.warning("api.profile_not_found", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            detail=str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        ).model_dump(),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    logger.error("api.rate_limit_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            detail=str(exc),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        ).model_dump(),
    )


@app.exception_handler(ScraperError)
async def scraper_error_handler(request: Request, exc: ScraperError) -> JSONResponse:
    logger.error("api.scraper_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            detail=str(exc),
            status_code=status.HTTP_502_BAD_GATEWAY,
        ).model_dump(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"], summary="Health Check")
async def health() -> dict[str, str]:
    """Returns 200 OK when the service is healthy. No auth required."""
    return {"status": "ok", "service": "tross"}


@app.post(
    "/api/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    summary="Scrape a LinkedIn profile",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {
            "description": "Profile scraped successfully",
            "model": ProfileResponse,
        },
        401: {
            "model": ErrorResponse,
            "description": "Bad API key or invalid backend LinkedIn credentials",
        },
        404: {
            "model": ErrorResponse,
            "description": "LinkedIn profile does not exist",
        },
        422: {"description": "Validation error (e.g. invalid LinkedIn URL)"},
        429: {
            "model": ErrorResponse,
            "description": "LinkedIn rate limit exceeded",
        },
        502: {
            "model": ErrorResponse,
            "description": "LinkedIn upstream gateway failure",
        },
    },
)
async def scrape(body: ScrapeRequest) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL and return structured JSON data.

    **Requirements:**
      - Header `X-API-Key: <INTERNAL_API_KEY>`
      - Body `{"linkedin_url": "https://www.linkedin.com/in/<vanity_slug>/"}`
    """
    trace_id = new_trace_id()
    logger.info("api.scrape.request", url=body.linkedin_url, trace_id=trace_id)

    profile = await scrape_profile(body.linkedin_url)
    profile.trace_id = trace_id

    logger.info(
        "api.scrape.response",
        name=profile.full_name,
        profile_id=profile.profile_id,
        trace_id=trace_id,
    )
    return profile
