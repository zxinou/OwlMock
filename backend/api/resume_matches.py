"""Asynchronous resume-to-JD matching endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from trace import trace_analysis_request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from agent.llm.providers.openai_compatible import build_multimodal_message
from agent.llm.router import chat_structured_with_fallback
from agent.profile_loader import ProfileLoader
from security.session import OWNER_ID
from service.resume_match_report import ResumeMatchReport
from service.resume_media import prepare_resume_images
from service.task_service import task_service
from storage.db.engine import async_session_factory
from storage.db.models import JdAnalysisRecord, Resume, ResumeMatchRecord

router = APIRouter(tags=["resume-matches"])
logger = logging.getLogger(__name__)

MAX_JD_LENGTH = 12000
ANALYSIS_UNAVAILABLE = "匹配报告暂时无法生成，请稍后重试"
_resume_match_background_tasks: dict[str, asyncio.Task] = {}


class ResumeMatchRequest(BaseModel):
    resume_id: str = Field(min_length=1)
    job_description: str = Field(min_length=20, max_length=MAX_JD_LENGTH)
    user_id: str = "default"


class ResumeMatchBatchRequest(BaseModel):
    resume_id: str = Field(min_length=1)
    jd_analysis_ids: list[str] = Field(min_length=1, max_length=20)
    user_id: str = "default"


class BatchDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)
    user_id: str = "default"


def _load_profile_and_prompt():
    loader = ProfileLoader("config/agents")
    loader.load_all()
    profile = loader.get("resume-matcher")
    if profile is None:
        raise RuntimeError("resume-matcher profile not found")
    with open(profile.prompt_template, encoding="utf-8") as handle:
        return profile, handle.read()


def _parse_result(record: ResumeMatchRecord) -> dict | None:
    try:
        payload = json.loads(record.result_json)
        if payload:
            return ResumeMatchReport.model_validate(payload).model_dump()
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _jd_summary(record: JdAnalysisRecord | None) -> dict | None:
    if record is None:
        return None
    job_summary = None
    try:
        payload = json.loads(record.result_json)
        job = payload.get("job") if isinstance(payload, dict) else None
        if isinstance(job, dict):
            difficulty = job.get("difficulty")
            job_summary = {
                "title": job.get("title"),
                "company": job.get("company"),
                "difficulty": difficulty.get("level")
                if isinstance(difficulty, dict)
                else difficulty,
            }
    except json.JSONDecodeError:
        pass
    return {
        "id": record.id,
        "text": record.text,
        "status": record.status,
        "source_type": record.source_type,
        "job": job_summary,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _serialize(
    record: ResumeMatchRecord,
    resume: Resume | None = None,
    jd_analysis: JdAnalysisRecord | None = None,
) -> dict:
    return {
        "id": record.id,
        "batch_id": record.batch_id,
        "user_id": record.user_id,
        "resume_id": record.resume_id,
        "jd_analysis_id": record.jd_analysis_id,
        "jd_analysis": _jd_summary(jd_analysis),
        "resume": {
            "id": resume.id,
            "file_name": resume.file_name,
            "file_type": resume.file_type,
        } if resume else None,
        "job_description": record.job_description,
        "result": _parse_result(record),
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
        "error": record.error,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


async def _persist_progress(
    match_id: str,
    stage: str,
    progress: float,
    *,
    status: str = "running",
    error: str | None = None,
) -> None:
    async with async_session_factory() as db:
        record = await db.get(ResumeMatchRecord, match_id)
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
            match_id,
            progress,
            stage,
            {"stage": stage, "match_id": match_id},
        )


async def run_resume_match_task(match_id: str) -> None:
    """Run one persisted match and keep SQLite as the source of truth."""
    try:
        await _persist_progress(match_id, "extracting", 0.15)
        async with async_session_factory() as db:
            record = await db.get(ResumeMatchRecord, match_id)
            if record is None:
                raise LookupError("Resume match not found")
            resume = await db.get(Resume, record.resume_id)
            if resume is None:
                raise LookupError("Resume not found")
            jd_analysis = (
                await db.get(JdAnalysisRecord, record.jd_analysis_id)
                if record.jd_analysis_id
                else None
            )

        if not resume.file_path or not os.path.isfile(resume.file_path):
            raise FileNotFoundError("Resume file not found")
        images = prepare_resume_images(resume.file_path, resume.file_type or "pdf")
        await _persist_progress(match_id, "parsing_jd", 0.34)
        profile, system_prompt = _load_profile_and_prompt()
        user_prompt = (
            "请将简历与下面的岗位描述逐条匹配，并严格按系统要求输出结构化报告。\n\n"
            f"岗位描述：\n{record.job_description}"
        )
        if jd_analysis is not None:
            try:
                jd_context = json.dumps(
                    json.loads(jd_analysis.result_json), ensure_ascii=False
                )
            except json.JSONDecodeError:
                jd_context = ""
            if jd_context:
                user_prompt += (
                    "\n\nThe following is the completed authoritative JD analysis. "
                    "Use it directly and do not re-analyze the JD:\n"
                    f"{jd_context}"
                )
        messages = [
            {"role": "system", "content": system_prompt},
            build_multimodal_message(user_prompt, images=images),
        ]
        await _persist_progress(match_id, "matching", 0.64)

        with trace_analysis_request(
            kind="resume_match",
            user_id=record.user_id,
            input_summary={
                "match_id": match_id,
                "resume_id": record.resume_id,
                "file_type": resume.file_type,
                "page_count": len(images),
                "jd_length": len(record.job_description),
            },
        ) as span:
            structured = await chat_structured_with_fallback(
                profile.llm, messages, ResumeMatchReport
            )
            if structured.value is None:
                logger.error(
                    "Resume match model failed id=%s provider=%s model=%s "
                    "error=%s parse_error=%s",
                    match_id,
                    structured.completion.error and profile.llm.provider,
                    profile.llm.model,
                    structured.completion.error or "none",
                    structured.parse_error or "none",
                )
                raise RuntimeError(
                    structured.completion.error
                    or structured.parse_error
                    or ANALYSIS_UNAVAILABLE
                )
            data = structured.value.model_dump()
            span.update(output={
                "status": "ok",
                "match_id": match_id,
                "score": data["score"]["value"],
                "requirements": len(data["requirements"]),
                "gaps": len(data["gaps"]),
            })

        await _persist_progress(match_id, "saving", 0.9)
        async with async_session_factory() as db:
            current = await db.get(ResumeMatchRecord, match_id)
            if current is None:
                return
            current.result_json = json.dumps(data, ensure_ascii=False)
            current.status = "completed"
            current.stage = "completed"
            current.progress = 1.0
            current.error = None
            await db.commit()
        await task_service.complete_task(match_id, {"match_id": match_id})
    except asyncio.CancelledError:
        await _persist_progress(
            match_id, "cancelled", 0.0, status="failed", error="匹配分析已取消"
        )
        raise
    except Exception:
        logger.exception("Resume match failed id=%s", match_id)
        await _persist_progress(
            match_id, "failed", 0.0, status="failed", error=ANALYSIS_UNAVAILABLE
        )
        await task_service.fail_task(match_id, ANALYSIS_UNAVAILABLE)


def _schedule_resume_match_task(match_id: str) -> None:
    current = _resume_match_background_tasks.get(match_id)
    if current is not None and not current.done():
        return
    task = asyncio.create_task(run_resume_match_task(match_id))
    _resume_match_background_tasks[match_id] = task
    task.add_done_callback(lambda _: _resume_match_background_tasks.pop(match_id, None))


async def cancel_resume_match_task(match_id: str) -> None:
    background = _resume_match_background_tasks.get(match_id)
    if background is not None and not background.done():
        background.cancel()
    if task_service.get_task(match_id) is not None:
        await task_service.cancel_task(match_id)


async def create_pending_resume_match(
    *,
    user_id: str,
    resume_id: str,
    job_description: str,
    jd_analysis_id: str | None = None,
    project_id: str | None = None,
) -> ResumeMatchRecord:
    """Persist and schedule a match through the shared task pipeline."""
    record = ResumeMatchRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        resume_id=resume_id,
        jd_analysis_id=jd_analysis_id,
        project_id=project_id,
        job_description=job_description.strip(),
        result_json="{}",
        status="pending",
        stage="waiting",
        progress=0.0,
    )
    async with async_session_factory() as db:
        db.add(record)
        await db.commit()
    task_service.create_task(task_id=record.id)
    _schedule_resume_match_task(record.id)
    return record


@router.post("/resume-matches/batch", status_code=202)
async def submit_resume_match_batch(body: ResumeMatchBatchRequest):
    """Create one independent persisted match for every selected JD analysis."""
    jd_ids = list(dict.fromkeys(body.jd_analysis_ids))
    async with async_session_factory() as db:
        resume = await db.get(Resume, body.resume_id)
        if resume is None or resume.user_id != OWNER_ID:
            raise HTTPException(status_code=404, detail="Resume not found")
        if not resume.file_path or not os.path.isfile(resume.file_path):
            raise HTTPException(status_code=400, detail="Resume file is unavailable")

        jd_rows = (await db.execute(
            select(JdAnalysisRecord).where(JdAnalysisRecord.id.in_(jd_ids))
        )).scalars().all()
        jd_by_id = {row.id: row for row in jd_rows}
        invalid_ids = [
            jd_id
            for jd_id in jd_ids
            if jd_id not in jd_by_id
            or jd_by_id[jd_id].user_id != OWNER_ID
            or jd_by_id[jd_id].status != "completed"
            or not jd_by_id[jd_id].result_json
            or jd_by_id[jd_id].result_json == "{}"
        ]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only completed JD analyses owned by the current user can be "
                    f"matched. Invalid ids: {', '.join(invalid_ids)}"
                ),
            )

        batch_id = str(uuid.uuid4())
        records = []
        for jd_id in jd_ids:
            jd = jd_by_id[jd_id]
            record = ResumeMatchRecord(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                user_id=OWNER_ID,
                resume_id=body.resume_id,
                jd_analysis_id=jd.id,
                job_description=jd.text,
                result_json="{}",
                status="pending",
                stage="waiting",
                progress=0.0,
            )
            db.add(record)
            records.append(record)
        await db.commit()

    for record in records:
        task_service.create_task(task_id=record.id)
        _schedule_resume_match_task(record.id)
    return {
        "batch_id": batch_id,
        "status": "pending",
        "stage": "waiting",
        "progress": 0.0,
        "tasks": [
            {
                "task_id": record.id,
                "jd_analysis_id": record.jd_analysis_id,
                "status": record.status,
            }
            for record in records
        ],
    }


@router.delete("/resume-matches/batch")
async def batch_delete_resume_matches(body: BatchDeleteRequest):
    """Cancel and delete selected match records without deleting resumes."""
    ids = list(dict.fromkeys(body.ids))
    async with async_session_factory() as db:
        records = (await db.execute(
            select(ResumeMatchRecord).where(
                ResumeMatchRecord.id.in_(ids),
                ResumeMatchRecord.user_id == OWNER_ID,
            )
        )).scalars().all()
        for record in records:
            await cancel_resume_match_task(record.id)
            await db.delete(record)
        await db.commit()
    return {"deleted_count": len(records), "ids": [record.id for record in records]}


@router.post("/resume-matches", status_code=202)
async def submit_resume_match(body: ResumeMatchRequest):
    async with async_session_factory() as db:
        resume = await db.get(Resume, body.resume_id)
        if resume is None or resume.user_id != OWNER_ID:
            raise HTTPException(status_code=404, detail="Resume not found")
        if not resume.file_path or not os.path.isfile(resume.file_path):
            raise HTTPException(status_code=400, detail="Resume file is unavailable")
    record = await create_pending_resume_match(
        user_id=OWNER_ID,
        resume_id=body.resume_id,
        job_description=body.job_description,
    )
    return {"task_id": record.id, "status": "pending", "stage": "waiting", "progress": 0.0}


@router.get("/resume-matches")
async def list_resume_matches(user_id: str = "default"):
    async with async_session_factory() as db:
        rows = (await db.execute(
            select(ResumeMatchRecord)
            .where(ResumeMatchRecord.user_id == OWNER_ID)
            .order_by(ResumeMatchRecord.created_at.desc())
        )).scalars().all()
        values = []
        for row in rows:
            values.append(_serialize(
                row,
                await db.get(Resume, row.resume_id),
                await db.get(JdAnalysisRecord, row.jd_analysis_id)
                if row.jd_analysis_id
                else None,
            ))
        return values


def _match_score(record: ResumeMatchRecord) -> float:
    try:
        payload = json.loads(record.result_json)
        score = payload.get("score") if isinstance(payload, dict) else None
        value = score.get("value") if isinstance(score, dict) else None
        return float(value) if value is not None else -1.0
    except (json.JSONDecodeError, TypeError, ValueError):
        return -1.0


@router.get("/resume-match-batches/{batch_id}")
async def get_resume_match_batch(batch_id: str, user_id: str = "default"):
    async with async_session_factory() as db:
        rows = (await db.execute(
            select(ResumeMatchRecord).where(
                ResumeMatchRecord.batch_id == batch_id,
                ResumeMatchRecord.user_id == OWNER_ID,
            )
        )).scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="Resume match batch not found")
        resume = await db.get(Resume, rows[0].resume_id)
        values = []
        for row in sorted(rows, key=_match_score, reverse=True):
            jd = (
                await db.get(JdAnalysisRecord, row.jd_analysis_id)
                if row.jd_analysis_id
                else None
            )
            values.append(_serialize(row, resume, jd))

    terminal = all(row.status in {"completed", "failed"} for row in rows)
    completed = sum(row.status == "completed" for row in rows)
    failed = sum(row.status == "failed" for row in rows)
    if terminal:
        status = "completed" if completed else "failed"
    else:
        status = "running"
    return {
        "batch_id": batch_id,
        "status": status,
        "stage": "completed" if terminal else "matching",
        "progress": sum(row.progress for row in rows) / len(rows),
        "completed_count": completed,
        "failed_count": failed,
        "total_count": len(rows),
        "resume": {
            "id": resume.id,
            "file_name": resume.file_name,
            "file_type": resume.file_type,
        } if resume else None,
        "matches": values,
    }


@router.get("/resume-matches/{match_id}")
async def get_resume_match(match_id: str):
    async with async_session_factory() as db:
        record = (
            await db.execute(
                select(ResumeMatchRecord).where(
                    ResumeMatchRecord.id == match_id,
                    ResumeMatchRecord.user_id == OWNER_ID,
                )
            )
        ).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Resume match not found")
        resume = await db.get(Resume, record.resume_id)
        jd = (
            await db.get(JdAnalysisRecord, record.jd_analysis_id)
            if record.jd_analysis_id
            else None
        )
        return _serialize(record, resume, jd)


@router.post("/resume-matches/{match_id}/resume")
async def resume_resume_match(match_id: str):
    async with async_session_factory() as db:
        record = (
            await db.execute(
                select(ResumeMatchRecord).where(
                    ResumeMatchRecord.id == match_id,
                    ResumeMatchRecord.user_id == OWNER_ID,
                )
            )
        ).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Resume match not found")
        if record.status == "completed":
            return {
                "task_id": match_id,
                "status": record.status,
                "stage": record.stage,
                "progress": record.progress,
            }
        if record.status == "failed":
            record.status = "pending"
            record.stage = "waiting"
            record.progress = 0.0
            record.error = None
            await db.commit()
    memory_task = task_service.get_task(match_id)
    memory_status = memory_task.status.value if memory_task else None
    if memory_task is None or memory_status in {"failed", "completed", "cancelled"}:
        task_service.create_task(task_id=match_id)
        _schedule_resume_match_task(match_id)
    return {
        "task_id": match_id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
    }


@router.delete("/resume-matches/{match_id}", status_code=204)
async def delete_resume_match(match_id: str):
    async with async_session_factory() as db:
        record = (
            await db.execute(
                select(ResumeMatchRecord).where(
                    ResumeMatchRecord.id == match_id,
                    ResumeMatchRecord.user_id == OWNER_ID,
                )
            )
        ).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Resume match not found")
        await cancel_resume_match_task(match_id)
        await db.delete(record)
        await db.commit()
