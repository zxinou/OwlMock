# JD Analysis Three-State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build recoverable input, task-progress, and structured report pages for pure JD analysis while preserving current history and synchronous API compatibility.

**Architecture:** Keep the existing FastAPI, SQLite, `TaskService`, structured LLM router, Vue 3, and `AnalysisLayout`. Add a focused JD report service for schema normalization, extend `JdAnalysisRecord` with additive task fields, expose new async endpoints beside existing sync endpoints, and split the frontend into three routes that render one shared report structure.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, SQLAlchemy async, pytest, Vue 3, Vue Router, Tailwind CSS, lucide-vue-next, Vite.

---

### Task 1: Define the structured JD report and legacy normalization

**Files:**
- Create: `backend/service/jd_report.py`
- Modify: `backend/tests/test_jd_analysis.py`

- [ ] **Step 1: Write failing schema and normalization tests**

Add tests that validate `JdReport`, reject an unsupported requirement category, keep absent metadata as `None`, and convert the existing four-array payload:

```python
def test_legacy_jd_payload_normalizes_to_dashboard_report(mock_llm_response):
    report = normalize_jd_report(mock_llm_response)
    assert report.job.title == "未识别岗位"
    assert report.requirements[0].category == "硬性要求"
    assert report.risks[0].evidence == mock_llm_response["red_flags"][0]["text"]
    assert report.recommendations == mock_llm_response["suggestions"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py -q`

Expected: collection fails because `service.jd_report` does not exist.

- [ ] **Step 3: Implement report models and normalizer**

Create Pydantic models for `JdJob`, `JdDifficulty`, `JdRequirement`, `JdSkill`, `JdExpectation`, `JdRisk`, `JdInterviewFocus`, `JdSummary`, and `JdReport`. Export:

```python
def normalize_jd_report(payload: dict | None) -> JdReport:
    """Validate a current report or convert a legacy four-array JD result."""
```

Use exact Chinese enums from the design spec. Legacy soft requirements map to `优先条件`; legacy red flags use their text as both title and evidence.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py -q`

Expected: schema and normalization tests pass; pre-existing endpoint tests may still fail until Task 3 updates the API.

### Task 2: Add reload-safe JD task persistence

**Files:**
- Modify: `backend/storage/db/models.py`
- Modify: `backend/storage/db/engine.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_db_models.py`
- Modify: `backend/tests/test_jd_analysis.py`

- [ ] **Step 1: Write failing migration and model tests**

Add assertions for `source_type`, `source_path`, `status`, `stage`, `progress`, `error`, and `updated_at`. Add a migration test that starts with the old JD table and verifies existing rows become `completed` while `result_json` remains non-null.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_db_models.py tests/test_jd_analysis.py -q`

Expected: attributes and `_ensure_jd_analysis_columns` are missing.

- [ ] **Step 3: Add model fields and additive migration**

Extend `JdAnalysisRecord` without changing relationships. New ORM inserts default to `pending/waiting/0.0`; SQLite migration adds the same columns with defaults suitable for old rows:

```sql
ALTER TABLE jd_analyses ADD COLUMN status VARCHAR NOT NULL DEFAULT 'completed';
ALTER TABLE jd_analyses ADD COLUMN stage VARCHAR NOT NULL DEFAULT 'completed';
ALTER TABLE jd_analyses ADD COLUMN progress FLOAT NOT NULL DEFAULT 1.0;
```

Add nullable source/error/timestamp columns and call `_ensure_jd_analysis_columns` from `init_db`. Add `JD_UPLOAD_ROOT: str = "../analysis_cache/jd_uploads"` so uploads stay outside the reload tree.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv/Scripts/python.exe -m pytest tests/test_db_models.py tests/test_jd_analysis.py -q`

Expected: model and migration tests pass.

### Task 3: Add asynchronous JD analysis lifecycle and endpoints

**Files:**
- Modify: `backend/api/jd_analysis.py`
- Modify: `backend/api/tasks.py`
- Modify: `backend/tests/test_jd_analysis.py`
- Modify: `backend/tests/test_analysis_pipeline.py`

- [ ] **Step 1: Write failing async endpoint tests**

Cover these behaviors with patched structured LLM calls and the test SQLite factory:

```python
async def test_submit_text_jd_returns_pending_task(client):
    response = await client.post("/api/jd/analyses", json={"text": VALID_JD})
    assert response.status_code == 202
    assert response.json()["status"] == "pending"

async def test_get_jd_analysis_returns_running_state(client, pending_record):
    response = await client.get(f"/api/jd/analyses/{pending_record.id}")
    assert response.json()["stage"] == "waiting"

async def test_resume_stale_jd_task_is_idempotent(client, stale_record):
    first = await client.post(f"/api/jd/analyses/{stale_record.id}/resume")
    second = await client.post(f"/api/jd/analyses/{stale_record.id}/resume")
    assert first.json()["task_id"] == second.json()["task_id"]
```

Also test image persistence, terminal status protection, task endpoint DB fallback, and deletion cleanup.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py tests/test_analysis_pipeline.py -q`

Expected: new routes return 404 and task fallback cannot find JD records.

- [ ] **Step 3: Implement shared LLM execution and background runner**

Refactor existing sync handlers to call a shared function:

```python
async def analyze_jd_source(record: JdAnalysisRecord) -> JdReport:
    """Build text or multimodal messages and return a validated report."""

async def run_jd_analysis_task(analysis_id: str) -> None:
    """Persist progress, run analysis once, and preserve terminal state."""
```

Persist stage before every task update. Use stages `extracting`, `structuring`, `analyzing`, `saving`, `completed`, and `failed`. On success atomically replace `"{}"` with the report JSON. On failure save a user-safe error and call `task_service.fail_task`.

- [ ] **Step 4: Implement new routes without removing old ones**

Add `POST /jd/analyses`, `POST /jd/analyses/image`, `GET /jd/analyses/{id}`, and `POST /jd/analyses/{id}/resume`. Keep `/jd/analyze` and `/jd/analyze-image` synchronous and make them return the new report shape. Place the static list route before the dynamic detail route.

Update `/tasks/{id}` DB fallback to query `RepoAnalysis` then `JdAnalysisRecord`.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py tests/test_analysis_pipeline.py -q`

Expected: all JD lifecycle and shared task tests pass.

### Task 4: Replace the JD prompt with evidence-based structured analysis

**Files:**
- Modify: `backend/data/prompt/jd_analyzer.md`
- Modify: `backend/tests/test_jd_analysis.py`

- [ ] **Step 1: Add a failing prompt-contract test**

Assert the prompt names every current top-level field, forbids HTML and resume matching scores, and requires evidence for risks and inferred expectations.

- [ ] **Step 2: Run the prompt test and verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py -q`

Expected: old four-array prompt lacks `skills`, `interview_focus`, and the no-match-score rule.

- [ ] **Step 3: Write the new prompt**

Require exactly the `JdReport` JSON schema. State that absent company/location/salary values are `null`, percentages are forbidden without a resume, evidence must quote or closely paraphrase JD text, and output language follows the JD language.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py -q`

Expected: prompt contract and endpoint tests pass.

### Task 5: Add frontend API state management and routes

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/api/index.js`
- Create: `frontend/src/composables/useJdTask.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/layouts/AnalysisLayout.vue`

- [ ] **Step 1: Add lucide-vue-next**

Run: `npm install lucide-vue-next`

Expected: dependency is recorded in package files.

- [ ] **Step 2: Add the async API methods**

Expose `submitJd`, `submitJdImage`, `getJdAnalysis`, and `resumeJdAnalysis`. Keep existing sync methods for compatibility.

- [ ] **Step 3: Implement task recovery composable**

`useJdTask(taskId)` must:

```javascript
// 1. GET the persisted JD record immediately.
// 2. Open EventSource when an in-memory task exists.
// 3. Poll GET /jd/analyses/:id after SSE errors.
// 4. Call resume once when DB is running but the task is stale.
// 5. expose status, stage, progress, error, start(), and stop().
```

Clean up EventSource and timers in `onBeforeUnmount`.

- [ ] **Step 4: Register three JD routes and route-specific widths**

Map `/analysis/jd`, `/analysis/jd/tasks/:taskId`, and `/analysis/jd/:analysisId`. The task route must appear before the dynamic report route. Add route metadata `contentWidth: "wide" | "narrow"`, and let `AnalysisLayout` map it to stable max widths without changing other pages.

- [ ] **Step 5: Verify the frontend compiles**

Run: `npm run build`

Expected: Vite exits 0 with all three lazy route chunks.

### Task 6: Build the input and task pages

**Files:**
- Rewrite: `frontend/src/pages/JdPage.vue`
- Create: `frontend/src/pages/jd/JdTaskPage.vue`
- Create: `frontend/src/components/jd/JdHistoryList.vue`
- Reuse: `frontend/src/components/common/FileUploadZone.vue`
- Reuse: `frontend/src/components/common/ConfirmDialog.vue`

- [ ] **Step 1: Build the input state**

Use a segmented text/image control, one framed analysis tool, recent history, inline validation, lucide icons, and the existing color tokens. Submission must navigate immediately to the returned task route.

- [ ] **Step 2: Build history navigation and custom deletion**

History rows route to reports. Confirm deletion with `ConfirmDialog`, remove the row after a 204 response, and never call `window.confirm`.

- [ ] **Step 3: Build the recoverable task page**

Map backend stages into the four approved user-facing steps. Keep AnalysisLayout navigation usable, show a contained failure state with retry, and `router.replace` the report route on completion.

- [ ] **Step 4: Verify build and targeted browser behavior**

Run: `npm run build`

Expected: build succeeds; input and task pages render in light/dark mode without full-screen loading UI.

### Task 7: Build the structured report dashboard

**Files:**
- Create: `frontend/src/pages/jd/JdReportPage.vue`
- Create: `frontend/src/components/jd/JdReportDashboard.vue`
- Create: `frontend/src/components/jd/JdRequirementGroup.vue`

- [ ] **Step 1: Implement report loading and terminal states**

Fetch by route ID. Redirect pending/running records to the task route. Render an inline error for failed or missing reports. Use `ConfirmDialog` for deletion.

- [ ] **Step 2: Implement approved dashboard modules**

Render header metadata, difficulty, four KPI values, grouped requirements, categorical skill weights, implicit expectations, evidence-based risks, interview focus, recommendations, and summary. Do not render a resume match percentage.

- [ ] **Step 3: Add responsive and dark-mode styling**

Use project tokens only. Desktop can use two-column report sections; below 900px switch to one column. Ensure long skills, evidence, and questions wrap rather than overflow.

- [ ] **Step 4: Build and verify**

Run: `npm run build`

Expected: Vite exits 0.

### Task 8: End-to-end verification

**Files:**
- Modify as needed only when a failing verification has a reproducible test.

- [ ] **Step 1: Run backend regression tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_jd_analysis.py tests/test_db_models.py tests/test_analysis_pipeline.py tests/test_openai_compatible.py tests/test_model_routing.py -q`

Expected: zero failures.

- [ ] **Step 2: Run the frontend production build**

Run: `npm run build`

Expected: Vite exits 0.

- [ ] **Step 3: Verify in the browser**

Test desktop and mobile widths in light and dark mode:

- submit a text JD and an image JD;
- leave the task page and return;
- refresh the task page and recover;
- confirm automatic report navigation;
- open old history;
- delete through the custom dialog;
- confirm no blank pages, overlaps, horizontal overflow, console errors, or full-screen blocking overlay.

- [ ] **Step 4: Check API and logs**

Confirm `GET /api/jd/analyses/{id}` returns persisted terminal state and that Langfuse receives one structured LLM generation per completed task.
