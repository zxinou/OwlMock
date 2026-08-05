"""Add public user accounts and tenant ownership for repository analyses."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_public_users"
down_revision: str | None = "0002_add_job_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_repo_analyses() -> None:
    op.create_table(
        "repo_analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("repo", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("repo_cache_key", sa.String(), nullable=True),
        sa.Column("source_commit", sa.String(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "url", name="uq_repo_analyses_user_url"),
    )
    op.create_index("ix_repo_analyses_user_id", "repo_analyses", ["user_id"])
    op.create_index(
        "ix_repo_analyses_repo_cache_key",
        "repo_analyses",
        ["repo_cache_key"],
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.rename_table("repo_analyses", "repo_analyses_legacy")
    op.execute("DROP INDEX IF EXISTS ix_repo_analyses_repo_cache_key")
    _create_repo_analyses()
    op.execute(
        """
        INSERT INTO repo_analyses (
            id, user_id, url, owner, repo, status, stage, progress,
            repo_cache_key, source_commit, result_json, error, analyzed_at, updated_at
        )
        SELECT
            id, 'default', url, owner, repo, status, stage, progress,
            repo_cache_key, source_commit, result_json, error, analyzed_at, updated_at
        FROM repo_analyses_legacy
        """
    )
    op.drop_table("repo_analyses_legacy")


def downgrade() -> None:
    op.rename_table("repo_analyses", "repo_analyses_public")
    op.execute("DROP INDEX IF EXISTS ix_repo_analyses_user_id")
    op.execute("DROP INDEX IF EXISTS ix_repo_analyses_repo_cache_key")
    op.create_table(
        "repo_analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("repo", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("repo_cache_key", sa.String(), nullable=True),
        sa.Column("source_commit", sa.String(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_repo_analyses_repo_cache_key",
        "repo_analyses",
        ["repo_cache_key"],
    )
    op.execute(
        """
        INSERT OR IGNORE INTO repo_analyses (
            id, url, owner, repo, status, stage, progress, repo_cache_key,
            source_commit, result_json, error, analyzed_at, updated_at
        )
        SELECT
            id, url, owner, repo, status, stage, progress, repo_cache_key,
            source_commit, result_json, error, analyzed_at, updated_at
        FROM repo_analyses_public
        ORDER BY updated_at DESC
        """
    )
    op.drop_table("repo_analyses_public")
    op.drop_table("users")
