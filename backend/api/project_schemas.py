from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ProjectCreateRequest(BaseModel):
    title: str = Field(default="Untitled role", min_length=1, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    current_jd_analysis_id: str | None = None
    current_resume_id: str | None = None
    archived: bool | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_optional_title(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("title must not be blank")
        return value.strip()


class ProjectResumeMatchRequest(BaseModel):
    resume_id: str | None = None


class ProjectSessionRequest(BaseModel):
    profile_id: str = Field(min_length=1, max_length=160)
    mode: str = Field(default="text", pattern="^(text|voice)$")
    github_repo_ids: list[str] = Field(default_factory=list, max_length=20)
