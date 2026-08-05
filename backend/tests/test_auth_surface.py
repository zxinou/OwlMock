from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app import app
from api.deps import enforce_same_origin, require_owner
from storage.db.models import Base, Resume

PUBLIC_HTTP_ROUTES = {
    ("GET", "/{full_path:path}"),
    ("HEAD", "/{full_path:path}"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    ("GET", "/api/health/live"),
    ("GET", "/api/health/ready"),
}


def _has_dependency(dependant, dependency) -> bool:
    return any(
        child.call is dependency or _has_dependency(child, dependency)
        for child in dependant.dependencies
    )


def test_every_non_public_http_route_requires_owner_authentication() -> None:
    missing: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if (method, route.path) in PUBLIC_HTTP_ROUTES:
                continue
            if not _has_dependency(route.dependant, require_owner):
                missing.append(f"{method} {route.path}")

    assert missing == []


async def test_unsafe_requests_reject_cross_origin_hosts() -> None:
    same_origin_app = FastAPI()

    @same_origin_app.post("/write", dependencies=[Depends(enforce_same_origin)])
    async def write():
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=same_origin_app), base_url="https://owlmock.test"
    ) as client:
        rejected = await client.post(
            "/write",
            headers={"Origin": "https://attacker.test"},
        )
        accepted = await client.post(
            "/write",
            headers={"Origin": "https://owlmock.test"},
        )

    assert rejected.status_code == 403
    assert accepted.status_code == 200


async def test_http_errors_include_stable_request_id_contract() -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/projects/project-does-not-exist")

    payload = response.json()
    assert response.status_code == 404
    assert payload["code"] == "not_found"
    assert payload["message"] == "Project not found"
    assert payload["request_id"]
    assert response.headers["X-Request-ID"] == payload["request_id"]


async def test_client_user_id_cannot_select_another_owners_records() -> None:
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
                Resume(id="owner-resume", user_id="default", content="owner"),
                Resume(id="foreign-resume", user_id="attacker", content="private"),
            ]
        )
        await database.commit()

    with patch("api.resume_analysis.async_session_factory", scoped_factory):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listed = await client.get("/api/resumes?user_id=attacker")
            foreign = await client.get("/api/resumes/foreign-resume")

    assert [item["id"] for item in listed.json()] == ["owner-resume"]
    assert foreign.status_code == 404
    await engine.dispose()
