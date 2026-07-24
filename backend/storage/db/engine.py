from __future__ import annotations

import os

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from storage.db.models import Base

# Ensure parent directory exists
_db_path = os.path.abspath(settings.SQLITE_PATH)
os.makedirs(os.path.dirname(_db_path), exist_ok=True)

# Create async engine
engine = create_async_engine(
    f"sqlite+aiosqlite:///{_db_path.replace(os.sep, '/')}",
    echo=False,
    poolclass=NullPool,  # Avoids "database is locked" with aiosqlite under concurrent async tasks
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize the database, creating tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_repo_analysis_columns)
        await conn.run_sync(_ensure_jd_analysis_columns)
        await conn.run_sync(_ensure_resume_match_columns)


def _ensure_repo_analysis_columns(sync_conn) -> None:
    """Add compatible RepoAnalysis columns for existing SQLite databases."""
    columns = {
        column["name"]
        for column in inspect(sync_conn).get_columns("repo_analyses")
    }
    if "stage" not in columns:
        sync_conn.execute(
            text("ALTER TABLE repo_analyses ADD COLUMN stage VARCHAR NOT NULL DEFAULT 'waiting'")
        )
    if "progress" not in columns:
        sync_conn.execute(
            text("ALTER TABLE repo_analyses ADD COLUMN progress FLOAT NOT NULL DEFAULT 0.0")
        )
    if "repo_cache_key" not in columns:
        sync_conn.execute(
            text("ALTER TABLE repo_analyses ADD COLUMN repo_cache_key VARCHAR")
        )
    if "source_commit" not in columns:
        sync_conn.execute(
            text("ALTER TABLE repo_analyses ADD COLUMN source_commit VARCHAR")
        )
    if "updated_at" not in columns:
        sync_conn.execute(
            text("ALTER TABLE repo_analyses ADD COLUMN updated_at DATETIME")
        )


def _ensure_jd_analysis_columns(sync_conn) -> None:
    """Add reload-safe task columns without rebuilding existing JD history."""
    columns = {
        column["name"]
        for column in inspect(sync_conn).get_columns("jd_analyses")
    }
    if "source_type" not in columns:
        sync_conn.execute(
            text("ALTER TABLE jd_analyses ADD COLUMN source_type VARCHAR NOT NULL DEFAULT 'text'")
        )
    if "source_path" not in columns:
        sync_conn.execute(text("ALTER TABLE jd_analyses ADD COLUMN source_path VARCHAR"))
    if "status" not in columns:
        sync_conn.execute(
            text("ALTER TABLE jd_analyses ADD COLUMN status VARCHAR NOT NULL DEFAULT 'completed'")
        )
    if "stage" not in columns:
        sync_conn.execute(
            text("ALTER TABLE jd_analyses ADD COLUMN stage VARCHAR NOT NULL DEFAULT 'completed'")
        )
    if "progress" not in columns:
        sync_conn.execute(
            text("ALTER TABLE jd_analyses ADD COLUMN progress FLOAT NOT NULL DEFAULT 1.0")
        )
    if "error" not in columns:
        sync_conn.execute(text("ALTER TABLE jd_analyses ADD COLUMN error TEXT"))
    if "updated_at" not in columns:
        sync_conn.execute(text("ALTER TABLE jd_analyses ADD COLUMN updated_at DATETIME"))


def _ensure_resume_match_columns(sync_conn) -> None:
    """Link new match batches to analyzed JDs without rebuilding history."""
    columns = {
        column["name"]
        for column in inspect(sync_conn).get_columns("resume_matches")
    }
    if "jd_analysis_id" not in columns:
        sync_conn.execute(
            text("ALTER TABLE resume_matches ADD COLUMN jd_analysis_id VARCHAR")
        )
    if "batch_id" not in columns:
        sync_conn.execute(text("ALTER TABLE resume_matches ADD COLUMN batch_id VARCHAR"))


async def get_session() -> AsyncSession:
    """Get a new async database session."""
    async with async_session_factory() as session:
        yield session
