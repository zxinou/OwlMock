from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

import management.backup as backup_module
from management.backup import BackupError, create_backup, restore_backup


def seed_data(data_dir: Path) -> Path:
    database = data_dir / "db" / "app.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO alembic_version VALUES ('0002_add_job_projects')"
        )
        connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
        connection.execute("INSERT INTO notes(body) VALUES ('original')")
    connection.close()

    (data_dir / "sessions").mkdir()
    (data_dir / "sessions" / "session-1.jsonl").write_text(
        '{"type":"session.started"}\n', encoding="utf-8"
    )
    (data_dir / "resumes").mkdir()
    (data_dir / "resumes" / "resume.txt").write_text("resume", encoding="utf-8")
    (data_dir / "repo_cache" / "owner" / "repo").mkdir(parents=True)
    (data_dir / "repo_cache" / "owner" / "repo" / "source.py").write_text(
        "print('cache')", encoding="utf-8"
    )
    (data_dir / ".session-secret").write_text("stable-secret", encoding="utf-8")
    return database


def test_backup_contains_consistent_database_manifest_and_excludes_repo_cache(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    database = seed_data(data_dir)

    archive = create_backup(
        data_dir=data_dir,
        database_path=database,
        output_path=tmp_path / "exports" / "owlmock.zip",
    )

    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        manifest = json.loads(bundle.read("manifest.json"))
        assert "db/app.db" in names
        assert "sessions/session-1.jsonl" in names
        assert ".session-secret" in names
        assert all(not name.startswith("repo_cache/") for name in names)
        assert manifest["format_version"] == 1
        assert manifest["database"]["schema_revision"] == "0002_add_job_projects"
        assert "repo_cache" in manifest["excluded"]
        for item in manifest["files"]:
            payload = bundle.read(item["path"])
            assert item["size"] == len(payload)
            assert item["sha256"] == hashlib.sha256(payload).hexdigest()

        restored_db = tmp_path / "snapshot.db"
        restored_db.write_bytes(bundle.read("db/app.db"))

    with sqlite3.connect(restored_db) as connection:
        assert connection.execute("SELECT body FROM notes").fetchone() == ("original",)


def test_restore_replaces_managed_data_atomically_and_keeps_repository_cache(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    database = seed_data(data_dir)
    archive = create_backup(
        data_dir=data_dir,
        database_path=database,
        output_path=tmp_path / "backup.zip",
    )

    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE notes SET body = 'mutated'")
    connection.close()
    (data_dir / "sessions" / "session-1.jsonl").write_text(
        "mutated", encoding="utf-8"
    )
    (data_dir / "sessions" / "stale.jsonl").write_text("stale", encoding="utf-8")
    cache_file = data_dir / "repo_cache" / "owner" / "repo" / "source.py"
    cache_file.write_text("keep cache", encoding="utf-8")

    report = restore_backup(archive_path=archive, data_dir=data_dir)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT body FROM notes").fetchone() == ("original",)
    assert (data_dir / "sessions" / "session-1.jsonl").read_text(
        encoding="utf-8"
    ).startswith('{"type"')
    assert not (data_dir / "sessions" / "stale.jsonl").exists()
    assert cache_file.read_text(encoding="utf-8") == "keep cache"
    assert report.schema_revision == "0002_add_job_projects"


def test_posix_restore_switches_the_data_root_as_one_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    database = seed_data(data_dir)
    archive = create_backup(
        data_dir=data_dir,
        database_path=database,
        output_path=tmp_path / "backup.zip",
    )

    swaps: list[tuple[Path, Path]] = []

    def swap_root(source: Path, destination: Path) -> None:
        swaps.append((source, destination))
        import shutil

        shutil.rmtree(destination)
        shutil.move(str(source), str(destination))

    monkeypatch.setattr(backup_module.os, "name", "posix")
    monkeypatch.setattr(backup_module, "_swap_data_root", swap_root)

    restore_backup(archive_path=archive, data_dir=data_dir)

    assert swaps and swaps == [(swaps[0][0], data_dir)]


@pytest.mark.parametrize(
    ("manifest_patch", "payload"),
    [
        ({"format_version": 999}, b"database"),
        ({}, b"tampered"),
    ],
)
def test_restore_validates_version_and_hashes_before_touching_data(
    tmp_path: Path,
    manifest_patch: dict,
    payload: bytes,
) -> None:
    data_dir = tmp_path / "data"
    database = seed_data(data_dir)
    archive = tmp_path / "invalid.zip"
    expected_hash = hashlib.sha256(b"database").hexdigest()
    manifest = {
        "format_version": 1,
        "database": {"path": "db/app.db", "schema_revision": "0002_add_job_projects"},
        "files": [
            {"path": "db/app.db", "size": len(b"database"), "sha256": expected_hash}
        ],
        "excluded": ["repo_cache"],
        **manifest_patch,
    }
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest))
        bundle.writestr("db/app.db", payload)

    with pytest.raises(BackupError):
        restore_backup(archive_path=archive, data_dir=data_dir)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT body FROM notes").fetchone() == ("original",)


def test_management_cli_creates_a_backup_with_explicit_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from management.__main__ import main

    data_dir = tmp_path / "data"
    database = seed_data(data_dir)
    output = tmp_path / "exports" / "cli-backup.zip"

    exit_code = main(
        [
            "backup",
            "--data-dir",
            str(data_dir),
            "--database",
            str(database),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert output.is_file()
    payload = json.loads(capsys.readouterr().out)
    assert Path(payload["archive"]) == output.resolve()
