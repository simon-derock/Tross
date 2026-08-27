# Memory Ledger & State Tracker

## PAST
- [x] Phase 1: Repository initialization, `PLAN.md` defined.
- [x] Phase 2: Base environment setup, logging, and pydantic-settings.
- [x] Phase 3: Comprehensive Pydantic v2 schemas (`app/schemas.py`).
- [x] Pure Reverse-Engineered Architecture:
  - Strict No-Browser & Zero-HTML Scraping rule enforced.
  - Direct HTTP calls to LinkedIn internal private Voyager REST API endpoints (`/voyager/api/identity/profiles/{vanity_slug}/profileView`).
  - Replicates exact Chrome 131 TLS ClientHello (JA3/JA4) and HTTP/2 SETTINGS frames using `curl_cffi`.
  - Dynamic `csrf-token` derivation (`JSESSIONID.strip('"')`) and Restli 2.0 protocol headers (`x-restli-protocol-version: 2.0.0`, `x-li-page-instance`, `x-li-track`).
- [x] Pure JSON Traversal & Extraction (`app/parser.py`):
  - Traverses raw Restli JSON tree directly into typed Pydantic v2 models (`ProfileResponse`).
  - Extracts full name, headline, location, about, promotions, date ranges, schools, skills, certifications, languages, and highest-resolution profile picture artifacts.
- [x] High-Performance In-Memory LRU Cache (`app/scraper.py`):
  - Caches responses in memory with a 24-hour TTL for sub-millisecond responses on repeated queries.
- [x] Candidate Header & Clean Swagger UI:
  - Official base Swagger UI at `/docs` with attribution `by PHILIP SIMON DEROCK`.
- [x] Full Automated Verification:
  - 104 tests passing (100%), Ruff linter clean, Ruff formatting clean.
  - GitHub Actions CI/CD workflow active (`.github/workflows/ci.yml`).

## PRESENT
- **Current Branch:** `main`
- **Total Automated Tests:** 104 passing (100%)
- **Lint / Formatting:** Ruff 100% clean
- **Active Error/Exception:** None. Project is 100% complete and production-ready.

## STATUS: PROJECT COMPLETE ✅

---

## Provider Handover Protocol

```xml
<provider_handover_protocol version="5.0">
  <metadata>
    <project_name>Tross</project_name>
    <candidate_name>PHILIP SIMON DEROCK</candidate_name>
    <repository_url>https://github.com/simon-derock/Tross.git</repository_url>
    <target_runtime>Python 3.12+ (FastAPI on Vercel Serverless)</target_runtime>
    <package_manager>uv</package_manager>
    <output_schema_format>Structured LinkedIn Profile JSON Schema</output_schema_format>
    <status>PRODUCTION_READY_PURE_VOYAGER_REVERSE_ENGINEERED</status>
    <total_tests>104</total_tests>
  </metadata>

  <system_architecture>
    <core_philosophy>
      Pure reverse-engineered API scraping directly hitting LinkedIn's private Voyager REST endpoints.
      Zero browser automation (no Selenium/Playwright) and zero HTML DOM parsing (pure JSON-to-JSON).
    </core_philosophy>
    <anti_detection_stack>
      <transport>curl_cffi with impersonate="chrome131" (replicates exact Chrome JA3/JA4 TLS handshake &amp; HTTP/2 SETTINGS frames).</transport>
      <csrf_derivation>Header 'csrf-token' derived from JSESSIONID with surrounding double-quotes stripped.</csrf_derivation>
      <header_authenticity>Chrome 131 headers with dynamic 'x-li-page-instance', 'x-li-track', 'x-restli-protocol-version: 2.0.0', and context-aware 'Referer'.</header_authenticity>
      <retry_resilience>Tenacity exponential backoff covering HTTP 429, 500, 502, 503, 504, and HTTP 999.</retry_resilience>
      <cache_layer>In-memory LRU Cache (24-hour TTL) delivering &lt;1ms responses for cached profiles.</cache_layer>
    </anti_detection_stack>
    <modules>
      <module name="app.config">pydantic-settings boot validator for LI_AT, JSESSIONID, PROXY_URL.</module>
      <module name="app.network">VoyagerClient using curl_cffi AsyncSession with Chrome 131 impersonation and tenacity retries.</module>
      <module name="app.parser">Pure JSON parser mapping Voyager profileView Restli entities to ProfileResponse schema.</module>
      <module name="app.scraper">Pure Voyager REST API orchestrator with In-Memory LRU Cache.</module>
      <module name="app.main">FastAPI ASGI application with open /api/scrape, /health, and standard /docs.</module>
      <module name="api.index">Vercel serverless entry point re-exporting FastAPI app.</module>
    </modules>
  </system_architecture>

  <quick_start_commands>
    <command desc="Install dependencies">uv sync</command>
    <command desc="Run test suite">uv run pytest -v</command>
    <command desc="Run linter">uv run ruff check .</command>
    <command desc="Start local dev server">uv run uvicorn app.main:app --reload --port 8000</command>
  </quick_start_commands>

  <deployment_guide>
    <step>Import repository into Vercel Dashboard.</step>
    <step>Configure Environment Secrets: LI_AT, JSESSIONID, PROXY_URL (optional).</step>
    <step>Deploy to production.</step>
  </deployment_guide>
</provider_handover_protocol>
```
