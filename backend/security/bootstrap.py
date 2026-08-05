from __future__ import annotations

import asyncio
import re
from datetime import datetime

from sqlalchemy import select

from config.settings import Settings
from security.password import hash_password
from security.session import OWNER_ID
from storage.db.engine import async_session_factory
from storage.db.models import User

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def ensure_bootstrap_user(runtime_settings: Settings) -> bool:
    """Expose legacy single-owner data through an explicitly configured account."""
    email = runtime_settings.OWLMOCK_BOOTSTRAP_EMAIL.strip().lower()
    password = runtime_settings.OWLMOCK_ADMIN_PASSWORD
    if not email or not password or not _EMAIL_PATTERN.fullmatch(email):
        return False

    async with async_session_factory() as database:
        existing = (
            await database.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            return False
        user = User(
            id=OWNER_ID,
            email=email,
            display_name="OwlMock owner",
            password_hash=await asyncio.to_thread(hash_password, password),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        database.add(user)
        try:
            await database.commit()
        except Exception:
            await database.rollback()
            return False
    return True
