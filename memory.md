# Memory Ledger & State Tracker

## PAST
- [x] Phase 1: Repository initialization, `PLAN.md` defined.
- [x] Phase 2: Base environment setup, logging, and pydantic-settings.
- [x] Phase 3: PhantomBuster-compliant Pydantic v2 schemas (`app/schemas.py`).
- [x] Architectural Pivot & Deep Research:
  - Eliminated naive HTML scraping / `httpx` in favor of pure LinkedIn Voyager REST API reverse engineering.
  - Eliminated mandatory Redis dependency for zero-friction local and cloud execution.
  - Adopted `curl_cffi` with Chrome 131 TLS (JA3/JA4) and HTTP/2 SETTINGS frame impersonation to prevent HTTP 999 bans.
- [x] Phase 2 Upgrade (`feature/core-config`):
  - Added `curl_cffi`, removed `redis` from `pyproject.toml`.
  - Updated `app/config.py` with fail-fast `pydantic-settings` validation (no Redis required).
  - Passed 13 config unit tests; merged to `main` and pushed.
- [x] Phase 4 Upgrade (`feature/voyager-network`):
  - Implemented `VoyagerClient` in `app/network.py` using `curl_cffi.requests.AsyncSession(impersonate="chrome131")`.
  - Built dynamic `csrf-token` generator (`JSESSIONID.strip('"')`), authentic Chrome 131 headers, and `tenacity` exponential backoff retries.
  - Passed 27 network unit tests; merged to `main` and pushed.

## PRESENT
- **Current Branch:** `main` (commit: `e4e7f81`)
- **Active Workstream:** Phase 5 Upgrade (`feature/voyager-parser` in `/home/simon/wt-parser`)
- **Active Error/Exception:** None. All quality gates passing (`ruff`, `pytest`).

## NEXT (Queue)
1. **Phase 5 Upgrade (`wt-parser` / `feature/voyager-parser`):**
   - Write realistic Voyager `profileView` JSON fixtures in `tests/fixtures/voyager_payloads.py`.
   - Implement `parse_voyager_profile` in `app/parser.py` (pure JSON extraction for Name, Headline, Location, About, highest-res Profile Image, Experience, Education, Skills, Certifications, Languages).
   - Test, verify, micro-commit, push, and merge into `main`.
2. **Phase 6 Upgrade (`wt-api` / `feature/api-orchestrator`):**
   - Update `app/scraper.py` orchestrator to run `VoyagerClient` -> `parse_voyager_profile`.
   - Update `app/main.py` with `/api/scrape` and `/health`.
   - Update integration tests in `tests/test_scraper.py` and `tests/test_main.py`.
   - Test, verify, micro-commit, push, and merge into `main`.
3. **Master Verification & Documentation:**
   - Compile `requirements.txt` via `uv pip compile`.
   - Update `README.md` with complete architecture, approach, API docs, and known limitations.
   - Run complete test suite and push final state to `origin/main`.

---

## Provider Handover Protocol

```xml
<provider_handover_protocol version="2.1">
  <metadata>
    <project_name>Tross</project_name>
    <repository_url>https://github.com/simon-derock/Tross.git</repository_url>
    <target_runtime>Python 3.12+ (FastAPI on Vercel Serverless)</target_runtime>
    <package_manager>uv</package_manager>
    <output_schema_format>PhantomBuster LinkedIn Profile Scraper JSON</output_schema_format>
  </metadata>

  <system_architecture>
    <core_philosophy>
      Pure reverse-engineered API scraping directly hitting LinkedIn's private Voyager REST endpoints.
      Zero browser automation (Selenium/Playwright) is used.
    </core_philosophy>
    <anti_detection_stack>
      <transport>curl_cffi with impersonate="chrome131" (replicates exact Chrome JA3/JA4 TLS handshake &amp; HTTP/2 SETTINGS frames).</transport>
      <csrf_derivation>Header 'csrf-token' must be JSESSIONID with surrounding double-quotes stripped.</csrf_derivation>
      <header_authenticity>Chrome 131 headers with dynamic 'x-li-page-instance', 'x-li-track', 'x-restli-protocol-version: 2.0.0', and context-aware 'Referer'.</header_authenticity>
      <retry_resilience>Tenacity exponential backoff covering HTTP 429, 500, 502, 503, 504, and HTTP 999.</retry_resilience>
    </anti_detection_stack>
  </system_architecture>

  <status_and_locations>
    <active_branch>main</active_branch>
    <worktrees>
      <worktree path="/home/simon/wt-parser" branch="feature/voyager-parser" purpose="Pure JSON Voyager parser implementation and fixtures" />
      <worktree path="/home/simon/wt-api" branch="feature/api-orchestrator" purpose="Scraper orchestrator and FastAPI endpoint integration" />
    </worktrees>
  </status_and_locations>

  <mandatory_guidelines>
    <rule>Always use isolated Git worktrees for features and micro-commit using Conventional Commits.</rule>
    <rule>Always run and pass `uv run pytest &amp;&amp; uv run ruff check . &amp;&amp; uv run ruff format --check .` before merging.</rule>
    <rule>Keep memory.md and this handover protocol updated on every merge to main.</rule>
  </mandatory_guidelines>
</provider_handover_protocol>
```
