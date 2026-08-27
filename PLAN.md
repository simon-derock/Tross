# Tross: LinkedIn Scraper API - Master Architecture Plan

## 1. Executive Objective
Build a world-class, production-ready backend API that reverse-engineers LinkedIn profile data. It will accept a LinkedIn profile URL via an HTTPS POST request and return a structured JSON payload. The service will be deployed as a serverless function on Vercel, built with Python 3.12+ and FastAPI, and managed entirely with `uv`.

## 2. Core Architecture & Guardrails
- **Framework:** Python 3.12+ / FastAPI.
- **Package Manager:** `uv` for ultra-fast dependency resolution and environment management.
- **Methodology:** Spec-Driven Development (SDD) & Test-Driven/Behavior-Driven Development (TDD/BDD).
- **CI/CD Quality Gates:** All commits must pass the validation chain: `uv run pytest && uv run ruff check && uv run ruff format --check`.

## 3. Git & State Discipline

- **MUST Make micro commits on each step**
- **Worktree Isolation:** The `main` branch must remain completely pristine. All implementation streams occur in isolated Git Worktrees (`git worktree add ../wt-<feature-name> -b feature/<feature-name>`).
- **Conventional Commits:** All commits must strictly adhere to the Conventional Commits format (`<type>(<scope>): <subject>`). 
  - Types allowed: `feat`, `fix`, `test`, `refactor`, `chore`, `docs`.
  - Imperative mood, max 50 characters for the subject line.
- **Memory Ledger:** The `memory.md` file acts as the ultimate single source of truth for execution state and must be updated alongside every micro-commit to ensure seamless AI provider handovers.

## 4. Scraper Engine & Infrastructure
- **Strict Environment Validation:** Application boot will use `pydantic-settings` to strictly validate the presence and format of required secrets (cookies, proxy URIs, internal API keys). Missing secrets will fail the build, preventing runtime crashes.
- **Authentication & Ephemeral State:** 
  - Zero hardcoded credentials. 
  - Valid `li_at` and `JSESSIONID` cookies will be stored and retrieved via a lightweight Upstash Redis caching layer to persist session validity across stateless Vercel invocations, preventing account flags.
- **Network Resiliency:** 
  - HTTPX used for asynchronous networking.
  - Integration of external residential proxy rotation injected directly into the HTTPX client.
  - Implement `tenacity` for exponential backoff and retries to gracefully handle transient network drops and HTTP 429s.
- **Extraction Layer:** 
  - Primary Strategy: Parse the embedded Voyager JSON state objects (`<code>` tags) to extract raw GraphQL payloads. 
  - Fallback Strategy: BeautifulSoup4 CSS selectors.
- **Data Serialization:** 
  - Strict Pydantic output schemas (Name, Headline, Location, About, Experience, Education, Skills, Certifications, Languages, Profile Image).

## 5. Security & Telemetry
- **Endpoint Protection:** The inbound POST endpoint (`/api/scrape`) will require internal API key authentication via headers to prevent unauthorized public execution and credential burning.
- **Structured Logging:** Implement `structlog` for JSON-formatted telemetry (Trace IDs, execution durations, proxy routing metadata) specifically configured to sanitize and mask all session cookies.

## 6. Deployment & Execution Timeline

### Phase 1: Repository & System Initialization (Completed)
- Initialize Git.
- Define `plan.md` and `memory.md`.

### Phase 2: Environment & Tooling Foundation (Worktree: `wt-setup`)
- Initialize `uv` project.
- Implement `pydantic-settings` for `.env` validation.
- Configure `structlog` for sanitized JSON output.

### Phase 3: Schema & TDD Base (Worktree: `wt-schema`)
- Define comprehensive Pydantic schemas.
- Write strict JSON fixture tests and endpoint behavior tests.

### Phase 4: Core Network Engine (Worktree: `wt-network`)
- Implement HTTPX client with proxy rotation and `tenacity` retries.
- Build Upstash Redis integration for session caching.

### Phase 5: Extraction Logic (Worktree: `wt-scraper`)
- Develop Voyager JSON-LD parsers and HTML fallbacks.
- Tie parsed data into Pydantic validators.

### Phase 6: Vercel Production Deployment (Worktree: `wt-deploy`)
- Implement `/api/scrape` FastAPI routing and API Key security.
- Create CI script `uv pip compile` to generate `requirements.txt` for Vercel builds.
- Configure `vercel.json` and deploy.


================================================================================
FILE: memory.md
================================================================================
# Memory Ledger

## PAST
- [x] Received initialization parameters for LinkedIn Scraper API.
- [x] Defined system guardrails, TDD pipeline constraints, and Provider Handover Protocol.
- [x] Integrated Conventional Commits protocol.
- [x] Added missing production architectures: proxies, retries (`tenacity`), Redis session state, `pydantic-settings`, structured logging, and internal API security.
- [x] Removed `.cursorrules` as requested.
- [x] Generated consolidated comprehensive master files.

## PRESENT
- **Branch:** `main`
- **Worktree Directory:** `root`
- **File:** `memory.md`
- **Line Number:** 21
- **Active Error/Exception:** None. System architecture finalized and verified.

## NEXT (Queue)
1. Initialize Python project via `uv init` and add core dependencies (`fastapi`, `httpx`, `pytest`, `pydantic`, `pydantic-settings`, `beautifulsoup4`, `tenacity`, `redis`, `structlog`, `ruff`).
2. Create isolated Git worktree: `git worktree add ../wt-setup -b feature/environment-setup`.
3. Implement `config.py` using `pydantic-settings` to enforce strict environment variable validation.