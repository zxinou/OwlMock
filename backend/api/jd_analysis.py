"""JD analysis API endpoint."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from trace import trace_analysis_request

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from agent.llm.providers.openai_compatible import build_multimodal_message
from agent.llm.router import chat_structured_with_fallback
from agent.profile_loader import ProfileLoader
from api.deps import require_owner
from config.settings import settings
from service.jd_report import JdReport, normalize_jd_report
from service.project_service import sync_project_from_jd_result
from service.task_service import task_service
from storage.db.engine import async_session_factory
from storage.db.models import JdAnalysisRecord

router = APIRouter(tags=["jd-analysis"])
logger = logging.getLogger(__name__)

ANALYSIS_UNAVAILABLE = (
    "\u5206\u6790\u7ed3\u679c\u6682\u65f6\u65e0\u6cd5\u751f\u6210"
    "\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5"
)
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_JD_TEXT_LENGTH = 12000
ANALYZE_JD_IMAGE_PROMPT = (
    "请阅读这张岗位 JD 截图，先识别其中的职位描述文字，再按系统要求输出结构化分析。"
)


class JdAnalyzeRequest(BaseModel):
    """Request body for JD analysis."""

    text: str = Field(
        ..., min_length=1, max_length=MAX_JD_TEXT_LENGTH, description="Job description text"
    )
    user_id: str = "default"


class BatchDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)
    user_id: str = "default"


# Compatibility export for integrations that imported the old API-local schema.
JdAnalysis = JdReport


def serialize_jd_record(record: JdAnalysisRecord) -> dict:
    """Convert a JD analysis DB record to frontend JSON."""
    result = None
    try:
        raw_result = json.loads(record.result_json)
        if raw_result:
            result = normalize_jd_report(raw_result).model_dump()
    except (json.JSONDecodeError, ValueError):
        result = None

    return {
        "id": record.id,
        "user_id": record.user_id,
        "text": record.text,
        "result": result,
        "source_type": record.source_type,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
        "error": record.error,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def load_jd_profile_and_prompt():
    """Load the JD analyzer profile and system prompt."""
    profile_loader = ProfileLoader("config/agents")
    profile_loader.load_all()
    profile = profile_loader.get("jd-analyzer")

    if not profile:
        raise HTTPException(500, "jd-analyzer profile not found")

    with open(profile.prompt_template, encoding="utf-8") as f:
        prompt = f.read()

    return profile, prompt


async def save_jd_analysis(
    user_id: str,
    text: str,
    data: dict,
    *,
    source_type: str = "text",
) -> JdAnalysisRecord:
    """Persist a JD analysis result and return the saved record."""
    async with async_session_factory() as db:
        record = JdAnalysisRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            text=text,
            result_json=json.dumps(data, ensure_ascii=False),
            source_type=source_type,
            status="completed",
            stage="completed",
            progress=1.0,
        )
        db.add(record)
        await db.commit()
        return record


_jd_background_tasks: dict[str, asyncio.Task] = {}


async def _persist_jd_progress(
    analysis_id: str,
    stage: str,
    progress: float,
    *,
    status: str = "running",
    error: str | None = None,
) -> None:
    async with async_session_factory() as db:
        record = await db.get(JdAnalysisRecord, analysis_id)
        if record is None:
            return
        if record.status in {"completed", "failed"} and status == "running":
            return
        record.status = status
        record.stage = stage
        record.progress = progress
        record.error = error
        await db.commit()

    if status == "running":
        await task_service.update_progress(
            analysis_id,
            progress,
            stage,
            {"stage": stage, "analysis_id": analysis_id},
        )


async def _load_jd_record(analysis_id: str) -> JdAnalysisRecord | None:
    async with async_session_factory() as db:
        return await db.get(JdAnalysisRecord, analysis_id)


def _build_jd_messages(record: JdAnalysisRecord, prompt: str) -> list[dict]:
    if record.source_type != "image":
        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": record.text},
        ]

    source_path = Path(record.source_path or "")
    if not source_path.is_file():
        raise FileNotFoundError("JD image source is missing")
    content = source_path.read_bytes()
    mime_type = "image/png" if source_path.suffix.lower() == ".png" else "image/jpeg"
    image_b64 = base64.b64encode(content).decode("utf-8")
    return [
        {"role": "system", "content": prompt},
        build_multimodal_message(
            ANALYZE_JD_IMAGE_PROMPT,
            file_b64=image_b64,
            mime_type=mime_type,
        ),
    ]


async def run_jd_analysis_task(analysis_id: str) -> None:
    """Run one persisted JD analysis and preserve terminal state in SQLite."""
    try:
        await _persist_jd_progress(analysis_id, "extracting", 0.15)
        record = await _load_jd_record(analysis_id)
        if record is None:
            raise LookupError("JD analysis record not found")

        profile, prompt = load_jd_profile_and_prompt()
        messages = _build_jd_messages(record, prompt)
        await _persist_jd_progress(analysis_id, "structuring", 0.35)
        await _persist_jd_progress(analysis_id, "analyzing", 0.62)

        with trace_analysis_request(
            kind="jd",
            user_id=record.user_id,
            input_summary={
                "analysis_id": analysis_id,
                "source_type": record.source_type,
                "text_length": len(record.text),
            },
        ) as span:
            structured = await chat_structured_with_fallback(
                profile.llm, messages, JdReport
            )
            if structured.value is None:
                raise RuntimeError(
                    structured.completion.error
                    or structured.parse_error
                    or ANALYSIS_UNAVAILABLE
                )
            data = structured.value.model_dump()
            span.update(
                output={
                    "status": "ok",
                    "analysis_id": analysis_id,
                    "requirements": len(data["requirements"]),
                    "skills": len(data["skills"]),
                    "risks": len(data["risks"]),
                }
            )

        await _persist_jd_progress(analysis_id, "saving", 0.9)
        async with async_session_factory() as db:
            current = await db.get(JdAnalysisRecord, analysis_id)
            if current is None:
                return
            current.result_json = json.dumps(data, ensure_ascii=False)
            current.status = "completed"
            current.stage = "completed"
            current.progress = 1.0
            current.error = None
            await sync_project_from_jd_result(db, current, data)
            await db.commit()
        await task_service.complete_task(analysis_id, {"analysis_id": analysis_id})
    except asyncio.CancelledError:
        await _persist_jd_progress(
            analysis_id, "cancelled", 0.0, status="failed", error="分析已取消"
        )
        raise
    except Exception:
        logger.exception("JD background analysis failed id=%s", analysis_id)
        await _persist_jd_progress(
            analysis_id,
            "failed",
            0.0,
            status="failed",
            error=ANALYSIS_UNAVAILABLE,
        )
        await task_service.fail_task(analysis_id, ANALYSIS_UNAVAILABLE)


def _schedule_jd_task(analysis_id: str) -> None:
    current = _jd_background_tasks.get(analysis_id)
    if current is not None and not current.done():
        return
    task = asyncio.create_task(run_jd_analysis_task(analysis_id))
    _jd_background_tasks[analysis_id] = task
    task.add_done_callback(lambda _: _jd_background_tasks.pop(analysis_id, None))


async def _create_pending_jd_record(
    *,
    user_id: str,
    text: str,
    source_type: str = "text",
    source_path: str | None = None,
    project_id: str | None = None,
) -> JdAnalysisRecord:
    record = JdAnalysisRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        text=text,
        result_json="{}",
        source_type=source_type,
        source_path=source_path,
        project_id=project_id,
        status="pending",
        stage="waiting",
        progress=0.0,
    )
    async with async_session_factory() as db:
        db.add(record)
        await db.commit()
    task_service.create_task(task_id=record.id)
    _schedule_jd_task(record.id)
    return record


async def create_pending_jd_image(
    *,
    file: UploadFile,
    user_id: str,
    project_id: str | None = None,
    upload_root: str | None = None,
) -> JdAnalysisRecord:
    """Persist an uploaded JD image and schedule the shared analysis task."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are supported")
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image size cannot exceed 10MB")

    root = Path(upload_root or settings.JD_UPLOAD_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    extension = ".png" if file.content_type == "image/png" else ".jpg"
    source_path = root / f"{uuid.uuid4()}{extension}"
    source_path.write_bytes(content)
    try:
        return await _create_pending_jd_record(
            user_id=user_id,
            text=f"Image JD: {file.filename or 'unnamed screenshot'}",
            source_type="image",
            source_path=str(source_path),
            project_id=project_id,
        )
    except Exception:
        source_path.unlink(missing_ok=True)
        raise


@router.post("/jd/analyze")
async def analyze_jd(
    body: JdAnalyzeRequest,
    user_id: str = Depends(require_owner),
):
    """Analyze a job description and return structured insights."""
    profile, prompt = load_jd_profile_and_prompt()

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": body.text},
    ]

    with trace_analysis_request(
        kind="jd",
        input_summary={"text_length": len(body.text)},
    ) as span:
        structured = await chat_structured_with_fallback(profile.llm, messages, JdReport)
        if structured.value is None:
            logger.warning(
                "JD analysis failed provider=%s model=%s provider_error=%s parse_error=%s",
                profile.llm.provider,
                profile.llm.model,
                bool(structured.completion.error),
                structured.parse_error or "none",
            )
            span.update(
                output={
                    "status": "failed",
                    "provider_error": bool(structured.completion.error),
                    "parse_error": bool(structured.parse_error),
                },
                level="ERROR",
                status_message=structured.completion.error or structured.parse_error or None,
            )
            raise HTTPException(502, ANALYSIS_UNAVAILABLE)

        data = structured.value.model_dump()
        record = await save_jd_analysis(user_id, body.text, data)

        span.update(
            output={
                "status": "ok",
                "analysis_id": record.id,
                "requirements": len(data["requirements"]),
                "skills": len(data["skills"]),
                "risks": len(data["risks"]),
                "interview_focus": len(data["interview_focus"]),
            }
        )
        return {
            **data,
            "id": record.id,
            "user_id": user_id,
            "text": body.text,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }


@router.post("/jd/analyze-image")
async def analyze_jd_image(
    file: UploadFile,
    user_id: str = Depends(require_owner),
):
    """Analyze a job description screenshot with a multimodal model."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are supported")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image size cannot exceed 10MB")

    profile, prompt = load_jd_profile_and_prompt()
    image_b64 = base64.b64encode(content).decode("utf-8")
    user_msg = build_multimodal_message(
        ANALYZE_JD_IMAGE_PROMPT,
        file_b64=image_b64,
        mime_type=file.content_type,
    )
    messages = [
        {"role": "system", "content": prompt},
        user_msg,
    ]

    with trace_analysis_request(
        kind="jd",
        user_id=user_id,
        input_summary={
            "source_type": "image",
            "file_name": file.filename,
            "mime_type": file.content_type,
            "file_size": len(content),
        },
    ) as span:
        structured = await chat_structured_with_fallback(profile.llm, messages, JdReport)
        if structured.value is None:
            logger.warning(
                "JD image analysis failed provider=%s model=%s provider_error=%s parse_error=%s",
                profile.llm.provider,
                profile.llm.model,
                bool(structured.completion.error),
                structured.parse_error or "none",
            )
            span.update(
                output={
                    "status": "failed",
                    "source_type": "image",
                    "provider_error": bool(structured.completion.error),
                    "parse_error": bool(structured.parse_error),
                },
                level="ERROR",
                status_message=structured.completion.error or structured.parse_error or None,
            )
            raise HTTPException(502, ANALYSIS_UNAVAILABLE)

        data = structured.value.model_dump()
        history_text = f"图片 JD：{file.filename or '未命名截图'}"
        record = await save_jd_analysis(
            user_id, history_text, data, source_type="image"
        )
        span.update(
            output={
                "status": "ok",
                "source_type": "image",
                "analysis_id": record.id,
                "requirements": len(data["requirements"]),
                "skills": len(data["skills"]),
                "risks": len(data["risks"]),
                "interview_focus": len(data["interview_focus"]),
            }
        )
        return {
            **data,
            "id": record.id,
            "user_id": user_id,
            "text": history_text,
            "source_type": "image",
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }


@router.post("/jd/analyses", status_code=202)
async def submit_jd_analysis(
    body: JdAnalyzeRequest,
    user_id: str = Depends(require_owner),
):
    """Persist a text JD and start a non-blocking analysis task."""
    record = await _create_pending_jd_record(
        user_id=user_id,
        text=body.text.strip(),
    )
    return {
        "task_id": record.id,
        "status": "pending",
        "stage": "waiting",
        "progress": 0.0,
    }


@router.post("/jd/analyses/image", status_code=202)
async def submit_jd_image_analysis(
    file: UploadFile,
    user_id: str = Depends(require_owner),
):
    """Persist a JD screenshot outside the reload tree and start analysis."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG images are supported")
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image size cannot exceed 10MB")

    upload_root = Path(settings.JD_UPLOAD_ROOT).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    extension = ".png" if file.content_type == "image/png" else ".jpg"
    source_path = upload_root / f"{uuid.uuid4()}{extension}"
    source_path.write_bytes(content)
    try:
        record = await _create_pending_jd_record(
        user_id=user_id,
            text=f"图片 JD：{file.filename or '未命名截图'}",
            source_type="image",
            source_path=str(source_path),
        )
    except Exception:
        source_path.unlink(missing_ok=True)
        raise
    return {
        "task_id": record.id,
        "status": "pending",
        "stage": "waiting",
        "progress": 0.0,
    }


@router.get("/jd/analyses")
async def list_jd_analyses(user_id: str = Depends(require_owner)):
    """List saved JD analysis history for one user."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(JdAnalysisRecord)
            .where(JdAnalysisRecord.user_id == user_id)
            .order_by(JdAnalysisRecord.created_at.desc())
        )
        records = result.scalars().all()

    return [serialize_jd_record(record) for record in records]


@router.get("/jd/analyses/{analysis_id}")
async def get_jd_analysis(
    analysis_id: str,
    user_id: str = Depends(require_owner),
):
    """Return persisted progress or the completed structured report."""
    async with async_session_factory() as db:
        record = (
            await db.execute(
                select(JdAnalysisRecord).where(
                    JdAnalysisRecord.id == analysis_id,
                    JdAnalysisRecord.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="JD analysis not found")
    return serialize_jd_record(record)


@router.post("/jd/analyses/{analysis_id}/resume")
async def resume_jd_analysis(
    analysis_id: str,
    user_id: str = Depends(require_owner),
):
    """Idempotently reclaim a task whose in-memory runner was lost."""
    async with async_session_factory() as db:
        record = (
            await db.execute(
                select(JdAnalysisRecord).where(
                    JdAnalysisRecord.id == analysis_id,
                    JdAnalysisRecord.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="JD analysis not found")
        if record.status == "completed":
            return {
                "task_id": record.id,
                "status": record.status,
                "stage": record.stage,
                "progress": record.progress,
            }

    memory_task = task_service.get_task(analysis_id)
    if memory_task is None:
        task_service.create_task(task_id=analysis_id)
        _schedule_jd_task(analysis_id)
    return {
        "task_id": analysis_id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
    }


@router.delete("/jd/analyses/batch")
async def batch_delete_jd_analyses(
    body: BatchDeleteRequest,
    user_id: str = Depends(require_owner),
):
    """Delete selected JD analyses and their persisted image sources."""
    ids = list(dict.fromkeys(body.ids))
    async with async_session_factory() as db:
        records = (await db.execute(
            select(JdAnalysisRecord).where(
                JdAnalysisRecord.id.in_(ids),
                JdAnalysisRecord.user_id == user_id,
            )
        )).scalars().all()
        for record in records:
            background = _jd_background_tasks.get(record.id)
            if background is not None and not background.done():
                background.cancel()
            if task_service.get_task(record.id) is not None:
                await task_service.cancel_task(record.id)
            if record.source_path:
                Path(record.source_path).unlink(missing_ok=True)
            await db.delete(record)
        await db.commit()
    return {"deleted_count": len(records), "ids": [record.id for record in records]}


@router.delete("/jd/analyses/{analysis_id}", status_code=204)
async def delete_jd_analysis(
    analysis_id: str,
    user_id: str = Depends(require_owner),
):
    """Delete a saved JD analysis history item."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(JdAnalysisRecord).where(
                JdAnalysisRecord.id == analysis_id,
                JdAnalysisRecord.user_id == user_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="JD analysis not found")
        background = _jd_background_tasks.get(analysis_id)
        if background is not None and not background.done():
            background.cancel()
        if task_service.get_task(analysis_id) is not None:
            await task_service.cancel_task(analysis_id)
        if record.source_path:
            Path(record.source_path).unlink(missing_ok=True)
        await db.delete(record)
        await db.commit()
