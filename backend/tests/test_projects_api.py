from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.projects import router as projects_router
from config.settings import Settings
from security.session import SESSION_COOKIE, SessionSigner
from storage.db.models import (
    Base,
    JdAnalysisRecord,
    JobProject,
    Resume,
    ResumeMatchRecord,
    Session,
)
from storage.session.store import SessionStore


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def db_factory(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def scoped_factory():
        async with factory() as session:
            yield session

    return scoped_factory


@pytest.fixture
async def client(db_factory, tmp_path: Path):
    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_ADMIN_PASSWORD="test-password",
        OWLMOCK_COOKIE_SECURE=False,
    )
    signer = SessionSigner("project-api-tests", 3600)
    app.state.session_signer = signer
    app.state.session_store = SessionStore(root_dir=str(tmp_path / "sessions"))
    app.include_router(projects_router, prefix="/api")

    with (
        patch("api.projects.async_session_factory", db_factory),
        patch("api.jd_analysis.async_session_factory", db_factory),
        patch("api.resume_matches.async_session_factory", db_factory),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={SESSION_COOKIE: signer.issue()},
        ) as test_client:
            yield test_client


async def create_project(client: AsyncClient, **overrides) -> dict:
    body = {
        "title": "Senior Frontend Engineer",
        "company": "Owl Labs",
        "location": "Remote",
        **overrides,
    }
    response = await client.post("/api/projects", json=body)
    assert response.status_code == 201
    return response.json()


async def test_projects_require_an_owner_session(tmp_path: Path) -> None:
    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_ADMIN_PASSWORD="test-password",
    )
    app.state.session_signer = SessionSigner("anonymous-project-tests", 3600)
    app.include_router(projects_router, prefix="/api")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as anonymous:
        response = await anonymous.get("/api/projects")

    assert response.status_code == 401


async def test_create_list_edit_and_archive_project(client: AsyncClient) -> None:
    project = await create_project(client)

    listed = await client.get("/api/projects")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == project["id"]

    edited = await client.patch(
        f"/api/projects/{project['id']}",
        json={"title": "Staff Frontend Engineer", "location": "Hong Kong"},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Staff Frontend Engineer"
    assert edited.json()["location"] == "Hong Kong"

    archived = await client.patch(
        f"/api/projects/{project['id']}", json={"archived": True}
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    active = await client.get("/api/projects")
    archive = await client.get("/api/projects?archived=true")
    assert active.json()["total"] == 0
    assert archive.json()["items"][0]["id"] == project["id"]


async def test_project_title_rejects_blank_and_null_values(client: AsyncClient) -> None:
    blank = await client.post("/api/projects", json={"title": "   "})
    assert blank.status_code == 422

    project = await create_project(client)
    null_title = await client.patch(
        f"/api/projects/{project['id']}", json={"title": None}
    )
    assert null_title.status_code == 422


async def test_project_detail_aggregates_current_assets_and_progress(
    client: AsyncClient,
    db_factory,
) -> None:
    project = await create_project(client)
    project_id = project["id"]
    async with db_factory() as database:
        database.add_all(
            [
                JdAnalysisRecord(
                    id="jd-current",
                    user_id="default",
                    project_id=project_id,
                    text="Build accessible Vue applications",
                    result_json=json.dumps(
                        {"job": {"title": "Senior Frontend Engineer"}}
                    ),
                    status="completed",
                    stage="completed",
                    progress=1.0,
                ),
                Resume(
                    id="resume-current",
                    user_id="default",
                    file_name="frontend-resume.pdf",
                    content="Vue and TypeScript",
                ),
            ]
        )
        await database.flush()
        database.add_all(
            [
                ResumeMatchRecord(
                    id="match-current",
                    user_id="default",
                    project_id=project_id,
                    resume_id="resume-current",
                    jd_analysis_id="jd-current",
                    job_description="Build accessible Vue applications",
                    result_json=json.dumps({"score": {"value": 86}}),
                    status="completed",
                    stage="completed",
                    progress=1.0,
                ),
                Session(
                    id="session-current",
                    user_id="default",
                    profile_id="interviewer-technical",
                    project_id=project_id,
                    resume_id="resume-current",
                    status="completed",
                    summary=json.dumps({"overview": "Strong technical round"}),
                ),
            ]
        )
        await database.commit()

    selected = await client.patch(
        f"/api/projects/{project_id}",
        json={
            "current_jd_analysis_id": "jd-current",
            "current_resume_id": "resume-current",
        },
    )
    assert selected.status_code == 200

    detail = await client.get(f"/api/projects/{project_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["current_jd"]["id"] == "jd-current"
    assert payload["current_resume"]["id"] == "resume-current"
    assert payload["latest_match"]["id"] == "match-current"
    assert payload["latest_match"]["score"] == 86
    assert payload["recent_sessions"][0]["id"] == "session-current"
    assert [step["status"] for step in payload["steps"]] == [
        "completed",
        "completed",
        "completed",
    ]


async def test_project_rejects_invalid_current_assets(
    client: AsyncClient,
    db_factory,
) -> None:
    project = await create_project(client)
    async with db_factory() as database:
        database.add(
            JdAnalysisRecord(
                id="foreign-jd",
                user_id="someone-else",
                text="Private JD",
                result_json="{}",
                status="completed",
            )
        )
        await database.commit()

    missing = await client.patch(
        f"/api/projects/{project['id']}",
        json={"current_resume_id": "missing-resume"},
    )
    foreign = await client.patch(
        f"/api/projects/{project['id']}",
        json={"current_jd_analysis_id": "foreign-jd"},
    )

    assert missing.status_code == 400
    assert foreign.status_code == 400


async def test_project_scoped_jd_match_and_session_creation(
    client: AsyncClient,
    db_factory,
    tmp_path: Path,
) -> None:
    project = await create_project(client)
    project_id = project["id"]

    with patch("api.jd_analysis._schedule_jd_task") as schedule_jd:
        submitted_jd = await client.post(
            f"/api/projects/{project_id}/jd-analyses",
            json={"text": "Senior Python engineer building reliable APIs"},
        )
    assert submitted_jd.status_code == 202
    jd_id = submitted_jd.json()["task_id"]
    schedule_jd.assert_called_once_with(jd_id)

    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"resume")
    async with db_factory() as database:
        jd = await database.get(JdAnalysisRecord, jd_id)
        assert jd is not None and jd.project_id == project_id
        jd.status = "completed"
        jd.stage = "completed"
        jd.progress = 1.0
        jd.result_json = json.dumps({"job": {"title": "Senior Python Engineer"}})
        database.add(
            Resume(
                id="project-resume",
                user_id="default",
                file_name="resume.pdf",
                file_path=str(resume_path),
                file_type="pdf",
                content="Python",
            )
        )
        await database.commit()

    selected = await client.patch(
        f"/api/projects/{project_id}",
        json={
            "current_jd_analysis_id": jd_id,
            "current_resume_id": "project-resume",
        },
    )
    assert selected.status_code == 200

    with patch("api.resume_matches._schedule_resume_match_task") as schedule_match:
        submitted_match = await client.post(
            f"/api/projects/{project_id}/resume-matches",
            json={"resume_id": "project-resume"},
        )
    assert submitted_match.status_code == 202
    match_id = submitted_match.json()["task_id"]
    schedule_match.assert_called_once_with(match_id)

    created_session = await client.post(
        f"/api/projects/{project_id}/sessions",
        json={"profile_id": "interviewer-technical", "mode": "text"},
    )
    assert created_session.status_code == 201
    session_id = created_session.json()["session_id"]

    async with db_factory() as database:
        match = await database.get(ResumeMatchRecord, match_id)
        session = await database.get(Session, session_id)
        assert match is not None and match.project_id == project_id
        assert match.jd_analysis_id == jd_id
        assert session is not None and session.project_id == project_id
        assert session.resume_id == "project-resume"


async def test_archived_project_rejects_new_work(client: AsyncClient) -> None:
    project = await create_project(client)
    await client.patch(
        f"/api/projects/{project['id']}", json={"archived": True}
    )

    response = await client.post(
        f"/api/projects/{project['id']}/jd-analyses",
        json={"text": "Senior data engineer responsible for production systems"},
    )

    assert response.status_code == 409


async def test_completed_jd_backfills_only_empty_project_metadata(db_factory) -> None:
    from service.project_service import sync_project_from_jd_result

    async with db_factory() as database:
        project = JobProject(
            id="draft-project",
            user_id="default",
            title="Untitled role",
            company=None,
            location="User supplied location",
            current_jd_analysis_id="draft-jd",
        )
        analysis = JdAnalysisRecord(
            id="draft-jd",
            user_id="default",
            project_id=project.id,
            text="Frontend role",
            result_json="{}",
        )
        database.add_all([project, analysis])
        await database.flush()

        await sync_project_from_jd_result(
            database,
            analysis,
            {
                "job": {
                    "title": "Senior Frontend Engineer",
                    "company": "Owl Labs",
                    "location": "Remote",
                }
            },
        )
        await database.commit()
        await database.refresh(project)

    assert project.title == "Senior Frontend Engineer"
    assert project.company == "Owl Labs"
    assert project.location == "User supplied location"
