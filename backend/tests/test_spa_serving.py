from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.static import mount_spa


def build_spa(tmp_path: Path) -> Path:
    static_dir = tmp_path / "dist"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text(
        "<!doctype html><title>OwlMock</title><main id='app'>workspace</main>",
        encoding="utf-8",
    )
    (assets_dir / "app-abc123.js").write_text("window.OWL=true", encoding="utf-8")
    return static_dir


def make_app(static_dir: Path) -> FastAPI:
    app = FastAPI()

    @app.get("/api/example")
    async def api_example() -> dict[str, bool]:
        return {"api": True}

    mount_spa(app, static_dir)
    return app


def test_spa_fallback_serves_root_and_nested_routes_without_caching(
    tmp_path: Path,
) -> None:
    with TestClient(make_app(build_spa(tmp_path))) as client:
        root = client.get("/")
        nested = client.get("/projects/project-42")

    assert root.status_code == 200
    assert nested.status_code == 200
    assert "OwlMock" in nested.text
    assert root.headers["cache-control"] == "no-cache, no-store, must-revalidate"
    assert nested.headers["cache-control"] == "no-cache, no-store, must-revalidate"


def test_hashed_assets_are_immutable_and_missing_assets_do_not_fall_back(
    tmp_path: Path,
) -> None:
    with TestClient(make_app(build_spa(tmp_path))) as client:
        asset = client.get("/assets/app-abc123.js")
        missing = client.get("/assets/missing.js")

    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert missing.status_code == 404
    assert "OwlMock" not in missing.text


def test_api_and_websocket_namespaces_are_never_intercepted_by_spa(
    tmp_path: Path,
) -> None:
    with TestClient(make_app(build_spa(tmp_path))) as client:
        existing_api = client.get("/api/example")
        missing_api = client.get("/api/missing")
        missing_ws = client.get("/ws/missing")

    assert existing_api.json() == {"api": True}
    assert missing_api.status_code == 404
    assert missing_ws.status_code == 404
    assert "OwlMock" not in missing_api.text
    assert "OwlMock" not in missing_ws.text


def test_mount_spa_is_a_noop_when_frontend_was_not_built(tmp_path: Path) -> None:
    app = FastAPI()

    assert mount_spa(app, tmp_path / "missing") is False
    with TestClient(app) as client:
        assert client.get("/").status_code == 404
