from pathlib import Path

from config.settings import Settings


def test_data_paths_derive_from_single_root(tmp_path: Path) -> None:
    settings = Settings(OWLMOCK_DATA_DIR=str(tmp_path))

    assert settings.SQLITE_PATH == str(tmp_path / "db" / "app.db")
    assert settings.JSONL_ROOT == str(tmp_path / "sessions")
    assert settings.RESUME_ROOT == str(tmp_path / "resumes")
    assert settings.JD_UPLOAD_ROOT == str(tmp_path / "jd_uploads")
    assert settings.MEMORY_ROOT == str(tmp_path / "memory")
    assert settings.REPO_ROOT == str(tmp_path / "repo_cache")


def test_explicit_storage_path_overrides_data_root(tmp_path: Path) -> None:
    custom_db = tmp_path / "custom" / "owlmock.db"
    settings = Settings(
        OWLMOCK_DATA_DIR=str(tmp_path / "runtime"),
        SQLITE_PATH=str(custom_db),
    )

    assert settings.SQLITE_PATH == str(custom_db)
    assert settings.JSONL_ROOT == str(tmp_path / "runtime" / "sessions")
