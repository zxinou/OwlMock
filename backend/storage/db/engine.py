from __future__ import annotations

import asyncio
import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from storage.db.migrations import upgrade_database
from storage.db.sqlite import configure_sqlite_connection

# Ensure parent directory exists
_db_path = os.path.abspath(settings.SQLITE_PATH)
os.makedirs(os.path.dirname(_db_path), exist_ok=True)

# Create async engine
engine = create_async_engine(
    f"sqlite+aiosqlite:///{_db_path.replace(os.sep, '/')}",
    echo=False,
    poolclass=NullPool,  # Avoids "database is locked" with aiosqlite under concurrent async tasks
)


event.listen(engine.sync_engine, "connect", configure_sqlite_connection)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Upgrade the configured SQLite database without blocking the event loop."""
    await asyncio.to_thread(upgrade_database, _db_path)


async def get_session() -> AsyncSession:
    """Get a new async database session."""
    async with async_session_factory() as session:
        yield session
