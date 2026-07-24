"""Repository indexing helpers for GitHub analysis."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    ".next",
    ".nuxt",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

SKIP_EXTENSIONS = {
    ".7z",
    ".bz2",
    ".class",
    ".dll",
    ".dylib",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lock",
    ".o",
    ".png",
    ".pyc",
    ".pyo",
    ".rar",
    ".so",
    ".tar",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

LANGUAGE_BY_EXTENSION = {
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".py": "Python",
    ".rs": "Rust",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
}

CONFIG_FILES = {
    "Cargo.toml",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "vite.config.js",
    "vite.config.ts",
}

ENTRY_NAMES = {
    "app.py",
    "main.go",
    "main.py",
    "main.rs",
    "server.py",
    "index.js",
    "index.ts",
    "main.js",
    "main.ts",
}

CORE_DIR_NAMES = {
    "agent",
    "agents",
    "api",
    "app",
    "backend",
    "cmd",
    "components",
    "config",
    "frontend",
    "lib",
    "models",
    "pages",
    "routes",
    "server",
    "service",
    "services",
    "src",
    "tests",
    "tool",
    "tools",
}

MAX_FILE_SIZE = 500_000
MAX_TREE_DEPTH = 4
MAX_TREE_CHILDREN = 80
MAX_IMPORTANT_FILES = 24
INDEX_VERSION = 1


def should_skip_path(path: Path, repo_root: Path) -> bool:
    """Return whether a path should be excluded from indexing."""
    try:
        relative = path.relative_to(repo_root)
    except ValueError:
        return True

    if any(part in SKIP_DIRS for part in relative.parts):
        return True
    if path.is_file() and path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    if path.is_file():
        try:
            return path.stat().st_size > MAX_FILE_SIZE
        except OSError:
            return True
    return False


def build_repo_index(repo_path: str | Path, repo_url: str = "") -> dict[str, Any]:
    """Build a compact repository index from a cloned source directory."""
    start = time.time()
    root = Path(repo_path).resolve()
    files: list[Path] = []
    skipped_files = 0

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if should_skip_path(path, root):
            skipped_files += 1
            continue
        files.append(path)

    rel_files = [path.relative_to(root).as_posix() for path in files]
    suffix_counts = Counter(path.suffix.lower() for path in files)
    language_counts = Counter(
        LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        for path in files
        if LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
    )

    language = language_counts.most_common(1)[0][0] if language_counts else "Unknown"
    frameworks = _detect_frameworks(root)
    entry_points = _detect_entry_points(rel_files)
    important_files = _select_important_files(root, rel_files, entry_points)
    core_directories = _detect_core_directories(root)
    project_structure = _build_tree(root, root, 0)

    return {
        "index_version": INDEX_VERSION,
        "name": root.parent.name if root.name == "source" else root.name,
        "repo_path": str(root),
        "repo_url": repo_url,
        "language": language,
        "languages": dict(language_counts),
        "frameworks": frameworks,
        "entry_points": entry_points,
        "important_files": important_files,
        "core_directories": core_directories,
        "project_structure": project_structure,
        "repository_summary": _build_summary(language, frameworks, entry_points, core_directories),
        "stats": {
            "file_count": len(files),
            "skipped_files": skipped_files,
            "extensions": dict(suffix_counts.most_common(12)),
            "index_seconds": round(time.time() - start, 3),
        },
    }


def write_repo_index(repo_path: str | Path, repo_url: str = "") -> dict[str, Any]:
    """Build and write repo_index.json next to the source directory."""
    root = Path(repo_path).resolve()
    index = build_repo_index(root, repo_url)
    index_path = root.parent / "repo_index.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return index


def read_repo_index(repo_path: str | Path) -> dict[str, Any]:
    """Read repo_index.json for a source directory."""
    root = Path(repo_path).resolve()
    index_path = root.parent / "repo_index.json"
    return json.loads(index_path.read_text(encoding="utf-8"))


def _detect_frameworks(root: Path) -> list[str]:
    frameworks: set[str] = set()

    package_json = root / "package.json"
    if package_json.exists():
        try:
            package = json.loads(package_json.read_text(encoding="utf-8", errors="replace"))
            deps = {
                **package.get("dependencies", {}),
                **package.get("devDependencies", {}),
            }
            mapping = {
                "@vitejs/plugin-vue": "Vue",
                "express": "Express",
                "next": "Next.js",
                "nuxt": "Nuxt",
                "react": "React",
                "vite": "Vite",
                "vue": "Vue",
            }
            for dep, framework in mapping.items():
                if dep in deps:
                    frameworks.add(framework)
        except Exception:
            pass

    pyproject = root / "pyproject.toml"
    requirements = root / "requirements.txt"
    python_text = ""
    for file_path in (pyproject, requirements):
        if file_path.exists():
            python_text += file_path.read_text(encoding="utf-8", errors="replace").lower()
    python_mapping = {
        "django": "Django",
        "fastapi": "FastAPI",
        "flask": "Flask",
        "langchain": "LangChain",
        "pydantic": "Pydantic",
        "pytest": "pytest",
        "sqlalchemy": "SQLAlchemy",
    }
    for marker, framework in python_mapping.items():
        if marker in python_text:
            frameworks.add(framework)

    if (root / "go.mod").exists():
        go_text = (root / "go.mod").read_text(encoding="utf-8", errors="replace").lower()
        if "gin-gonic/gin" in go_text:
            frameworks.add("Gin")
        if "gofiber/fiber" in go_text:
            frameworks.add("Fiber")

    return sorted(frameworks)


def _detect_entry_points(rel_files: list[str]) -> list[str]:
    entries = [
        path for path in rel_files
        if Path(path).name in ENTRY_NAMES
        or path.startswith(("cmd/", "api/", "backend/api/", "src/main."))
    ]
    return entries[:12]


def _select_important_files(root: Path, rel_files: list[str], entry_points: list[str]) -> list[str]:
    selected: list[str] = []

    def add(path: str) -> None:
        if path in rel_files and path not in selected:
            selected.append(path)

    for candidate in ("README.md", "readme.md", "README.rst", "README"):
        add(candidate)
    for config in sorted(CONFIG_FILES):
        add(config)
    for entry in entry_points:
        add(entry)

    preferred_parts = (
        "/agent/",
        "/api/",
        "/model",
        "/schema",
        "/service/",
        "/tool/",
        "/tools/",
        "/route",
        "/test",
    )
    for path in rel_files:
        normalized = f"/{path.lower()}"
        if any(part in normalized for part in preferred_parts):
            add(path)
        if len(selected) >= MAX_IMPORTANT_FILES:
            break

    if len(selected) < MAX_IMPORTANT_FILES:
        for path in rel_files:
            if Path(path).suffix.lower() in LANGUAGE_BY_EXTENSION:
                add(path)
            if len(selected) >= MAX_IMPORTANT_FILES:
                break

    return selected[:MAX_IMPORTANT_FILES]


def _detect_core_directories(root: Path) -> list[str]:
    dirs: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name in SKIP_DIRS:
            continue
        if child.name.lower() in CORE_DIR_NAMES:
            dirs.append(child.name)
    return dirs[:12]


def _build_tree(root: Path, current: Path, depth: int) -> dict[str, Any]:
    if depth >= MAX_TREE_DEPTH:
        return {"name": current.name, "type": "folder", "children": []}

    children: list[dict[str, Any]] = []
    try:
        entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        entries = []

    for entry in entries:
        if len(children) >= MAX_TREE_CHILDREN:
            break
        if should_skip_path(entry, root):
            continue
        if entry.is_dir():
            children.append(_build_tree(root, entry, depth + 1))
        else:
            children.append({
                "name": entry.name,
                "type": "file",
                "language": entry.suffix.lstrip(".") or "text",
            })

    return {"name": current.name, "type": "folder", "children": children}


def _build_summary(
    language: str,
    frameworks: list[str],
    entry_points: list[str],
    core_directories: list[str],
) -> str:
    parts = [f"Primary language: {language}"]
    if frameworks:
        parts.append(f"Frameworks: {', '.join(frameworks)}")
    if entry_points:
        parts.append(f"Entry points: {', '.join(entry_points[:5])}")
    if core_directories:
        parts.append(f"Core directories: {', '.join(core_directories)}")
    return "; ".join(parts)
