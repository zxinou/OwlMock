from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.project_schemas import ProjectCreateRequest, ProjectUpdateRequest
from storage.db.models import (
    JdAnalysisRecord,
    JobProject,
    Resume,
    ResumeMatchRecord,
    Session,
)


class ProjectNotFoundError(LookupError):
    pass


class ProjectArchivedError(RuntimeError):
    pass


class InvalidProjectAssetError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _json_object(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def sync_project_from_jd_result(
    database: AsyncSession,
    analysis: JdAnalysisRecord,
    result: dict[str, Any],
) -> None:
    """Backfill blank project metadata from its authoritative current JD."""
    if not analysis.project_id:
        return
    project = await database.get(JobProject, analysis.project_id)
    if (
        project is None
        or project.user_id != analysis.user_id
        or project.current_jd_analysis_id != analysis.id
    ):
        return
    job = result.get("job")
    if not isinstance(job, dict):
        return

    title = job.get("title")
    company = job.get("company")
    location = job.get("location")
    if project.title == "Untitled role" and isinstance(title, str) and title.strip():
        project.title = title.strip()
    if not project.company and isinstance(company, str) and company.strip():
        project.company = company.strip()
    if not project.location and isinstance(location, str) and location.strip():
        project.location = location.strip()
    project.updated_at = utc_now()


class ProjectService:
    def __init__(self, database: AsyncSession, owner_id: str) -> None:
        self.database = database
        self.owner_id = owner_id

    async def create(self, request: ProjectCreateRequest) -> JobProject:
        project = JobProject(
            id=str(uuid.uuid4()),
            user_id=self.owner_id,
            title=request.title,
            company=request.company,
            location=request.location,
        )
        self.database.add(project)
        await self.database.commit()
        await self.database.refresh(project)
        return project

    async def get(self, project_id: str) -> JobProject:
        project = await self.database.get(JobProject, project_id)
        if project is None or project.user_id != self.owner_id:
            raise ProjectNotFoundError(project_id)
        return project

    async def require_active(self, project_id: str) -> JobProject:
        project = await self.get(project_id)
        if project.archived_at is not None:
            raise ProjectArchivedError(project_id)
        return project

    async def list(
        self,
        *,
        archived: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[JobProject], int]:
        archive_filter = (
            JobProject.archived_at.is_not(None)
            if archived
            else JobProject.archived_at.is_(None)
        )
        filters = (JobProject.user_id == self.owner_id, archive_filter)
        rows = (
            await self.database.execute(
                select(JobProject)
                .where(*filters)
                .order_by(JobProject.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        total = (
            await self.database.execute(
                select(func.count()).select_from(JobProject).where(*filters)
            )
        ).scalar_one()
        return list(rows), int(total)

    async def update(
        self,
        project_id: str,
        request: ProjectUpdateRequest,
    ) -> JobProject:
        project = await self.get(project_id)
        fields = request.model_fields_set

        if "title" in fields:
            project.title = request.title
        if "company" in fields:
            project.company = request.company
        if "location" in fields:
            project.location = request.location
        if "current_jd_analysis_id" in fields:
            await self._set_current_jd(project, request.current_jd_analysis_id)
        if "current_resume_id" in fields:
            await self._set_current_resume(project, request.current_resume_id)
        if "archived" in fields:
            project.archived_at = utc_now() if request.archived else None

        project.updated_at = utc_now()
        await self.database.commit()
        await self.database.refresh(project)
        return project

    async def attach_pending_jd(
        self,
        project_id: str,
        analysis_id: str,
    ) -> None:
        project = await self.require_active(project_id)
        analysis = await self.database.get(JdAnalysisRecord, analysis_id)
        if analysis is None or analysis.user_id != self.owner_id:
            raise InvalidProjectAssetError("JD analysis not found")
        analysis.project_id = project.id
        project.current_jd_analysis_id = analysis.id
        project.updated_at = utc_now()
        await self.database.commit()

    async def get_completed_jd(self, project: JobProject) -> JdAnalysisRecord:
        analysis = (
            await self.database.get(JdAnalysisRecord, project.current_jd_analysis_id)
            if project.current_jd_analysis_id
            else None
        )
        if (
            analysis is None
            or analysis.user_id != self.owner_id
            or analysis.status != "completed"
        ):
            raise InvalidProjectAssetError("Select a completed JD analysis first")
        return analysis

    async def get_resume(self, resume_id: str) -> Resume:
        resume = await self.database.get(Resume, resume_id)
        if resume is None or resume.user_id != self.owner_id:
            raise InvalidProjectAssetError("Resume not found")
        return resume

    async def set_current_resume(
        self,
        project_id: str,
        resume_id: str,
    ) -> Resume:
        project = await self.require_active(project_id)
        resume = await self.get_resume(resume_id)
        project.current_resume_id = resume.id
        project.updated_at = utc_now()
        await self.database.commit()
        return resume

    async def aggregate(self, project_id: str) -> dict[str, Any]:
        project = await self.get(project_id)
        jd = (
            await self.database.get(JdAnalysisRecord, project.current_jd_analysis_id)
            if project.current_jd_analysis_id
            else None
        )
        resume = (
            await self.database.get(Resume, project.current_resume_id)
            if project.current_resume_id
            else None
        )

        match_filters = [
            ResumeMatchRecord.project_id == project.id,
            ResumeMatchRecord.user_id == self.owner_id,
            ResumeMatchRecord.status == "completed",
        ]
        if project.current_jd_analysis_id:
            match_filters.append(
                ResumeMatchRecord.jd_analysis_id == project.current_jd_analysis_id
            )
        if project.current_resume_id:
            match_filters.append(
                ResumeMatchRecord.resume_id == project.current_resume_id
            )
        latest_match = (
            await self.database.execute(
                select(ResumeMatchRecord)
                .where(*match_filters)
                .order_by(ResumeMatchRecord.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        sessions = list(
            (
                await self.database.execute(
                    select(Session)
                    .where(
                        Session.project_id == project.id,
                        Session.user_id == self.owner_id,
                    )
                    .order_by(Session.updated_at.desc())
                    .limit(8)
                )
            )
            .scalars()
            .all()
        )

        return {
            **serialize_project(project),
            "current_jd": serialize_jd(jd),
            "current_resume": serialize_resume(resume),
            "latest_match": serialize_match(latest_match),
            "recent_sessions": [serialize_session(session) for session in sessions],
            "steps": derive_steps(jd, resume, latest_match, sessions),
        }

    async def _set_current_jd(
        self,
        project: JobProject,
        analysis_id: str | None,
    ) -> JdAnalysisRecord | None:
        if analysis_id is None:
            project.current_jd_analysis_id = None
            return None
        analysis = await self.database.get(JdAnalysisRecord, analysis_id)
        if (
            analysis is None
            or analysis.user_id != self.owner_id
            or analysis.status != "completed"
            or analysis.project_id not in {None, project.id}
        ):
            raise InvalidProjectAssetError("Completed JD analysis not found")
        analysis.project_id = project.id
        project.current_jd_analysis_id = analysis.id
        return analysis

    async def _set_current_resume(
        self,
        project: JobProject,
        resume_id: str | None,
    ) -> Resume | None:
        if resume_id is None:
            project.current_resume_id = None
            return None
        resume = await self.get_resume(resume_id)
        project.current_resume_id = resume.id
        return resume


def serialize_project(project: JobProject) -> dict[str, Any]:
    return {
        "id": project.id,
        "title": project.title,
        "company": project.company,
        "location": project.location,
        "current_jd_analysis_id": project.current_jd_analysis_id,
        "current_resume_id": project.current_resume_id,
        "archived_at": project.archived_at.isoformat() if project.archived_at else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


def serialize_jd(record: JdAnalysisRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "id": record.id,
        "text": record.text,
        "source_type": record.source_type,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
        "result": _json_object(record.result_json),
        "error": record.error,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def serialize_resume(record: Resume | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "id": record.id,
        "file_name": record.file_name,
        "file_type": record.file_type,
        "has_analysis": bool(record.analysis_result),
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def serialize_match(record: ResumeMatchRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    result = _json_object(record.result_json)
    score_data = result.get("score") if result else None
    score = score_data.get("value") if isinstance(score_data, dict) else None
    return {
        "id": record.id,
        "resume_id": record.resume_id,
        "jd_analysis_id": record.jd_analysis_id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
        "score": score,
        "result": result,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def serialize_session(record: Session) -> dict[str, Any]:
    return {
        "id": record.id,
        "profile_id": record.profile_id,
        "mode": record.mode,
        "status": record.status,
        "turn_count": record.turn_count,
        "summary": _json_object(record.summary),
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def derive_steps(
    jd: JdAnalysisRecord | None,
    resume: Resume | None,
    latest_match: ResumeMatchRecord | None,
    sessions: list[Session],
) -> list[dict[str, str]]:
    jd_status = (
        "completed"
        if jd is not None and jd.status == "completed"
        else "in_progress"
        if jd is not None
        else "not_started"
    )
    match_status = (
        "completed"
        if resume is not None and latest_match is not None
        else "in_progress"
        if resume is not None
        else "not_started"
    )
    interview_status = (
        "completed"
        if any(session.status == "completed" for session in sessions)
        else "in_progress"
        if sessions
        else "not_started"
    )
    return [
        {"key": "job", "status": jd_status},
        {"key": "resume", "status": match_status},
        {"key": "interview", "status": interview_status},
    ]
