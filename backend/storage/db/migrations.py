from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

BASELINE_REVISION = "0001_legacy_baseline"
PROJECT_REVISION = "0002_add_job_projects"
HEAD_REVISION = "0003_add_public_users"
LEGACY_TABLES = {
    "sessions",
    "repo_analyses",
    "jd_analyses",
    "resumes",
    "resume_matches",
}
LEGACY_REQUIRED_COLUMNS = {
    "sessions": {
        "id",
        "user_id",
        "profile_id",
        "status",
        "mode",
        "created_at",
        "updated_at",
        "last_event_ts",
        "event_count",
        "turn_count",
        "summary",
        "resume_id",
        "github_repo_ids",
        "audio_seconds_in",
        "audio_seconds_out",
    },
    "repo_analyses": {
        "id",
        "url",
        "owner",
        "repo",
        "status",
        "stage",
        "progress",
        "repo_cache_key",
        "source_commit",
        "result_json",
        "error",
        "analyzed_at",
        "updated_at",
    },
    "jd_analyses": {
        "id",
        "user_id",
        "text",
        "result_json",
        "source_type",
        "source_path",
        "status",
        "stage",
        "progress",
        "error",
        "created_at",
        "updated_at",
    },
    "resumes": {
        "id",
        "user_id",
        "file_name",
        "file_path",
        "file_type",
        "content",
        "parsed_json",
        "analysis_result",
        "created_at",
        "updated_at",
    },
    "resume_matches": {
        "id",
        "user_id",
        "resume_id",
        "jd_analysis_id",
        "batch_id",
        "job_description",
        "result_json",
        "status",
        "stage",
        "progress",
        "error",
        "created_at",
        "updated_at",
    },
}


def _alembic_config(database: Path) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    return config


def _legacy_schema(database: Path) -> dict[str, set[str]]:
    if not database.exists():
        return {}
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        table_names = {
            str(row[0]) for row in rows if not str(row[0]).startswith("sqlite_")
        }
        return {
            table: {
                str(column[1])
                for column in connection.execute(
                    "SELECT * FROM pragma_table_info(?)",
                    (table,),
                ).fetchall()
            }
            for table in table_names
        }
    finally:
        connection.close()


def upgrade_database(database_path: str | Path) -> None:
    """Upgrade a fresh or verified legacy SQLite database to the current schema."""
    database = Path(database_path).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    schema = _legacy_schema(database)
    tables = set(schema)
    config = _alembic_config(database)

    if tables and "alembic_version" not in tables:
        found_legacy = tables & LEGACY_TABLES
        if found_legacy != LEGACY_TABLES:
            missing = ", ".join(sorted(LEGACY_TABLES - found_legacy))
            raise RuntimeError(
                f"Refusing to stamp partial legacy schema; missing tables: {missing}"
            )
        invalid = {
            table: sorted(required - schema[table])
            for table, required in LEGACY_REQUIRED_COLUMNS.items()
            if required - schema[table]
        }
        if invalid:
            details = "; ".join(
                f"{table}: {', '.join(columns)}"
                for table, columns in sorted(invalid.items())
            )
            raise RuntimeError(
                f"Refusing to stamp incompatible legacy schema; missing columns: {details}"
            )
        command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, "head")
