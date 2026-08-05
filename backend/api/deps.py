from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Cookie, Depends, HTTPException, Request

from agent.factory import AgentFactory
from config.settings import Settings, settings
from security.session import OWNER_ID, SESSION_COOKIE, SessionSigner
from storage.session.store import SessionStore


def get_runtime_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", settings)


def get_session_signer(
    request: Request,
    runtime_settings: Settings = Depends(get_runtime_settings),
) -> SessionSigner:
    signer = getattr(request.app.state, "session_signer", None)
    if signer is None:
        signer = SessionSigner.from_settings(runtime_settings)
        request.app.state.session_signer = signer
    return signer


def require_owner(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    signer: SessionSigner = Depends(get_session_signer),
) -> str:
    if not token or signer.verify(token) is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "authentication_required",
                "message": "Please sign in to this OwlMock instance.",
            },
        )
    return OWNER_ID


def enforce_same_origin(request: Request) -> None:
    """Reject browser writes whose Origin does not match the request Host."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    parsed = urlsplit(origin)
    request_host = request.headers.get("host", "").lower()
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request_host:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "cross_origin_request",
                "message": "This request must come from the OwlMock application.",
            },
        )


def get_agent_factory(request: Request) -> AgentFactory:
    """Get agent factory from app state."""
    return request.app.state.agent_factory


def get_session_store(request: Request) -> SessionStore:
    """Get session store from app state."""
    return request.app.state.session_store
