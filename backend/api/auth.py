from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api.deps import (
    enforce_same_origin,
    get_runtime_settings,
    get_session_signer,
    require_owner,
)
from config.settings import Settings
from security.session import OWNER_ID, SESSION_COOKIE, SessionSigner

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    runtime_settings: Settings = Depends(get_runtime_settings),
    signer: SessionSigner = Depends(get_session_signer),
    _: None = Depends(enforce_same_origin),
) -> dict[str, object]:
    configured_password = runtime_settings.OWLMOCK_ADMIN_PASSWORD
    if not configured_password:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "configuration_required",
                "message": "Set OWLMOCK_ADMIN_PASSWORD before signing in.",
            },
        )
    if not secrets.compare_digest(body.password, configured_password):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_credentials",
                "message": "The password is incorrect.",
            },
        )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=signer.issue(),
        max_age=signer.max_age_seconds,
        httponly=True,
        secure=runtime_settings.OWLMOCK_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "owner_id": OWNER_ID}


@router.get("/session")
async def get_session(owner_id: str = Depends(require_owner)) -> dict[str, object]:
    return {"authenticated": True, "owner_id": owner_id}


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    runtime_settings: Settings = Depends(get_runtime_settings),
    _: str = Depends(require_owner),
    __: None = Depends(enforce_same_origin),
) -> dict[str, bool]:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=runtime_settings.OWLMOCK_COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )
    return {"authenticated": False}
