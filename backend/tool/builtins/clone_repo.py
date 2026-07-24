"""clone_repo tool — shallow clone a git repo with limits."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import logging
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlparse

from pydantic import BaseModel, Field
from sqlalchemy import select

from config.settings import settings
from service.repo_indexer import INDEX_VERSION, write_repo_index
from storage.db.models import RepoAnalysis
from tool.base import ToolContext, ToolResult, tool

logger = logging.getLogger(__name__)

_REPO_LOCKS: dict[str, asyncio.Lock] = {}

CLONE_TIMEOUT = min(settings.CLONE_TIMEOUT, 30)  # seconds
MAX_FILE_COUNT = 10_000
SNAPSHOT_MAX_FILES = 40
SNAPSHOT_MAX_FILE_SIZE = 512 * 1024
SNAPSHOT_MAX_TOTAL_BYTES = 3 * 1024 * 1024
SNAPSHOT_TIMEOUT = 30
SNAPSHOT_FILE_TIMEOUT = 5
SNAPSHOT_DOWNLOAD_TIMEOUT = 45
SNAPSHOT_WORKERS = 8

SNAPSHOT_ALLOWED_EXTENSIONS = {
    ".cfg",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".scss",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".yaml",
    ".yml",
}

SNAPSHOT_ALWAYS_INCLUDE = {
    "dockerfile",
    "makefile",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pyproject.toml",
    "readme.md",
    "requirements.txt",
    "tsconfig.json",
    "vite.config.js",
    "vite.config.ts",
}

SNAPSHOT_PRIORITY_DIRS = (
    "app/",
    "api/",
    "backend/",
    "components/",
    "config/",
    "frontend/",
    "lib/",
    "pages/",
    "server/",
    "src/",
    "tests/",
)

SNAPSHOT_SKIP_PARTS = {
    ".git",
    ".next",
    ".nuxt",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


def _rmtree_onexc(func, path, exc):
    """Handle Windows read-only files during rmtree."""
    if isinstance(exc, PermissionError) and os.name == "nt":
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass  # File locked by git process, skip
    else:
        raise exc


class CloneRepoArgs(BaseModel):
    """Arguments for clone_repo tool."""

    analysis_id: str = Field(
        default="",
        description="The analysis ID (UUID). Use the analysis_id from the current task context.",
    )
    url: str = Field(
        default="",
        description="The GitHub repository URL to clone (e.g. https://github.com/owner/repo).",
    )


def _parse_github_repo_url(url: str) -> tuple[str, str] | None:
    """Return owner/repo for GitHub URLs supported by archive download."""
    value = url.strip()
    if value.startswith("git@github.com:"):
        path = value.removeprefix("git@github.com:")
        parts = path.split("/")
    else:
        if not value.startswith(("http://", "https://")):
            value = f"https://{value}"
        parsed = urlparse(value)
        if parsed.netloc.lower() != "github.com":
            return None
        parts = [part for part in parsed.path.split("/") if part]

    if len(parts) < 2:
        return None
    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        return None
    return owner, repo


def _github_request(url: str) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "OwlMock-RepoAnalyzer",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return urllib.request.Request(
        url,
        headers=headers,
    )


def _github_proxy_handler() -> urllib.request.ProxyHandler | None:
    proxies: dict[str, str] = {}
    if settings.github_http_proxy:
        proxies["http"] = settings.github_http_proxy
    if settings.github_https_proxy:
        proxies["https"] = settings.github_https_proxy
    return urllib.request.ProxyHandler(proxies) if proxies else None


def _urlopen(request: urllib.request.Request, timeout: int):
    proxy_handler = _github_proxy_handler()
    if proxy_handler is None:
        return urllib.request.urlopen(request, timeout=timeout)
    opener = urllib.request.build_opener(proxy_handler)
    return opener.open(request, timeout=timeout)


def _proxied_github_url(url: str, proxy_base_url: str) -> str:
    proxy_base_url = proxy_base_url.strip().rstrip("/")
    if "{url}" in proxy_base_url:
        return proxy_base_url.format(url=url)
    return f"{proxy_base_url}/{url}"


def _github_candidate_urls(url: str) -> list[str]:
    mirrors = [
        _proxied_github_url(url, proxy_base_url)
        for proxy_base_url in settings.github_proxy_base_urls
    ]
    urls = [*mirrors, url] if settings.GITHUB_PREFER_MIRROR else [url, *mirrors]
    return list(dict.fromkeys(urls))


def _open_github_url(url: str, timeout: int, *, use_mirrors: bool = False):
    last_error: Exception | None = None
    urls = _github_candidate_urls(url) if use_mirrors else [url]
    for candidate_url in urls:
        try:
            return _urlopen(_github_request(candidate_url), timeout=timeout)
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"No GitHub URL candidates for {url}")


def _github_https_clone_url(url: str) -> str:
    repo_parts = _parse_github_repo_url(url)
    if repo_parts is None:
        return url
    owner, repo = repo_parts
    return f"https://github.com/{owner}/{repo}.git"


def _git_clone_candidate_urls(url: str) -> list[str]:
    if _parse_github_repo_url(url) is None:
        return [url]
    return _github_candidate_urls(_github_https_clone_url(url))


def _git_proxy_env() -> dict[str, str]:
    env = os.environ.copy()
    if settings.github_http_proxy:
        env["HTTP_PROXY"] = settings.github_http_proxy
        env["http_proxy"] = settings.github_http_proxy
    if settings.github_https_proxy:
        env["HTTPS_PROXY"] = settings.github_https_proxy
        env["https_proxy"] = settings.github_https_proxy
    return env


def _repo_cache_key(url: str) -> str:
    """Create a stable cache key for a repository URL."""
    normalized = url.strip().rstrip("/").lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def _workspace_paths(repo_root: str, url: str) -> tuple[Path, Path]:
    """Return workspace root and source directory for a cached repo."""
    workspace = Path(repo_root).expanduser().resolve() / _repo_cache_key(url)
    return workspace, workspace / "source"


def _repo_lock(url: str) -> asyncio.Lock:
    """Return the process-local lock for a repository cache key."""
    key = _repo_cache_key(url)
    lock = _REPO_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _REPO_LOCKS[key] = lock
    return lock


def _read_repo_meta(workspace: Path) -> dict:
    """Read cache metadata, treating missing or invalid files as empty."""
    try:
        value = json.loads((workspace / "repo_meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_repo_meta(
    workspace: Path,
    *,
    url: str,
    source: str,
    file_count: int,
    default_branch: str = "",
    commit_sha: str = "",
) -> dict:
    """Persist versioned metadata next to the cached source and index."""
    meta = {
        "repo_url": url,
        "source": source,
        "file_count": file_count,
        "default_branch": default_branch,
        "commit_sha": commit_sha,
        "fetched_at": datetime.now(UTC).isoformat(),
        "index_version": INDEX_VERSION,
    }
    (workspace / "repo_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def _git_source_metadata(source_dir: Path) -> tuple[str, str]:
    """Read the current branch and commit without making a network request."""
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(source_dir), *args],
            capture_output=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.decode("utf-8", errors="replace").strip()

    return run("branch", "--show-current"), run("rev-parse", "HEAD")


def _cache_metadata_is_fresh(meta: dict) -> bool:
    """Return true while remote commit validation can be safely skipped."""
    raw = meta.get("fetched_at")
    if not raw:
        return True
    try:
        fetched_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
    except ValueError:
        return True
    return (datetime.now(UTC) - fetched_at).total_seconds() < max(
        0,
        settings.GITHUB_CACHE_TTL_SECONDS,
    )


def _remote_commit_sha(url: str, branch: str) -> str:
    """Fetch the latest GitHub commit when authenticated cache validation is enabled."""
    repo_parts = _parse_github_repo_url(url)
    if repo_parts is None or not settings.GITHUB_TOKEN or not branch:
        return ""
    owner, repo = repo_parts
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{quote(branch, safe='')}"
    with _open_github_url(api_url, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("sha") or "")


def _count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())


def _success_result(
    *,
    source_dir: Path,
    url: str,
    analysis_id: str,
    file_count: int,
    source: str,
) -> ToolResult:
    return ToolResult.ok(
        data={
            "repo_path": str(source_dir),
            "repo_url": url,
            "analysis_id": analysis_id,
            "file_count": file_count,
            "status": "ready",
            "source": source,
        },
        summary=f"Repository ready ({file_count} files, {source})",
    )


def _extract_github_zip(zip_path: Path, dest: Path) -> int:
    """Extract a GitHub source zip while stripping its top-level folder."""
    file_count = 0
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            if len(parts) < 2:
                continue
            relative = Path(*parts[1:])
            target = dest / relative
            target_resolved = target.resolve()
            if dest_resolved not in target_resolved.parents and target_resolved != dest_resolved:
                raise ValueError(f"Unsafe archive path: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, open(target, "wb") as output:
                shutil.copyfileobj(source, output)
            file_count += 1
            if file_count > MAX_FILE_COUNT:
                raise ValueError(
                    f"Repository has more than {MAX_FILE_COUNT} files"
                )
    return file_count


def _download_github_archive(url: str, dest: Path) -> int:
    """Download a GitHub repository source archive into dest."""
    repo_parts = _parse_github_repo_url(url)
    if repo_parts is None:
        raise ValueError("Not a GitHub repository URL")

    owner, repo = repo_parts
    default_branch = "main"
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        with _open_github_url(api_url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            default_branch = data.get("default_branch") or default_branch
    except Exception:
        pass

    branches = list(dict.fromkeys([default_branch, "main", "master"]))
    last_error: Exception | None = None
    dest.parent.mkdir(parents=True, exist_ok=True)

    for branch in branches:
        tmp_name = ""
        try:
            if dest.exists():
                shutil.rmtree(dest, onexc=_rmtree_onexc)
            dest.mkdir(parents=True, exist_ok=True)

            archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".zip",
                dir=str(dest.parent),
            ) as tmp_file:
                tmp_name = tmp_file.name
                with _open_github_url(
                    archive_url,
                    timeout=CLONE_TIMEOUT,
                    use_mirrors=True,
                ) as response:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        tmp_file.write(chunk)

            return _extract_github_zip(Path(tmp_name), dest)
        except Exception as exc:
            last_error = exc
            if dest.exists():
                shutil.rmtree(dest, onexc=_rmtree_onexc)
        finally:
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    raise RuntimeError(f"GitHub archive download failed: {last_error}")


def _is_snapshot_candidate(path: str, size: int) -> bool:
    """Return whether a GitHub tree item should be fetched for analysis."""
    lower = path.lower().replace("\\", "/")
    parts = set(lower.split("/"))
    if parts & SNAPSHOT_SKIP_PARTS:
        return False
    if size > SNAPSHOT_MAX_FILE_SIZE:
        return False

    name = lower.rsplit("/", 1)[-1]
    if name in SNAPSHOT_ALWAYS_INCLUDE:
        return True
    if lower.startswith(SNAPSHOT_PRIORITY_DIRS):
        return Path(lower).suffix in SNAPSHOT_ALLOWED_EXTENSIONS
    return False


def _snapshot_sort_key(item: dict) -> tuple[int, int, str]:
    path = item["path"].lower()
    name = path.rsplit("/", 1)[-1]
    priority = 0 if name in SNAPSHOT_ALWAYS_INCLUDE else 1
    return priority, len(path.split("/")), path


def _download_github_api_snapshot(url: str, dest: Path) -> int:
    """Fetch a lightweight source snapshot via GitHub API and raw file URLs."""
    repo_parts = _parse_github_repo_url(url)
    if repo_parts is None:
        raise ValueError("Not a GitHub repository URL")

    owner, repo = repo_parts
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    with _open_github_url(api_url, timeout=SNAPSHOT_TIMEOUT) as response:
        repo_data = json.loads(response.read().decode("utf-8"))
    branch = repo_data.get("default_branch") or "main"

    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    with _open_github_url(tree_url, timeout=SNAPSHOT_TIMEOUT) as response:
        tree_data = json.loads(response.read().decode("utf-8"))

    candidates = [
        item
        for item in tree_data.get("tree", [])
        if item.get("type") == "blob"
        and _is_snapshot_candidate(item.get("path", ""), int(item.get("size") or 0))
    ]
    candidates.sort(key=_snapshot_sort_key)
    candidates = candidates[:SNAPSHOT_MAX_FILES]
    if not candidates:
        raise RuntimeError("GitHub API snapshot found no analyzable files")

    if dest.exists():
        shutil.rmtree(dest, onexc=_rmtree_onexc)
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    def fetch_candidate(item: dict) -> tuple[str, bytes] | None:
        path = item["path"]
        encoded_path = quote(path, safe="/")
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"
        try:
            with _open_github_url(
                raw_url,
                timeout=SNAPSHOT_FILE_TIMEOUT,
                use_mirrors=True,
            ) as response:
                content = response.read(SNAPSHOT_MAX_FILE_SIZE + 1)
        except Exception:
            return None
        if len(content) > SNAPSHOT_MAX_FILE_SIZE:
            return None
        return path, content

    total_bytes = 0
    fetched = 0
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=SNAPSHOT_WORKERS)
    futures = [executor.submit(fetch_candidate, item) for item in candidates]
    try:
        for future in concurrent.futures.as_completed(
            futures,
            timeout=SNAPSHOT_DOWNLOAD_TIMEOUT,
        ):
            fetched_item = future.result()
            if fetched_item is None:
                continue
            path, content = fetched_item
            if total_bytes + len(content) > SNAPSHOT_MAX_TOTAL_BYTES:
                break
            target = dest / path
            target_resolved = target.resolve()
            if dest_resolved not in target_resolved.parents and target_resolved != dest_resolved:
                raise ValueError(f"Unsafe GitHub path: {path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            total_bytes += len(content)
            fetched += 1
    except concurrent.futures.TimeoutError:
        pass
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    if fetched == 0:
        raise RuntimeError("GitHub API snapshot downloaded no files")
    return fetched


@tool
async def clone_repo(args: CloneRepoArgs, ctx: ToolContext) -> ToolResult:
    """Load a repository into its shared cache workspace."""
    import traceback
    try:
        url = args.url or ctx.repo_url or "missing-repository-url"
        async with _repo_lock(url):
            return await _clone_repo_impl(args, ctx)
    except Exception as e:
        tb = traceback.format_exc()
        return ToolResult.err(
            code="clone_error",
            message=f"clone_repo failed: {type(e).__name__}: {str(e) or repr(e)}\n{tb}",
            summary=f"Clone error: {type(e).__name__}",
        )


async def _clone_repo_impl(args: CloneRepoArgs, ctx: ToolContext) -> ToolResult:
    """
    Clone repository with timing logs.

    The first two fetch methods follow GITHUB_FETCH_STRATEGY, with the
    GitHub API snapshot kept as the final fallback.
    """
    total_start = time.time()
    url = args.url or ctx.repo_url
    analysis_id = args.analysis_id

    if not analysis_id and ctx.session_id:
        analysis_id = ctx.session_id.removeprefix("analysis-")

    if not url:
        return ToolResult.err(
            code="missing_arg",
            message="url is required",
            summary="Missing repo URL",
        )

    if not analysis_id:
        return ToolResult.err(
            code="missing_arg",
            message="analysis_id is required",
            summary="Missing analysis_id",
        )

    if ctx.db_session is None:
        return ToolResult.err(
            code="no_db_session",
            message="No database session in context",
            summary="No DB session",
        )

    db = ctx.db_session

    workspace, source_dir = _workspace_paths(ctx.repo_root, url)
    workspace.mkdir(parents=True, exist_ok=True)

    if source_dir.exists() and source_dir.is_dir():
        existing_files = _count_files(source_dir)
        if existing_files > 0:
            logger.info("[repo-loader] cache hit files=%s path=%s", existing_files, source_dir)
            meta = _read_repo_meta(workspace)
            index_is_current = (
                (workspace / "repo_index.json").is_file()
                and meta.get("repo_url") == url
                and meta.get("index_version") == INDEX_VERSION
            )

            remote_changed = False
            if index_is_current and not _cache_metadata_is_fresh(meta):
                try:
                    remote_sha = await asyncio.to_thread(
                        _remote_commit_sha,
                        url,
                        str(meta.get("default_branch") or ""),
                    )
                    remote_changed = bool(
                        remote_sha
                        and meta.get("commit_sha")
                        and remote_sha != meta.get("commit_sha")
                    )
                except Exception as exc:
                    logger.warning("[repo-loader] cache validation failed; using cache: %s", exc)

            if not remote_changed:
                if not index_is_current:
                    index_start = time.time()
                    logger.info("[repo-loader] index refresh start %s", source_dir)
                    try:
                        await asyncio.to_thread(write_repo_index, source_dir, url)
                    except Exception as exc:
                        logger.warning("[repo-loader] cache index refresh failed %s", exc)
                        return ToolResult.err(
                            code="index_error",
                            message=f"Cached repository index could not be rebuilt: {exc}",
                            summary="Repository index failed",
                        )
                    else:
                        _write_repo_meta(
                            workspace,
                            url=url,
                            source=str(meta.get("source") or "cache"),
                            file_count=existing_files,
                            default_branch=str(meta.get("default_branch") or ""),
                            commit_sha=str(meta.get("commit_sha") or ""),
                        )
                        logger.info(
                            "[repo-loader] index refresh end %.2fs",
                            time.time() - index_start,
                        )
                ctx.current_repo_path = str(source_dir)
                ctx.repo_url = url
                return _success_result(
                    source_dir=source_dir,
                    url=url,
                    analysis_id=analysis_id,
                    file_count=existing_files,
                    source="cache",
                )

            logger.info("[repo-loader] remote commit changed; refreshing %s", url)
            shutil.rmtree(source_dir, onexc=_rmtree_onexc)

    result = await db.execute(
        select(RepoAnalysis)
        .where(
            RepoAnalysis.id == analysis_id
        )
    )

    analysis = result.scalar_one_or_none()

    if analysis:
        analysis.status = "running"
        analysis.stage = "cloning"
        analysis.progress = 0.1
        await db.commit()

    last_error = ""

    async def finalize_ready(file_count: int, source: str) -> ToolResult:
        index_start = time.time()
        logger.info("[repo-loader] index start %s", source_dir)
        if analysis:
            analysis.stage = "indexing"
            analysis.progress = 0.35
            await db.commit()
        try:
            await asyncio.to_thread(write_repo_index, source_dir, url)
        except Exception as exc:
            logger.exception("[repo-loader] index failed")
            return ToolResult.err(
                code="index_error",
                message=f"Repository downloaded but indexing failed: {exc}",
                summary="Repository index failed",
            )
        logger.info("[repo-loader] index end %.2fs", time.time() - index_start)

        default_branch = ""
        commit_sha = ""
        if source == "git_clone":
            default_branch, commit_sha = await asyncio.to_thread(
                _git_source_metadata,
                source_dir,
            )
        _write_repo_meta(
            workspace,
            url=url,
            source=source,
            file_count=file_count,
            default_branch=default_branch,
            commit_sha=commit_sha,
        )

        if analysis:
            analysis.repo_cache_key = _repo_cache_key(url)
            analysis.source_commit = commit_sha or None
            await db.commit()

        ctx.current_repo_path = str(source_dir)
        ctx.repo_url = url
        logger.info(
            "[repo-loader] total %.2fs files=%s source=%s",
            time.time() - total_start,
            file_count,
            source,
        )
        return _success_result(
            source_dir=source_dir,
            url=url,
            analysis_id=analysis_id,
            file_count=file_count,
            source=source,
        )

    async def try_git_clone() -> ToolResult | None:
        nonlocal last_error
        if not shutil.which("git"):
            last_error = "git is not installed"
            return None

        git_env = _git_proxy_env()
        loop = asyncio.get_running_loop()
        for clone_url in _git_clone_candidate_urls(url):
            if source_dir.exists():
                shutil.rmtree(source_dir, onexc=_rmtree_onexc)
            git_start = time.time()
            logger.info("[repo-loader] clone start %s", clone_url)
            try:
                clone_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda clone_url=clone_url: subprocess.run(
                            [
                                "git",
                                "clone",
                                "--depth",
                                "1",
                                clone_url,
                                str(source_dir),
                            ],
                            capture_output=True,
                            timeout=CLONE_TIMEOUT,
                            env=git_env,
                        ),
                    ),
                    timeout=CLONE_TIMEOUT + 5,
                )
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "[repo-loader] clone failed %.2fs %s",
                    time.time() - git_start,
                    exc,
                )
                if source_dir.exists():
                    shutil.rmtree(source_dir, onexc=_rmtree_onexc)
                continue

            logger.info("[repo-loader] clone end %.2fs", time.time() - git_start)
            if clone_result.returncode == 0:
                return await finalize_ready(_count_files(source_dir), "git_clone")

            last_error = clone_result.stderr.decode("utf-8", errors="replace")
            logger.warning("[repo-loader] clone failed %s", last_error)
            if source_dir.exists():
                shutil.rmtree(source_dir, onexc=_rmtree_onexc)
        return None

    async def try_archive() -> ToolResult | None:
        nonlocal last_error
        if _parse_github_repo_url(url) is None:
            return None
        try:
            archive_start = time.time()
            logger.info("[repo-loader] archive start %s", url)
            file_count = await asyncio.to_thread(
                _download_github_archive,
                url,
                source_dir,
            )
            logger.info(
                "[repo-loader] archive end %.2fs files=%s",
                time.time() - archive_start,
                file_count,
            )
            return await finalize_ready(file_count, "github_archive")
        except Exception as exc:
            last_error = str(exc)
            logger.warning("[repo-loader] archive failed %s", exc)
            if source_dir.exists():
                shutil.rmtree(source_dir, onexc=_rmtree_onexc)
            return None

    async def try_snapshot() -> ToolResult | None:
        nonlocal last_error
        if _parse_github_repo_url(url) is None:
            return None
        try:
            snapshot_start = time.time()
            logger.info("[repo-loader] snapshot start %s", url)
            file_count = await asyncio.to_thread(
                _download_github_api_snapshot,
                url,
                source_dir,
            )
            logger.info(
                "[repo-loader] snapshot end %.2fs files=%s",
                time.time() - snapshot_start,
                file_count,
            )
            return await finalize_ready(file_count, "github_snapshot")
        except Exception as exc:
            last_error = str(exc)
            logger.warning("[repo-loader] snapshot failed %s", exc)
            if source_dir.exists():
                shutil.rmtree(source_dir, onexc=_rmtree_onexc)
            return None

    strategy = settings.GITHUB_FETCH_STRATEGY.strip().lower()
    if strategy not in {"clone_first", "archive_first"}:
        logger.warning(
            "[repo-loader] unknown fetch strategy %r; using clone_first",
            settings.GITHUB_FETCH_STRATEGY,
        )
        strategy = "clone_first"

    attempts = (
        [try_archive, try_git_clone, try_snapshot]
        if strategy == "archive_first"
        else [try_git_clone, try_archive, try_snapshot]
    )
    for attempt in attempts:
        loaded = await attempt()
        if loaded is not None:
            return loaded

    return ToolResult.err(
        code="clone_failed",
        message=last_error or "Repository loading failed",
        summary="Repository loading failed",
    )
