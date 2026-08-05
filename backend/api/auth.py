from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.deps import (
    enforce_same_origin,
    get_runtime_settings,
    get_session_signer,
    require_owner,
)
from config.settings import Settings
from security.password import hash_password, verify_password
from security.rate_limit import AuthRateLimiter
from security.session import SESSION_COOKIE, SessionSigner
from storage.db.engine import async_session_factory
from storage.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DUMMY_PASSWORD_HASH = hash_password("not-the-requested-user-password")
auth_rate_limiter = AuthRateLimiter()


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not _EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid email address")
    return email


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


def _serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _set_session_cookie(
    response: Response,
    *,
    signer: SessionSigner,
    runtime_settings: Settings,
    user_id: str,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=signer.issue(user_id),
        max_age=signer.max_age_seconds,
        httponly=True,
        secure=runtime_settings.OWLMOCK_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def _rate_limit_key(request: Request, endpoint: str) -> str:
    address = request.client.host if request.client else "unknown"
    return f"{endpoint}:{address}"


def _check_rate_limit(
    request: Request,
    endpoint: str,
    runtime_settings: Settings,
) -> str:
    auth_rate_limiter.max_attempts = max(1, runtime_settings.OWLMOCK_AUTH_RATE_LIMIT)
    auth_rate_limiter.window_seconds = max(
        1, runtime_settings.OWLMOCK_AUTH_RATE_WINDOW_SECONDS
    )
    key = _rate_limit_key(request, endpoint)
    retry_after = auth_rate_limiter.retry_after(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many authentication attempts. Try again shortly.",
            },
            headers={"Retry-After": str(retry_after)},
        )
    return key


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    request: Request,
    runtime_settings: Settings = Depends(get_runtime_settings),
    signer: SessionSigner = Depends(get_session_signer),
    _: None = Depends(enforce_same_origin),
) -> dict[str, object]:
    rate_key = _check_rate_limit(request, "register", runtime_settings)
    if not runtime_settings.OWLMOCK_ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "registration_disabled",
                "message": "New account registration is currently closed.",
            },
        )

    password_hash = await asyncio.to_thread(hash_password, body.password)
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        display_name=body.display_name,
        password_hash=password_hash,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    async with async_session_factory() as database:
        database.add(user)
        try:
            await database.commit()
        except IntegrityError as error:
            await database.rollback()
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "account_exists",
                    "message": "An account with this email already exists.",
                },
            ) from error

    _set_session_cookie(
        response,
        signer=signer,
        runtime_settings=runtime_settings,
        user_id=user.id,
    )
    auth_rate_limiter.clear(rate_key)
    return {"authenticated": True, "user": _serialize_user(user)}


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    runtime_settings: Settings = Depends(get_runtime_settings),
    signer: SessionSigner = Depends(get_session_signer),
    _: None = Depends(enforce_same_origin),
) -> dict[str, object]:
    rate_key = _check_rate_limit(request, "login", runtime_settings)
    async with async_session_factory() as database:
        user = (
            await database.execute(select(User).where(User.email == body.email))
        ).scalar_one_or_none()

    encoded = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_matches = await asyncio.to_thread(verify_password, body.password, encoded)
    if user is None or not user.is_active or not password_matches:
        auth_rate_limiter.record_failure(rate_key)
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_credentials",
                "message": "The email or password is incorrect.",
            },
        )

    _set_session_cookie(
        response,
        signer=signer,
        runtime_settings=runtime_settings,
        user_id=user.id,
    )
    auth_rate_limiter.clear(rate_key)
    return {"authenticated": True, "user": _serialize_user(user)}


@router.get("/session")
async def get_session(user_id: str = Depends(require_owner)) -> dict[str, object]:
    async with async_session_factory() as database:
        user = await database.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "authentication_required",
                "message": "Please sign in to OwlMock.",
            },
        )
    return {"authenticated": True, "user": _serialize_user(user)}


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
