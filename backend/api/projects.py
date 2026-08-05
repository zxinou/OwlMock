from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from api.deps import require_owner
from api.jd_analysis import JdAnalyzeRequest, _create_pending_jd_record
from api.project_schemas import (
    ProjectCreateRequest,
    ProjectResumeMatchRequest,
    ProjectSessionRequest,
    ProjectUpdateRequest,
)
from api.resume_matches import create_pending_resume_match
from api.schemas import CreateSessionRequest
from service.project_service import (
    InvalidProjectAssetError,
    ProjectArchivedError,
    ProjectNotFoundError,
    ProjectService,
    serialize_project,
)
from service.session_service import SessionService
from storage.db.engine import async_session_factory

router = APIRouter(prefix="/projects", tags=["projects"])
Owner = Annotated[str, Depends(require_owner)]


async def get_project_service(owner_id: Owner) -> AsyncIterator[ProjectService]:
    async with async_session_factory() as database:
        yield ProjectService(database, owner_id)


ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


def _raise_project_error(error: Exception) -> NoReturn:
    if isinstance(error, ProjectNotFoundError):
        raise HTTPException(status_code=404, detail="Project not found") from error
    if isinstance(error, ProjectArchivedError):
        raise HTTPException(status_code=409, detail="Project is archived") from error
    if isinstance(error, InvalidProjectAssetError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    service: ProjectServiceDependency,
):
    return serialize_project(await service.create(body))


@router.get("")
async def list_projects(
    service: ProjectServiceDependency,
    archived: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    projects, total = await service.list(
        archived=archived,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [serialize_project(project) for project in projects],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{project_id}")
async def get_project(project_id: str, service: ProjectServiceDependency):
    try:
        return await service.aggregate(project_id)
    except (ProjectNotFoundError, InvalidProjectAssetError) as error:
        _raise_project_error(error)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    service: ProjectServiceDependency,
):
    try:
        return serialize_project(await service.update(project_id, body))
    except (ProjectNotFoundError, InvalidProjectAssetError) as error:
        _raise_project_error(error)


@router.post("/{project_id}/jd-analyses", status_code=status.HTTP_202_ACCEPTED)
async def submit_project_jd(
    project_id: str,
    body: JdAnalyzeRequest,
    owner_id: Owner,
    service: ProjectServiceDependency,
):
    try:
        await service.require_active(project_id)
        record = await _create_pending_jd_record(
            user_id=owner_id,
            text=body.text.strip(),
            project_id=project_id,
        )
        await service.attach_pending_jd(project_id, record.id)
    except (
        ProjectNotFoundError,
        ProjectArchivedError,
        InvalidProjectAssetError,
    ) as error:
        _raise_project_error(error)
    return {
        "task_id": record.id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
    }


@router.post(
    "/{project_id}/jd-analyses/image",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_project_jd_image(
    project_id: str,
    request: Request,
    owner_id: Owner,
    service: ProjectServiceDependency,
    file: UploadFile = File(...),
):
    from api.jd_analysis import create_pending_jd_image

    try:
        await service.require_active(project_id)
        record = await create_pending_jd_image(
            file=file,
            user_id=owner_id,
            project_id=project_id,
            upload_root=request.app.state.settings.JD_UPLOAD_ROOT,
        )
        await service.attach_pending_jd(project_id, record.id)
    except (
        ProjectNotFoundError,
        ProjectArchivedError,
        InvalidProjectAssetError,
    ) as error:
        _raise_project_error(error)
    return {
        "task_id": record.id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
    }


@router.post(
    "/{project_id}/resume-matches",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_project_resume_match(
    project_id: str,
    body: ProjectResumeMatchRequest,
    owner_id: Owner,
    service: ProjectServiceDependency,
):
    try:
        project = await service.require_active(project_id)
        jd = await service.get_completed_jd(project)
        resume_id = body.resume_id or project.current_resume_id
        if not resume_id:
            raise InvalidProjectAssetError("Select a resume first")
        resume = await service.get_resume(resume_id)
        if not resume.file_path or not os.path.isfile(resume.file_path):
            raise InvalidProjectAssetError("Resume file is unavailable")
        await service.set_current_resume(project_id, resume.id)
        record = await create_pending_resume_match(
            user_id=owner_id,
            resume_id=resume.id,
            job_description=jd.text,
            jd_analysis_id=jd.id,
            project_id=project_id,
        )
    except (
        ProjectNotFoundError,
        ProjectArchivedError,
        InvalidProjectAssetError,
    ) as error:
        _raise_project_error(error)
    return {
        "task_id": record.id,
        "status": record.status,
        "stage": record.stage,
        "progress": record.progress,
    }


@router.post("/{project_id}/sessions", status_code=status.HTTP_201_CREATED)
async def create_project_session(
    project_id: str,
    body: ProjectSessionRequest,
    request: Request,
    owner_id: Owner,
    service: ProjectServiceDependency,
):
    try:
        project = await service.require_active(project_id)
        await service.get_completed_jd(project)
        session_service = SessionService(
            db_session=service.database,
            session_store=request.app.state.session_store,
            owner_id=owner_id,
        )
        return await session_service.create_session(
            CreateSessionRequest(
                profile_id=body.profile_id,
                mode=body.mode,
                resume_id=project.current_resume_id,
                github_repo_ids=body.github_repo_ids,
                user_id=owner_id,
                project_id=project.id,
            )
        )
    except (
        ProjectNotFoundError,
        ProjectArchivedError,
        InvalidProjectAssetError,
    ) as error:
        _raise_project_error(error)
