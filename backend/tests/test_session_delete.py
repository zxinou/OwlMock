"""Tests for deleting interview sessions."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api import sessions as sessions_api
from api.schemas import CreateSessionRequest
from service.session_service import SessionService
from storage.db.models import Base, Session
from storage.session.store import SessionStore


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_delete_session_removes_metadata_and_event_file(
    db: AsyncSession, tmp_path: Path
) -> None:
    store = SessionStore(root_dir=str(tmp_path / "sessions"))
    service = SessionService(db_session=db, session_store=store)
    created = await service.create_session(
        CreateSessionRequest(
            profile_id="interviewer-technical",
            mode="text",
            user_id="user-1",
        )
    )
    event_file = tmp_path / "sessions" / "user-1" / f"{created.session_id}.jsonl"
    assert event_file.exists()

    deleted = await service.delete_session(created.session_id)

    assert deleted is True
    result = await db.execute(select(Session).where(Session.id == created.session_id))
    assert result.scalar_one_or_none() is None
    assert not event_file.exists()


@pytest.mark.asyncio
async def test_delete_session_returns_false_for_missing_session(
    db: AsyncSession, tmp_path: Path
) -> None:
    store = SessionStore(root_dir=str(tmp_path / "sessions"))
    service = SessionService(db_session=db, session_store=store)

    deleted = await service.delete_session("missing-session")

    assert deleted is False


class FakeDeleteSessionService:
    def __init__(self, result: bool) -> None:
        self.result = result
        self.deleted_session_id: str | None = None

    async def delete_session(self, session_id: str) -> bool:
        self.deleted_session_id = session_id
        return self.result


@pytest.mark.asyncio
async def test_delete_session_endpoint_returns_204_when_deleted() -> None:
    service = FakeDeleteSessionService(result=True)

    response = await sessions_api.delete_session(
        "session-1", session_service=service
    )

    assert response.status_code == 204
    assert service.deleted_session_id == "session-1"


@pytest.mark.asyncio
async def test_delete_session_endpoint_returns_404_when_missing() -> None:
    service = FakeDeleteSessionService(result=False)

    with pytest.raises(HTTPException) as exc:
        await sessions_api.delete_session("missing", session_service=service)

    assert exc.value.status_code == 404
