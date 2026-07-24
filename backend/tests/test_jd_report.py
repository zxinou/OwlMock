"""Tests for the structured JD report contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from service.jd_report import JdReport, normalize_jd_report


def current_payload() -> dict:
    return {
        "job": {
            "title": "高级后端工程师",
            "company": None,
            "location": "深圳",
            "salary": None,
            "difficulty": {"level": "高", "reason": "要求复杂系统经验"},
        },
        "requirements": [
            {
                "category": "硬性要求",
                "title": "后端经验",
                "detail": "5 年以上后端开发经验",
                "keywords": ["Python", "Go"],
                "evidence": "5 年以上 Python 或 Go 开发经验",
            }
        ],
        "skills": [
            {"name": "Python", "importance": "核心", "reason": "主要开发语言"}
        ],
        "implicit_expectations": [
            {"text": "需要独立推进复杂模块", "evidence": "独立负责核心系统"}
        ],
        "risks": [
            {
                "title": "职责范围较宽",
                "severity": "中",
                "evidence": "负责架构、开发和运维",
                "suggestion": "面试时确认团队分工",
            }
        ],
        "interview_focus": [
            {
                "question": "如何设计高并发服务？",
                "why": "岗位强调高并发",
                "preparation": "准备容量规划和故障恢复案例",
            }
        ],
        "recommendations": ["准备系统设计案例"],
        "summary": {"text": "偏资深的后端岗位", "tags": ["高并发", "系统设计"]},
    }


def test_current_report_preserves_missing_metadata_as_none():
    report = JdReport.model_validate(current_payload())

    assert report.job.company is None
    assert report.job.salary is None
    assert report.job.difficulty.level == "高"


def test_report_rejects_unknown_requirement_category():
    payload = current_payload()
    payload["requirements"][0]["category"] = "一般要求"

    with pytest.raises(ValidationError):
        JdReport.model_validate(payload)


def test_legacy_jd_payload_normalizes_to_dashboard_report():
    legacy = {
        "requirements": [
            {"type": "硬性要求", "text": "3 年以上前端开发经验"},
            {"type": "软性要求", "text": "有跨团队协作经验优先"},
        ],
        "implicit_expectations": [{"text": "需要独立负责模块"}],
        "red_flags": [{"text": "职责边界不清晰", "severity": "中"}],
        "suggestions": ["准备复杂项目推进案例"],
    }

    report = normalize_jd_report(legacy)

    assert report.job.title == "未识别岗位"
    assert [item.category for item in report.requirements] == ["硬性要求", "优先条件"]
    assert report.risks[0].evidence == "职责边界不清晰"
    assert report.recommendations == ["准备复杂项目推进案例"]


def test_normalize_current_payload_is_idempotent():
    report = normalize_jd_report(current_payload())

    assert report.model_dump() == JdReport.model_validate(current_payload()).model_dump()


def test_jd_prompt_matches_structured_report_contract():
    prompt = Path("data/prompt/jd_analyzer.md").read_text(encoding="utf-8")

    for field in (
        "job",
        "requirements",
        "skills",
        "implicit_expectations",
        "risks",
        "interview_focus",
        "recommendations",
        "summary",
    ):
        assert f'"{field}"' in prompt
    assert "不要输出 HTML" in prompt
    assert "不得生成简历匹配分数" in prompt
    assert "evidence" in prompt
