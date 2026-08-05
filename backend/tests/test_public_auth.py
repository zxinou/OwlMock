from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.auth import router as auth_router
from api.resume_analysis import router as resumes_router
from config.settings import Settings
from security.password import hash_password, verify_password
from security.session import SESSION_COOKIE, SessionSigner
from storage.db.models import Base, Resume


def test_password_hashes_are_salted_and_verifiable() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first != second
    assert "correct horse battery staple" not in first
    assert verify_password("correct horse battery staple", first) is True
    assert verify_password("wrong password", first) is False
    assert verify_password("correct horse battery staple", "not-a-hash") is False


def test_session_tokens_preserve_each_user_subject() -> None:
    signer = SessionSigner("multi-user-session-tests", 3600)

    first = signer.issue("user-a")
    second = signer.issue("user-b")

    assert signer.verify(first)["sub"] == "user-a"
    assert signer.verify(second)["sub"] == "user-b"
    assert signer.verify(first + "tampered") is None


async def test_registration_login_and_session_return_the_authenticated_user(
    tmp_path: Path,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def scoped_factory():
        async with factory() as database:
            yield database

    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_ALLOW_REGISTRATION=True,
        OWLMOCK_COOKIE_SECURE=False,
    )
    app.state.session_signer = SessionSigner("registration-tests", 3600)
    app.include_router(auth_router, prefix="/api")

    with patch("api.auth.async_session_factory", scoped_factory):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            registered = await client.post(
                "/api/auth/register",
                json={
                    "email": "  Person@Example.COM ",
                    "password": "a-public-password-123",
                    "display_name": "Person",
                },
            )
            assert registered.status_code == 201
            first_user = registered.json()["user"]
            assert first_user["email"] == "person@example.com"
            assert first_user["display_name"] == "Person"
            assert client.cookies.get(SESSION_COOKIE)

            session = await client.get("/api/auth/session")
            assert session.status_code == 200
            assert session.json()["user"]["id"] == first_user["id"]

            await client.post("/api/auth/logout")
            rejected = await client.post(
                "/api/auth/login",
                json={"email": "person@example.com", "password": "wrong-password"},
            )
            assert rejected.status_code == 401

            logged_in = await client.post(
                "/api/auth/login",
                json={
                    "email": "PERSON@example.com",
                    "password": "a-public-password-123",
                },
            )
            assert logged_in.status_code == 200
            assert logged_in.json()["user"]["id"] == first_user["id"]

            duplicate = await client.post(
                "/api/auth/register",
                json={
                    "email": "person@example.com",
                    "password": "another-public-password-123",
                },
            )
            assert duplicate.status_code == 409

    await engine.dispose()


async def test_registration_can_be_disabled(tmp_path: Path) -> None:
    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_ALLOW_REGISTRATION=False,
    )
    app.state.session_signer = SessionSigner("closed-registration-tests", 3600)
    app.include_router(auth_router, prefix="/api")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "person@example.com",
                "password": "a-public-password-123",
            },
        )

    assert response.status_code == 403


async def test_authenticated_users_cannot_read_each_others_resumes(
    tmp_path: Path,
) -> None:
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
                Resume(id="resume-a", user_id="user-a", content="private A"),
                Resume(id="resume-b", user_id="user-b", content="private B"),
            ]
        )
        await database.commit()

    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_COOKIE_SECURE=False,
    )
    signer = SessionSigner("resume-isolation-tests", 3600)
    app.state.session_signer = signer
    app.include_router(resumes_router, prefix="/api")

    with patch("api.resume_analysis.async_session_factory", scoped_factory):
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
            first_list = await first_client.get("/api/resumes")
            second_list = await second_client.get("/api/resumes")
            foreign = await first_client.get("/api/resumes/resume-b")

    assert [resume["id"] for resume in first_list.json()] == ["resume-a"]
    assert [resume["id"] for resume in second_list.json()] == ["resume-b"]
    assert foreign.status_code == 404
    await engine.dispose()
