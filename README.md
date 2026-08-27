# Tross — LinkedIn Scraper API

> Production-ready, serverless LinkedIn profile scraper. Accepts a profile URL, returns a PhantomBuster-compatible JSON payload. Deployed on Vercel.

---

## Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI + Python 3.12 |
| Package manager | `uv` |
| Networking | HTTPX (async) + `tenacity` retries |
| Session cache | Upstash Redis |
| Parsing | Voyager JSON-LD + BeautifulSoup4 fallback |
| Validation | Pydantic v2 + pydantic-settings |
| Logging | structlog (JSON, cookie-masked) |
| Deployment | Vercel Serverless (Python runtime) |
| Quality | ruff (lint + format) + pytest |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/simon-derock/Tross.git
cd Tross
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: LI_AT, JSESSIONID, INTERNAL_API_KEY, UPSTASH_REDIS_URL
```

### 3. Run locally

```bash
uv run uvicorn app.main:app --reload
```

API docs at → http://localhost:8000/docs

### 4. Run tests

```bash
uv run pytest && uv run ruff check . && uv run ruff format --check .
```

---

## API Reference

### `POST /api/scrape`

Scrape a LinkedIn profile.

**Headers:**
```
X-API-Key: <INTERNAL_API_KEY>
Content-Type: application/json
```

**Body:**
```json
{ "linkedin_url": "https://www.linkedin.com/in/username/" }
```

**Response `200`:**
```json
{
  "full_name": "Jane Doe",
  "headline": "Senior SWE @ BigCo",
  "location": "San Francisco, CA",
  "about": "...",
  "experience": [...],
  "education": [...],
  "skills": ["Python", "FastAPI"],
  "certifications": [...],
  "languages": [...],
  "profile_image_url": "https://media.licdn.com/...",
  "trace_id": "abc123"
}
```

**Errors:**
| Code | Meaning |
|---|---|
| `401` | Wrong API key OR expired LinkedIn cookies |
| `422` | Invalid LinkedIn URL |
| `502` | LinkedIn fetch/parse failure |

### `GET /health`

No auth required. Returns `{"status": "ok"}`.

---

## Architecture

```
POST /api/scrape
      │
      ▼
verify_api_key (X-API-Key header)
      │
      ▼
scraper.scrape_profile()
      │
      ├─ SessionCache.get_cookies()  ←  Upstash Redis
      │
      ├─ LinkedInClient.get()        ←  HTTPX + Proxy + tenacity retries
      │
      └─ parse_profile()
            ├─ _parse_voyager()      ←  Primary: <code> tag JSON-LD
            └─ _build_from_html()   ←  Fallback: BeautifulSoup4 CSS
```

---

## Deployment (Vercel)

1. Push to GitHub.
2. Import project in [Vercel dashboard](https://vercel.com).
3. Set environment variables (use Vercel Secrets):
   - `LI_AT`, `JSESSIONID`, `INTERNAL_API_KEY`, `UPSTASH_REDIS_URL`, `PROXY_URL`
4. Vercel auto-detects `vercel.json` and deploys using `requirements.txt`.

---

## Security

- **Zero hardcoded credentials** — all secrets via env vars / Vercel secrets.
- **API Key gate** on all `/api/*` routes — prevents unauthorized cookie burning.
- **Cookie masking** in all logs via structlog processor.
- **Security headers** (`HSTS`, `X-Frame-Options`, `X-Content-Type-Options`) via `vercel.json`.
- **Ephemeral Redis TTL** (20h) prevents stale cookie reuse.
