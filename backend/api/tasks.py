from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from security.session import OWNER_ID
from service.task_service import TaskStatus, task_service
from storage.db.engine import async_session_factory
from storage.db.models import JdAnalysisRecord, RepoAnalysis, ResumeMatchRecord

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskResponse(BaseModel):
    """Response for task submission."""
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response for task status check."""
    task_id: str
    status: str
    progress: float | None = None
    stage: str | None = None
    message: str | None = None
    result: dict | None = None
    error: str | None = None


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get task status and result."""
    task = task_service.get_task(task_id)
    if task is None:
        async with async_session_factory() as db:
            result = await db.execute(
                select(RepoAnalysis).where(RepoAnalysis.id == task_id)
            )
            analysis = result.scalar_one_or_none()
            if analysis is None:
                result = await db.execute(
                    select(JdAnalysisRecord).where(
                        JdAnalysisRecord.id == task_id,
                        JdAnalysisRecord.user_id == OWNER_ID,
                    )
                )
                analysis = result.scalar_one_or_none()
            if analysis is None:
                result = await db.execute(
                    select(ResumeMatchRecord).where(
                        ResumeMatchRecord.id == task_id,
                        ResumeMatchRecord.user_id == OWNER_ID,
                    )
                )
                analysis = result.scalar_one_or_none()
        if analysis is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskStatusResponse(
            task_id=analysis.id,
            status=analysis.status,
            progress=analysis.progress,
            stage=analysis.stage,
            message=analysis.error,
            error=analysis.error,
        )

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        stage=task.stage,
        message=task.message,
        result=task.result if task.status == TaskStatus.COMPLETED else None,
        error=task.error,
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE endpoint for streaming task progress."""
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # If task is already completed, return immediately
    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        async def single_event():
            data = {
                "status": task.status.value,
                "progress": task.progress,
                "stage": task.stage,
                "message": "Task already completed",
            }
            yield f"data: {json.dumps(data)}\n\n"

        return StreamingResponse(
            single_event(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_generator() -> AsyncIterator[str]:
        async for update in task_service.stream_progress(task_id):
            data = {
                "status": update.status.value,
                "progress": update.progress,
                "stage": update.data.get("stage"),
                "message": update.message,
                "data": update.data,
            }
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await task_service.cancel_task(task_id)
    return {"status": "ok", "task_id": task_id}
