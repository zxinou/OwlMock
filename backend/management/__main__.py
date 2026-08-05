from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from config.settings import settings
from management.backup import BackupError, create_backup, restore_backup


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m management")
    commands = parser.add_subparsers(dest="command", required=True)

    backup = commands.add_parser("backup", help="Create a consistent OwlMock backup")
    backup.add_argument("--data-dir", type=Path)
    backup.add_argument("--database", type=Path)
    backup.add_argument("--output", type=Path)

    restore = commands.add_parser(
        "restore",
        help="Validate and restore an OwlMock backup while the app is stopped",
    )
    restore.add_argument("archive", type=Path)
    restore.add_argument("--data-dir", type=Path)
    return parser


def _data_dir(value: Path | None) -> Path:
    return value or settings.data_dir


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "backup":
            data_dir = _data_dir(args.data_dir)
            database = args.database or (
                data_dir / "db" / "app.db"
                if args.data_dir
                else Path(settings.SQLITE_PATH)
            )
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            output = args.output or data_dir / "backups" / f"owlmock-{timestamp}.zip"
            archive = create_backup(
                data_dir=data_dir,
                database_path=database,
                output_path=output,
            )
            print(json.dumps({"status": "ok", "archive": str(archive)}))
            return 0

        report = restore_backup(
            archive_path=args.archive,
            data_dir=_data_dir(args.data_dir),
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "restored_files": report.restored_files,
                    "schema_revision": report.schema_revision,
                }
            )
        )
        return 0
    except BackupError as error:
        print(json.dumps({"status": "error", "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
