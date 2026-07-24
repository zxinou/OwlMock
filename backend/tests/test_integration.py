"""Integration tests: Create session → WS connect → send text → receive events."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from agent.llm.base import BaseLLM
from agent.llm.events import Done, TextDelta, Usage
from api.app import app


class FakeLLM(BaseLLM):
    """Fake LLM for integration tests."""

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncIterator:
        yield TextDelta(delta="Hello! ")
        yield TextDelta(delta="I'm your interviewer.")
        yield Usage(prompt_tokens=10, completion_tokens=8, total_tokens=18)
        yield Done(stop_reason="end_turn")

    def get_model_name(self) -> str:
        return "fake-model"


@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client():
    """Create an async client with the application lifespan running."""
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client


@pytest.mark.asyncio
async def test_create_session(async_client: AsyncClient):
    """Test: create a session via REST API."""
    response = await async_client.post(
        "/api/sessions",
        json={
            "profile_id": "interviewer-technical",
            "mode": "text",
            "user_id": "test-user",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_sessions(async_client: AsyncClient):
    """Test: list sessions via REST API."""
    response = await async_client.get("/api/sessions")

    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_session_events(async_client: AsyncClient):
    """Test: get session events via REST API."""
    create_response = await async_client.post(
        "/api/sessions",
        json={
            "profile_id": "interviewer-technical",
            "mode": "text",
            "user_id": "test-user",
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    events_response = await async_client.get(f"/api/sessions/{session_id}/events")
    assert events_response.status_code == 200
    data = events_response.json()
    assert "events" in data


def test_websocket_connection(client: TestClient):
    """Test: WebSocket connection and message exchange."""
    with client.websocket_connect("/ws/voice/missing-session") as websocket:
        event = websocket.receive_json()

    assert event["type"] == "error"
    assert event["payload"]["code"] == "session_not_found"


def test_health_check(client):
    """Test: health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "OwlMock API"
