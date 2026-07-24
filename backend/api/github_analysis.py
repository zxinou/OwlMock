"""GitHub analysis API — async pipeline with caching and result storage."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import EventType
from service.task_service import task_service
from storage.db.engine import async_session_factory
from storage.db.models import RepoAnalysis

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request to start GitHub analysis."""
    repo_url: str
    session_id: str | None = None


class AnalysisResponse(BaseModel):
    """Response for analysis submission."""
    task_id: str
    status: str
    stage: str | None = None
    progress: float | None = None
    cached: bool = False
    reusedTask: bool = False


@dataclass(frozen=True)
class NormalizedGithubRepo:
    """Canonical GitHub repository URL parts."""

    url: str
    owner: str
    repo: str


@dataclass(frozen=True)
class AnalysisSubmissionDecision:
    """Result of deciding whether a repository analysis needs new work."""

    analysis_id: str
    status: str
    stage: str
    progress: float
    should_start_task: bool
    reused_task: bool = False
    cached: bool = False


_submission_locks: dict[str, asyncio.Lock] = {}


def _submission_lock(repo_url: str) -> asyncio.Lock:
    """Return the process-local lock that serializes submissions per repository."""
    lock = _submission_locks.get(repo_url)
    if lock is None:
        lock = asyncio.Lock()
        _submission_locks[repo_url] = lock
    return lock


# --- JSON parsing helpers ---


def parse_analysis_json(raw: str) -> dict | None:
    """Parse analysis JSON with fence stripping and retry.

    Handles:
    - Clean JSON
    - JSON wrapped in ```json fences
    - JSON surrounded by extra text
    """
    # Try direct parse first
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strip ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # Try to find JSON object in the text
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def get_analysis_payload_error(result: dict | None) -> str | None:
    """Return the embedded analysis error message if this payload is an error."""
    if not isinstance(result, dict):
        return None
    error = result.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()
    return None


def normalize_github_repo_url(raw_url: str) -> NormalizedGithubRepo:
    """Normalize common GitHub URL variants to https://github.com/owner/repo."""
    value = raw_url.strip()
    markdown_match = re.search(r"\((https://github\.com/[^)\s]+)\)", value)
    if markdown_match:
        value = markdown_match.group(1)

    ssh_match = re.fullmatch(r"git@github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?", value)
    if ssh_match:
        owner, repo = ssh_match.groups()
        return NormalizedGithubRepo(
            url=f"https://github.com/{owner}/{repo}",
            owner=owner,
            repo=repo,
        )

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        raise ValueError("Only GitHub repository URLs are supported")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub repository URL must include owner and repository")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo or any(ch.isspace() for ch in f"{owner}{repo}"):
        raise ValueError("Invalid GitHub repository URL")

    return NormalizedGithubRepo(
        url=f"https://github.com/{owner}/{repo}",
        owner=owner,
        repo=repo,
    )


# --- Database helpers ---


async def check_analysis_cache(db: AsyncSession, url: str) -> dict | None:
    """Check if a completed analysis exists for this URL. Returns result_json or None."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.url == url, RepoAnalysis.status == "done")
    )
    analysis = result.scalar_one_or_none()
    if analysis and analysis.result_json:
        try:
            data = json.loads(analysis.result_json)
        except json.JSONDecodeError:
            return None
        if get_analysis_payload_error(data):
            return None
        return data
    return None


async def create_analysis_record(
    db: AsyncSession, url: str, owner: str, repo: str
) -> str:
    """Create a pending analysis record. Returns the analysis ID.

    If a record with the same URL already exists, return its ID.
    """
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.url == url)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing_data = parse_analysis_json(existing.result_json) if existing.result_json else None
        if existing.status == "done" and get_analysis_payload_error(existing_data):
            existing.status = "pending"
            existing.stage = "waiting"
            existing.progress = 0.0
            existing.error = None
            existing.result_json = None
            existing.analyzed_at = None
            await db.commit()
        return existing.id

    analysis_id = str(uuid.uuid4())
    analysis = RepoAnalysis(
        id=analysis_id,
        url=url,
        owner=owner,
        repo=repo,
        status="pending",
        stage="waiting",
        progress=0.0,
    )
    db.add(analysis)
    await db.commit()
    return analysis_id


async def prepare_analysis_submission(
    db: AsyncSession,
    repo: NormalizedGithubRepo,
) -> AnalysisSubmissionDecision:
    """Reuse live work, reclaim stale work, or create a new analysis task."""
    analysis = await get_analysis_by_url(db, repo.url)

    if analysis is not None:
        parsed = parse_analysis_json(analysis.result_json) if analysis.result_json else None
        if parsed is not None and get_analysis_payload_error(parsed) is None:
            if analysis.status != "done":
                analysis.status = "done"
                analysis.stage = "completed"
                analysis.progress = 1.0
                analysis.error = None
                analysis.analyzed_at = analysis.analyzed_at or datetime.now(UTC)
                await db.commit()
            return AnalysisSubmissionDecision(
                analysis_id=analysis.id,
                status="done",
                stage="completed",
                progress=1.0,
                should_start_task=False,
                cached=True,
            )

        memory_task = task_service.get_task(analysis.id)
        if analysis.status in {"pending", "running"} and memory_task is not None:
            memory_status = memory_task.status.value
            if memory_status in {"pending", "running"}:
                return AnalysisSubmissionDecision(
                    analysis_id=analysis.id,
                    status=memory_status,
                    stage=memory_task.stage or analysis.stage or "waiting",
                    progress=memory_task.progress,
                    should_start_task=False,
                    reused_task=True,
                )

        analysis.status = "pending"
        analysis.stage = "waiting"
        analysis.progress = 0.0
        analysis.error = None
        analysis.result_json = None
        analysis.analyzed_at = None
        await db.commit()
        task_service.create_task(task_id=analysis.id)
        return AnalysisSubmissionDecision(
            analysis_id=analysis.id,
            status="pending",
            stage="waiting",
            progress=0.0,
            should_start_task=True,
        )

    analysis_id = await create_analysis_record(db, repo.url, repo.owner, repo.repo)
    task_service.create_task(task_id=analysis_id)
    return AnalysisSubmissionDecision(
        analysis_id=analysis_id,
        status="pending",
        stage="waiting",
        progress=0.0,
        should_start_task=True,
    )


async def complete_analysis(
    db: AsyncSession, analysis_id: str, result_data: dict
) -> None:
    """Mark analysis as done with result JSON."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis:
        payload_error = get_analysis_payload_error(result_data)
        if payload_error:
            analysis.status = "failed"
            analysis.stage = "failed"
            analysis.progress = 0.0
            analysis.error = payload_error
            analysis.result_json = json.dumps(result_data)
            analysis.analyzed_at = datetime.now(UTC)
            await db.commit()
            return
        analysis.status = "done"
        analysis.stage = "completed"
        analysis.progress = 1.0
        analysis.result_json = json.dumps(result_data)
        analysis.analyzed_at = datetime.now(UTC)
        await db.commit()


async def fail_analysis(db: AsyncSession, analysis_id: str, error: str) -> None:
    """Mark analysis as failed with error message."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis:
        analysis.status = "failed"
        analysis.stage = "failed"
        analysis.progress = 0.0
        analysis.error = error
        await db.commit()


async def update_analysis_progress(
    db: AsyncSession, analysis_id: str, stage: str, progress: float
) -> None:
    """Persist the latest analysis stage for reload-safe progress recovery."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis and analysis.status not in {"done", "failed"}:
        analysis.status = "running"
        analysis.stage = stage
        analysis.progress = progress
        await db.commit()


async def get_analysis_result(db: AsyncSession, analysis_id: str) -> dict | None:
    """Get analysis result for frontend. Returns parsed JSON or None."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis and analysis.status == "done" and analysis.result_json:
        try:
            data = json.loads(analysis.result_json)
        except json.JSONDecodeError:
            return None
        if get_analysis_payload_error(data):
            return None
        return data
    return None


async def get_analysis_record(db: AsyncSession, analysis_id: str) -> RepoAnalysis | None:
    """Get full analysis record by ID."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    return result.scalar_one_or_none()


async def get_saved_analysis_result(
    db: AsyncSession, analysis_id: str
) -> dict | None:
    """Return parsed result if save_repo_analysis already persisted it."""
    analysis = await get_analysis_record(db, analysis_id)
    if analysis and analysis.status == "done" and analysis.result_json:
        data = parse_analysis_json(analysis.result_json)
        if get_analysis_payload_error(data):
            return None
        return data
    return None


async def finalize_analysis_run(
    db: AsyncSession, task_id: str, final_text: str
) -> None:
    """Finalize analysis after agent loop — prefer tool-saved result over final text."""
    result_data = parse_analysis_json(final_text) if final_text else None
    if result_data:
        payload_error = get_analysis_payload_error(result_data)
        if payload_error:
            await fail_analysis(db, task_id, payload_error)
            await task_service.fail_task(task_id, payload_error)
            return
        await complete_analysis(db, task_id, result_data)
        await task_service.complete_task(task_id, result_data)
        return

    saved = await get_saved_analysis_result(db, task_id)
    if saved:
        await task_service.complete_task(task_id, saved)
        return

    error_msg = (
        "Agent produced unparseable output"
        if final_text
        else "Agent produced no output"
    )
    await fail_analysis(db, task_id, error_msg)
    await task_service.fail_task(task_id, error_msg)


def merge_analysis(analysis: RepoAnalysis, result: dict) -> dict:
    """Merge DB record with agent-generated result_json into frontend format."""
    return {
        "id": analysis.id,
        "fullName": f"{analysis.owner}/{analysis.repo}",
        "owner": analysis.owner,
        "repoName": analysis.repo,
        "description": result.get("description", ""),
        "url": analysis.url,
        "status": analysis.status,
        "stage": analysis.stage,
        "progress": analysis.progress,
        "analyzedAt": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
        "techTags": result.get("techTags", []),
        "score": result.get("score"),
        "directoryTree": result.get("directoryTree"),
        "highlights": result.get("highlights", []),
        "suggestions": result.get("suggestions", []),
        "questions": result.get("questions", []),
        "sections": result.get("sections", []),
        "codeSnippets": result.get("codeSnippets", []),
    }


def failed_analysis_response(analysis: RepoAnalysis, error: str | None = None) -> dict:
    """Return a frontend-compatible failed analysis object."""
    return {
        "id": analysis.id,
        "fullName": f"{analysis.owner}/{analysis.repo}",
        "owner": analysis.owner,
        "repoName": analysis.repo,
        "url": analysis.url,
        "status": "failed",
        "stage": analysis.stage,
        "progress": analysis.progress,
        "analyzedAt": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
        "error": error or analysis.error or "Analysis failed",
    }


def analysis_status_payload(analysis: RepoAnalysis) -> dict:
    """Return a stable frontend payload while an analysis is still running."""
    return {
        "id": analysis.id,
        "fullName": f"{analysis.owner}/{analysis.repo}",
        "owner": analysis.owner,
        "repoName": analysis.repo,
        "url": analysis.url,
        "status": analysis.status,
        "stage": analysis.stage or "waiting",
        "progress": analysis.progress or 0.0,
        "analyzedAt": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
    }


async def get_analysis_by_url(db: AsyncSession, url: str) -> RepoAnalysis | None:
    """Get analysis record by URL."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.url == url)
    )
    return result.scalar_one_or_none()


async def delete_analysis_record(db: AsyncSession, analysis_id: str) -> bool:
    """Delete one stored GitHub analysis record."""
    result = await db.execute(
        select(RepoAnalysis).where(RepoAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        return False

    await db.delete(analysis)
    await db.commit()
    return True


# --- API endpoints ---


@router.post("/analysis", response_model=AnalysisResponse)
async def submit_analysis(request: AnalysisRequest):
    """Submit a GitHub repository analysis task."""
    try:
        normalized = normalize_github_repo_url(request.repo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async with _submission_lock(normalized.url):
        async with async_session_factory() as db:
            decision = await prepare_analysis_submission(db, normalized)

        if decision.should_start_task:
            asyncio.create_task(
                _run_analysis(task_id=decision.analysis_id, repo_url=normalized.url)
            )

    return AnalysisResponse(
        task_id=decision.analysis_id,
        status=decision.status,
        stage=decision.stage,
        progress=decision.progress,
        cached=decision.cached,
        reusedTask=decision.reused_task,
    )


@router.get("/analysis")
async def list_analyses():
    """List all completed and failed analyses."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(RepoAnalysis)
            .where(RepoAnalysis.status.in_(["done", "failed"]))
            .order_by(RepoAnalysis.analyzed_at.desc())
        )
        analyses = result.scalars().all()

    items = []
    for analysis in analyses:
        if analysis.status == "done" and analysis.result_json:
            parsed = parse_analysis_json(analysis.result_json)
            payload_error = get_analysis_payload_error(parsed)
            if payload_error:
                items.append(failed_analysis_response(analysis, payload_error))
            elif parsed:
                items.append(merge_analysis(analysis, parsed))
        elif analysis.status == "failed":
            items.append(failed_analysis_response(analysis))
    return items


@router.get("/analysis/{analysis_id}")
async def read_analysis(analysis_id: str):
    """Read analysis result by ID (supports both done and failed)."""
    async with async_session_factory() as db:
        analysis = await get_analysis_record(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status == "failed":
        return failed_analysis_response(analysis)

    if analysis.status in {"pending", "running"}:
        return analysis_status_payload(analysis)

    if analysis.status != "done" or not analysis.result_json:
        raise HTTPException(status_code=409, detail="Analysis is not in a readable state")
    parsed = parse_analysis_json(analysis.result_json)
    if parsed is None:
        raise HTTPException(status_code=500, detail="Failed to parse analysis result")
    payload_error = get_analysis_payload_error(parsed)
    if payload_error:
        return failed_analysis_response(analysis, payload_error)
    return merge_analysis(analysis, parsed)


@router.delete("/analysis/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: str):
    """Delete a GitHub analysis history item."""
    async with async_session_factory() as db:
        deleted = await delete_analysis_record(db, analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found")


async def _run_analysis(task_id: str, repo_url: str):
    """Run GitHub analysis using the ReAct agent with TaskService progress."""
    from agent.loop import CancelToken
    from api.app import app
    from config.settings import settings

    agent_factory = app.state.agent_factory
    session_store = app.state.session_store

    # Create a synthetic session for the agent
    # Clear existing history to avoid stale context from previous runs
    session_id = f"analysis-{task_id}"
    session_store.create("system", session_id, "repo-analyzer", clear_existing=True)

    # Create cancel token and bridge to TaskService
    cancel_token = CancelToken()
    asyncio.create_task(_bridge_cancel(task_id, cancel_token))

    await task_service.update_progress(task_id, 0.05, "正在初始化分析...")
    logger.info("[repo-analysis] agent start %s", task_id)

    async with async_session_factory() as db:
        try:
            await update_analysis_progress(db, task_id, "cloning", 0.10)
            agent = agent_factory.create(
                profile_id="repo-analyzer",
                session_id=session_id,
                mode="text",
                user_id="system",
                db_session=db,
            )
            agent.cancel_token = cancel_token
            agent._repo_root = settings.REPO_ROOT
            agent._repo_url = repo_url

            user_input = (
                f"Analyze repository {repo_url}. "
                f"Use analysis_id={task_id}. "
                f"First call read_skill(skill_id=\"repo-analyzer\"), then follow that workflow. "
                f"Cache was already checked by the API; proceed with clone and analysis."
            )

            tool_count = 0
            final_text = ""

            async for event in agent.run(user_input):
                if event.type == EventType.TOOL_CALL_START:
                    tool_count += 1
                    tool_name = event.payload.get("tool_name", "")
                    progress = min(0.90, 0.05 + tool_count * 0.04)
                    stage = _stage_for_tool(tool_name)
                    await update_analysis_progress(db, task_id, stage, progress)
                    await task_service.update_progress(
                        task_id, progress, _progress_message(tool_name),
                        data={"tool_name": tool_name, "stage": stage},
                    )
                elif event.type == EventType.ASSISTANT_TEXT_DONE:
                    final_text = event.payload.get("text", "")
                    await update_analysis_progress(db, task_id, "saving", 0.95)
                    await task_service.update_progress(
                        task_id,
                        0.95,
                        "正在生成分析报告...",
                        data={"stage": "saving"},
                    )
                elif event.type == EventType.ERROR:
                    error_msg = event.payload.get("message", "Unknown error")
                    await task_service.fail_task(task_id, error_msg)
                    await fail_analysis(db, task_id, error_msg)
                    return

            await finalize_analysis_run(db, task_id, final_text)
            logger.info("[repo-analysis] agent end %s", task_id)

        except Exception as e:
            logger.error(f"Analysis failed for {task_id}: {e}")
            await fail_analysis(db, task_id, str(e))
            await task_service.fail_task(task_id, str(e))


async def _bridge_cancel(task_id: str, cancel_token) -> None:
    """Bridge TaskService cancel event to agent CancelToken."""
    event = task_service.get_cancel_token(task_id)
    await event.wait()
    cancel_token.cancel()


def _progress_message(tool_name: str) -> str:
    """Map tool name to a human-readable progress message."""
    messages = {
        "read_skill": "正在加载分析流程...",
        "clone_repo": "正在克隆仓库...",
        "list_directory": "正在扫描目录结构...",
        "read_file": "正在分析源代码...",
        "search_code": "正在搜索代码模式...",
        "save_repo_analysis": "正在保存分析结果...",
    }
    return messages.get(tool_name, "正在分析...")


def _stage_for_tool(tool_name: str) -> str:
    """Map a tool name to a durable analysis stage."""
    if tool_name == "clone_repo":
        return "cloning"
    if tool_name == "read_repo_context":
        return "indexing"
    if tool_name == "save_repo_analysis":
        return "saving"
    return "analyzing"
