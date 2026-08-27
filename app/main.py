"""
app/main.py
───────────
FastAPI application — Production ASGI entry point for Tross.

Endpoints:
  GET  /              — Redirects to /docs
  GET  /docs         — Interactive Swagger UI (Open Public Access)
  GET  /redoc        — ReDoc 3-Column API Documentation
  POST /api/scrape   — Scrape a LinkedIn profile (body JSON, open access)
  GET  /api/scrape   — Scrape a LinkedIn profile (query param ?url=..., open access)
  POST /scrape       — Alias route (open access)
  GET  /scrape       — Alias route (open access)
  GET  /health       — Health check (open)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Header,
    Request,
    status,
)
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import get_settings  # noqa: F401
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
    title="Tross: LinkedIn Profile API — by PHILIP SIMON DEROCK",
    description=(
        "**Assignment Submission by PHILIP SIMON DEROCK**\n\n"
        "Reverse-engineered, production-ready REST API for extracting structured LinkedIn "
        "profile information using high-fidelity Voyager client TLS impersonation.\n\n"
        "**Direct Public Testing**: Enter any LinkedIn profile URL and click Execute."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,  # Handled by dark-mode route below
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

logger = get_logger(__name__)


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


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """Base Swagger UI with zero-breakage Dark Mode."""
    res = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )
    dark_css = """
    <style>
        body { background-color: #0f172a !important; margin: 0; }
        .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
        .swagger-ui .highlight-code, .swagger-ui .microlight, .swagger-ui img { filter: invert(100%) hue-rotate(180deg); }
    </style>
    """
    html_content = res.body.decode("utf-8").replace("</head>", f"{dark_css}</head>")
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["meta"], summary="Health Check")
async def health() -> dict[str, str]:
    """Returns 200 OK when the service is healthy. No auth required."""
    return {"status": "ok", "service": "tross"}


# ── Scraper Endpoints (Open Public Access) ────────────────────────────────────


@app.post(
    "/api/scrape",
    response_model=ProfileResponse,
    tags=["scraper"],
    summary="Scrape a LinkedIn profile (POST)",
    responses={
        200: {
            "description": "Profile scraped successfully",
            "model": ProfileResponse,
        },
        401: {
            "model": ErrorResponse,
            "description": "Invalid or missing LinkedIn session credentials",
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
    include_in_schema=False,
)
async def scrape_post(
    body: ScrapeRequest,
    x_li_at: str | None = Header(default=None, alias="X-Li-At"),
    x_jsessionid: str | None = Header(default=None, alias="X-JSESSIONID"),
) -> ProfileResponse:
    """
    Scrape a LinkedIn profile URL via POST request. Direct open access for recruiters and evaluators.

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
