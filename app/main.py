"""
app/main.py
───────────
FastAPI application — Production ASGI entry point for Tross.

Endpoints:
  GET  /              — Redirects to /docs
  GET  /docs         — Interactive Swagger UI (Nord Dark Theme)
  GET  /redoc        — ReDoc 3-Column API Documentation
  POST /api/scrape   — Scrape a LinkedIn profile (body JSON)
  GET  /api/scrape   — Scrape a LinkedIn profile (query param ?url=...)
  POST /scrape       — Alias route
  GET  /scrape       — Alias route
  GET  /health       — Health check (open)

Authentication:
  Supports 'X-API-Key' header, 'Authorization: Bearer <key>' header,
  or '?api_key=<key>' query parameter.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Security,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

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
async def lifespan(app: FastAPI):
    """Application startup and graceful shutdown lifecycle handler."""
    configure_logging()
    logger = get_logger("app.lifecycle")
    logger.info("tross.startup", message="Tross LinkedIn Scraper API starting up...")
    yield
    logger.info("tross.shutdown", message="Tross shutting down...")


# ── FastAPI App Instance ──────────────────────────────────────────────────────
app = FastAPI(
    title="Tross: LinkedIn Profile API",
    description=(
        "Reverse-engineered, production-ready REST API for extracting structured LinkedIn "
        "profile information using high-fidelity Voyager client TLS impersonation."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

logger = get_logger(__name__)

# ── Security & Authentication ─────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    x_api_key: str | None = Security(api_key_header),  # noqa: B008
    auth_header: HTTPAuthorizationCredentials | None = Security(bearer_scheme),  # noqa: B008
    api_key_query: str | None = Query(None, alias="api_key"),  # noqa: B008
) -> None:
    """
    Validate inbound API key from multiple sources:
      1. 'X-API-Key' request header
      2. 'Authorization: Bearer <key>' request header
      3. '?api_key=<key>' query parameter
    """
    settings = get_settings()

    provided_key: str | None = None
    if x_api_key:
        provided_key = x_api_key.strip()
    elif auth_header and auth_header.credentials:
        provided_key = auth_header.credentials.strip()
    elif api_key_query:
        provided_key = api_key_query.strip()

    if not provided_key or provided_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid or missing API key. Provide via 'X-API-Key' header, "
                "Bearer token, or '?api_key=' parameter."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Global Exception Handlers ─────────────────────────────────────────────────


@app.exception_handler(AuthenticationError)
async def handle_auth_error(request: Request, exc: AuthenticationError) -> JSONResponse:
    logger.error("api.auth_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            detail=f"LinkedIn authentication failure: {exc}",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ).model_dump(),
    )


@app.exception_handler(ProfileNotFoundError)
async def handle_not_found(request: Request, exc: ProfileNotFoundError) -> JSONResponse:
    logger.warning("api.profile_not_found", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            detail=str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        ).model_dump(),
    )


@app.exception_handler(RateLimitError)
async def handle_rate_limit(request: Request, exc: RateLimitError) -> JSONResponse:
    logger.warning("api.rate_limit_exceeded", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            detail=f"LinkedIn rate limit encountered: {exc}",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        ).model_dump(),
    )


@app.exception_handler(ScraperError)
async def handle_scraper_error(request: Request, exc: ScraperError) -> JSONResponse:
    logger.error("api.scraper_error", detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ErrorResponse(
            detail=str(exc),
            status_code=status.HTTP_502_BAD_GATEWAY,
        ).model_dump(),
    )


# ── Navigation & Root Redirect ────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root path to interactive documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"], summary="Health Check")
async def health() -> dict[str, str]:
    """Returns 200 OK when the service is healthy. No auth required."""
    return {"status": "ok", "service": "tross"}


# ── Scraper Endpoints ─────────────────────────────────────────────────────────


@app.post(
    "/api/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    summary="Scrape a LinkedIn profile (POST)",
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
        422: {"description": "Validation error"},
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
@app.post(
    "/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    dependencies=[Depends(verify_api_key)],
    include_in_schema=False,
)
async def scrape_post(
    body: ScrapeRequest,
    x_li_at: str | None = Header(default=None, alias="X-Li-At"),
    x_jsessionid: str | None = Header(default=None, alias="X-JSESSIONID"),
) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL via POST request.

    **Input format:**
    ```json
    {
      "url": "https://www.linkedin.com/in/satyanadella/"
    }
    ```
    """
    trace_id = new_trace_id()
    logger.info("api.scrape.post", url=body.linkedin_url, trace_id=trace_id)

    override_cookies: dict[str, str] | None = None
    if x_li_at or x_jsessionid:
        override_cookies = {}
        if x_li_at:
            override_cookies["li_at"] = x_li_at
        if x_jsessionid:
            override_cookies["JSESSIONID"] = x_jsessionid

    profile = await scrape_profile(body.linkedin_url, override_cookies=override_cookies)
    profile.trace_id = trace_id

    logger.info(
        "api.scrape.success",
        name=profile.full_name,
        profile_id=profile.profile_id,
        trace_id=trace_id,
    )
    return profile


@app.get(
    "/api/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    summary="Scrape a LinkedIn profile (GET)",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {
            "description": "Profile scraped successfully",
            "model": ProfileResponse,
        },
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"description": "Validation error"},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
@app.get(
    "/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    dependencies=[Depends(verify_api_key)],
    include_in_schema=False,
)
async def scrape_get(
    url: str = Query(
        ...,
        alias="url",
        description="LinkedIn profile URL or member vanity slug",
        examples=["https://www.linkedin.com/in/satyanadella/"],
    ),
    x_li_at: str | None = Header(default=None, alias="X-Li-At"),
    x_jsessionid: str | None = Header(default=None, alias="X-JSESSIONID"),
) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL via GET query parameter.

    **Example:** `/api/scrape?url=https://www.linkedin.com/in/satyanadella/`
    """
    trace_id = new_trace_id()
    logger.info("api.scrape.get", url=url, trace_id=trace_id)

    override_cookies: dict[str, str] | None = None
    if x_li_at or x_jsessionid:
        override_cookies = {}
        if x_li_at:
            override_cookies["li_at"] = x_li_at
        if x_jsessionid:
            override_cookies["JSESSIONID"] = x_jsessionid

    profile = await scrape_profile(url, override_cookies=override_cookies)
    profile.trace_id = trace_id

    logger.info(
        "api.scrape.success",
        name=profile.full_name,
        profile_id=profile.profile_id,
        trace_id=trace_id,
    )
    return profile
