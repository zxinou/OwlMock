from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import router as auth_router
from api.system import router as system_router
from config.settings import Settings
from security.session import SessionSigner


def make_app(tmp_path: Path, password: str = "correct-horse") -> FastAPI:
    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_ADMIN_PASSWORD=password,
        OWLMOCK_COOKIE_SECURE=False,
    )
    app.state.session_signer = SessionSigner.from_settings(app.state.settings)
    app.include_router(auth_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    return app


def test_login_sets_owner_session_cookie(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path)) as client:
        response = client.post("/api/auth/login", json={"password": "correct-horse"})

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "owner_id": "default"}
    cookie = response.headers["set-cookie"]
    assert "owlmock_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie


def test_invalid_password_does_not_create_session(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path)) as client:
        response = client.post("/api/auth/login", json={"password": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"
    assert "owlmock_session=" not in response.headers.get("set-cookie", "")


def test_session_and_logout_round_trip(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path)) as client:
        login = client.post("/api/auth/login", json={"password": "correct-horse"})
        assert login.status_code == 200

        session = client.get("/api/auth/session")
        assert session.status_code == 200
        assert session.json() == {"authenticated": True, "owner_id": "default"}

        logout = client.post("/api/auth/logout")
        assert logout.status_code == 200
        assert logout.json() == {"authenticated": False}

        after_logout = client.get("/api/auth/session")
        assert after_logout.status_code == 401


def test_login_is_unavailable_without_configured_password(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path, password="")) as client:
        response = client.post("/api/auth/login", json={"password": "anything"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "configuration_required"


def test_protected_system_status_rejects_anonymous_request(tmp_path: Path) -> None:
    with TestClient(make_app(tmp_path)) as client:
        response = client.get("/api/system/status")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"
