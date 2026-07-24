"""Tests for analysis pipeline: JSON parsing, caching, state machine."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from storage.db.models import Base, RepoAnalysis


@pytest.fixture
async def db() -> AsyncSession:
    """In-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# --- 7.1/7.2: JSON fence stripping + retry ---


class TestJsonParsing:
    """Test JSON parsing with fence stripping and retry."""

    def test_parse_clean_json(self) -> None:
        """Clean JSON parses directly."""
        from api.github_analysis import parse_analysis_json

        data = parse_analysis_json('{"overview": "test"}')
        assert data == {"overview": "test"}

    def test_parse_json_with_fences(self) -> None:
        """JSON wrapped in ```json fences is stripped and parsed."""
        from api.github_analysis import parse_analysis_json

        raw = '```json\n{"overview": "test"}\n```'
        data = parse_analysis_json(raw)
        assert data == {"overview": "test"}

    def test_parse_json_with_extra_text(self) -> None:
        """JSON with surrounding text: extract the JSON object."""
        from api.github_analysis import parse_analysis_json

        raw = 'Here is the analysis:\n```json\n{"overview": "test"}\n```\nDone.'
        data = parse_analysis_json(raw)
        assert data is not None
        assert data["overview"] == "test"

    def test_parse_invalid_json_returns_none(self) -> None:
        """Invalid JSON returns None."""
        from api.github_analysis import parse_analysis_json

        data = parse_analysis_json("not json at all")
        assert data is None


class TestGithubUrlNormalization:
    """Test GitHub repository URL normalization before analysis starts."""

    @pytest.mark.parametrize(
        ("raw", "normalized", "owner", "repo"),
        [
            (
                "github.com/openai/codex",
                "https://github.com/openai/codex",
                "openai",
                "codex",
            ),
            (
                "https://github.com/openai/codex.git",
                "https://github.com/openai/codex",
                "openai",
                "codex",
            ),
            (
                "https://github.com/openai/codex/tree/main/packages/app?tab=readme",
                "https://github.com/openai/codex",
                "openai",
                "codex",
            ),
            (
                "git@github.com:openai/codex.git",
                "https://github.com/openai/codex",
                "openai",
                "codex",
            ),
            (
                "[openai/codex.git](https://github.com/openai/codex.git)",
                "https://github.com/openai/codex",
                "openai",
                "codex",
            ),
        ],
    )
    def test_normalize_github_repo_url(self, raw, normalized, owner, repo) -> None:
        """Common GitHub link variants resolve to canonical cloneable repo URL."""
        from api.github_analysis import normalize_github_repo_url

        parsed = normalize_github_repo_url(raw)

        assert parsed.url == normalized
        assert parsed.owner == owner
        assert parsed.repo == repo

    @pytest.mark.parametrize(
        "raw",
        [
            "https://gitlab.com/openai/codex",
            "https://github.com/openai",
            "not a url",
        ],
    )
    def test_normalize_github_repo_url_rejects_invalid_url(self, raw) -> None:
        """Invalid or unsupported URLs are rejected with a user-facing 400."""
        from api.github_analysis import normalize_github_repo_url

        with pytest.raises(ValueError):
            normalize_github_repo_url(raw)


# --- 7.3: Caching tests ---


class TestAnalysisCaching:
    """Test that done analyses are cached and not re-run."""

    async def test_cache_hit_returns_immediately(self, db: AsyncSession) -> None:
        """Same URL with status=done → return cached result, no re-analysis."""
        from api.github_analysis import check_analysis_cache

        result_data = {"overview": "cached analysis"}
        analysis = RepoAnalysis(
            id="ra-cache-1",
            url="https://github.com/owner/repo",
            owner="owner",
            repo="repo",
            status="done",
            result_json=json.dumps(result_data),
        )
        db.add(analysis)
        await db.commit()

        cached = await check_analysis_cache(db, "https://github.com/owner/repo")
        assert cached is not None
        assert cached["overview"] == "cached analysis"

    async def test_cache_miss_returns_none(self, db: AsyncSession) -> None:
        """No existing analysis → returns None."""
        from api.github_analysis import check_analysis_cache

        cached = await check_analysis_cache(db, "https://github.com/owner/missing")
        assert cached is None

    async def test_pending_returns_none(self, db: AsyncSession) -> None:
        """Pending analysis → returns None (not cached yet)."""
        from api.github_analysis import check_analysis_cache

        analysis = RepoAnalysis(
            id="ra-cache-2",
            url="https://github.com/owner/repo",
            owner="owner",
            repo="repo",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        cached = await check_analysis_cache(db, "https://github.com/owner/repo")
        assert cached is None

    async def test_error_payload_is_not_cache_hit(self, db: AsyncSession) -> None:
        """A done row containing an error payload must not block re-analysis."""
        from api.github_analysis import check_analysis_cache

        analysis = RepoAnalysis(
            id="ra-cache-error",
            url="https://github.com/owner/repo",
            owner="owner",
            repo="repo",
            status="done",
            result_json=json.dumps({"error": "clone timeout"}),
        )
        db.add(analysis)
        await db.commit()

        cached = await check_analysis_cache(db, "https://github.com/owner/repo")

        assert cached is None


class TestAnalysisSubmissionDedup:
    """Test GitHub analysis submission de-duplicates running work."""

    async def test_running_record_with_memory_task_is_reused(
        self, db: AsyncSession
    ) -> None:
        """A live in-memory task for the same URL is returned without starting another run."""
        from api.github_analysis import NormalizedGithubRepo, prepare_analysis_submission
        from service.task_service import task_service

        analysis = RepoAnalysis(
            id="ra-dedup-live",
            url="https://github.com/o/live",
            owner="o",
            repo="live",
            status="running",
            stage="analyzing",
            progress=0.42,
        )
        db.add(analysis)
        await db.commit()
        task_service.create_task(task_id=analysis.id)
        await task_service.update_progress(
            analysis.id,
            0.42,
            "Analyzing",
            data={"stage": "analyzing"},
        )

        decision = await prepare_analysis_submission(
            db,
            NormalizedGithubRepo(
                url=analysis.url,
                owner=analysis.owner,
                repo=analysis.repo,
            ),
        )

        assert decision.analysis_id == analysis.id
        assert decision.should_start_task is False
        assert decision.reused_task is True
        assert decision.status == "running"
        assert decision.stage == "analyzing"
        assert decision.progress == 0.42

    async def test_running_record_without_memory_task_is_reclaimed(
        self, db: AsyncSession
    ) -> None:
        """A DB-running task lost by reload is re-registered and should be restarted."""
        from api.github_analysis import NormalizedGithubRepo, prepare_analysis_submission
        from service.task_service import task_service

        analysis = RepoAnalysis(
            id="ra-dedup-stale",
            url="https://github.com/o/stale",
            owner="o",
            repo="stale",
            status="running",
            stage="waiting",
            progress=0.0,
        )
        db.add(analysis)
        await db.commit()
        assert task_service.get_task(analysis.id) is None

        decision = await prepare_analysis_submission(
            db,
            NormalizedGithubRepo(
                url=analysis.url,
                owner=analysis.owner,
                repo=analysis.repo,
            ),
        )

        assert decision.analysis_id == analysis.id
        assert decision.should_start_task is True
        assert decision.reused_task is False
        assert task_service.get_task(analysis.id) is not None

    def test_pending_analysis_returns_status_payload(self) -> None:
        """Pending/running analyses have a frontend-safe status payload."""
        from api.github_analysis import analysis_status_payload

        analysis = RepoAnalysis(
            id="ra-pending-payload",
            url="https://github.com/o/pending",
            owner="o",
            repo="pending",
            status="running",
            stage="cloning",
            progress=0.2,
        )

        payload = analysis_status_payload(analysis)

        assert payload["id"] == "ra-pending-payload"
        assert payload["status"] == "running"
        assert payload["stage"] == "cloning"
        assert payload["progress"] == 0.2
        assert payload["url"] == "https://github.com/o/pending"

    async def test_valid_saved_payload_recovers_failed_terminal_state(
        self, db: AsyncSession
    ) -> None:
        """A report saved before a late state-machine failure is reused without rerunning."""
        from api.github_analysis import NormalizedGithubRepo, prepare_analysis_submission

        analysis = RepoAnalysis(
            id="ra-recover-saved",
            url="https://github.com/o/recover",
            owner="o",
            repo="recover",
            status="failed",
            stage="failed",
            progress=0.0,
            error="Agent produced unparseable output",
            result_json=json.dumps({"description": "valid saved report"}),
        )
        db.add(analysis)
        await db.commit()

        decision = await prepare_analysis_submission(
            db,
            NormalizedGithubRepo(
                url=analysis.url,
                owner=analysis.owner,
                repo=analysis.repo,
            ),
        )

        assert decision.status == "done"
        assert decision.cached is True
        assert decision.should_start_task is False
        await db.refresh(analysis)
        assert analysis.status == "done"
        assert analysis.stage == "completed"
        assert analysis.progress == 1.0
        assert analysis.error is None


# --- 7.4: State machine test ---


class TestAnalysisStateMachine:
    """Test analysis status transitions."""

    async def test_pending_to_done(self, db: AsyncSession) -> None:
        """Analysis goes from pending → running → done with result."""
        from api.github_analysis import complete_analysis, create_analysis_record

        analysis_id = await create_analysis_record(
            db, "https://github.com/o/r", "o", "r"
        )

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "pending"

        await complete_analysis(db, analysis_id, {"overview": "done"})

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "done"
        assert json.loads(row.result_json) == {"overview": "done"}

    async def test_update_analysis_progress_persists_stage(
        self, db: AsyncSession
    ) -> None:
        """Analysis progress is persisted so reload can recover task stage."""
        from api.github_analysis import create_analysis_record, update_analysis_progress

        analysis_id = await create_analysis_record(
            db, "https://github.com/o/progress", "o", "progress"
        )

        await update_analysis_progress(db, analysis_id, "indexing", 0.35)

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "running"
        assert row.stage == "indexing"
        assert row.progress == 0.35

    async def test_progress_update_does_not_overwrite_completed_analysis(
        self, db: AsyncSession
    ) -> None:
        """Late agent progress events must not move a saved result back to running."""
        from api.github_analysis import complete_analysis, update_analysis_progress

        analysis = RepoAnalysis(
            id="ra-terminal-progress",
            url="https://github.com/o/terminal",
            owner="o",
            repo="terminal",
            status="running",
        )
        db.add(analysis)
        await db.commit()
        await complete_analysis(db, analysis.id, {"description": "saved"})

        await update_analysis_progress(db, analysis.id, "saving", 0.95)

        result = await db.execute(
            select(RepoAnalysis).where(RepoAnalysis.id == analysis.id)
        )
        row = result.scalar_one()
        assert row.status == "done"
        assert row.stage == "completed"
        assert row.progress == 1.0

    async def test_failed_analysis(self, db: AsyncSession) -> None:
        """Analysis with error → status=failed + error message."""
        from api.github_analysis import create_analysis_record, fail_analysis

        analysis_id = await create_analysis_record(
            db, "https://github.com/o/private", "o", "private"
        )
        await fail_analysis(db, analysis_id, "Repository is private")

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "failed"
        assert row.error == "Repository is private"

    async def test_complete_analysis_with_error_payload_marks_failed(
        self, db: AsyncSession
    ) -> None:
        """An agent/tool error payload is stored as failed, not as an empty report."""
        from api.github_analysis import complete_analysis, create_analysis_record

        analysis_id = await create_analysis_record(
            db, "https://github.com/o/r", "o", "r"
        )

        await complete_analysis(db, analysis_id, {"error": "clone timeout"})

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "failed"
        assert row.error == "clone timeout"

    async def test_finalize_prefers_saved_result_over_markdown(self, db: AsyncSession) -> None:
        """When save_repo_analysis already saved JSON, markdown final text must not fail."""
        from api.github_analysis import (
            complete_analysis,
            create_analysis_record,
            finalize_analysis_run,
        )
        from service.task_service import task_service

        analysis_id = await create_analysis_record(
            db, "https://github.com/o/r", "o", "r"
        )
        saved_data = {"description": "saved by tool", "highlights": []}
        await complete_analysis(db, analysis_id, saved_data)

        task_service.create_task(task_id=analysis_id)
        await finalize_analysis_run(
            db,
            analysis_id,
            "# Repo Report\n\nMarkdown summary after save_repo_analysis.",
        )

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "done"
        assert json.loads(row.result_json) == saved_data

        task = task_service.get_task(analysis_id)
        assert task is not None
        assert task.status == "completed"
        assert task.result == saved_data

    async def test_finalize_fails_when_no_json_and_not_saved(self, db: AsyncSession) -> None:
        """Unparseable final text with no prior save → failed."""
        from api.github_analysis import create_analysis_record, finalize_analysis_run
        from service.task_service import task_service

        analysis_id = await create_analysis_record(
            db, "https://github.com/o/r", "o", "r"
        )
        task_service.create_task(task_id=analysis_id)
        await finalize_analysis_run(db, analysis_id, "not json")

        result = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == analysis_id))
        row = result.scalar_one()
        assert row.status == "failed"
        assert row.error == "Agent produced unparseable output"


# --- 7.6: Frontend read endpoint test ---


class TestFrontendReadEndpoint:
    """Test GET /api/analysis/{id} returns result_json."""

    async def test_read_completed_analysis(self, db: AsyncSession) -> None:
        """Read completed analysis returns result_json."""
        from api.github_analysis import get_analysis_result

        result_data = {"overview": "test", "highlights": []}
        analysis = RepoAnalysis(
            id="ra-read-1",
            url="https://github.com/o/r",
            owner="o",
            repo="r",
            status="done",
            result_json=json.dumps(result_data),
        )
        db.add(analysis)
        await db.commit()

        result = await get_analysis_result(db, "ra-read-1")
        assert result is not None
        assert result["overview"] == "test"

    async def test_read_pending_analysis(self, db: AsyncSession) -> None:
        """Read pending analysis returns None (not ready)."""
        from api.github_analysis import get_analysis_result

        analysis = RepoAnalysis(
            id="ra-read-2",
            url="https://github.com/o/r",
            owner="o",
            repo="r",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        result = await get_analysis_result(db, "ra-read-2")
        assert result is None

    async def test_read_error_payload_returns_none(self, db: AsyncSession) -> None:
        """A legacy done row with an error payload is not treated as a completed report."""
        from api.github_analysis import get_analysis_result

        analysis = RepoAnalysis(
            id="ra-read-error",
            url="https://github.com/o/r",
            owner="o",
            repo="r",
            status="done",
            result_json=json.dumps({"error": "clone timeout"}),
        )
        db.add(analysis)
        await db.commit()

        result = await get_analysis_result(db, "ra-read-error")

        assert result is None


class TestAnalysisDelete:
    """Test deleting stored GitHub analysis history."""

    async def test_delete_analysis_removes_row(self, db: AsyncSession) -> None:
        """Deleting an existing analysis removes it from SQL history."""
        from api.github_analysis import delete_analysis_record

        analysis = RepoAnalysis(
            id="ra-delete-1",
            url="https://github.com/o/delete-me",
            owner="o",
            repo="delete-me",
            status="done",
            result_json=json.dumps({"description": "old"}),
        )
        db.add(analysis)
        await db.commit()

        deleted = await delete_analysis_record(db, "ra-delete-1")

        assert deleted is True
        result = await db.execute(
            select(RepoAnalysis).where(RepoAnalysis.id == "ra-delete-1")
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_analysis_returns_false_for_missing(self, db: AsyncSession) -> None:
        """Deleting a missing analysis reports false for the endpoint to map to 404."""
        from api.github_analysis import delete_analysis_record

        deleted = await delete_analysis_record(db, "missing-analysis")

        assert deleted is False


class TestTaskProgress:
    """Test task progress state retained for reconnects."""

    async def test_task_service_keeps_latest_progress_and_stage(self) -> None:
        """Task status includes the latest progress payload without waiting for SSE."""
        from service.task_service import task_service

        task_id = "task-progress-latest"
        task_service.create_task(task_id=task_id)

        await task_service.update_progress(
            task_id,
            0.42,
            "Indexing repository",
            data={"stage": "indexing"},
        )

        task = task_service.get_task(task_id)

        assert task is not None
        assert task.status == "running"
        assert task.progress == 0.42
        assert task.message == "Indexing repository"
        assert task.stage == "indexing"


class TestRepoAnalyzerPerformanceGuards:
    """Test repo-analyzer is configured for bounded tool exploration."""

    def test_repo_analyzer_policy_is_bounded(self) -> None:
        """The profile should keep the ReAct loop small enough for fast reports."""
        import yaml
        from pathlib import Path

        profile = yaml.safe_load(
            Path("config/agents/repo-analyzer.yaml").read_text(encoding="utf-8")
        )

        assert profile["policy"]["max_steps"] <= 10
        assert profile["context"]["max_history_tokens"] <= 60_000
        assert profile["context"]["compact_threshold"] <= 50_000
        assert profile["policy"]["tool_timeout"] <= 90

    def test_repo_analyzer_prompt_prefers_repo_context_tree(self) -> None:
        """Prompt text must not tell the model to call list_directory for directoryTree."""
        from pathlib import Path

        prompt = Path("data/prompt/repo_analyzer_system_prompt.md").read_text(
            encoding="utf-8"
        )
        skill = Path("data/skill/repo-analyzer/SKILL.md").read_text(encoding="utf-8")

        assert "project_structure" in prompt
        assert "Use the `directoryTree` from `list_directory`" not in prompt
        assert "Use the `directoryTree` from the `list_directory`" not in skill
