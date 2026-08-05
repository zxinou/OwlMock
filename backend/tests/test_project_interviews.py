from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from security.session import OWNER_ID
from storage.db.models import Base, JdAnalysisRecord, JobProject, Session


@pytest.fixture
async def project_session_factory():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as database:
        project = JobProject(
            id="project-context",
            user_id=OWNER_ID,
            title="Platform Engineer",
        )
        database.add(project)
        await database.flush()
        jd = JdAnalysisRecord(
            id="jd-context",
            user_id=OWNER_ID,
            project_id=project.id,
            text="Build a reliable internal developer platform with Kubernetes.",
            result_json="{}",
            status="completed",
        )
        database.add(jd)
        await database.flush()
        project.current_jd_analysis_id = jd.id
        database.add(
            Session(
                id="session-context",
                user_id=OWNER_ID,
                profile_id="interviewer-technical",
                status="active",
                mode="voice",
                project_id=project.id,
            )
        )
        await database.commit()

    yield factory
    await engine.dispose()


async def test_session_context_loads_authoritative_project_jd(
    project_session_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api import chat

    monkeypatch.setattr(chat, "async_session_factory", project_session_factory)

    context = await chat._load_session_context("session-context")

    assert context["project_id"] == "project-context"
    assert context["job_description"].startswith("Build a reliable")


def test_context_builder_injects_job_description(tmp_path) -> None:
    from agent.context.builder import ContextBuilder
    from agent.context.skill_loader import SkillLoader

    builder = ContextBuilder(SkillLoader(skills_dir=str(tmp_path / "skills")))
    builder._memory_root = str(tmp_path / "memory")
    profile = MagicMock()
    profile.id = "interviewer"
    profile.prompt_template = str(tmp_path / "missing.md")
    profile.skills = []

    messages = builder.build_messages(
        profile,
        [],
        current_input="Start the interview",
        job_description="Own Kubernetes reliability and developer experience.",
    )

    assert "Kubernetes reliability" in messages[0]["content"]


def test_realtime_instructions_include_project_job_description(tmp_path) -> None:
    from agent.factory import AgentFactory

    profile = MagicMock()
    profile.prompt_template = str(tmp_path / "missing.md")
    factory = object.__new__(AgentFactory)

    instructions = factory._build_realtime_instructions(
        profile,
        resume_content="Resume evidence",
        github_repos=[],
        capy_note="",
        job_description="Own Kubernetes reliability and developer experience.",
    )

    assert "Kubernetes reliability" in instructions
