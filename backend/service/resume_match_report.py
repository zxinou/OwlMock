"""Structured report models for matching one resume against one JD."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


MatchLevel = Literal["很高", "较高", "一般", "较低", "很低"]
CoverageCategory = Literal["硬性要求", "优先条件", "加分项"]
Importance = Literal["核心", "重要", "加分"]
MatchStatus = Literal["匹配", "部分匹配", "缺失"]
Severity = Literal["高", "中", "低"]
Priority = Literal["高", "中", "低"]


class MatchJob(BaseModel):
    title: str = Field(min_length=1)
    company: str | None = None


class MatchCandidate(BaseModel):
    headline: str = Field(min_length=1)
    seniority: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def normalize_model_aliases(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        data.setdefault(
            "headline",
            data.get("current_title") or data.get("name") or "候选人",
        )
        data.setdefault(
            "seniority",
            data.get("years_of_experience") or data.get("education") or "未明确",
        )
        return data


class MatchScore(BaseModel):
    value: int = Field(ge=0, le=100)
    level: MatchLevel
    reason: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def normalize_model_aliases(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "value" not in data and "overall" in data:
            data["value"] = data["overall"]
        data.setdefault(
            "reason",
            data.get("explanation") or "基于岗位要求覆盖度与简历证据综合评估",
        )
        return data


class MatchMetrics(BaseModel):
    required_coverage: int = Field(ge=0, le=100)
    preferred_coverage: int = Field(ge=0, le=100)
    skill_coverage: int = Field(ge=0, le=100)
    evidence_quality: int = Field(ge=0, le=100)


class MatchRequirement(BaseModel):
    category: CoverageCategory
    importance: Importance
    status: MatchStatus
    requirement: str = Field(min_length=1)
    resume_evidence: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class MatchSkill(BaseModel):
    name: str = Field(min_length=1)
    importance: Importance
    status: MatchStatus
    resume_evidence: str = Field(min_length=1)
    gap: str | None = None


class MatchStrength(BaseModel):
    title: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    impact: str = Field(min_length=1)


class MatchGap(BaseModel):
    title: str = Field(min_length=1)
    severity: Severity
    evidence: str = Field(min_length=1)
    action: str = Field(min_length=1)


class MatchInterviewFocus(BaseModel):
    question: str = Field(min_length=1)
    why: str = Field(min_length=1)
    preparation: str = Field(min_length=1)


class MatchResumeAction(BaseModel):
    priority: Priority
    section: str = Field(min_length=1)
    action: str = Field(min_length=1)
    example: str | None = None


class MatchSummary(BaseModel):
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class ResumeMatchReport(BaseModel):
    job: MatchJob
    candidate: MatchCandidate
    score: MatchScore
    metrics: MatchMetrics
    requirements: list[MatchRequirement]
    skills: list[MatchSkill]
    strengths: list[MatchStrength]
    gaps: list[MatchGap]
    interview_focus: list[MatchInterviewFocus]
    resume_actions: list[MatchResumeAction]
    summary: MatchSummary

    @model_validator(mode="before")
    @classmethod
    def normalize_nested_metrics(cls, value):
        if not isinstance(value, dict) or "metrics" in value:
            return value
        data = dict(value)
        score = data.get("score")
        if not isinstance(score, dict):
            return data
        nested = score.get("metrics")
        if not isinstance(nested, dict):
            return data

        overall = score.get("value", score.get("overall", 0))

        def metric(*names: str) -> int:
            for name in names:
                candidate = nested.get(name)
                if isinstance(candidate, (int, float)):
                    return max(0, min(100, round(candidate)))
            return max(0, min(100, round(overall))) if isinstance(overall, (int, float)) else 0

        data["metrics"] = {
            "required_coverage": metric("required_coverage", "technical_stack_match"),
            "preferred_coverage": metric(
                "preferred_coverage", "project_experience_relevance"
            ),
            "skill_coverage": metric("skill_coverage", "technical_stack_match"),
            "evidence_quality": metric(
                "evidence_quality",
                "engineering_capability",
                "theoretical_foundation_evidence",
            ),
        }
        return data
