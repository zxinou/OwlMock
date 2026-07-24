"""read_repo_context tool - load the generated repository index."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from service.repo_indexer import read_repo_index
from tool.base import ToolContext, ToolResult, tool


class ReadRepoContextArgs(BaseModel):
    """Arguments for read_repo_context."""


@tool
async def read_repo_context(args: ReadRepoContextArgs, ctx: ToolContext) -> ToolResult:
    """Read the generated Repository Context for the current cloned repository."""
    if not ctx.current_repo_path:
        return ToolResult.err(
            code="missing_repo",
            message="No current repository path is available. Call clone_repo first.",
            summary="Repository context unavailable",
        )

    repo_path = Path(ctx.current_repo_path)
    index_path = repo_path.parent / "repo_index.json"
    if not index_path.exists():
        return ToolResult.err(
            code="index_not_found",
            message=f"Repository index not found: {index_path}",
            summary="Repository index not found",
        )

    try:
        data = read_repo_index(repo_path)
    except Exception as exc:
        return ToolResult.err(
            code="index_read_error",
            message=f"Failed to read repository index: {exc}",
            summary="Repository index read failed",
        )

    if ctx.repo_url and not data.get("repo_url"):
        data["repo_url"] = ctx.repo_url

    return ToolResult.ok(
        data=data,
        summary=f"Loaded repository context ({len(data.get('important_files', []))} important files)",
    )
