"""Resume management and analysis API endpoints."""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from trace import trace_analysis_request

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from agent.llm.providers.openai_compatible import build_multimodal_message
from agent.llm.router import chat_structured_with_fallback
from agent.profile_loader import ProfileLoader
from config.settings import settings
from security.session import OWNER_ID
from service.resume_media import extract_resume_text, prepare_resume_images
from storage.db.engine import async_session_factory
from storage.db.models import Resume, ResumeMatchRecord

router = APIRouter(tags=["resumes"])
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg"}
TYPE_EXTENSIONS = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
}
MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
}
MAX_FILE_SIZE = 10 * 1024 * 1024
RESUME_ROOT = Path(settings.RESUME_ROOT)
ANALYSIS_UNAVAILABLE = (
    "\u5206\u6790\u7ed3\u679c\u6682\u65f6\u65e0\u6cd5\u751f\u6210"
    "\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5"
)
ANALYZE_RESUME_PROMPT = "\u8bf7\u5206\u6790\u8fd9\u4efd\u7b80\u5386{page_hint}"


class ResumeResponse(BaseModel):
    """Response for resume metadata."""

    id: str
    file_name: str | None = None
    file_type: str | None = None
    has_analysis: bool = False
    created_at: str | None = None


class ResumeDetailResponse(BaseModel):
    """Response for resume detail."""

    id: str
    file_name: str | None = None
    file_type: str | None = None
    has_analysis: bool = False
    analysis_result: dict | None = None
    created_at: str | None = None


class ResumeStrength(BaseModel):
    text: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class ResumeWeakness(BaseModel):
    text: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class ResumeAnalysis(BaseModel):
    strengths: list[ResumeStrength]
    weaknesses: list[ResumeWeakness]
    suggestions: list[str]


@router.post("/resumes/upload")
async def upload_resume(file: UploadFile, user_id: str = "default"):
    """Upload a resume file (PDF, PNG, JPG)."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, PNG, JPG",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size cannot exceed 10MB")

    resume_id = str(uuid.uuid4())
    ext = TYPE_EXTENSIONS[file.content_type]
    user_dir = RESUME_ROOT / OWNER_ID
    os.makedirs(user_dir, exist_ok=True)
    file_path = user_dir / f"{resume_id}.{ext}"

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        text_content = extract_resume_text(content, ext)
    except Exception:
        text_content = ""

    async with async_session_factory() as db:
        resume = Resume(
            id=resume_id,
            user_id=OWNER_ID,
            file_name=file.filename,
            file_path=str(file_path),
            file_type=ext,
            content=text_content,
        )
        db.add(resume)
        await db.commit()

    return {
        "id": resume_id,
        "file_name": file.filename,
        "file_type": ext,
        "has_analysis": False,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
    }


@router.get("/resumes")
async def list_resumes(user_id: str = "default"):
    """List all resumes for a user."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Resume)
            .where(Resume.user_id == OWNER_ID)
            .order_by(Resume.created_at.desc())
        )
        resumes = result.scalars().all()

    return [
        {
            "id": r.id,
            "file_name": r.file_name,
            "file_type": r.file_type,
            "has_analysis": r.analysis_result is not None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in resumes
    ]


@router.get("/resumes/{resume_id}")
async def get_resume(resume_id: str):
    """Get resume detail with analysis result if available."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.user_id == OWNER_ID,
            )
        )
        resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    analysis = None
    if resume.analysis_result:
        try:
            analysis = json.loads(resume.analysis_result)
        except json.JSONDecodeError:
            pass

    return {
        "id": resume.id,
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "has_analysis": resume.analysis_result is not None,
        "analysis_result": analysis,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
    }


@router.delete("/resumes/{resume_id}", status_code=204)
async def delete_resume(resume_id: str):
    """Delete a resume file and its DB record."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.user_id == OWNER_ID,
            )
        )
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)

        matches = (await db.execute(
            select(ResumeMatchRecord.id).where(ResumeMatchRecord.resume_id == resume_id)
        )).scalars().all()
        if matches:
            from api.resume_matches import cancel_resume_match_task

            for match_id in matches:
                await cancel_resume_match_task(match_id)
            await db.execute(
                delete(ResumeMatchRecord).where(ResumeMatchRecord.resume_id == resume_id)
            )

        await db.delete(resume)
        await db.commit()


@router.post("/resumes/{resume_id}/analyze")
async def analyze_resume(resume_id: str, force: bool = False):
    """Analyze a resume using multimodal LLM. Returns cached result unless force=true."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.user_id == OWNER_ID,
            )
        )
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        if resume.analysis_result and not force:
            try:
                return json.loads(resume.analysis_result)
            except json.JSONDecodeError:
                pass

    profile_loader = ProfileLoader("config/agents")
    profile_loader.load_all()
    profile = profile_loader.get("resume-analyzer")

    if not profile:
        raise HTTPException(500, "resume-analyzer profile not found")

    with open(profile.prompt_template, encoding="utf-8") as f:
        prompt = f.read()

    if not resume.file_path or not os.path.exists(resume.file_path):
        raise HTTPException(500, "Resume file not found on disk")

    try:
        images = prepare_resume_images(resume.file_path, resume.file_type or "pdf")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Failed to prepare resume images: {exc}") from exc

    page_hint = f"\uff08\u5171 {len(images)} \u9875\uff09" if len(images) > 1 else ""
    user_msg = build_multimodal_message(
        ANALYZE_RESUME_PROMPT.format(page_hint=page_hint),
        images=images,
    )
    messages = [
        {"role": "system", "content": prompt},
        user_msg,
    ]

    with trace_analysis_request(
        kind="resume",
        user_id=resume.user_id,
        input_summary={
            "resume_id": resume_id,
            "file_type": resume.file_type,
            "page_count": len(images),
            "force": force,
        },
    ) as span:
        structured = await chat_structured_with_fallback(
            profile.llm,
            messages,
            ResumeAnalysis,
        )
        if structured.value is None:
            logger.warning(
                "Resume analysis failed provider=%s model=%s provider_error=%s parse_error=%s",
                profile.llm.provider,
                profile.llm.model,
                bool(structured.completion.error),
                structured.parse_error or "none",
            )
            span.update(
                output={
                    "status": "failed",
                    "provider_error": bool(structured.completion.error),
                    "parse_error": bool(structured.parse_error),
                },
                level="ERROR",
                status_message=structured.completion.error or structured.parse_error or None,
            )
            raise HTTPException(502, ANALYSIS_UNAVAILABLE)

        data = structured.value.model_dump()
        span.update(
            output={
                "status": "ok",
                "strengths": len(data["strengths"]),
                "weaknesses": len(data["weaknesses"]),
                "suggestions": len(data["suggestions"]),
            }
        )

    async with async_session_factory() as db:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if resume:
            resume.analysis_result = json.dumps(data, ensure_ascii=False)
            if not (resume.content or "").strip() and resume.file_path:
                try:
                    with open(resume.file_path, "rb") as handle:
                        resume.content = extract_resume_text(
                            handle.read(), resume.file_type or "pdf"
                        )
                except Exception:
                    pass
            await db.commit()

    return data
