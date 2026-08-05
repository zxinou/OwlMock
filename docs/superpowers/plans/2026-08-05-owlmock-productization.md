# OwlMock Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn OwlMock into a secure, persistent, self-hosted web application organized around job-preparation projects and deployable as one Railway/Docker image.

**Architecture:** Keep Vue 3 and FastAPI, add a signed single-owner session boundary, a versioned SQLite schema with `job_projects`, and a same-origin application shell. Build the frontend into the backend image, store all mutable state beneath one data root, and make task state recoverable from SQLite.

**Tech Stack:** Vue 3, Vite, Vue Router, Tailwind CSS, FastAPI, SQLAlchemy 2, aiosqlite, Alembic, pytest, Vitest, Playwright, Docker, Railway.

---

### Task 1: Production Configuration, Storage, Health, and Authentication

**Files:**
- Create: `backend/security/session.py`
- Create: `backend/api/auth.py`
- Create: `backend/api/system.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/api/app.py`
- Modify: `backend/api/deps.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_auth.py`
- Test: `backend/tests/test_system_status.py`
- Test: `backend/tests/test_settings.py`

- [x] Add failing tests proving that data paths derive from `OWLMOCK_DATA_DIR`, health is public, protected APIs reject anonymous requests, login sets an HttpOnly SameSite cookie, logout clears it, and status never returns secret values.
- [x] Run `uv run pytest tests/test_auth.py tests/test_system_status.py tests/test_settings.py -q` and confirm the new tests fail before implementation.
- [x] Add `itsdangerous` and implement `SessionSigner` with payload `{"sub":"default","iat":<unix>}` and a seven-day max age.
- [x] Add `require_owner()` for REST; identity always resolves to internal owner `default` and never from client input. WebSocket enforcement remains in Task 4 with the full protected-surface inventory.
- [x] Add `/api/auth/login`, `/api/auth/session`, `/api/auth/logout`, `/api/health/live`, `/api/health/ready`, and authenticated `/api/system/status`.
- [x] Derive `SQLITE_PATH`, `JSONL_ROOT`, `RESUME_ROOT`, `JD_UPLOAD_ROOT`, `MEMORY_ROOT`, and `REPO_ROOT` from `OWLMOCK_DATA_DIR` unless explicitly overridden.
- [x] Run the focused tests, then `uv run pytest -q` for backend regression (`409 passed`).
- [x] Commit as `feat: add secure single-owner runtime foundation`.

### Task 2: Versioned Database and Job Project Model

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_legacy_baseline.py`
- Create: `backend/migrations/versions/0002_add_job_projects.py`
- Create: `backend/storage/db/migrations.py`
- Modify: `backend/storage/db/models.py`
- Modify: `backend/storage/db/engine.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_migrations.py`
- Test: `backend/tests/test_job_project_models.py`

- [ ] Add failing tests for clean-database upgrade and upgrade of a fixture legacy database containing existing `default` rows.
- [ ] Add `JobProject(id,user_id,title,company,location,current_jd_analysis_id,current_resume_id,archived_at,created_at,updated_at)` and nullable indexed `project_id` columns on JD analyses, resume matches, and sessions.
- [ ] Replace ad hoc startup ALTER calls with a migration runner that validates and stamps the legacy baseline before upgrading to head.
- [ ] Enable SQLite foreign keys, WAL, and busy timeout on every connection.
- [ ] Verify old rows remain readable with `project_id = NULL` and no existing file path is changed.
- [ ] Commit as `feat: add versioned job project schema`.

### Task 3: Project Service and API

**Files:**
- Create: `backend/service/project_service.py`
- Create: `backend/api/projects.py`
- Create: `backend/api/project_schemas.py`
- Modify: `backend/api/app.py`
- Modify: `backend/api/jd_analysis.py`
- Modify: `backend/api/resume_matches.py`
- Modify: `backend/api/sessions.py`
- Test: `backend/tests/test_projects_api.py`

- [ ] Write failing API tests for create/list/detail/edit/archive, current JD/resume validation, dashboard aggregation, and rejection of nonexistent or archived projects.
- [ ] Implement project CRUD with server-owned `user_id="default"`; archive via `PATCH {"archived":true}` and never cascade-delete assets.
- [ ] Add project-scoped JD submission, resume matching, and session creation endpoints that reuse existing task/service logic rather than duplicate model calls.
- [ ] Return a project aggregate containing current JD, current resume, latest completed match, recent sessions, and derived three-step status.
- [ ] Keep generic history endpoints compatible while removing public `user_id` trust from all mutations and reads.
- [ ] Run project tests and the full backend suite.
- [ ] Commit as `feat: add job project workflow api`.

### Task 4: Protect Existing REST, SSE, Upload, and WebSocket Surfaces

**Files:**
- Modify: `backend/api/chat.py`
- Modify: `backend/api/github_analysis.py`
- Modify: `backend/api/jd_analysis.py`
- Modify: `backend/api/resume_analysis.py`
- Modify: `backend/api/resume_matches.py`
- Modify: `backend/api/sessions.py`
- Modify: `backend/api/tasks.py`
- Modify: `backend/api/ws.py`
- Test: `backend/tests/test_auth_surface.py`
- Test: `backend/tests/test_realtime_auth.py`

- [ ] Add a route inventory test that asserts every non-public HTTP route depends on owner auth and every WebSocket rejects missing/invalid cookies before accept.
- [ ] Enforce same-origin checks for unsafe requests and remove all client-controlled `user_id` behavior.
- [ ] Validate record ownership on every detail, update, delete, SSE, resume, and task endpoint.
- [ ] Add stable error payloads `{code,message,request_id}` and redact model/file content from server errors.
- [ ] Run backend security and regression suites.
- [ ] Commit as `fix: enforce owner boundary across api surfaces`.

### Task 5: Authentication UI and Production App Shell

**Files:**
- Create: `frontend/src/stores/auth.js`
- Create: `frontend/src/pages/LoginPage.vue`
- Create: `frontend/src/layouts/AppShell.vue`
- Create: `frontend/src/components/app/AppSidebar.vue`
- Create: `frontend/src/components/app/AppTopbar.vue`
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/assets/styles/base.css`
- Test: `frontend/tests/auth.test.mjs`

- [ ] Add failing tests for session bootstrap, login/logout, 401 redirect, and protected route guards.
- [ ] Make API requests same-origin with credentials and centralized structured error handling.
- [ ] Implement `/login`; root redirects to `/projects` after authentication and to `/login` otherwise.
- [ ] Implement the approved fixed-sidebar AppShell using existing OwlMock assets, CSS tokens, Lucide icons, dark mode, keyboard focus, and mobile navigation.
- [ ] Run frontend tests and `npm run build`.
- [ ] Commit as `feat: add authenticated OwlMock app shell`.

### Task 6: Job Project Frontend and Core Workflow

**Files:**
- Create: `frontend/src/stores/projects.js`
- Create: `frontend/src/pages/projects/ProjectListPage.vue`
- Create: `frontend/src/pages/projects/ProjectCreatePage.vue`
- Create: `frontend/src/pages/projects/ProjectWorkspacePage.vue`
- Create: `frontend/src/components/projects/ProjectPipeline.vue`
- Create: `frontend/src/components/projects/ProjectFocus.vue`
- Create: `frontend/src/components/projects/ProjectInterviewHistory.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/pages/InterviewConfigPage.vue`
- Test: `frontend/tests/projects.test.mjs`

- [ ] Add failing store/component tests for project loading, draft creation, JD task recovery, resume selection/match, derived steps, archive, and empty/error states.
- [ ] Implement project list and create flow for text/image JD with stable task URLs.
- [ ] Implement the approved workspace composition: header, three-stage pipeline, preparation focus, job summary, next actions, and recent interviews.
- [ ] Route project actions into existing JD reports, resume match reports, and project-scoped interview configuration.
- [ ] Preserve global unassigned history for legacy data and optional GitHub analysis.
- [ ] Verify desktop/mobile and light/dark rendering; run tests and build.
- [ ] Commit as `feat: add job preparation workspace`.

### Task 7: Text and Voice Production Reliability

**Files:**
- Modify: `backend/agent/realtime_agent.py`
- Modify: `backend/api/ws.py`
- Modify: `frontend/src/composables/useVoiceInterview.js`
- Modify: `frontend/src/components/interview/VoiceMode.vue`
- Modify: `frontend/src/components/interview/TextMode.vue`
- Modify: `frontend/src/pages/InterviewSessionPage.vue`
- Test: `backend/tests/test_project_interviews.py`
- Test: `backend/tests/test_realtime_events.py`
- Test: `frontend/tests/useVoiceInterview.test.mjs`

- [ ] Add tests for project context injection, duplicate commit protection, reconnect/retry states, idempotent finalize, and authenticated WebSocket sessions.
- [ ] Add voice preflight status for secure context, microphone permission/device, provider readiness, and configured duration.
- [ ] Preserve manual turn control; on disconnect or incomplete audio, return to an explicit retry state without submitting partial input.
- [ ] Restore text and voice histories from persisted session events and return completed summaries to the project workspace.
- [ ] Run focused and full test suites.
- [ ] Commit as `fix: harden project text and voice interviews`.

### Task 8: Single-Image Railway and Docker Delivery

**Files:**
- Create: `Dockerfile`
- Create: `railway.toml`
- Create: `backend/api/static.py`
- Modify: `backend/api/app.py`
- Replace: `backend/docker-compose.yml`
- Modify: `.dockerignore`
- Test: `backend/tests/test_spa_serving.py`

- [ ] Add tests proving API precedence and SPA fallback for `/projects/...` without intercepting `/api` or `/ws`.
- [ ] Build frontend assets in a Node stage and copy them into the Python runtime image.
- [ ] Serve immutable assets with cache headers and `index.html` without long-lived caching.
- [ ] Configure Railway health check, one worker, `/data` volume contract, proxy headers, and graceful shutdown.
- [ ] Make Compose run the same image and named volume; keep Langfuse optional.
- [ ] Run `docker build -t owlmock:local .` and smoke test health, login, SPA refresh, SSE, and WebSocket upgrade.
- [ ] Commit as `build: ship OwlMock as one deployable image`.

### Task 9: Backup, CI, Documentation, and Release Verification

**Files:**
- Create: `backend/management/backup.py`
- Create: `backend/management/__main__.py`
- Create: `.github/workflows/ci.yml`
- Create: `frontend/tests/e2e/core-flow.spec.js`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/package.json`
- Test: `backend/tests/test_backup.py`

- [ ] Add failing tests for consistent backup manifest, repository-cache exclusion, restore version validation, and restored data readability.
- [ ] Implement `python -m management backup` and `restore` with SQLite online backup and atomic restore while stopped.
- [ ] Add CI jobs for backend pytest/ruff, frontend tests/build, Playwright core flow, and Docker build.
- [ ] Document Railway, Compose, environment variables, upgrade, backup/restore, reverse proxy, and troubleshooting with copyable commands.
- [ ] Run the entire CI-equivalent suite locally.
- [ ] Start the production image and use browser QA at desktop and mobile sizes for login, project creation, JD task, resume match, text interview, voice preflight/turn, summary, restart recovery, and logout.
- [ ] Compare the rendered workspace to the approved concept with `view_image`, record the fidelity ledger, and fix every non-intentional mismatch.
- [ ] Commit as `docs: complete OwlMock self-hosted release`.
