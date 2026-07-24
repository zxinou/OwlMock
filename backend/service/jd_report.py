"""Structured JD report models and legacy result normalization."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DifficultyLevel = Literal["高", "中", "低"]
RequirementCategory = Literal["硬性要求", "优先条件", "加分项"]
SkillImportance = Literal["核心", "重要", "加分"]
RiskSeverity = Literal["高", "中", "低"]


class JdDifficulty(BaseModel):
    level: DifficultyLevel
    reason: str = Field(min_length=1)


class JdJob(BaseModel):
    title: str = Field(min_length=1)
    company: str | None = None
    location: str | None = None
    salary: str | None = None
    difficulty: JdDifficulty


class JdRequirement(BaseModel):
    category: RequirementCategory
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    evidence: str = Field(min_length=1)


class JdSkill(BaseModel):
    name: str = Field(min_length=1)
    importance: SkillImportance
    reason: str = Field(min_length=1)


class JdExpectation(BaseModel):
    text: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class JdRisk(BaseModel):
    title: str = Field(min_length=1)
    severity: RiskSeverity
    evidence: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class JdInterviewFocus(BaseModel):
    question: str = Field(min_length=1)
    why: str = Field(min_length=1)
    preparation: str = Field(min_length=1)


class JdSummary(BaseModel):
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class JdReport(BaseModel):
    job: JdJob
    requirements: list[JdRequirement]
    skills: list[JdSkill]
    implicit_expectations: list[JdExpectation]
    risks: list[JdRisk]
    interview_focus: list[JdInterviewFocus]
    recommendations: list[str]
    summary: JdSummary


def _legacy_category(value: object) -> RequirementCategory:
    return "硬性要求" if value == "硬性要求" else "优先条件"


def _safe_text(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def normalize_jd_report(payload: dict | None) -> JdReport:
    """Validate a current report or convert a legacy four-array JD result."""
    data = payload if isinstance(payload, dict) else {}
    if "job" in data:
        return JdReport.model_validate(data)

    requirements = []
    for item in data.get("requirements", []):
        if not isinstance(item, dict):
            continue
        text = _safe_text(item.get("text"), "未命名要求")
        requirements.append(
            {
                "category": _legacy_category(item.get("type")),
                "title": text,
                "detail": text,
                "keywords": [],
                "evidence": text,
            }
        )

    expectations = []
    for item in data.get("implicit_expectations", []):
        if not isinstance(item, dict):
            continue
        text = _safe_text(item.get("text"), "历史记录未提供隐含期待")
        expectations.append({"text": text, "evidence": text})

    risks = []
    for item in data.get("red_flags", []):
        if not isinstance(item, dict):
            continue
        text = _safe_text(item.get("text"), "历史记录未提供风险详情")
        severity = item.get("severity") if item.get("severity") in {"高", "中", "低"} else "中"
        risks.append(
            {
                "title": text,
                "severity": severity,
                "evidence": text,
                "suggestion": "面试时进一步确认该项信息",
            }
        )

    recommendations = [
        item.strip()
        for item in data.get("suggestions", [])
        if isinstance(item, str) and item.strip()
    ]
    summary_text = (
        "这是一份旧版 JD 分析记录，已转换为新版报告格式。"
        if data
        else "该分析记录暂时没有可展示的报告内容。"
    )

    return JdReport.model_validate(
        {
            "job": {
                "title": "未识别岗位",
                "company": None,
                "location": None,
                "salary": None,
                "difficulty": {
                    "level": "中",
                    "reason": "历史报告未包含岗位难度判断",
                },
            },
            "requirements": requirements,
            "skills": [],
            "implicit_expectations": expectations,
            "risks": risks,
            "interview_focus": [],
            "recommendations": recommendations,
            "summary": {"text": summary_text, "tags": ["历史报告"]},
        }
    )
