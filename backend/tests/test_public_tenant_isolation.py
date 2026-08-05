from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.github_analysis import router as github_router
from api.tasks import router as tasks_router
from config.settings import Settings
from security.session import SESSION_COOKIE, SessionSigner
from storage.db.models import Base, JdAnalysisRecord, RepoAnalysis


async def _make_isolation_app(tmp_path: Path):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def scoped_factory():
        async with factory() as database:
            yield database

    async with scoped_factory() as database:
        database.add_all(
            [
                RepoAnalysis(
                    id="repo-a",
                    user_id="user-a",
                    url="https://github.com/a/repo",
                    owner="a",
                    repo="repo",
                    status="failed",
                    stage="error",
                    progress=1.0,
                    error="provider unavailable",
                    updated_at=datetime.utcnow(),
                ),
                RepoAnalysis(
                    id="repo-b",
                    user_id="user-b",
                    url="https://github.com/b/repo",
                    owner="b",
                    repo="repo",
                    status="failed",
                    stage="error",
                    progress=1.0,
                    error="provider unavailable",
                    updated_at=datetime.utcnow(),
                ),
                JdAnalysisRecord(
                    id="task-a",
                    user_id="user-a",
                    text="private A",
                    result_json="{}",
                    status="failed",
                    stage="error",
                    progress=1.0,
                    error="provider unavailable",
                ),
                JdAnalysisRecord(
                    id="task-b",
                    user_id="user-b",
                    text="private B",
                    result_json="{}",
                    status="failed",
                    stage="error",
                    progress=1.0,
                    error="provider unavailable",
                ),
            ]
        )
        await database.commit()

    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_SESSION_SECRET="isolation-test-secret",
        OWLMOCK_COOKIE_SECURE=False,
    )
    app.state.session_signer = SessionSigner("isolation-test-secret", 3600)
    app.include_router(github_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    return app, engine, factory


async def test_users_cannot_read_or_list_each_others_analysis_and_tasks(tmp_path: Path) -> None:
    app, engine, factory = await _make_isolation_app(tmp_path)
    signer = app.state.session_signer
    try:
        with (
            patch("api.github_analysis.async_session_factory", factory),
            patch("api.tasks.async_session_factory", factory),
        ):
            async with (
                AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                    cookies={SESSION_COOKIE: signer.issue("user-a")},
                ) as first_client,
                AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                    cookies={SESSION_COOKIE: signer.issue("user-b")},
                ) as second_client,
            ):
                first_repos = await first_client.get("/api/analysis")
                second_repos = await second_client.get("/api/analysis")
                foreign_repo = await first_client.get("/api/analysis/repo-b")
                foreign_task = await first_client.get("/api/tasks/task-b")

        assert [item["id"] for item in first_repos.json()] == ["repo-a"]
        assert [item["id"] for item in second_repos.json()] == ["repo-b"]
        assert foreign_repo.status_code == 404
        assert foreign_task.status_code == 404
    finally:
        await engine.dispose()
