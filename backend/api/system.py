from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Response, status

from api.deps import get_runtime_settings, require_owner
from config.settings import Settings

router = APIRouter(tags=["system"])


def _storage_status(runtime_settings: Settings) -> dict[str, object]:
    data_dir = runtime_settings.data_dir
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        ready = data_dir.is_dir() and os.access(data_dir, os.W_OK)
    except OSError:
        ready = False
    return {"ready": ready, "data_dir": str(data_dir)}


def _analysis_provider(runtime_settings: Settings) -> str | None:
    if runtime_settings.DASHSCOPE_API_KEY:
        return "dashscope"
    if runtime_settings.ZHIPU_API_KEY:
        return "zhipu"
    return None


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": "OwlMock API"}


@router.get("/health/ready")
async def ready(
    response: Response,
    runtime_settings: Settings = Depends(get_runtime_settings),
) -> dict[str, object]:
    missing: list[str] = []
    if not runtime_settings.OWLMOCK_ADMIN_PASSWORD:
        missing.append("OWLMOCK_ADMIN_PASSWORD")
    if not (
        runtime_settings.DASHSCOPE_API_KEY or runtime_settings.ZHIPU_API_KEY
    ):
        missing.append("DASHSCOPE_API_KEY or ZHIPU_API_KEY")
    storage = _storage_status(runtime_settings)
    if not storage["ready"]:
        missing.append("writable OWLMOCK_DATA_DIR")

    if missing:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "missing": missing}
    return {"status": "ready", "missing": []}


@router.get("/system/status")
async def system_status(
    _: str = Depends(require_owner),
    runtime_settings: Settings = Depends(get_runtime_settings),
) -> dict[str, object]:
    provider = _analysis_provider(runtime_settings)
    return {
        "storage": _storage_status(runtime_settings),
        "database": {
            "ready": Path(runtime_settings.SQLITE_PATH).parent.exists(),
            "kind": "sqlite",
        },
        "capabilities": {
            "analysis": {"ready": provider is not None, "provider": provider},
            "voice": {
                "ready": bool(runtime_settings.DASHSCOPE_API_KEY),
                "provider": "dashscope_realtime"
                if runtime_settings.DASHSCOPE_API_KEY
                else None,
            },
            "github": {"ready": bool(runtime_settings.GITHUB_TOKEN)},
            "tracing": {"ready": runtime_settings.TRACER == "langfuse"},
        },
    }
