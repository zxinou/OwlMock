"""Tests for the structured resume-to-JD matching report."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from service.resume_match_report import ResumeMatchReport


def valid_report() -> dict:
    return {
        "job": {"title": "高级前端工程师", "company": None},
        "candidate": {"headline": "Vue 前端工程师", "seniority": "中高级"},
        "score": {"value": 82, "level": "较高", "reason": "核心技术栈覆盖良好"},
        "metrics": {
            "required_coverage": 80,
            "preferred_coverage": 50,
            "skill_coverage": 75,
            "evidence_quality": 70,
        },
        "requirements": [{
            "category": "硬性要求",
            "importance": "核心",
            "status": "匹配",
            "requirement": "熟悉 Vue 3",
            "resume_evidence": "项目 A 使用 Vue 3",
            "recommendation": "面试时补充项目规模",
        }],
        "skills": [{
            "name": "Vue 3",
            "importance": "核心",
            "status": "匹配",
            "resume_evidence": "项目 A 使用 Vue 3",
            "gap": None,
        }],
        "strengths": [{"title": "技术栈吻合", "evidence": "项目 A 使用 Vue 3", "impact": "可快速上手"}],
        "gaps": [{"title": "缺少性能数据", "severity": "中", "evidence": "未提供量化指标", "action": "补充 LCP 改善数据"}],
        "interview_focus": [{"question": "如何优化首屏？", "why": "JD 强调性能", "preparation": "准备量化案例"}],
        "resume_actions": [{"priority": "高", "section": "项目经历", "action": "补充性能指标", "example": "LCP 从 3.2s 降至 1.8s"}],
        "summary": {"text": "适合投递，但需要补强量化证据。", "tags": ["Vue 3", "性能优化"]},
    }


def test_resume_match_report_validates_current_shape():
    report = ResumeMatchReport.model_validate(valid_report())
    assert report.score.value == 82
    assert report.requirements[0].status == "匹配"
    assert report.job.company is None


def test_resume_match_report_rejects_score_over_100():
    payload = valid_report()
    payload["score"]["value"] = 101
    with pytest.raises(ValidationError):
        ResumeMatchReport.model_validate(payload)


def test_resume_match_report_rejects_unknown_match_status():
    payload = valid_report()
    payload["requirements"][0]["status"] = "大概可以"
    with pytest.raises(ValidationError):
        ResumeMatchReport.model_validate(payload)


def test_resume_match_report_accepts_common_omni_aliases():
    payload = valid_report()
    payload["candidate"] = {
        "name": "Test Candidate",
        "current_title": "AI Engineer",
        "years_of_experience": "Graduate",
    }
    payload["score"] = {
        "overall": 72,
        "level": "较高",
        "metrics": {
            "technical_stack_match": 85,
            "project_experience_relevance": 90,
            "theoretical_foundation_evidence": 60,
            "engineering_capability": 75,
        },
    }
    payload.pop("metrics")

    report = ResumeMatchReport.model_validate(payload)

    assert report.candidate.headline == "AI Engineer"
    assert report.candidate.seniority == "Graduate"
    assert report.score.value == 72
    assert report.metrics.required_coverage == 85
    assert report.metrics.preferred_coverage == 90
    assert report.metrics.evidence_quality == 75
