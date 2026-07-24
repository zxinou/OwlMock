"""Tests for reload-safe asynchronous JD analysis endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app import app
from service.task_service import task_service
from storage.db.models import Base, JdAnalysisRecord


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
def clean_task_service():
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
        patch("api.jd_analysis.async_session_factory", db_factory),
        patch("api.tasks.async_session_factory", db_factory),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client


@pytest.mark.asyncio
async def test_submit_text_jd_returns_pending_task(client, db_factory):
    with patch("api.jd_analysis._schedule_jd_task", create=True) as schedule:
        response = await client.post(
            "/api/jd/analyses",
            json={"text": "高级后端工程师，要求 5 年 Python 经验"},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["stage"] == "waiting"
    assert payload["progress"] == 0.0
    schedule.assert_called_once_with(payload["task_id"])

    async with db_factory() as db:
        row = await db.get(JdAnalysisRecord, payload["task_id"])
        assert row is not None
        assert row.text.startswith("高级后端工程师")
        assert row.result_json == "{}"


@pytest.mark.asyncio
async def test_get_jd_analysis_returns_persisted_running_state(client, db_factory):
    async with db_factory() as db:
        db.add(
            JdAnalysisRecord(
                id="jd-running",
                user_id="default",
                text="Backend JD",
                result_json="{}",
                status="running",
                stage="analyzing",
                progress=0.62,
            )
        )
        await db.commit()

    response = await client.get("/api/jd/analyses/jd-running")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["stage"] == "analyzing"
    assert payload["progress"] == 0.62
    assert payload["result"] is None


@pytest.mark.asyncio
async def test_task_status_falls_back_to_jd_database_record(client, db_factory):
    async with db_factory() as db:
        db.add(
            JdAnalysisRecord(
                id="jd-db-task",
                user_id="default",
                text="Backend JD",
                result_json="{}",
                status="running",
                stage="structuring",
                progress=0.35,
            )
        )
        await db.commit()

    response = await client.get("/api/tasks/jd-db-task")

    assert response.status_code == 200
    assert response.json()["stage"] == "structuring"
    assert response.json()["progress"] == 0.35


@pytest.mark.asyncio
async def test_resume_stale_jd_task_schedules_only_once(client, db_factory):
    async with db_factory() as db:
        db.add(
            JdAnalysisRecord(
                id="jd-stale",
                user_id="default",
                text="Backend JD",
                result_json="{}",
                status="running",
                stage="analyzing",
                progress=0.5,
            )
        )
        await db.commit()

    with patch("api.jd_analysis._schedule_jd_task", create=True) as schedule:
        first = await client.post("/api/jd/analyses/jd-stale/resume")
        second = await client.post("/api/jd/analyses/jd-stale/resume")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["task_id"] == "jd-stale"
    assert second.json()["task_id"] == "jd-stale"
    schedule.assert_called_once_with("jd-stale")


@pytest.mark.asyncio
async def test_delete_image_jd_cleans_persisted_source(client, db_factory, tmp_path):
    image_path = tmp_path / "jd.png"
    image_path.write_bytes(b"image")
    async with db_factory() as db:
        db.add(
            JdAnalysisRecord(
                id="jd-image-delete",
                user_id="default",
                text="图片 JD：jd.png",
                result_json="{}",
                source_type="image",
                source_path=str(image_path),
            )
        )
        await db.commit()

    response = await client.delete("/api/jd/analyses/jd-image-delete")

    assert response.status_code == 204
    assert not image_path.exists()
    async with db_factory() as db:
        assert await db.get(JdAnalysisRecord, "jd-image-delete") is None


@pytest.mark.asyncio
async def test_batch_delete_jd_analyses_removes_selected_rows_and_sources(
    client, db_factory, tmp_path
):
    image_path = tmp_path / "batch-jd.png"
    image_path.write_bytes(b"image")
    async with db_factory() as db:
        db.add_all([
            JdAnalysisRecord(
                id="jd-batch-text", user_id="default", text="Text JD",
                result_json="{}",
            ),
            JdAnalysisRecord(
                id="jd-batch-image", user_id="default", text="Image JD",
                result_json="{}", source_type="image", source_path=str(image_path),
            ),
            JdAnalysisRecord(
                id="jd-keep", user_id="default", text="Keep JD",
                result_json="{}",
            ),
        ])
        await db.commit()

    response = await client.request("DELETE", "/api/jd/analyses/batch", json={
        "ids": ["jd-batch-text", "jd-batch-image"],
    })

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert not image_path.exists()
    async with db_factory() as db:
        assert await db.get(JdAnalysisRecord, "jd-batch-text") is None
        assert await db.get(JdAnalysisRecord, "jd-batch-image") is None
        assert await db.get(JdAnalysisRecord, "jd-keep") is not None
