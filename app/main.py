"""
app/main.py
───────────
FastAPI application — the core ASGI entry point for Tross.

Endpoints:
  POST /api/scrape   — Scrape a LinkedIn profile (API key protected)
  GET  /health       — Health check (unauthenticated)

Security:
  All /api/* routes require X-API-Key header matching INTERNAL_API_KEY env var.
  Missing or wrong key → 401 Unauthorized (no credential burning).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import configure_logging, get_logger, new_trace_id
from app.schemas import ErrorResponse, ProfileResponse, ScrapeRequest
from app.scraper import AuthenticationError, ScraperError, scrape_profile

# ── Startup ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    settings = get_settings()
    configure_logging(settings.log_level)
    get_logger(__name__).info("tross.startup", log_level=settings.log_level)
    yield
    get_logger(__name__).info("tross.shutdown")


app = FastAPI(
    title="Tross — LinkedIn Scraper API",
    description="PhantomBuster-compatible LinkedIn profile data extraction.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

logger = get_logger(__name__)


# ── Auth dependency ───────────────────────────────────────────────────────────


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """Validate inbound X-API-Key header against INTERNAL_API_KEY env var."""
    settings = get_settings()
    if x_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )


# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(AuthenticationError)
async def auth_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    logger.error("api.auth_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            detail=str(exc),
            status_code=401,
        ).model_dump(),
    )


@app.exception_handler(ScraperError)
async def scraper_error_handler(request: Request, exc: ScraperError) -> JSONResponse:
    logger.error("api.scraper_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            detail=str(exc),
            status_code=502,
        ).model_dump(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"], summary="Health check")
async def health() -> dict[str, str]:
    """Returns 200 OK when the service is up. No auth required."""
    return {"status": "ok", "service": "tross"}


@app.post(
    "/api/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    summary="Scrape a LinkedIn profile",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Profile scraped successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Bad API key or expired LinkedIn cookies",
        },
        422: {"description": "Invalid request body"},
        502: {"model": ErrorResponse, "description": "LinkedIn fetch or parse failure"},
    },
)
async def scrape(body: ScrapeRequest) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL and return structured JSON data.

    Requires:
      - `X-API-Key` header matching the `INTERNAL_API_KEY` env var.
      - Body: `{"linkedin_url": "https://www.linkedin.com/in/<slug>"}`
    """
    trace_id = new_trace_id()
    logger.info("api.scrape.request", url=body.linkedin_url, trace_id=trace_id)

    profile = await scrape_profile(body.linkedin_url)
    profile.trace_id = trace_id

    logger.info(
        "api.scrape.response",
        name=profile.full_name,
        trace_id=trace_id,
    )
    return profile
