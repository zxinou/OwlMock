"""Add the project workspace and optional links for legacy records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_job_projects"
down_revision: str | None = "0001_legacy_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column(
            "current_jd_analysis_id",
            sa.String(),
            sa.ForeignKey(
                "jd_analyses.id",
                name="fk_job_projects_current_jd_analysis_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "current_resume_id",
            sa.String(),
            sa.ForeignKey("resumes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_job_projects_user_id", "job_projects", ["user_id"])
    op.create_index(
        "ix_job_projects_current_jd_analysis_id",
        "job_projects",
        ["current_jd_analysis_id"],
    )
    op.create_index(
        "ix_job_projects_current_resume_id",
        "job_projects",
        ["current_resume_id"],
    )
    op.create_index("ix_job_projects_archived_at", "job_projects", ["archived_at"])

    for table in ("jd_analyses", "resume_matches", "sessions"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "project_id",
                    sa.String(),
                    sa.ForeignKey(
                        "job_projects.id",
                        name=f"fk_{table}_project_id_job_projects",
                        ondelete="SET NULL",
                    ),
                    nullable=True,
                )
            )
            batch_op.create_index(f"ix_{table}_project_id", ["project_id"])


def downgrade() -> None:
    for table in ("sessions", "resume_matches", "jd_analyses"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_project_id")
            batch_op.drop_column("project_id")
    op.drop_table("job_projects")
