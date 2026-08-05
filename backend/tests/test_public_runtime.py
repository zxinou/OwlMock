from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import Settings
from security.bootstrap import ensure_bootstrap_user
from security.password import verify_password
from security.rate_limit import AuthRateLimiter
from storage.db.models import Base, User


def test_auth_rate_limiter_returns_retry_window_after_burst() -> None:
    limiter = AuthRateLimiter(max_attempts=2, window_seconds=60)

    assert limiter.retry_after("login:127.0.0.1") is None
    limiter.record_failure("login:127.0.0.1")
    assert limiter.retry_after("login:127.0.0.1") is None
    limiter.record_failure("login:127.0.0.1")
    assert limiter.retry_after("login:127.0.0.1") is not None

    limiter.clear("login:127.0.0.1")
    assert limiter.retry_after("login:127.0.0.1") is None


@pytest.mark.asyncio
async def test_bootstrap_user_is_created_once_for_legacy_data(tmp_path: Path) -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path),
        OWLMOCK_BOOTSTRAP_EMAIL="Legacy@Example.com",
        OWLMOCK_ADMIN_PASSWORD="a-legacy-password-123",
    )

    with patch("security.bootstrap.async_session_factory", factory):
        created = await ensure_bootstrap_user(settings)
        duplicate = await ensure_bootstrap_user(settings)

    assert created is True
    assert duplicate is False
    async with factory() as database:
        user = await database.get(User, "default")
    assert user.email == "legacy@example.com"
    assert verify_password("a-legacy-password-123", user.password_hash)
    await engine.dispose()
