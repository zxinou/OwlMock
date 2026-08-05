from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import router as auth_router
from api.system import router as system_router
from config.settings import Settings
from security.session import SESSION_COOKIE, SessionSigner


def make_app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_SESSION_SECRET="system-test-secret",
        OWLMOCK_COOKIE_SECURE=False,
        DASHSCOPE_API_KEY="dashscope-secret",
        ZHIPU_API_KEY="zhipu-secret",
        GITHUB_TOKEN="github-secret",
    )
    app.state.session_signer = SessionSigner("system-test-secret", 3600)
    app.include_router(auth_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    return app


def test_liveness_is_public(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path)) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "OwlMock API"}


def test_authenticated_status_reports_capabilities_without_secrets(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE, app.state.session_signer.issue("user-1"))
        response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage"]["ready"] is True
    assert payload["capabilities"]["analysis"]["ready"] is True
    assert payload["capabilities"]["voice"]["ready"] is True
    assert payload["capabilities"]["voice"]["max_session_minutes"] == 15
    assert payload["capabilities"]["github"]["ready"] is True
    serialized = response.text
    assert "dashscope-secret" not in serialized
    assert "zhipu-secret" not in serialized
    assert "github-secret" not in serialized


def test_readiness_reports_only_missing_session_secret(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    app.state.settings.OWLMOCK_SESSION_SECRET = ""

    with TestClient(app) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["missing"] == ["OWLMOCK_SESSION_SECRET"]


def test_readiness_does_not_require_ai_provider_keys(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    app.state.settings.DASHSCOPE_API_KEY = ""
    app.state.settings.ZHIPU_API_KEY = ""

    with TestClient(app) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "missing": []}
