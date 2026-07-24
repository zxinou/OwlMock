"""Tests for reload-safe resume-to-JD match tasks."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app import app
from service.task_service import task_service
from storage.db.models import Base, JdAnalysisRecord, Resume, ResumeMatchRecord


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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


@pytest.fixture(autouse=True)
def clean_tasks():
    task_service._tasks.clear()
    task_service._progress_queues.clear()
    task_service._cancel_tokens.clear()
    yield
    task_service._tasks.clear()
    task_service._progress_queues.clear()
    task_service._cancel_tokens.clear()


@pytest.fixture
async def client(db_factory):
    with (
        patch("api.resume_matches.async_session_factory", db_factory),
        patch("api.tasks.async_session_factory", db_factory),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
            yield value


@pytest.fixture
async def stored_resume(db_factory, tmp_path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"pdf")
    async with db_factory() as db:
        db.add(Resume(id="resume-1", user_id="default", file_name="resume.pdf", file_type="pdf", file_path=str(path), content="Vue developer"))
        await db.commit()
    return path


async def store_jd(
    db_factory,
    *,
    jd_id: str,
    text: str,
    title: str,
    status: str = "completed",
):
    result_json = json.dumps({"job": {"title": title}}, ensure_ascii=False)
    async with db_factory() as db:
        db.add(JdAnalysisRecord(
            id=jd_id,
            user_id="default",
            text=text,
            result_json=result_json,
            status=status,
            stage="completed" if status == "completed" else "waiting",
            progress=1.0 if status == "completed" else 0.0,
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_submit_resume_match_returns_persisted_pending_task(client, db_factory, stored_resume):
    with patch("api.resume_matches._schedule_resume_match_task") as schedule:
        response = await client.post("/api/resume-matches", json={
            "resume_id": "resume-1",
            "job_description": "高级前端工程师，要求 Vue 3 和 TypeScript",
        })

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["stage"] == "waiting"
    schedule.assert_called_once_with(payload["task_id"])
    async with db_factory() as db:
        row = await db.get(ResumeMatchRecord, payload["task_id"])
        assert row.resume_id == "resume-1"
        assert row.result_json == "{}"


@pytest.mark.asyncio
async def test_get_resume_match_returns_running_state(client, db_factory, stored_resume):
    async with db_factory() as db:
        db.add(ResumeMatchRecord(
            id="match-running", user_id="default", resume_id="resume-1",
            job_description="Frontend JD", result_json="{}", status="running",
            stage="matching", progress=0.68,
        ))
        await db.commit()

    response = await client.get("/api/resume-matches/match-running")
    assert response.status_code == 200
    assert response.json()["stage"] == "matching"
    assert response.json()["progress"] == 0.68
    assert response.json()["result"] is None


@pytest.mark.asyncio
async def test_task_status_falls_back_to_resume_match_record(client, db_factory, stored_resume):
    async with db_factory() as db:
        db.add(ResumeMatchRecord(
            id="match-db-task", user_id="default", resume_id="resume-1",
            job_description="Frontend JD", result_json="{}", status="running",
            stage="parsing_jd", progress=0.34,
        ))
        await db.commit()

    response = await client.get("/api/tasks/match-db-task")

    assert response.status_code == 200
    assert response.json()["stage"] == "parsing_jd"
    assert response.json()["progress"] == 0.34


@pytest.mark.asyncio
async def test_resume_stale_match_schedules_only_once(client, db_factory, stored_resume):
    async with db_factory() as db:
        db.add(ResumeMatchRecord(
            id="match-stale", user_id="default", resume_id="resume-1",
            job_description="Frontend JD", result_json="{}", status="running",
            stage="matching", progress=0.5,
        ))
        await db.commit()

    with patch("api.resume_matches._schedule_resume_match_task") as schedule:
        first = await client.post("/api/resume-matches/match-stale/resume")
        second = await client.post("/api/resume-matches/match-stale/resume")

    assert first.status_code == 200
    assert second.status_code == 200
    schedule.assert_called_once_with("match-stale")


@pytest.mark.asyncio
async def test_resume_pending_match_replaces_terminal_memory_task(
    client, db_factory, stored_resume
):
    async with db_factory() as db:
        db.add(ResumeMatchRecord(
            id="match-terminal-memory", user_id="default", resume_id="resume-1",
            job_description="Frontend JD", result_json="{}", status="pending",
            stage="waiting", progress=0.0,
        ))
        await db.commit()
    task_service.create_task(task_id="match-terminal-memory")
    await task_service.fail_task("match-terminal-memory", "old runner failed")

    with patch("api.resume_matches._schedule_resume_match_task") as schedule:
        response = await client.post(
            "/api/resume-matches/match-terminal-memory/resume"
        )

    assert response.status_code == 200
    assert task_service.get_task("match-terminal-memory").status.value == "pending"
    schedule.assert_called_once_with("match-terminal-memory")


@pytest.mark.asyncio
async def test_delete_resume_match_keeps_resume_file(client, db_factory, stored_resume):
    async with db_factory() as db:
        db.add(ResumeMatchRecord(
            id="match-delete", user_id="default", resume_id="resume-1",
            job_description="Frontend JD", result_json="{}",
        ))
        await db.commit()

    response = await client.delete("/api/resume-matches/match-delete")
    assert response.status_code == 204
    assert stored_resume.exists()
    async with db_factory() as db:
        assert await db.get(ResumeMatchRecord, "match-delete") is None
        assert await db.get(Resume, "resume-1") is not None


@pytest.mark.asyncio
async def test_batch_delete_resume_matches_only_removes_selected_records(
    client, db_factory, stored_resume
):
    async with db_factory() as db:
        db.add_all([
            ResumeMatchRecord(
                id="match-batch-1", user_id="default", resume_id="resume-1",
                job_description="JD 1", result_json="{}",
            ),
            ResumeMatchRecord(
                id="match-batch-2", user_id="default", resume_id="resume-1",
                job_description="JD 2", result_json="{}",
            ),
            ResumeMatchRecord(
                id="match-keep", user_id="default", resume_id="resume-1",
                job_description="JD keep", result_json="{}",
            ),
        ])
        await db.commit()

    response = await client.request("DELETE", "/api/resume-matches/batch", json={
        "ids": ["match-batch-1", "match-batch-2"],
    })

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert stored_resume.exists()
    async with db_factory() as db:
        assert await db.get(ResumeMatchRecord, "match-batch-1") is None
        assert await db.get(ResumeMatchRecord, "match-batch-2") is None
        assert await db.get(ResumeMatchRecord, "match-keep") is not None


@pytest.mark.asyncio
async def test_batch_match_uses_completed_jd_records_as_server_side_snapshots(
    client, db_factory, stored_resume
):
    await store_jd(
        db_factory,
        jd_id="jd-frontend",
        text="Frontend engineer requiring Vue and TypeScript",
        title="Frontend Engineer",
    )
    await store_jd(
        db_factory,
        jd_id="jd-fullstack",
        text="Full-stack engineer requiring FastAPI and Vue",
        title="Full-stack Engineer",
    )

    with patch("api.resume_matches._schedule_resume_match_task") as schedule:
        response = await client.post("/api/resume-matches/batch", json={
            "resume_id": "resume-1",
            "jd_analysis_ids": ["jd-frontend", "jd-fullstack"],
        })

    assert response.status_code == 202
    payload = response.json()
    assert payload["batch_id"]
    assert [item["jd_analysis_id"] for item in payload["tasks"]] == [
        "jd-frontend",
        "jd-fullstack",
    ]
    assert schedule.call_count == 2

    async with db_factory() as db:
        rows = (await db.execute(
            select(ResumeMatchRecord).where(
                ResumeMatchRecord.batch_id == payload["batch_id"]
            )
        )).scalars().all()
        assert len(rows) == 2
        assert {row.resume_id for row in rows} == {"resume-1"}
        assert {row.jd_analysis_id for row in rows} == {
            "jd-frontend",
            "jd-fullstack",
        }
        assert {row.job_description for row in rows} == {
            "Frontend engineer requiring Vue and TypeScript",
            "Full-stack engineer requiring FastAPI and Vue",
        }


@pytest.mark.asyncio
async def test_batch_match_rejects_jd_that_is_not_completed(
    client, db_factory, stored_resume
):
    await store_jd(
        db_factory,
        jd_id="jd-pending",
        text="Pending JD",
        title="Pending position",
        status="pending",
    )

    response = await client.post("/api/resume-matches/batch", json={
        "resume_id": "resume-1",
        "jd_analysis_ids": ["jd-pending"],
    })

    assert response.status_code == 400
    assert "completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_resume_match_batch_returns_ranked_completed_matches(
    client, db_factory, stored_resume
):
    for match_id, jd_id, score in [
        ("match-low", "jd-low", 62),
        ("match-high", "jd-high", 91),
    ]:
        await store_jd(
            db_factory,
            jd_id=jd_id,
            text=f"JD {jd_id}",
            title=jd_id,
        )
        async with db_factory() as db:
            db.add(ResumeMatchRecord(
                id=match_id,
                batch_id="batch-1",
                jd_analysis_id=jd_id,
                user_id="default",
                resume_id="resume-1",
                job_description=f"JD {jd_id}",
                result_json=json.dumps({"score": {"value": score}}),
                status="completed",
                stage="completed",
                progress=1.0,
            ))
            await db.commit()

    response = await client.get("/api/resume-match-batches/batch-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["progress"] == 1.0
    assert [item["id"] for item in payload["matches"]] == [
        "match-high",
        "match-low",
    ]
