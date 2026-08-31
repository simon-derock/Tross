# Tross — LinkedIn Profile API (Reverse-Engineered)

[![Live API Docs](https://img.shields.io/badge/Live%20Docs-Swagger%20UI-009688.svg?style=for-the-badge&logo=swagger)](https://tross-api.vercel.app/docs)
[![Live Web Playground](https://img.shields.io/badge/Web%20Playground-Active-brightgreen.svg?style=for-the-badge)](https://tross-api.vercel.app/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![CI](https://github.com/simon-derock/Tross/actions/workflows/ci.yml/badge.svg)](https://github.com/simon-derock/Tross/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-118%20passed-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **Live Deployment:**
> - 🌐 **Interactive Swagger UI:** [https://tross-api.vercel.app/docs](https://tross-api.vercel.app/docs)
> - ⚡ **Web Playground:** [https://tross-api.vercel.app/](https://tross-api.vercel.app/)
> - 📡 **Scrape Endpoint:** `POST https://tross-api.vercel.app/api/profile`
>
> **Tross** is a high-precision, production-ready backend API that reverse-engineers LinkedIn's internal **Voyager REST API**. It accepts a LinkedIn profile URL over an HTTPS POST request and returns comprehensive, structured, typed JSON profile data.
>
> Developed by **PHILIP SIMON DEROCK**. Built with **Python 3.12+**, **FastAPI**, **curl_cffi** (Chrome 131 TLS impersonation), and native **Swagger UI** (`/docs`). Deployed serverless on **Vercel**.

---

### ⚡ Quick Live Testing & Evaluation

1. **Interactive Swagger UI:** Navigate to `/docs` on your deployed Vercel URL (or `http://localhost:8000/docs` locally).
2. **Execute Scrape:** Expand **`POST /api/profile`**, click **Try it out**, enter any LinkedIn profile URL (e.g. `{"url": "https://www.linkedin.com/in/satyanadella/"}`), and click **Execute**.
3. **Optional Dynamic Headers:** If testing with custom credentials, pass your `li_at` and `JSESSIONID` in the `X-Li-At` and `X-JSESSIONID` headers directly in Swagger UI.

---

## 🏛️ System Architecture & Reverse Engineering Methodology

Unlike naive scrapers that rely on heavy headless browsers (Selenium / Playwright / Puppeteer) or basic HTML scraping, **Tross communicates directly with LinkedIn's internal private REST API ("Voyager Dash")**.

```
Client / Consumer
       │
       │  POST /api/profile  OR  POST /api/scrape
       │  Body: {"url": "https://www.linkedin.com/in/satyanadella/"}
       ▼
FastAPI Gateway (Vercel Serverless)
       │
       ├─ 1. In-Memory LRU Cache check (<1ms return on hit)
       ├─ 2. Extracts member vanity slug: "satyanadella"
       ├─ 3. Injects Mobile SDK headers (`x-li-src: msdk`, `x-li-device-id`)
       ├─ 4. Derives internal `csrf-token` header from JSESSIONID (clean unquoted)
       ├─ 5. Injects authenticated session credentials (LI_AT / LI_AT_COOKIE)
       │
       ▼
curl_cffi Chrome 131 Engine
       │
       │  • Replicates Chrome 131 TLS Client Hello (JA3/JA4)
       │  • Replicates Chrome HTTP/2 SETTINGS & window frames
       │  • Sends authentic Restli 2.0 headers & tracking telemetry
       │  • Mobile SDK lifecycle decoupling (prevents tab-close session invalidation)
       │  • Optional residential proxy pass-through
       │
       ▼
LinkedIn Internal Microservice Endpoint
   GET https://www.linkedin.com/voyager/api/identity/dash/profiles?q=memberIdentity...&decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-118
       │
       │  Returns raw Restli / JSON payload (~800ms)
       ▼
Tross Normalization & Extraction Engine
       │
       │  • Direct JSON-to-JSON entity traversal (Zero HTML / Zero DOM)
       │  • Selects highest-resolution vectorImage artifacts (800x800+)
       │  • Traverses nested position groups, titles, and promotions
       │  • Parses structured date ranges (Start, End / "Present")
       │  • Serializes into typed Pydantic v2 ProfileResponse
       ▼
Client receives 200 OK with structured profile JSON (< 1.2s)
```

---

## 🛡️ Anti-Detection & Session Persistence

LinkedIn employs **HUMAN Security (formerly PerimeterX)** and desktop browser page-lifecycle events (e.g. `beforeunload`, websocket beacons) to terminate desktop browser sessions. Tross implements the following protocol-level countermeasures:

| Vector | Challenge | How Tross Solves It |
|---|---|---|
| **Session Lifecycle Decoupling** | Desktop cookies (`li_at`) are invalidated by LinkedIn when the desktop browser window/tab is closed. | By injecting **`x-li-src: msdk`** and **`x-li-device-id`**, LinkedIn treats the connection as a persistent native mobile app session, decoupling it from desktop browser lifecycle events. |
| **TLS Fingerprinting (JA3 / JA4)** | Python `requests` and `httpx` use standard OpenSSL, producing non-browser TLS signatures that trigger **HTTP 999 Request Denied** blocks. | Tross uses **`curl_cffi`** with `impersonate="chrome131"`, compiling against BoringSSL to reproduce Chrome's exact cipher suites, extension ordering, and ALPN negotiation. |
| **HTTP/2 SETTINGS Frame** | Anti-bot systems evaluate `MAX_CONCURRENT_STREAMS`, window sizes, and header table sizes in initial HTTP/2 frames. | `curl_cffi` reproduces authentic Google Chrome HTTP/2 frame sizes and HPACK compression. |
| **CSRF Token Validation** | Voyager endpoints reject requests missing valid CSRF protection. | Tross automatically cleans `ajax:` prefixes and strips enclosing double quotes from `JSESSIONID`, transmitting it via the `csrf-token` header. |
| **Telemetry & Header Order** | Missing browser headers or incorrect pseudo-header ordering triggers bot classification. | Tross constructs complete Chrome headers including `x-restli-protocol-version: 2.0.0`, `x-li-track` JSON metadata, dynamic `x-li-page-instance` URNs, `sec-ch-ua`, and context-aware `Referer`. |
| **Transient Retry Resilience** | Occasional 429 rate limits or 5xx gateway drops. | Managed with **`tenacity`** exponential backoff and jitter across retryable status codes (`429, 500, 502, 503, 504, 999`). |
| **Sub-Millisecond Caching** | High-concurrency duplicate requests. | Built-in thread-safe **In-Memory LRU Cache** with 24-hour TTL, returning instant responses (<1ms). |

---

## 📦 Tech Stack

- **Runtime:** Python 3.12+
- **API Framework:** [FastAPI](https://fastapi.tiangolo.com/) + [Starlette](https://www.starlette.io/)
- **Package & Environment Manager:** [`uv`](https://github.com/astral-sh/uv) (ultra-fast dependency resolution)
- **HTTP / TLS Impersonation:** [`curl_cffi`](https://github.com/lexiforest/curl_cffi) (BoringSSL Chrome 131 engine)
- **Data Validation & Settings:** [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Resilience:** [`tenacity`](https://tenacity.readthedocs.io/)
- **Structured Logging:** [`structlog`](https://www.structlog.org/) (JSON logs with automatic credential masking)
- **Code Quality:** [`ruff`](https://github.com/astral-sh/ruff) (linter and formatter) & [`pytest`](https://docs.pytest.org/)

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) or standard `pip`:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/simon-derock/Tross.git
cd Tross
uv sync
# OR with pip:
# pip install -r requirements.txt
```

### 3. Configure Environment Variables & Cookie Extraction
Copy the template:
```bash
cp .env.example .env
```

#### 🔑 Mobile Session Cookie Extraction (Recommended for Long-Lived Sessions):
1. Open Google Chrome in an **Incognito Window**.
2. Press `F12` (DevTools) → `Ctrl+Shift+M` (Toggle Device Toolbar) → Select **iPhone 12 Pro** (or any mobile device).
3. Navigate to `https://www.linkedin.com/login` and log in. *(Mobile emulation instructs LinkedIn to issue a persistent, device-bound session token).*
4. In DevTools, go to **Application** tab → **Cookies** → `https://www.linkedin.com`.
5. Copy the values of `li_at` and `JSESSIONID`.

Edit `.env`:
```env
LI_AT_COOKIE=your_actual_li_at_value
JSESSIONID="ajax:your_actual_jsessionid_value"
```

### 4. Run the Server
```bash
uv run uvicorn main:app --reload --port 8000
# OR:
# uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing & Quality Assurance

The codebase includes an extensive automated test suite covering concurrency stress, network retries, CSRF token generation, JSON normalization, and 15+ dynamic profile persona generators.

```bash
# Run all 102 unit, integration, and stress tests
uv run pytest -v

# Run Ruff linter
uv run ruff check .

# Check formatting
uv run ruff format --check .
```

---

## 📖 API Reference

### `POST /api/profile`
Extracts comprehensive, structured profile data for a given LinkedIn profile URL. *(Note: `/api/scrape` is also supported as an alias).*

**Request Headers (Optional Dynamic Overrides):**
- `Content-Type: application/json`
- `X-Li-At`: *(Optional)* Dynamic session cookie override
- `X-JSESSIONID`: *(Optional)* Dynamic JSESSIONID cookie override

**Request Body:**
```json
{
  "url": "https://www.linkedin.com/in/satyanadella/"
}
```
*(Accepts both `"url"` and `"linkedin_url"` keys).*

**Example cURL Request:**
```bash
curl -X POST "http://localhost:8000/api/profile" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.linkedin.com/in/satyanadella/"}'
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
  "location": "Greater Seattle Area, Washington, United States",
  "country": "United States",
  "industry": "Computer Software",
  "about": "Satya Nadella is Chairman and Chief Executive Officer of Microsoft...",
  "followers": 10500000,
  "connections": 500,
  "profile_image_url": "https://media.licdn.com/dms/image/v2/D5603AQ/.../profile-displayphoto-shrink_800_800/...",
  "background_image_url": "https://media.licdn.com/dms/image/v2/D5616AQ/.../profile-displaybackgroundimage-shrink_350_1400/...",
  "experience": [
    {
      "title": "Chairman and Chief Executive Officer",
      "company": "Microsoft",
      "company_url": "https://www.linkedin.com/company/microsoft",
      "location": "Redmond, Washington, United States",
      "description": "Leading Microsoft's mission to empower every person and organization to achieve more.",
      "date_range": {
        "start_date": "Feb 2014",
        "end_date": "Present"
      },
      "duration": "12+ yrs"
    },
    {
      "title": "Executive Vice President, Cloud & Enterprise",
      "company": "Microsoft",
      "company_url": "https://www.linkedin.com/company/microsoft",
      "location": "Redmond, WA",
      "description": "Led the transformation to cloud infrastructure and services.",
      "date_range": {
        "start_date": "Jan 2011",
        "end_date": "Feb 2014"
      },
      "duration": "3 yrs"
    }
  ],
  "education": [
    {
      "school": "The University of Chicago Booth School of Business",
      "school_url": "https://www.linkedin.com/school/uchicagobooth/",
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
    }
  ],
  "scraped_at": "2026-08-28T00:00:00.000000+00:00",
  "trace_id": "9a38f7124b8d4c7ea1b65e903a9d7f12"
}
```

---

### Status Codes & Error Envelope

All error responses adhere to a consistent JSON envelope:
```json
{
  "detail": "Descriptive error message",
  "status_code": 401,
  "trace_id": "9a38f7124b8d4c7ea1b65e903a9d7f12"
}
```

| HTTP Status | Error Type | Description |
|---|---|---|
| **`200 OK`** | `Success` | Profile successfully extracted and structured. |
| **`401 Unauthorized`** | `AuthenticationError` | LinkedIn session cookies are missing, invalid, or expired. |
| **`404 Not Found`** | `ProfileNotFoundError` | The requested LinkedIn profile vanity slug does not exist. |
| **`422 Unprocessable Content`** | `ValidationError` | Invalid URL format (must contain `/in/<vanity_slug>`). |
| **`429 Too Many Requests`** | `RateLimitError` | LinkedIn rate limit reached after exponential retries. |
| **`502 Bad Gateway`** | `ScraperError` | Upstream LinkedIn connection failure or network error. |

---

### `GET /health`
Returns service health status.
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
   - `LI_AT_COOKIE` or `LI_AT`: Your LinkedIn `li_at` cookie value
   - `JSESSIONID`: Your LinkedIn `JSESSIONID` cookie value
   - `PROXY_URL` *(Optional)*: Residential proxy URL
4. Vercel automatically builds and deploys via `vercel.json` and `api/index.py`.

---

## ⚠️ Known Limitations & Operational Considerations

1. **Cookie Expiration & Refreshing:** LinkedIn session cookies (`li_at`) have a natural validity window (typically 30–90 days when extracted via mobile emulation). When the session expires, refresh `LI_AT_COOKIE` and `JSESSIONID` in your Vercel Environment Variables.
2. **Rate Limiting:** LinkedIn applies account-level and IP-level request throttling. If high volume is expected, configuring `PROXY_URL` with rotating residential proxies is recommended.
3. **Privacy Controls:** If a user has restricted sections of their profile (e.g. hidden connections, private email, or unlisted education), those specific fields will return null or empty lists as per LinkedIn's privacy policy.

---

## 👤 Author

**PHILIP SIMON DEROCK**  
GitHub: [@simon-derock](https://github.com/simon-derock)
