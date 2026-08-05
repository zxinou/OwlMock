from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class User(Base):
    """A public OwlMock account that owns all user-scoped records."""

    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=True)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class JobProject(Base):
    """One concrete target role and its active preparation context."""

    __tablename__ = "job_projects"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, default="default", index=True)
    title = Column(String, nullable=False, default="Untitled role")
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    current_jd_analysis_id = Column(
        String,
        ForeignKey(
            "jd_analyses.id",
            name="fk_job_projects_current_jd_analysis_id",
            ondelete="SET NULL",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    current_resume_id = Column(
        String,
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    archived_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Session(Base):
    """Session metadata stored in SQLite."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    profile_id = Column(String, nullable=False)
    # active, paused, completed, abandoned
    status = Column(String, nullable=False, default="active")
    mode = Column(String, nullable=False, default="text")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_event_ts = Column(DateTime, nullable=True)
    event_count = Column(Integer, nullable=False, default=0)
    turn_count = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)  # JSON string of summary dict
    project_id = Column(
        String,
        ForeignKey("job_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True, index=True)
    github_repo_ids = Column(Text, nullable=True)  # JSON array of repo analysis IDs
    audio_seconds_in = Column(Float, nullable=False, default=0.0)
    audio_seconds_out = Column(Float, nullable=False, default=0.0)


class RepoAnalysis(Base):
    """GitHub repository analysis result stored in SQLite."""

    __tablename__ = "repo_analyses"
    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_repo_analyses_user_url"),
    )

    id = Column(String, primary_key=True)
    # Legacy tools and tests construct repository records directly. Public API
    # paths always pass the authenticated user ID; this preserves old local data.
    user_id = Column(String, nullable=False, default="default", index=True)
    url = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    repo = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, running, done, failed
    stage = Column(String, nullable=False, default="waiting")
    progress = Column(Float, nullable=False, default=0.0)
    repo_cache_key = Column(String, nullable=True, index=True)
    source_commit = Column(String, nullable=True)
    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)


class JdAnalysisRecord(Base):
    """JD analysis result stored in SQLite."""

    __tablename__ = "jd_analyses"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(
        String,
        ForeignKey("job_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)
    source_type = Column(String, nullable=False, default="text")
    source_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    stage = Column(String, nullable=False, default="waiting")
    progress = Column(Float, nullable=False, default=0.0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resume(Base):
    """Resume stored in SQLite."""

    __tablename__ = "resumes"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=True)  # Original file name
    file_path = Column(String, nullable=True)  # File storage path
    file_type = Column(String, nullable=True)  # pdf, png, jpg
    content = Column(Text, nullable=False, default="")
    parsed_json = Column(Text, nullable=True)
    analysis_result = Column(Text, nullable=True)  # Cached analysis JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResumeMatchRecord(Base):
    """Persisted resume-to-JD matching task and report."""

    __tablename__ = "resume_matches"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    project_id = Column(
        String,
        ForeignKey("job_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False, index=True)
    jd_analysis_id = Column(
        String, ForeignKey("jd_analyses.id"), nullable=True, index=True
    )
    batch_id = Column(String, nullable=True, index=True)
    job_description = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False, default="{}")
    status = Column(String, nullable=False, default="pending")
    stage = Column(String, nullable=False, default="waiting")
    progress = Column(Float, nullable=False, default=0.0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
