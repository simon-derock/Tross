# Tross — LinkedIn Profile Scraper API (Reverse-Engineered)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688.svg)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/badge/managed%20by-uv-DE5FE9.svg)](https://github.com/astral-sh/uv)
[![CI](https://github.com/simon-derock/Tross/actions/workflows/ci.yml/badge.svg)](https://github.com/simon-derock/Tross/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-126%20passed-brightgreen.svg)]()

> **Tross** is a high-precision, production-ready backend API that reverse-engineers LinkedIn's internal **Voyager REST API**. It accepts a LinkedIn profile URL over an HTTPS POST or GET request and returns comprehensive, structured, typed JSON profile data.
>
> Built with **Python 3.12+**, **FastAPI**, **curl_cffi** (Chrome 131 TLS impersonation), and native **Swagger UI** (`/docs`). Deployed serverless on **Vercel**.

---

## 🏛️ System Architecture & Reverse Engineering Methodology

Unlike naive scrapers that spin up heavy headless browsers (Selenium / Playwright / Puppeteer) or fetch and parse HTML markup, **Tross directly communicates with LinkedIn's internal private REST API ("Voyager")**.

```
Client / Evaluator
       │
       │  POST /api/scrape  (Header: X-API-Key)
       │  Body: {"linkedin_url": "https://www.linkedin.com/in/satyanadella/"}
       ▼
FastAPI Gateway (Vercel Serverless)
       │
       ├─ 1. Verifies X-API-Key against INTERNAL_API_KEY
       ├─ 2. Extracts member vanity slug: "satyanadella"
       ├─ 3. Derives csrf-token header from JSESSIONID (unquoted)
       │
       ▼
curl_cffi Chrome 131 Engine
       │
       │  • Replicates Chrome 131 TLS Client Hello (JA3/JA4)
       │  • Replicates Chrome HTTP/2 SETTINGS & window frames
       │  • Sends authentic Voyager headers & tracking metadata
       │  • Optional residential proxy pass-through
       │
       ▼
LinkedIn Voyager REST API
   GET https://www.linkedin.com/voyager/api/identity/profiles/satyanadella/profileView
       │
       │  Returns raw Restli / JSON payload (~800ms)
       ▼
Tross Normalization & Extraction Engine
       │
       │  • Selects highest-resolution vectorImage artifacts
       │  • Traverses nested position groups & promotions
       │  • Parses structured date ranges (Start, End / "Present")
       │  • Serializes into typed Pydantic v2 ProfileResponse
       ▼
Client receives 200 OK with structured profile JSON (< 1.5s)
```

---

## 🛡️ Anti-Detection & Protocol Engineering

LinkedIn employs **HUMAN Security (formerly PerimeterX)** and internal edge filters to detect automation. Tross implements the following protocol-level countermeasures:

| Vector | The Problem | How Tross Solves It |
|---|---|---|
| **TLS Fingerprinting (JA3 / JA4)** | Python `requests` & `httpx` use standard OpenSSL, which produces recognizable non-browser TLS signatures that trigger **HTTP 999 Request Denied** blocks. | Tross uses **`curl_cffi`** with `impersonate="chrome131"`, compiling against BoringSSL to reproduce Chrome's exact cipher suites, extension ordering, and ALPN negotiation. |
| **HTTP/2 SETTINGS Frame** | Anti-bot systems evaluate `MAX_CONCURRENT_STREAMS`, window sizes, and header table sizes in initial HTTP/2 frames. | `curl_cffi` reproduces authentic Google Chrome HTTP/2 frame sizes and HPACK compression. |
| **CSRF Token Validation** | Voyager endpoints reject requests missing valid CSRF protection. | Tross automatically strips enclosing double quotes from the `JSESSIONID` cookie and transmits it via the `csrf-token` header. |
| **Telemetry & Header Order** | Missing browser headers or incorrect pseudo-header ordering triggers bot classification. | Tross constructs complete Chrome headers including `x-restli-protocol-version: 2.0.0`, `x-li-track` JSON metadata, dynamic `x-li-page-instance` URNs, `sec-ch-ua`, and context-aware `Referer`. |
| **Network Transient Failures** | Occasional 429 rate limits or 5xx gateway drops. | Managed with **`tenacity`** exponential backoff and jitter across retryable status codes (`429, 500, 502, 503, 504, 999`). |

---

## 📦 Tech Stack

- **Runtime:** Python 3.12+
- **API Framework:** [FastAPI](https://fastapi.tiangolo.com/) + [Starlette](https://www.starlette.io/)
- **Package & Environment Manager:** [`uv`](https://github.com/astral-sh/uv) (ultra-fast dependency resolution)
- **HTTP / TLS Impersonation:** [`curl_cffi`](https://github.com/lexiforest/curl_cffi)
- **Data Validation & Settings:** [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Resilience:** [`tenacity`](https://tenacity.readthedocs.io/)
- **Structured Logging:** [`structlog`](https://www.structlog.org/) (JSON logs with automatic credential masking)
- **Code Quality:** [`ruff`](https://github.com/astral-sh/ruff) (linter and formatter) & [`pytest`](https://docs.pytest.org/)

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) installed:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/simon-derock/Tross.git
cd Tross
uv sync
```

### 3. Configure Environment Variables
Copy the template and fill in your LinkedIn session cookies:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# ── Required: LinkedIn Session Cookies (from your logged-in browser) ─────────
LI_AT=AQEDAT...your_li_at_cookie_here...
JSESSIONID="ajax:1234567890123456789"

# ── Required: Internal API Security ─────────────────────────────────────────
INTERNAL_API_KEY=your_secret_api_key_at_least_16_chars

# ── Optional: Proxy Rotation & Tuning ───────────────────────────────────────
PROXY_URL=
LOG_LEVEL=INFO
MAX_RETRIES=3
RETRY_BACKOFF_SECONDS=2.0
```

> **How to get your LinkedIn cookies:**
> 1. Open [LinkedIn](https://www.linkedin.com) in your browser and log in.
> 2. Open Developer Tools (`F12` or `Cmd+Option+I`) → **Application** tab → **Cookies** → `https://www.linkedin.com`.
> 3. Copy the values of `li_at` and `JSESSIONID`.

### 4. Run the Development Server
```bash
uv run uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing & Quality Gates

Run the automated test suite and strict linting checks:

```bash
# Run all 97 unit and integration tests
uv run pytest -v

# Run Ruff linter
uv run ruff check .

# Check formatting
uv run ruff format --check .
```

---

## 📖 API Documentation

### 1. `POST /api/scrape`
Extracts structured profile data for a given LinkedIn profile URL.

**Security:** Header `X-API-Key: <INTERNAL_API_KEY>`

**Request Body:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/satyanadella/"
}
```

**Example cURL Request:**
```bash
curl -X POST "http://localhost:8000/api/scrape" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_secret_api_key_at_least_16_chars" \
     -d '{"linkedin_url": "https://www.linkedin.com/in/satyanadella/"}'
```

**Response Schema (`200 OK`):**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/satyanadella",
  "profile_id": "satyanadella",
  "first_name": "Satya",
  "last_name": "Nadella",
  "full_name": "Satya Nadella",
  "headline": "Chairman and CEO at Microsoft",
  "location": "Greater Seattle Area",
  "country": "United States",
  "industry": "Computer Software",
  "about": "Satya Nadella is Chairman and Chief Executive Officer of Microsoft...",
  "followers": 10500000,
  "connections": 500,
  "profile_image_url": "https://media.licdn.com/dms/image/v2/D5603AQ/.../profile-displayphoto-shrink_800_800/...",
  "background_image_url": "https://media.licdn.com/dms/image/v2/D5616AQ/.../profile-displaybackgroundimage-shrink_350_1400/...",
  "experience": [
    {
      "title": "Chairman and CEO",
      "company": "Microsoft",
      "company_url": "https://www.linkedin.com/company/microsoft",
      "location": "Redmond, Washington, United States",
      "description": "Leading Microsoft's mission to empower every person...",
      "date_range": {
        "start_date": "Feb 2014",
        "end_date": "Present"
      },
      "duration": null
    },
    {
      "title": "Executive Vice President, Cloud and Enterprise",
      "company": "Microsoft",
      "company_url": "https://www.linkedin.com/company/microsoft",
      "location": "Redmond, WA",
      "description": "Led the transformation to the cloud infrastructure...",
      "date_range": {
        "start_date": "Jan 2011",
        "end_date": "Feb 2014"
      },
      "duration": null
    }
  ],
  "education": [
    {
      "school": "The University of Chicago Booth School of Business",
      "school_url": null,
      "degree": "Master of Business Administration (MBA)",
      "field_of_study": "Business Administration and Management",
      "date_range": {
        "start_date": "1995",
        "end_date": "1997"
      },
      "description": "Concentrations in Finance and Strategy."
    }
  ],
  "skills": [
    "Cloud Computing",
    "Enterprise Software",
    "Distributed Systems",
    "SaaS",
    "Strategic Leadership"
  ],
  "certifications": [
    {
      "name": "Advanced Executive Leadership",
      "issuing_organization": "Harvard Business School Executive Education",
      "issue_date": "May 2005",
      "expiration_date": null,
      "credential_id": "EXEC-9921",
      "credential_url": "https://www.exed.hbs.edu/verify/EXEC-9921"
    }
  ],
  "languages": [
    {
      "name": "English",
      "proficiency": "Native or bilingual proficiency"
    },
    {
      "name": "Telugu",
      "proficiency": "Native or bilingual proficiency"
    }
  ],
  "scraped_at": "2026-08-27T14:35:00.000000+00:00",
  "trace_id": "9a38f7124b8d4c7ea1b65e903a9d7f12"
}
```

### 2. Status Codes & Error Envelope

All error responses return a uniform JSON schema:
```json
{
  "detail": "Descriptive error message",
  "status_code": 401,
  "trace_id": "9a38f7124b8d4c7ea1b65e903a9d7f12"
}
```

| HTTP Status | Error Type | Cause |
|---|---|---|
| **`401 Unauthorized`** | `AuthenticationError` | Missing/wrong `X-API-Key` OR invalid/expired LinkedIn backend cookies (`li_at`, `JSESSIONID`). |
| **`404 Not Found`** | `ProfileNotFoundError` | The requested LinkedIn vanity slug does not exist. |
| **`422 Unprocessable Content`** | `ValidationError` | Invalid URL format (must contain `/in/<vanity_slug>`). |
| **`429 Too Many Requests`** | `RateLimitError` | LinkedIn rate limit reached after exponential retries. |
| **`502 Bad Gateway`** | `ScraperError` | Upstream LinkedIn connection failure or network error. |

### 3. `GET /health`
Returns service health status (unauthenticated).
```json
{
  "status": "ok",
  "service": "tross"
}
```

---

## ☁️ Deployment on Vercel

Tross is configured out-of-the-box for serverless deployment on Vercel:

1. Push your repository to GitHub.
2. Import the project into your [Vercel Dashboard](https://vercel.com).
3. Configure Environment Variables in Project Settings:
   - `LI_AT`: Your `li_at` cookie value
   - `JSESSIONID`: Your `JSESSIONID` cookie value
   - `INTERNAL_API_KEY`: Your secret API key
   - `PROXY_URL` *(Optional)*: Residential proxy URL
4. Vercel automatically deploys via `vercel.json` and `api/index.py`.

---

## ⚠️ Known Limitations & Operational Considerations

1. **Session Cookie Lifespan:**
   - LinkedIn session cookies (`li_at`) can expire if the account password changes, manual logout occurs, or if LinkedIn challenges the session due to sudden geographical IP shifts.
2. **Private API Evolution:**
   - Because Voyager is LinkedIn's internal web API, payload structures and `decorationId` keys may evolve across major LinkedIn frontend releases. The engine's graceful fallback ensures top-level metadata is preserved even if specific sub-entities shift.
3. **Daily Rate Limits:**
   - For a single LinkedIn account without proxies, the safe threshold is approximately **50–100 profile views per day**. For high-volume production deployments, routing traffic through residential sticky proxies (e.g. Bright Data, Decodo) and rotating cookie pools is recommended.
4. **Member Privacy Settings:**
   - Profiles with private visibility restrictions (e.g. "Only visible to 1st-degree connections" or "LinkedIn members only") will reflect the visibility level accessible to the authenticated backend account.
