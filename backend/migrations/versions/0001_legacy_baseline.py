"""Create the pre-project OwlMock schema for fresh installations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_legacy_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parsed_json", sa.Text(), nullable=True),
        sa.Column("analysis_result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "jd_analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_jd_analyses_user_id", "jd_analyses", ["user_id"])

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

    op.create_table(
        "resume_matches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("resume_id", sa.String(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column(
            "jd_analysis_id",
            sa.String(),
            sa.ForeignKey("jd_analyses.id"),
            nullable=True,
        ),
        sa.Column("batch_id", sa.String(), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_resume_matches_user_id", "resume_matches", ["user_id"])
    op.create_index("ix_resume_matches_resume_id", "resume_matches", ["resume_id"])
    op.create_index(
        "ix_resume_matches_jd_analysis_id",
        "resume_matches",
        ["jd_analysis_id"],
    )
    op.create_index("ix_resume_matches_batch_id", "resume_matches", ["batch_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_event_ts", sa.DateTime(), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("resume_id", sa.String(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("github_repo_ids", sa.Text(), nullable=True),
        sa.Column("audio_seconds_in", sa.Float(), nullable=False),
        sa.Column("audio_seconds_out", sa.Float(), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_resume_id", "sessions", ["resume_id"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("resume_matches")
    op.drop_table("repo_analyses")
    op.drop_table("jd_analyses")
    op.drop_table("resumes")

