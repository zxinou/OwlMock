# Resume Match Three-State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build recoverable input, task-progress, and structured report pages for true resume-to-JD matching without breaking uploaded resumes or legacy analysis.

**Architecture:** Add a focused `ResumeMatchRecord` and report schema beside the existing `Resume` model. Use the established `TaskService` plus persisted status pattern from JD analysis, a dedicated multimodal `resume-matcher` profile, and three Vue routes with shared matching components.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, SQLAlchemy async, SQLite, pytest, Vue 3, Vue Router, lucide-vue-next, Vite.

---

### Task 1: Define matching schema and persistence

**Files:**
- Create: `backend/service/resume_match_report.py`
- Modify: `backend/storage/db/models.py`
- Modify: `backend/storage/db/engine.py`
- Create: `backend/tests/test_resume_match_report.py`
- Create: `backend/tests/test_resume_match_async.py`

- [ ] Write failing tests for score bounds, match-status enums, evidence fields, and the `ResumeMatchRecord` defaults.
- [ ] Run `python -m pytest tests/test_resume_match_report.py tests/test_resume_match_async.py -q` and confirm failures.
- [ ] Implement focused Pydantic report models and the additive table model.
- [ ] Run the tests and confirm schema/persistence passes.

### Task 2: Implement async matching lifecycle

**Files:**
- Create: `backend/api/resume_matches.py`
- Modify: `backend/api/app.py`
- Modify: `backend/api/tasks.py`
- Create: `backend/config/agents/resume-matcher.yaml`
- Create: `backend/data/prompt/resume_matcher.md`
- Modify: `backend/tests/test_resume_match_async.py`

- [ ] Add failing endpoint tests for submit, running detail, idempotent stale resume, completion, failure, history, and delete.
- [ ] Implement shared multimodal execution using the selected resume images plus JD text and `ResumeMatchReport` structured output.
- [ ] Persist each stage before publishing `TaskService` progress and protect terminal records from late updates.
- [ ] Register the router and task-status database fallback.
- [ ] Run new tests plus `tests/test_resume_analyze.py tests/test_resume_api.py`.

### Task 3: Add frontend API and recovery state

**Files:**
- Modify: `frontend/src/api/index.js`
- Create: `frontend/src/composables/useResumeMatchTask.js`
- Modify: `frontend/src/router/index.js`

- [ ] Add submit/list/detail/resume/delete API methods.
- [ ] Implement persisted GET first, idempotent resume, SSE, polling fallback, and cleanup.
- [ ] Register input, task, report, and legacy-report routes in non-conflicting order.
- [ ] Run `npm run build`.

### Task 4: Build input and task pages

**Files:**
- Rewrite: `frontend/src/pages/ResumePage.vue`
- Create: `frontend/src/pages/resume/ResumeMatchTaskPage.vue`
- Create: `frontend/src/components/resume/ResumeLibrary.vue`
- Create: `frontend/src/components/resume/ResumeMatchHistory.vue`

- [ ] Build resume selection/upload plus JD input with inline validation.
- [ ] Add recent match history and custom deletion using `ConfirmDialog`.
- [ ] Build four-step nonblocking task progress with failure/retry and automatic report routing.
- [ ] Verify responsive and dark-mode styles through the production build.

### Task 5: Build matching report and legacy compatibility

**Files:**
- Create: `frontend/src/pages/resume/ResumeMatchReportPage.vue`
- Create: `frontend/src/pages/resume/ResumeLegacyReportPage.vue`
- Create: `frontend/src/components/resume/ResumeMatchDashboard.vue`
- Create: `frontend/src/components/resume/ResumeRequirementGroup.vue`

- [ ] Render score, KPIs, grouped requirement evidence, skill matrix, strengths, gaps, interview focus, resume actions, and summary.
- [ ] Redirect running records back to the task route and provide contained terminal errors.
- [ ] Keep legacy standalone analysis accessible without calling the model again.
- [ ] Use custom delete confirmation and no browser-native dialogs.

### Task 6: End-to-end verification

**Files:**
- Modify only files tied to reproducible verification failures.

- [ ] Run all resume, database, task, structured-output, and model-routing backend tests.
- [ ] Run the frontend production build.
- [ ] Verify desktop/mobile and light/dark input, task, report, legacy report, navigation recovery, and delete dialog.
- [ ] Confirm one completed task creates one traced structured generation and refresh does not call the model again.
