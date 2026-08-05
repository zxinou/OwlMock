from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from storage.db.models import (
    Base,
    JdAnalysisRecord,
    JobProject,
    Resume,
    ResumeMatchRecord,
    Session,
)


async def test_job_project_links_current_assets_and_history() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as database:
        resume = Resume(id="resume-1", user_id="default", content="")
        jd = JdAnalysisRecord(
            id="jd-1",
            user_id="default",
            text="Senior frontend engineer",
            result_json="{}",
        )
        database.add_all([resume, jd])
        await database.flush()
        project = JobProject(
            id="project-1",
            user_id="default",
            title="Senior Frontend Engineer",
            company="Owl Labs",
            current_jd_analysis_id=jd.id,
            current_resume_id=resume.id,
        )
        database.add(project)
        await database.flush()
        database.add_all(
            [
                Session(
                    id="session-1",
                    user_id="default",
                    profile_id="interviewer-technical",
                    project_id=project.id,
                ),
                ResumeMatchRecord(
                    id="match-1",
                    user_id="default",
                    resume_id=resume.id,
                    project_id=project.id,
                    job_description=jd.text,
                ),
            ]
        )
        jd.project_id = project.id
        await database.commit()

        saved = (
            await database.execute(select(JobProject).where(JobProject.id == project.id))
        ).scalar_one()
        saved_session = await database.get(Session, "session-1")
        saved_match = await database.get(ResumeMatchRecord, "match-1")
        saved_jd = await database.get(JdAnalysisRecord, "jd-1")

    assert saved.current_jd_analysis_id == "jd-1"
    assert saved.current_resume_id == "resume-1"
    assert saved_session is not None and saved_session.project_id == "project-1"
    assert saved_match is not None and saved_match.project_id == "project-1"
    assert saved_jd is not None and saved_jd.project_id == "project-1"
    await engine.dispose()
