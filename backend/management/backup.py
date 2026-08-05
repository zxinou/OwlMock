from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from storage.db.migrations import BASELINE_REVISION, HEAD_REVISION, PROJECT_REVISION

FORMAT_VERSION = 1
APP_VERSION = "0.1.0"
DATABASE_ARCHIVE_PATH = "db/app.db"
EXCLUDED_TOP_LEVEL = frozenset({"backups", "repo_cache"})
SUPPORTED_SCHEMA_REVISIONS = frozenset(
    {BASELINE_REVISION, PROJECT_REVISION, HEAD_REVISION}
)


class BackupError(RuntimeError):
    """Raised when a backup cannot be created or restored safely."""


@dataclass(frozen=True)
class RestoreReport:
    schema_revision: str
    restored_files: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schema_revision(database: Path) -> str:
    connection = None
    try:
        connection = sqlite3.connect(database)
        quick_check = connection.execute("PRAGMA quick_check").fetchone()
        if quick_check != ("ok",):
            raise BackupError("Backup database failed SQLite integrity check")
        row = connection.execute(
            "SELECT version_num FROM alembic_version LIMIT 1"
        ).fetchone()
    except sqlite3.Error as error:
        raise BackupError(f"Unable to read backup database: {error}") from error
    finally:
        if connection is not None:
            connection.close()
    if not row or not row[0]:
        raise BackupError("Backup database does not contain an Alembic revision")
    return str(row[0])


def _is_excluded(relative: Path) -> bool:
    first = relative.parts[0] if relative.parts else ""
    return first in EXCLUDED_TOP_LEVEL or first.startswith(".owlmock-")


def _managed_files(data_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in data_dir.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and not _is_excluded(path.relative_to(data_dir))
        ),
        key=lambda path: path.as_posix(),
    )


def _snapshot_database(source_path: Path, destination_path: Path) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    destination = sqlite3.connect(destination_path)
    try:
        source.execute("PRAGMA busy_timeout=5000")
        source.backup(destination)
    except sqlite3.Error as error:
        raise BackupError(f"Unable to snapshot SQLite database: {error}") from error
    finally:
        destination.close()
        source.close()


def _manifest(payload_root: Path) -> dict:
    files = []
    for path in sorted(payload_root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.name == "manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(payload_root).as_posix(),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    database = payload_root / DATABASE_ARCHIVE_PATH
    return {
        "format_version": FORMAT_VERSION,
        "app_version": APP_VERSION,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "database": {
            "path": DATABASE_ARCHIVE_PATH,
            "schema_revision": _schema_revision(database),
        },
        "excluded": sorted(EXCLUDED_TOP_LEVEL),
        "files": files,
    }


def create_backup(
    *,
    data_dir: Path,
    database_path: Path,
    output_path: Path,
) -> Path:
    data_dir = data_dir.resolve()
    database_path = database_path.resolve()
    output_path = output_path.resolve()
    if not database_path.is_file():
        raise BackupError(f"SQLite database does not exist: {database_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=".owlmock-backup-", dir=output_path.parent)
    )
    payload_root = temporary_root / "payload"
    payload_root.mkdir()
    try:
        snapshot_path = payload_root / DATABASE_ARCHIVE_PATH
        _snapshot_database(database_path, snapshot_path)

        database_sidecars = {
            database_path,
            Path(f"{database_path}-shm"),
            Path(f"{database_path}-wal"),
        }
        for source in _managed_files(data_dir):
            if source.resolve() in database_sidecars or source.resolve() == output_path:
                continue
            relative = source.relative_to(data_dir)
            destination = payload_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        manifest = _manifest(payload_root)
        (payload_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        temporary_archive = temporary_root / "backup.zip"
        with zipfile.ZipFile(
            temporary_archive,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as bundle:
            for path in sorted(
                payload_root.rglob("*"), key=lambda item: item.as_posix()
            ):
                if path.is_file():
                    bundle.write(path, path.relative_to(payload_root).as_posix())
        os.replace(temporary_archive, output_path)
        return output_path
    except BackupError:
        raise
    except Exception as error:
        raise BackupError(f"Unable to create backup: {error}") from error
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _safe_archive_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise BackupError("Backup manifest contains an invalid file path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise BackupError(f"Unsafe path in backup archive: {value}")
    if path.parts[0] in EXCLUDED_TOP_LEVEL or path.parts[0].startswith(".owlmock-"):
        raise BackupError(f"Excluded path found in backup archive: {value}")
    return path.as_posix()


def _validate_manifest(manifest: object) -> tuple[list[dict], str]:
    if not isinstance(manifest, dict):
        raise BackupError("Backup manifest must be a JSON object")
    if manifest.get("format_version") != FORMAT_VERSION:
        raise BackupError("Unsupported OwlMock backup format version")

    database = manifest.get("database")
    if not isinstance(database, dict) or database.get("path") != DATABASE_ARCHIVE_PATH:
        raise BackupError("Backup manifest has an invalid database path")
    schema_revision = database.get("schema_revision")
    if schema_revision not in SUPPORTED_SCHEMA_REVISIONS:
        raise BackupError(f"Unsupported database schema revision: {schema_revision}")

    raw_files = manifest.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise BackupError("Backup manifest does not contain any files")
    files: list[dict] = []
    seen: set[str] = set()
    for item in raw_files:
        if not isinstance(item, dict):
            raise BackupError("Backup manifest contains an invalid file entry")
        path = _safe_archive_path(item.get("path"))
        if path in seen:
            raise BackupError(f"Duplicate file in backup manifest: {path}")
        size = item.get("size")
        checksum = item.get("sha256")
        if not isinstance(size, int) or size < 0:
            raise BackupError(f"Invalid file size in backup manifest: {path}")
        if not isinstance(checksum, str) or len(checksum) != 64:
            raise BackupError(f"Invalid checksum in backup manifest: {path}")
        seen.add(path)
        files.append({"path": path, "size": size, "sha256": checksum})
    if DATABASE_ARCHIVE_PATH not in seen:
        raise BackupError("Backup manifest does not contain the SQLite database")
    return files, str(schema_revision)


def _extract_and_validate(archive_path: Path, stage: Path) -> tuple[list[dict], str]:
    try:
        with zipfile.ZipFile(archive_path) as bundle:
            try:
                manifest = json.loads(bundle.read("manifest.json"))
            except KeyError as error:
                raise BackupError("Backup archive does not contain manifest.json") from error
            except json.JSONDecodeError as error:
                raise BackupError("Backup manifest is not valid JSON") from error
            files, schema_revision = _validate_manifest(manifest)
            archive_names = {item.filename for item in bundle.infolist() if not item.is_dir()}
            expected_names = {"manifest.json", *(item["path"] for item in files)}
            if archive_names != expected_names:
                raise BackupError("Backup archive contents do not match its manifest")

            for item in files:
                destination = stage / Path(item["path"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item["path"]) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                if destination.stat().st_size != item["size"]:
                    raise BackupError(f"Backup file size mismatch: {item['path']}")
                if _sha256(destination) != item["sha256"]:
                    raise BackupError(f"Backup file checksum mismatch: {item['path']}")
    except zipfile.BadZipFile as error:
        raise BackupError("Backup archive is not a valid ZIP file") from error

    actual_revision = _schema_revision(stage / DATABASE_ARCHIVE_PATH)
    if actual_revision != schema_revision:
        raise BackupError("Database schema does not match the backup manifest")
    return files, schema_revision


def _swap_data_root(replacement: Path, data_dir: Path) -> None:
    """Atomically exchange two directories on Linux after a full staged restore."""
    if os.name != "posix" or os.uname().sysname != "Linux":
        raise BackupError("Atomic directory restore requires Linux")

    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise BackupError("Atomic directory restore requires Linux renameat2")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_exchange = 0x2
    result = renameat2(
        at_fdcwd,
        os.fsencode(replacement),
        at_fdcwd,
        os.fsencode(data_dir),
        rename_exchange,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise BackupError(
            f"Unable to atomically replace data directory: {os.strerror(error_number)}"
        )


def _restore_posix_data_root(
    *,
    data_dir: Path,
    stage: Path,
    files: list[dict],
    operation_root: Path,
) -> None:
    replacement = operation_root / "replacement"
    shutil.copytree(data_dir, replacement)
    for current in _managed_files(replacement):
        current.unlink()
    for item in files:
        relative = Path(item["path"])
        source = stage / relative
        destination = replacement / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
    _swap_data_root(replacement, data_dir)


def restore_backup(*, archive_path: Path, data_dir: Path) -> RestoreReport:
    archive_path = archive_path.resolve()
    data_dir = data_dir.resolve()
    if not archive_path.is_file():
        raise BackupError(f"Backup archive does not exist: {archive_path}")
    data_dir.mkdir(parents=True, exist_ok=True)

    operation_root = data_dir.parent / f".owlmock-restore-{uuid.uuid4().hex}"
    stage = operation_root / "stage"
    rollback = operation_root / "rollback"
    stage.mkdir(parents=True)
    rollback.mkdir()
    installed: list[Path] = []
    moved: list[tuple[Path, Path]] = []
    try:
        files, schema_revision = _extract_and_validate(archive_path, stage)

        if os.name == "posix":
            _restore_posix_data_root(
                data_dir=data_dir,
                stage=stage,
                files=files,
                operation_root=operation_root,
            )
            return RestoreReport(
                schema_revision=schema_revision,
                restored_files=len(files),
            )

        try:
            for current in _managed_files(data_dir):
                relative = current.relative_to(data_dir)
                saved = rollback / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                os.replace(current, saved)
                moved.append((saved, current))

            for item in files:
                relative = Path(item["path"])
                source = stage / relative
                destination = data_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, destination)
                installed.append(destination)
        except Exception as install_error:
            rollback_errors = []
            for destination in reversed(installed):
                try:
                    destination.unlink(missing_ok=True)
                except OSError as error:
                    rollback_errors.append(str(error))
            for saved, original in reversed(moved):
                try:
                    original.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(saved, original)
                except OSError as error:
                    rollback_errors.append(str(error))
            details = f"; rollback errors: {', '.join(rollback_errors)}" if rollback_errors else ""
            raise BackupError(
                f"Unable to install backup: {install_error}{details}"
            ) from install_error

        return RestoreReport(
            schema_revision=schema_revision,
            restored_files=len(files),
        )
    finally:
        shutil.rmtree(operation_root, ignore_errors=True)
