from pathlib import Path
from typing import ClassVar

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # API Keys
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    GITHUB_TOKEN: str = ""

    # Single-owner deployment authentication.
    OWLMOCK_ADMIN_PASSWORD: str = ""
    OWLMOCK_SESSION_SECRET: str = ""
    OWLMOCK_SESSION_DAYS: int = 7
    OWLMOCK_COOKIE_SECURE: bool = True

    # Network acceleration for GitHub analysis.
    # HTTP(S)_PROXY is intentionally supported because tools like Clash/V2ray
    # commonly expose a local proxy such as http://127.0.0.1:9895.
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    GITHUB_HTTP_PROXY: str = ""
    GITHUB_HTTPS_PROXY: str = ""
    GITHUB_PROXY_BASE_URLS: str = ""
    GITHUB_PREFER_MIRROR: bool = False
    GITHUB_FETCH_STRATEGY: str = "clone_first"  # "clone_first" | "archive_first"
    GITHUB_CACHE_TTL_SECONDS: int = 300

    _PROVIDER_KEY_MAP: ClassVar[dict[str, str]] = {
        "dashscope": "DASHSCOPE_API_KEY",
        "dashscope_realtime": "DASHSCOPE_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
    }

    def get_api_key(self, provider: str) -> str:
        attr = self._PROVIDER_KEY_MAP.get(provider, "")
        return getattr(self, attr, "") if attr else ""

    @property
    def github_proxy_base_urls(self) -> list[str]:
        values = self.GITHUB_PROXY_BASE_URLS.replace("\n", ",").split(",")
        return [value.strip() for value in values if value.strip()]

    @property
    def github_http_proxy(self) -> str:
        return self.GITHUB_HTTP_PROXY or self.HTTP_PROXY

    @property
    def github_https_proxy(self) -> str:
        return self.GITHUB_HTTPS_PROXY or self.HTTPS_PROXY or self.github_http_proxy

    # Tracer
    TRACER: str = "noop"  # "noop" | "langfuse"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"  # legacy alias for LANGFUSE_BASE_URL
    LANGFUSE_TRACING_ENVIRONMENT: str = "development"

    @property
    def langfuse_base_url(self) -> str:
        return self.LANGFUSE_BASE_URL or self.LANGFUSE_HOST

    # Storage. Fine-grained paths remain supported as explicit overrides.
    OWLMOCK_DATA_DIR: str = ""
    SQLITE_PATH: str = ""
    JSONL_ROOT: str = ""

    # Voice / Realtime
    VOICE_DEFAULT_SESSION_MINUTES: int = 15
    VOICE_INACTIVITY_TIMEOUT_SECONDS: int = 300

    # Resume storage
    RESUME_ROOT: str = ""

    # JD image task storage stays outside backend so reload ignores uploads.
    JD_UPLOAD_ROOT: str = ""

    # Repo analysis & memory
    REPO_ROOT: str = ""
    MEMORY_ROOT: str = ""
    CLONE_TIMEOUT: int = 120
    MAX_REPO_FILES: int = 10000

    @model_validator(mode="after")
    def resolve_storage_paths(self) -> "Settings":
        """Derive all mutable paths from one root unless explicitly overridden."""
        legacy_defaults = {
            "SQLITE_PATH": Path("storage/db/app.db"),
            "JSONL_ROOT": Path("storage/sessions"),
            "RESUME_ROOT": Path("storage/resumes"),
            "JD_UPLOAD_ROOT": Path("../analysis_cache/jd_uploads"),
            "REPO_ROOT": Path("../repo_cache"),
            "MEMORY_ROOT": Path("storage/memory"),
        }
        if self.OWLMOCK_DATA_DIR:
            root = Path(self.OWLMOCK_DATA_DIR)
            defaults = {
                "SQLITE_PATH": root / "db" / "app.db",
                "JSONL_ROOT": root / "sessions",
                "RESUME_ROOT": root / "resumes",
                "JD_UPLOAD_ROOT": root / "jd_uploads",
                "REPO_ROOT": root / "repo_cache",
                "MEMORY_ROOT": root / "memory",
            }
        else:
            defaults = legacy_defaults

        for field, path in defaults.items():
            current = getattr(self, field)
            is_legacy_default = (
                self.OWLMOCK_DATA_DIR
                and current
                and Path(current) == legacy_defaults[field]
            )
            if not current or is_legacy_default:
                object.__setattr__(self, field, str(path))
        return self

    @property
    def data_dir(self) -> Path:
        if self.OWLMOCK_DATA_DIR:
            return Path(self.OWLMOCK_DATA_DIR)
        return Path(self.SQLITE_PATH).parent.parent

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
