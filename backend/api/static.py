from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles

NO_CACHE = "no-cache, no-store, must-revalidate"
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
RESERVED_NAMESPACES = frozenset({"api", "ws", "assets"})


class ImmutableStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = IMMUTABLE_CACHE
        return response


def mount_spa(app: FastAPI, static_dir: Path) -> bool:
    """Mount the built frontend when it is present."""
    index_path = static_dir / "index.html"
    assets_dir = static_dir / "assets"
    if not index_path.is_file() or not assets_dir.is_dir():
        return False

    app.mount(
        "/assets",
        ImmutableStaticFiles(directory=assets_dir),
        name="frontend-assets",
    )

    async def spa_fallback(request: Request, full_path: str) -> FileResponse:
        namespace = full_path.partition("/")[0]
        if namespace in RESERVED_NAMESPACES:
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index_path, headers={"Cache-Control": NO_CACHE})

    app.add_api_route(
        "/{full_path:path}",
        spa_fallback,
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
    return True
