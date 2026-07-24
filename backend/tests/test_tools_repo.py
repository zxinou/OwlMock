"""Tests for GitHub analysis tools: list_directory, read_file, search_code,
save_repo_analysis, clone_repo, query_github_analysis."""

from __future__ import annotations

import asyncio
import json
import importlib
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from storage.db.models import Base, RepoAnalysis
from tool.base import ToolContext

# --- Fixtures ---


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


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    """Create a sample repo directory structure."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')")
    (root / "src" / "utils.py").write_text("def helper(): pass")
    (root / "tests").mkdir()
    (root / "tests" / "test_main.py").write_text("def test_hello(): pass")
    (root / "README.md").write_text("# My Project")
    (root / "pyproject.toml").write_text("[project]\nname = 'test'")
    # Directories that should be pruned
    (root / ".git").mkdir()
    (root / "node_modules").mkdir()
    (root / "__pycache__").mkdir()
    (root / "dist").mkdir()
    return root


@pytest.fixture
def ctx(repo_dir: Path) -> ToolContext:
    """ToolContext with sandbox set to repo_dir."""
    return ToolContext(user_id="test-user", sandbox_root=str(repo_dir))


# --- list_directory tests (3.1) ---


class TestListDirectory:
    """Test list_directory tool."""

    async def test_list_root(self, ctx: ToolContext, repo_dir: Path) -> None:
        """List root directory: returns files and folders, skips pruned dirs."""
        from tool.builtins.list_directory import ListDirectoryArgs, list_directory

        args = ListDirectoryArgs(path=".")
        result = await list_directory(args, ctx)

        assert result.status == "ok"
        names = [item["name"] for item in result.data["entries"]]
        assert "src" in names
        assert "tests" in names
        assert "README.md" in names
        assert "pyproject.toml" in names
        # Pruned directories should not appear
        assert ".git" not in names
        assert "node_modules" not in names
        assert "__pycache__" not in names
        assert "dist" not in names

    async def test_list_subdirectory(self, ctx: ToolContext) -> None:
        """List a subdirectory."""
        from tool.builtins.list_directory import ListDirectoryArgs, list_directory

        args = ListDirectoryArgs(path="src")
        result = await list_directory(args, ctx)

        assert result.status == "ok"
        names = [item["name"] for item in result.data["entries"]]
        assert "main.py" in names
        assert "utils.py" in names

    async def test_list_sandbox_violation(self, ctx: ToolContext) -> None:
        """Path outside sandbox is rejected."""
        from tool.builtins.list_directory import ListDirectoryArgs, list_directory

        args = ListDirectoryArgs(path="../../etc")
        result = await list_directory(args, ctx)

        assert result.status == "err"
        assert result.error["code"] == "path_forbidden"

    async def test_list_returns_directory_tree(self, ctx: ToolContext) -> None:
        """list_directory returns a directoryTree-compatible structure."""
        from tool.builtins.list_directory import ListDirectoryArgs, list_directory

        args = ListDirectoryArgs(path=".", max_depth=2)
        result = await list_directory(args, ctx)

        assert result.status == "ok"
        assert "directoryTree" in result.data
        tree = result.data["directoryTree"]
        assert tree["type"] == "folder"
        assert "children" in tree

    async def test_list_nonexistent_path(self, ctx: ToolContext) -> None:
        """Non-existent path returns error."""
        from tool.builtins.list_directory import ListDirectoryArgs, list_directory

        args = ListDirectoryArgs(path="nonexistent")
        result = await list_directory(args, ctx)

        assert result.status == "err"


# --- read_file tests (3.3) ---


class TestReadFile:
    """Test read_file tool."""

    async def test_read_normal_file(self, ctx: ToolContext) -> None:
        """Read a normal file returns content."""
        from tool.builtins.read_file import ReadFileArgs, read_file

        args = ReadFileArgs(path="README.md")
        result = await read_file(args, ctx)

        assert result.status == "ok"
        assert result.data["content"] == "# My Project"
        assert result.data["path"] == "README.md"

    async def test_read_truncated(self, ctx: ToolContext, repo_dir: Path) -> None:
        """Long file is truncated."""
        from tool.builtins.read_file import ReadFileArgs, read_file

        long_content = "x" * 100_000
        (repo_dir / "huge.py").write_text(long_content)

        args = ReadFileArgs(path="huge.py")
        result = await read_file(args, ctx)

        assert result.status == "ok"
        assert len(result.data["content"]) <= 50_000  # default max
        assert result.data.get("truncated") is True

    async def test_read_sandbox_violation(self, ctx: ToolContext) -> None:
        """Path outside sandbox is rejected."""
        from tool.builtins.read_file import ReadFileArgs, read_file

        args = ReadFileArgs(path="../../etc/passwd")
        result = await read_file(args, ctx)

        assert result.status == "err"
        assert result.error["code"] == "path_forbidden"

    async def test_read_nonexistent(self, ctx: ToolContext) -> None:
        """Non-existent file returns error."""
        from tool.builtins.read_file import ReadFileArgs, read_file

        args = ReadFileArgs(path="nope.txt")
        result = await read_file(args, ctx)

        assert result.status == "err"

    async def test_read_empty_path_defaults_to_readme(self, ctx: ToolContext) -> None:
        """Empty path picks README.md when inside a cloned repo."""
        from tool.builtins.read_file import ReadFileArgs, read_file
        from tool.executor import ToolCall, ToolExecutor

        result = await read_file(ReadFileArgs(), ctx)
        assert result.status == "ok"
        assert result.data["path"] == "README.md"
        assert result.data.get("auto_resolved_path") is True

        meta = read_file._tool_meta
        executor = ToolExecutor()
        batch = await executor.run_parallel(
            [ToolCall(tool_call_id="1", tool_name="read_file", args={})],
            lambda _c: ctx,
            {meta.name: meta},
        )
        assert batch[0].status == "ok"
        assert batch[0].data["path"] == "README.md"


# --- search_code tests (3.5) ---


class TestSearchCode:
    """Test search_code tool."""

    async def test_search_hit(self, ctx: ToolContext) -> None:
        """Search finds matching content."""
        from tool.builtins.search_code import SearchCodeArgs, search_code

        args = SearchCodeArgs(pattern="def helper")
        result = await search_code(args, ctx)

        assert result.status == "ok"
        assert result.data["match_count"] > 0
        matches = result.data["matches"]
        assert any("utils.py" in m["path"] for m in matches)

    async def test_search_no_hit(self, ctx: ToolContext) -> None:
        """Search with no matches returns zero count."""
        from tool.builtins.search_code import SearchCodeArgs, search_code

        args = SearchCodeArgs(pattern="nonexistent_function_xyz")
        result = await search_code(args, ctx)

        assert result.status == "ok"
        assert result.data["match_count"] == 0

    async def test_search_sandbox_violation(self, ctx: ToolContext) -> None:
        """Search outside sandbox is rejected."""
        from tool.builtins.search_code import SearchCodeArgs, search_code

        args = SearchCodeArgs(pattern="root", path="../../etc")
        result = await search_code(args, ctx)

        assert result.status == "err"
        assert result.error["code"] == "path_forbidden"

    async def test_search_skips_pruned_dirs(self, ctx: ToolContext, repo_dir: Path) -> None:
        """Search skips .git, node_modules, etc."""
        from tool.builtins.search_code import SearchCodeArgs, search_code

        # Put a match in .git that should be skipped
        (repo_dir / ".git" / "config").write_text("secret_match_123")

        args = SearchCodeArgs(pattern="secret_match_123")
        result = await search_code(args, ctx)

        assert result.status == "ok"
        assert result.data["match_count"] == 0


# --- save_repo_analysis tests (3.7) ---


class TestSaveRepoAnalysis:
    """Test save_repo_analysis tool."""

    async def test_save_sets_result_json(self, db: AsyncSession) -> None:
        """save_repo_analysis writes result_json and sets status=done."""
        from tool.builtins.save_repo_analysis import SaveRepoAnalysisArgs, save_repo_analysis

        # Create the row first
        analysis = RepoAnalysis(
            id="ra-1", url="https://github.com/o/r", owner="o", repo="r", status="running"
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db

        result_data = {"overview": "test analysis", "highlights": []}
        args = SaveRepoAnalysisArgs(analysis_id="ra-1", result_json=json.dumps(result_data))
        result = await save_repo_analysis(args, ctx)

        assert result.status == "ok"

        # Verify in DB
        row = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == "ra-1"))
        updated = row.scalar_one()
        assert updated.status == "done"
        assert json.loads(updated.result_json) == result_data
        assert updated.analyzed_at is not None

    async def test_save_error_payload_marks_failed(self, db: AsyncSession) -> None:
        """save_repo_analysis rejects error payloads instead of creating empty reports."""
        from tool.builtins.save_repo_analysis import SaveRepoAnalysisArgs, save_repo_analysis

        analysis = RepoAnalysis(
            id="ra-error", url="https://github.com/o/r", owner="o", repo="r", status="running"
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db

        args = SaveRepoAnalysisArgs(
            analysis_id="ra-error",
            result_json=json.dumps({"error": "clone timeout"}),
        )
        result = await save_repo_analysis(args, ctx)

        assert result.status == "err"
        row = await db.execute(select(RepoAnalysis).where(RepoAnalysis.id == "ra-error"))
        updated = row.scalar_one()
        assert updated.status == "failed"
        assert updated.error == "clone timeout"

    async def test_save_nonexistent(self, db: AsyncSession) -> None:
        """Saving to non-existent analysis returns error."""
        from tool.builtins.save_repo_analysis import SaveRepoAnalysisArgs, save_repo_analysis

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db

        args = SaveRepoAnalysisArgs(analysis_id="nope", result_json="{}")
        result = await save_repo_analysis(args, ctx)

        assert result.status == "err"


# --- query_github_analysis tests (3.11) ---


class TestQueryGithubAnalysis:
    """Test query_github_analysis reads from SQL."""

    async def test_query_hit(self, db: AsyncSession) -> None:
        """Query returns cached result from SQL."""
        from tool.builtins.query_github_analysis import (
            QueryGithubAnalysisArgs,
            query_github_analysis,
        )

        result_data = {"overview": "cached"}
        analysis = RepoAnalysis(
            id="ra-2",
            url="https://github.com/o/r",
            owner="o",
            repo="r",
            status="done",
            result_json=json.dumps(result_data),
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db

        args = QueryGithubAnalysisArgs(repo_url="https://github.com/o/r")
        result = await query_github_analysis(args, ctx)

        assert result.status == "ok"
        assert result.data["analysis"] == result_data

    async def test_query_miss(self, db: AsyncSession) -> None:
        """Query returns not_found for missing URL."""
        from tool.builtins.query_github_analysis import (
            QueryGithubAnalysisArgs,
            query_github_analysis,
        )

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db

        args = QueryGithubAnalysisArgs(repo_url="https://github.com/o/missing")
        result = await query_github_analysis(args, ctx)

        assert result.status == "err"
        assert result.error["code"] == "not_found"

    async def test_query_pending_returns_not_ready(self, db: AsyncSession) -> None:
        """Query for pending analysis returns not_ready error."""
        from tool.builtins.query_github_analysis import (
            QueryGithubAnalysisArgs,
            query_github_analysis,
        )

        analysis = RepoAnalysis(
            id="ra-3",
            url="https://github.com/o/r",
            owner="o",
            repo="r",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db

        args = QueryGithubAnalysisArgs(repo_url="https://github.com/o/r")
        result = await query_github_analysis(args, ctx)

        assert result.status == "err"
        assert result.error["code"] == "not_ready"


# --- clone_repo tests (3.9) ---


@pytest.fixture
def local_git_repo(tmp_path: Path) -> Path:
    """Create a small local git repo for clone testing."""
    repo = tmp_path / "source-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    (repo / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(repo),
        check=True,
        capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t.com"},
    )
    return repo


class TestCloneRepo:
    """Test clone_repo tool."""

    @pytest.fixture(autouse=True)
    def clear_github_network_settings(self, monkeypatch) -> None:
        """Keep tests independent from local .env proxy/token settings."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")

        monkeypatch.setattr(clone_module.settings, "GITHUB_TOKEN", "")
        monkeypatch.setattr(clone_module.settings, "GITHUB_HTTP_PROXY", "")
        monkeypatch.setattr(clone_module.settings, "GITHUB_HTTPS_PROXY", "")
        monkeypatch.setattr(clone_module.settings, "HTTP_PROXY", "")
        monkeypatch.setattr(clone_module.settings, "HTTPS_PROXY", "")
        monkeypatch.setattr(clone_module.settings, "GITHUB_PROXY_BASE_URLS", "")
        monkeypatch.setattr(clone_module.settings, "GITHUB_PREFER_MIRROR", False)
        monkeypatch.setattr(clone_module.settings, "GITHUB_FETCH_STRATEGY", "clone_first")

    def test_github_request_uses_token_and_proxy_settings(self, monkeypatch) -> None:
        """GitHub requests and git env use configured auth/proxy values."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")

        monkeypatch.setattr(clone_module.settings, "GITHUB_TOKEN", "ghp-test")
        monkeypatch.setattr(clone_module.settings, "GITHUB_HTTP_PROXY", "http://127.0.0.1:9895")
        monkeypatch.setattr(clone_module.settings, "GITHUB_HTTPS_PROXY", "")
        monkeypatch.setattr(clone_module.settings, "HTTP_PROXY", "")
        monkeypatch.setattr(clone_module.settings, "HTTPS_PROXY", "")

        request = clone_module._github_request("https://api.github.com/repos/o/r")
        env = clone_module._git_proxy_env()

        assert request.headers["Authorization"] == "Bearer ghp-test"
        assert env["HTTP_PROXY"] == "http://127.0.0.1:9895"
        assert env["HTTPS_PROXY"] == "http://127.0.0.1:9895"

    def test_github_mirror_candidates_can_be_preferred(self, monkeypatch) -> None:
        """Mirror/proxy URL rewriting supports common GitHub acceleration services."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")

        monkeypatch.setattr(clone_module.settings, "GITHUB_PROXY_BASE_URLS", "https://mirror.test")
        monkeypatch.setattr(clone_module.settings, "GITHUB_PREFER_MIRROR", True)

        candidates = clone_module._github_candidate_urls(
            "https://github.com/o/r.git"
        )

        assert candidates[0] == "https://mirror.test/https://github.com/o/r.git"
        assert candidates[1] == "https://github.com/o/r.git"

    async def test_clone_local_repo(
        self, local_git_repo: Path, tmp_path: Path, db: AsyncSession
    ) -> None:
        """Clone a local git repo to a repo cache workspace and build an index."""
        from tool.builtins.clone_repo import CloneRepoArgs, clone_repo

        # Create the analysis row
        analysis = RepoAnalysis(
            id="ra-clone-1",
            url=str(local_git_repo),
            owner="test",
            repo="source-repo",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db
        ctx.repo_root = str(tmp_path / "repos")

        args = CloneRepoArgs(analysis_id="ra-clone-1", url=str(local_git_repo))
        result = await clone_repo(args, ctx)

        assert result.status == "ok"
        assert "repo_path" in result.data
        assert result.data["repo_url"] == str(local_git_repo)
        assert result.data["status"] == "ready"
        repo_path = Path(result.data["repo_path"])
        assert repo_path.exists()
        assert (repo_path / "main.py").exists()
        assert repo_path.name == "source"
        assert (repo_path.parent / "repo_index.json").exists()
        assert ctx.current_repo_path == str(repo_path)
        assert ctx.repo_url == str(local_git_repo)

    async def test_clone_reuses_cache_by_url(
        self, local_git_repo: Path, tmp_path: Path, db: AsyncSession
    ) -> None:
        """A second analysis of the same URL reuses the existing workspace."""
        from tool.builtins.clone_repo import CloneRepoArgs, clone_repo

        db.add(
            RepoAnalysis(
                id="ra-cache-a",
                url=str(local_git_repo),
                owner="test",
                repo="source-repo",
                status="pending",
            )
        )
        await db.commit()

        ctx = ToolContext(user_id="test-user", db_session=db, repo_root=str(tmp_path / "repos"))

        first = await clone_repo(CloneRepoArgs(analysis_id="ra-cache-a", url=str(local_git_repo)), ctx)
        second = await clone_repo(CloneRepoArgs(analysis_id="ra-cache-b", url=str(local_git_repo)), ctx)

        assert first.status == "ok"
        assert second.status == "ok"
        assert second.data["source"] == "cache"
        assert second.data["repo_path"] == first.data["repo_path"]

    async def test_cache_hit_with_valid_index_meta_does_not_rebuild_index(
        self, monkeypatch, tmp_path: Path, db: AsyncSession
    ) -> None:
        """Existing source + current repo_meta skips expensive index refresh."""
        import importlib

        clone_module = importlib.import_module("tool.builtins.clone_repo")
        url = "https://github.com/o/indexed"
        workspace, source_dir = clone_module._workspace_paths(str(tmp_path / "repos"), url)
        source_dir.mkdir(parents=True)
        (source_dir / "README.md").write_text("# Indexed", encoding="utf-8")
        (workspace / "repo_index.json").write_text("{}", encoding="utf-8")
        (workspace / "repo_meta.json").write_text(
            json.dumps(
                {
                    "repo_url": url,
                    "source": "git_clone",
                    "file_count": 1,
                    "default_branch": "main",
                    "commit_sha": "abc123",
                    "index_version": clone_module.INDEX_VERSION,
                }
            ),
            encoding="utf-8",
        )

        def fail_rebuild(*args, **kwargs):
            raise AssertionError("cache hit should not rebuild repo_index.json")

        monkeypatch.setattr(clone_module, "write_repo_index", fail_rebuild)

        ctx = ToolContext(
            user_id="test-user",
            db_session=db,
            repo_root=str(tmp_path / "repos"),
        )
        result = await clone_module.clone_repo(
            clone_module.CloneRepoArgs(analysis_id="ra-indexed-cache", url=url),
            ctx,
        )

        assert result.status == "ok"
        assert result.data["source"] == "cache"
        assert result.data["file_count"] == 1

    async def test_archive_first_strategy_skips_git_when_archive_succeeds(
        self, monkeypatch, tmp_path: Path, db: AsyncSession
    ) -> None:
        """archive_first avoids paying the clone timeout before a successful archive."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")
        url = "https://github.com/o/archive-first"
        db.add(
            RepoAnalysis(
                id="ra-archive-first",
                url=url,
                owner="o",
                repo="archive-first",
                status="pending",
            )
        )
        await db.commit()
        calls: list[str] = []

        def fake_archive(_url: str, destination: Path) -> int:
            calls.append("archive")
            destination.mkdir(parents=True)
            (destination / "README.md").write_text("# Archive", encoding="utf-8")
            return 1

        def fail_git(*args, **kwargs):
            calls.append("git")
            raise AssertionError("git clone should not run after archive succeeds")

        monkeypatch.setattr(clone_module.settings, "GITHUB_FETCH_STRATEGY", "archive_first")
        monkeypatch.setattr(clone_module, "_download_github_archive", fake_archive)
        monkeypatch.setattr(clone_module.subprocess, "run", fail_git)

        result = await clone_module.clone_repo(
            clone_module.CloneRepoArgs(analysis_id="ra-archive-first", url=url),
            ToolContext(
                user_id="test-user",
                db_session=db,
                repo_root=str(tmp_path / "repos"),
            ),
        )

        assert result.status == "ok"
        assert result.data["source"] == "github_archive"
        assert calls == ["archive"]

    async def test_concurrent_same_repo_loads_source_once(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """The per-repository lock collapses concurrent cache misses into one clone."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")
        clone_calls = 0

        class EmptyResult:
            def scalar_one_or_none(self):
                return None

        class FakeDb:
            async def execute(self, *_args, **_kwargs):
                return EmptyResult()

            async def commit(self):
                return None

        def fake_run(command, **kwargs):
            nonlocal clone_calls
            if command[1] == "clone":
                clone_calls += 1
                destination = Path(command[-1])
                destination.mkdir(parents=True)
                (destination / "README.md").write_text("# Once", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, b"", b"")
            output = b"main\n" if command[-2:] == ["branch", "--show-current"] else b"abc123\n"
            return subprocess.CompletedProcess(command, 0, output, b"")

        monkeypatch.setattr(clone_module.shutil, "which", lambda _name: "git")
        monkeypatch.setattr(clone_module.subprocess, "run", fake_run)
        url = "https://github.com/o/concurrent"
        repo_root = str(tmp_path / "repos")

        first, second = await asyncio.gather(
            clone_module.clone_repo(
                clone_module.CloneRepoArgs(analysis_id="first", url=url),
                ToolContext(user_id="test", db_session=FakeDb(), repo_root=repo_root),
            ),
            clone_module.clone_repo(
                clone_module.CloneRepoArgs(analysis_id="second", url=url),
                ToolContext(user_id="test", db_session=FakeDb(), repo_root=repo_root),
            ),
        )

        assert first.status == "ok"
        assert second.status == "ok"
        assert {first.data["source"], second.data["source"]} == {"git_clone", "cache"}
        assert clone_calls == 1

    def test_default_repo_root_is_outside_backend_reload_tree(self) -> None:
        """Default repository cache is outside the backend directory watched by reload."""
        from config.settings import settings

        backend_root = Path(__file__).resolve().parents[1]
        repo_root = (backend_root / settings.REPO_ROOT).resolve()

        assert not repo_root.is_relative_to(backend_root)

    async def test_read_repo_context_returns_generated_index(
        self, local_git_repo: Path, tmp_path: Path, db: AsyncSession
    ) -> None:
        """read_repo_context exposes the generated Repository Context."""
        from tool.builtins.clone_repo import CloneRepoArgs, clone_repo
        from tool.builtins.read_repo_context import ReadRepoContextArgs, read_repo_context

        analysis = RepoAnalysis(
            id="ra-context",
            url=str(local_git_repo),
            owner="test",
            repo="source-repo",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user", db_session=db, repo_root=str(tmp_path / "repos"))
        clone_result = await clone_repo(CloneRepoArgs(analysis_id="ra-context", url=str(local_git_repo)), ctx)

        assert clone_result.status == "ok"
        context_result = await read_repo_context(ReadRepoContextArgs(), ctx)

        assert context_result.status == "ok"
        assert context_result.data["repo_path"] == clone_result.data["repo_path"]
        assert context_result.data["repo_url"] == str(local_git_repo)
        assert "main.py" in context_result.data["important_files"]

    async def test_clone_invalid_url(self, db: AsyncSession, tmp_path: Path) -> None:
        """Clone with invalid URL returns error."""
        from tool.builtins.clone_repo import CloneRepoArgs, clone_repo

        analysis = RepoAnalysis(
            id="ra-clone-2",
            url="https://github.com/nonexistent/repo-xyz",
            owner="nonexistent",
            repo="repo-xyz",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db
        ctx.repo_root = str(tmp_path / "repos")

        args = CloneRepoArgs(analysis_id="ra-clone-2", url="https://github.com/nonexistent/repo-xyz")
        result = await clone_repo(args, ctx)

        assert result.status == "err"
        assert result.error["code"] == "clone_failed"

    async def test_github_archive_fallback_when_clone_times_out(
        self, monkeypatch, db: AsyncSession, tmp_path: Path
    ) -> None:
        """GitHub repos can be fetched from source archive when git clone times out."""
        from tool.builtins.clone_repo import CloneRepoArgs, clone_repo
        clone_module = importlib.import_module("tool.builtins.clone_repo")

        analysis = RepoAnalysis(
            id="ra-archive-1",
            url="https://github.com/o/r",
            owner="o",
            repo="r",
            status="pending",
        )
        db.add(analysis)
        await db.commit()

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git clone", timeout=1)

        zip_bytes = BytesIO()
        with zipfile.ZipFile(zip_bytes, "w") as archive:
            archive.writestr("r-main/README.md", "# Repo")
            archive.writestr("r-main/src/app.py", "print('hello')")
        zip_payload = zip_bytes.getvalue()

        class FakeResponse:
            def __init__(self, payload: bytes):
                self._payload = payload
                self._pos = 0

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, size: int = -1):
                if size == -1:
                    return self._payload
                chunk = self._payload[self._pos:self._pos + size]
                self._pos += len(chunk)
                return chunk

        def fake_urlopen(request, timeout=0):
            url = request.full_url if hasattr(request, "full_url") else request
            if "/repos/o/r" in url:
                return FakeResponse(b'{"default_branch":"main"}')
            if "codeload.github.com/o/r/zip/refs/heads/main" in url:
                return FakeResponse(zip_payload)
            raise AssertionError(f"unexpected URL: {url}")

        monkeypatch.setattr(clone_module.subprocess, "run", fake_run)
        monkeypatch.setattr(clone_module.urllib.request, "urlopen", fake_urlopen)

        ctx = ToolContext(user_id="test-user")
        ctx.db_session = db
        ctx.repo_root = str(tmp_path / "repos")

        result = await clone_repo(
            CloneRepoArgs(
                analysis_id="ra-archive-1",
                url="https://github.com/o/r",
            ),
            ctx,
        )

        assert result.status == "ok"
        assert result.data["source"] == "github_archive"
        assert result.data["status"] == "ready"
        assert result.data["repo_url"] == "https://github.com/o/r"
        repo_path = Path(result.data["repo_path"])
        assert (repo_path / "README.md").exists()
        assert (repo_path / "src" / "app.py").exists()

    async def test_github_archive_uses_mirror_after_direct_failure(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """Archive download retries configured mirrors when direct codeload fails."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")

        monkeypatch.setattr(clone_module.settings, "GITHUB_PROXY_BASE_URLS", "https://mirror.test")
        monkeypatch.setattr(clone_module.settings, "GITHUB_PREFER_MIRROR", False)

        zip_bytes = BytesIO()
        with zipfile.ZipFile(zip_bytes, "w") as archive:
            archive.writestr("r-main/README.md", "# Repo")
        zip_payload = zip_bytes.getvalue()
        seen_urls: list[str] = []

        class FakeResponse:
            def __init__(self, payload: bytes):
                self._payload = payload
                self._pos = 0

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, size: int = -1):
                if size == -1:
                    return self._payload
                chunk = self._payload[self._pos:self._pos + size]
                self._pos += len(chunk)
                return chunk

        def fake_urlopen(request, timeout=0):
            url = request.full_url if hasattr(request, "full_url") else request
            seen_urls.append(url)
            if "/repos/o/r" in url:
                return FakeResponse(b'{"default_branch":"main"}')
            if url == "https://codeload.github.com/o/r/zip/refs/heads/main":
                raise TimeoutError("direct codeload is slow")
            if url == "https://mirror.test/https://codeload.github.com/o/r/zip/refs/heads/main":
                return FakeResponse(zip_payload)
            raise AssertionError(f"unexpected URL: {url}")

        monkeypatch.setattr(clone_module.urllib.request, "urlopen", fake_urlopen)

        dest = tmp_path / "archive"
        count = clone_module._download_github_archive("https://github.com/o/r", dest)

        assert count == 1
        assert (dest / "README.md").read_text() == "# Repo"
        assert "https://codeload.github.com/o/r/zip/refs/heads/main" in seen_urls
        assert "https://mirror.test/https://codeload.github.com/o/r/zip/refs/heads/main" in seen_urls

    async def test_github_api_snapshot_fetches_key_files(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """GitHub API snapshot fetches selected key files without cloning."""
        clone_module = importlib.import_module("tool.builtins.clone_repo")

        responses = {
            "https://api.github.com/repos/o/r": b'{"default_branch":"main"}',
            "https://api.github.com/repos/o/r/git/trees/main?recursive=1": json.dumps({
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 10},
                    {"path": "src/app.py", "type": "blob", "size": 14},
                    {"path": "dist/bundle.js", "type": "blob", "size": 12},
                ]
            }).encode("utf-8"),
            "https://raw.githubusercontent.com/o/r/main/README.md": b"# Repo",
            "https://raw.githubusercontent.com/o/r/main/src/app.py": b"print('hello')",
        }

        class FakeResponse:
            def __init__(self, payload: bytes):
                self._payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, size: int = -1):
                return self._payload

        def fake_urlopen(request, timeout=0):
            url = request.full_url if hasattr(request, "full_url") else request
            if url not in responses:
                raise AssertionError(f"unexpected URL: {url}")
            return FakeResponse(responses[url])

        monkeypatch.setattr(clone_module.urllib.request, "urlopen", fake_urlopen)

        dest = tmp_path / "snapshot"
        count = clone_module._download_github_api_snapshot(
            "https://github.com/o/r",
            dest,
        )

        assert count == 2
        assert (dest / "README.md").read_text() == "# Repo"
        assert (dest / "src" / "app.py").read_text() == "print('hello')"
        assert not (dest / "dist" / "bundle.js").exists()
