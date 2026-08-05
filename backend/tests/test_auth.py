from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.auth import auth_rate_limiter
from api.auth import router as auth_router
from api.system import router as system_router
from config.settings import Settings
from security.password import hash_password
from security.session import SESSION_COOKIE, SessionSigner
from storage.db.models import Base, User


async def _make_app(tmp_path: Path):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def scoped_factory():
        async with factory() as database:
            yield database

    async with scoped_factory() as database:
        database.add(
            User(
                id="user-1",
                email="person@example.com",
                display_name="Person",
                password_hash=hash_password("correct-horse-battery"),
                is_active=True,
            )
        )
        await database.commit()

    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_SESSION_SECRET="auth-test-secret",
        OWLMOCK_COOKIE_SECURE=False,
    )
    app.state.session_signer = SessionSigner("auth-test-secret", 3600)
    app.include_router(auth_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    return app, engine, scoped_factory


async def test_login_sets_user_session_cookie(tmp_path: Path) -> None:
    app, engine, factory = await _make_app(tmp_path)
    try:
        with patch("api.auth.async_session_factory", factory):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/auth/login",
                    json={"email": "person@example.com", "password": "correct-horse-battery"},
                )

        assert response.status_code == 200
        assert response.json()["user"]["id"] == "user-1"
        cookie = response.headers["set-cookie"]
        assert f"{SESSION_COOKIE}=" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=strict" in cookie
    finally:
        await engine.dispose()


async def test_invalid_password_does_not_create_session(tmp_path: Path) -> None:
    app, engine, factory = await _make_app(tmp_path)
    try:
        with patch("api.auth.async_session_factory", factory):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/auth/login",
                    json={"email": "person@example.com", "password": "wrong-password"},
                )

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "invalid_credentials"
        assert f"{SESSION_COOKIE}=" not in response.headers.get("set-cookie", "")
    finally:
        await engine.dispose()


async def test_login_rate_limit_returns_retry_after_after_failed_burst(tmp_path: Path) -> None:
    app, engine, factory = await _make_app(tmp_path)
    app.state.settings.OWLMOCK_AUTH_RATE_LIMIT = 1
    auth_rate_limiter.clear("login:127.0.0.1")
    try:
        with patch("api.auth.async_session_factory", factory):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                first = await client.post(
                    "/api/auth/login",
                    json={"email": "person@example.com", "password": "wrong-password"},
                )
                second = await client.post(
                    "/api/auth/login",
                    json={"email": "person@example.com", "password": "wrong-password"},
                )

        assert first.status_code == 401
        assert second.status_code == 429
        assert second.json()["detail"]["code"] == "rate_limited"
        assert int(second.headers["retry-after"]) >= 1
    finally:
        auth_rate_limiter.clear("login:127.0.0.1")
        await engine.dispose()


async def test_session_and_logout_round_trip(tmp_path: Path) -> None:
    app, engine, factory = await _make_app(tmp_path)
    try:
        with patch("api.auth.async_session_factory", factory):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                login = await client.post(
                    "/api/auth/login",
                    json={"email": "person@example.com", "password": "correct-horse-battery"},
                )
                assert login.status_code == 200

                session = await client.get("/api/auth/session")
                assert session.status_code == 200
                assert session.json()["user"]["email"] == "person@example.com"

                logout = await client.post("/api/auth/logout")
                assert logout.status_code == 200
                assert logout.json() == {"authenticated": False}

                after_logout = await client.get("/api/auth/session")
                assert after_logout.status_code == 401
    finally:
        await engine.dispose()


async def test_protected_system_status_rejects_anonymous_request(tmp_path: Path) -> None:
    app, engine, _ = await _make_app(tmp_path)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/system/status")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "authentication_required"
    finally:
        await engine.dispose()
