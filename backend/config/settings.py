from typing import ClassVar

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # API Keys
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    GITHUB_TOKEN: str = ""

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

    # Storage
    SQLITE_PATH: str = "storage/db/app.db"
    JSONL_ROOT: str = "storage/sessions"

    # Voice / Realtime
    VOICE_DEFAULT_SESSION_MINUTES: int = 15
    VOICE_INACTIVITY_TIMEOUT_SECONDS: int = 300

    # Resume storage
    RESUME_ROOT: str = "data/resumes"

    # JD image task storage stays outside backend so reload ignores uploads.
    JD_UPLOAD_ROOT: str = "../analysis_cache/jd_uploads"

    # Repo analysis & memory
    REPO_ROOT: str = "../repo_cache"
    MEMORY_ROOT: str = "storage/memory"
    CLONE_TIMEOUT: int = 120
    MAX_REPO_FILES: int = 10000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
