from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.ws import router as websocket_router
from config.settings import Settings
from security.session import SESSION_COOKIE, SessionSigner


def make_app(tmp_path) -> tuple[FastAPI, SessionSigner]:
    app = FastAPI()
    app.state.settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_ADMIN_PASSWORD="test-password",
        OWLMOCK_COOKIE_SECURE=False,
    )
    signer = SessionSigner("websocket-auth-tests", 3600)
    app.state.session_signer = signer
    app.include_router(websocket_router)
    return app, signer


@pytest.mark.parametrize("cookie", [None, "invalid-token"])
def test_websocket_rejects_missing_or_invalid_cookie_before_accept(
    tmp_path,
    cookie: str | None,
) -> None:
    app, _ = make_app(tmp_path)

    with TestClient(app) as client:
        if cookie:
            client.cookies.set(SESSION_COOKIE, cookie)
        with pytest.raises(WebSocketDisconnect) as raised:
            with client.websocket_connect("/ws/voice/missing-session"):
                pass

    assert raised.value.code == 4401

