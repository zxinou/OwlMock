from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from storage.db.migrations import HEAD_REVISION, upgrade_database
from storage.db.sqlite import configure_sqlite_connection

LEGACY_SCHEMA = """
CREATE TABLE resumes (
    id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, file_name VARCHAR,
    file_path VARCHAR, file_type VARCHAR, content TEXT NOT NULL,
    parsed_json TEXT, analysis_result TEXT, created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
CREATE TABLE jd_analyses (
    id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, text TEXT NOT NULL,
    result_json TEXT NOT NULL, source_type VARCHAR NOT NULL, source_path VARCHAR,
    status VARCHAR NOT NULL, stage VARCHAR NOT NULL, progress FLOAT NOT NULL,
    error TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
);
CREATE TABLE repo_analyses (
    id VARCHAR PRIMARY KEY, url VARCHAR NOT NULL, owner VARCHAR NOT NULL,
    repo VARCHAR NOT NULL, status VARCHAR NOT NULL, stage VARCHAR NOT NULL,
    progress FLOAT NOT NULL, repo_cache_key VARCHAR, source_commit VARCHAR,
    result_json TEXT, error TEXT, analyzed_at DATETIME, updated_at DATETIME
);
CREATE TABLE resume_matches (
    id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, resume_id VARCHAR NOT NULL,
    jd_analysis_id VARCHAR, batch_id VARCHAR, job_description TEXT NOT NULL,
    result_json TEXT NOT NULL, status VARCHAR NOT NULL, stage VARCHAR NOT NULL,
    progress FLOAT NOT NULL, error TEXT, created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
CREATE TABLE sessions (
    id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, profile_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL, mode VARCHAR NOT NULL, created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL, last_event_ts DATETIME,
    event_count INTEGER NOT NULL, turn_count INTEGER NOT NULL, summary TEXT,
    resume_id VARCHAR, github_repo_ids TEXT, audio_seconds_in FLOAT NOT NULL,
    audio_seconds_out FLOAT NOT NULL
);
"""


def test_clean_database_upgrades_to_project_schema(tmp_path: Path) -> None:
    database = tmp_path / "clean.db"

    upgrade_database(database)

    engine = create_engine(f"sqlite:///{database.as_posix()}")
    inspector = inspect(engine)
    assert "job_projects" in inspector.get_table_names()
    assert "project_id" in {column["name"] for column in inspector.get_columns("sessions")}
    assert "project_id" in {
        column["name"] for column in inspector.get_columns("jd_analyses")
    }
    assert "project_id" in {
        column["name"] for column in inspector.get_columns("resume_matches")
    }
    for table in ("jd_analyses", "resume_matches", "sessions"):
        foreign_keys = inspector.get_foreign_keys(table)
        assert any(
            key["constrained_columns"] == ["project_id"]
            and key["referred_table"] == "job_projects"
            for key in foreign_keys
        )
        assert f"ix_{table}_project_id" in {
            index["name"] for index in inspector.get_indexes(table)
        }
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version"))
        assert revision.scalar_one() == HEAD_REVISION
    engine.dispose()


def test_legacy_database_is_stamped_and_upgraded_without_data_loss(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        LEGACY_SCHEMA
        + """
        INSERT INTO jd_analyses (
            id, user_id, text, result_json, source_type, status, stage,
            progress, created_at, updated_at
        )
        VALUES (
            'legacy-jd', 'default', 'legacy job', '{}', 'text', 'completed',
            'completed', 1.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        """
    )
    connection.commit()
    connection.close()

    upgrade_database(database)

    upgraded = sqlite3.connect(database)
    row = upgraded.execute(
        "SELECT id, user_id, project_id FROM jd_analyses WHERE id = 'legacy-jd'"
    ).fetchone()
    revision = upgraded.execute("SELECT version_num FROM alembic_version").fetchone()
    upgraded.close()

    assert row == ("legacy-jd", "default", None)
    assert revision == (HEAD_REVISION,)


def test_partial_legacy_schema_is_rejected(tmp_path: Path) -> None:
    database = tmp_path / "partial.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE sessions (id VARCHAR PRIMARY KEY)")
    connection.commit()
    connection.close()

    try:
        upgrade_database(database)
    except RuntimeError as error:
        assert "partial legacy schema" in str(error).lower()
    else:
        raise AssertionError("partial legacy schema must not be stamped")


def test_incompatible_legacy_columns_are_rejected(tmp_path: Path) -> None:
    database = tmp_path / "incompatible.db"
    connection = sqlite3.connect(database)
    connection.executescript(LEGACY_SCHEMA)
    connection.execute("ALTER TABLE sessions RENAME TO old_sessions")
    connection.execute(
        "CREATE TABLE sessions (id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL)"
    )
    connection.commit()
    connection.close()

    try:
        upgrade_database(database)
    except RuntimeError as error:
        assert "incompatible legacy schema" in str(error).lower()
        assert "profile_id" in str(error)
    else:
        raise AssertionError("incompatible legacy schema must not be stamped")


def test_sqlite_connection_settings_enable_integrity_and_wal(tmp_path: Path) -> None:
    database = tmp_path / "configured.db"
    connection = sqlite3.connect(database)

    configure_sqlite_connection(connection)

    assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert connection.execute("PRAGMA busy_timeout").fetchone() == (5000,)
    connection.close()
