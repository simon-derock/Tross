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
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
    docs_url=None,  # Handled by custom dark-theme route below
    redoc_url=None,  # Handled by custom route below
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


# ── Documentation & Navigation Routes ─────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root path to interactive documentation."""
    return RedirectResponse(url="/docs")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """Built-in Swagger UI with clean Dark theme."""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{app.title} - Swagger UI</title>
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
        <style>
            html {{
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }}
            *, *:before, *:after {{
                box-sizing: inherit;
            }}
            body {{
                margin: 0;
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
            .swagger-ui {{
                color: #e2e8f0;
            }}
            .swagger-ui .topbar {{
                display: none;
            }}
            .swagger-ui .info .title,
            .swagger-ui .info h1,
            .swagger-ui .info h2,
            .swagger-ui .info h3,
            .swagger-ui .info h4,
            .swagger-ui .info h5 {{
                color: #f8fafc;
            }}
            .swagger-ui .info p,
            .swagger-ui .info li,
            .swagger-ui .info .base-url {{
                color: #94a3b8;
            }}
            .swagger-ui .scheme-container {{
                background: #0f172a;
                box-shadow: none;
                border-bottom: 1px solid #1e293b;
            }}
            .swagger-ui .opblock-tag {{
                color: #f8fafc;
                border-bottom: 1px solid #1e293b;
            }}
            .swagger-ui .opblock {{
                background: #1e293b;
                border-radius: 8px;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.3);
                border: 1px solid #334155;
                margin-bottom: 12px;
            }}
            .swagger-ui .opblock.opblock-post {{
                border-color: #059669;
                background: rgba(5, 150, 105, 0.08);
            }}
            .swagger-ui .opblock.opblock-get {{
                border-color: #0284c7;
                background: rgba(2, 132, 199, 0.08);
            }}
            .swagger-ui .opblock .opblock-summary-operation-id,
            .swagger-ui .opblock .opblock-summary-path,
            .swagger-ui .opblock .opblock-summary-path__deprecated {{
                color: #f8fafc;
            }}
            .swagger-ui .opblock .opblock-summary-description {{
                color: #94a3b8;
            }}
            .swagger-ui .opblock-description-wrapper p,
            .swagger-ui .opblock-external-docs-wrapper p,
            .swagger-ui .opblock-title_normal p {{
                color: #cbd5e1;
            }}
            .swagger-ui .btn {{
                background: #1e293b;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
            }}
            .swagger-ui .btn.authorize {{
                color: #10b981;
                border-color: #10b981;
            }}
            .swagger-ui .btn.authorize svg {{
                fill: #10b981;
            }}
            .swagger-ui .btn.execute {{
                background-color: #0284c7;
                color: #fff;
                border-color: #0284c7;
            }}
            .swagger-ui select {{
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
            }}
            .swagger-ui input[type="text"],
            .swagger-ui input[type="password"],
            .swagger-ui textarea {{
                background: #0f172a;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 6px;
            }}
            .swagger-ui section.models {{
                border: 1px solid #334155;
                border-radius: 8px;
                background: #1e293b;
            }}
            .swagger-ui section.models h4 {{
                color: #f8fafc;
            }}
            .swagger-ui section.models .model-container {{
                background: #1e293b;
            }}
            .swagger-ui .model-box {{
                background: #1e293b;
            }}
            .swagger-ui .model {{
                color: #e2e8f0;
            }}
            .swagger-ui .prop-type {{
                color: #38bdf8;
            }}
            .swagger-ui .prop-format {{
                color: #94a3b8;
            }}
            .swagger-ui .response-col_status {{
                color: #f8fafc;
            }}
            .swagger-ui .response-col_description {{
                color: #cbd5e1;
            }}
            .swagger-ui table thead tr td,
            .swagger-ui table thead tr th {{
                color: #94a3b8;
                border-bottom: 1px solid #334155;
            }}
            .swagger-ui table.parameters tbody tr td {{
                border-color: #334155;
            }}
            .swagger-ui .parameter__name,
            .swagger-ui .parameter__type {{
                color: #f8fafc;
            }}
            .swagger-ui .parameter__deprecated {{
                color: #ef4444;
            }}
            .swagger-ui .tab li button.tablinks {{
                color: #94a3b8;
            }}
            .swagger-ui .tab li button.tablinks.active {{
                color: #f8fafc;
                font-weight: bold;
            }}
            .swagger-ui .highlight-code pre {{
                background: #0f172a !important;
            }}
            .swagger-ui .microlight {{
                background: #0f172a !important;
                color: #38bdf8 !important;
            }}
            .swagger-ui .responses-inner h4,
            .swagger-ui .responses-inner h5 {{
                color: #f8fafc;
            }}
            .swagger-ui .dialog-ux .modal-ux {{
                background: #1e293b;
                border: 1px solid #334155;
                color: #f8fafc;
            }}
            .swagger-ui .dialog-ux .modal-ux-header {{
                border-bottom: 1px solid #334155;
            }}
            .swagger-ui .dialog-ux .modal-ux-header h3 {{
                color: #f8fafc;
            }}
            .swagger-ui .dialog-ux .modal-ux-content h4 {{
                color: #cbd5e1;
            }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
        window.onload = function() {{
            window.ui = SwaggerUIBundle({{
                url: '{app.openapi_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout"
            }});
        }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Built-in ReDoc 3-column documentation."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )


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
