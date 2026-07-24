"""Tests for JD analysis API endpoint."""

from __future__ import annotations

import io
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app import app
from service.jd_report import JdReport
from storage.db.models import Base


def structured_result(value=None, *, error: str | None = None, parse_error: str = ""):
    result = MagicMock()
    result.value = value
    result.completion.error = error
    result.parse_error = parse_error
    return result


@pytest.fixture
def mock_profile_loader():
    """Mock ProfileLoader that returns a jd-analyzer profile."""
    profile = MagicMock()
    profile.id = "jd-analyzer"
    profile.prompt_template = "data/prompt/jd_analyzer.md"
    profile.llm.provider = "dashscope"
    profile.llm.model = "qwen-max"
    profile.llm.temperature = 0.3
    return profile


@pytest.fixture
def valid_jd_text():
    return """岗位名称：高级前端工程师
工作职责：
1. 负责公司核心产品的前端开发
2. 参与技术方案设计和评审
任职要求：
1. 3年以上前端开发经验
2. 精通 Vue/React
3. 有跨团队协作经验优先"""


@pytest.fixture
def mock_llm_response():
    return {
        "job": {
            "title": "高级前端工程师",
            "company": None,
            "location": None,
            "salary": None,
            "difficulty": {"level": "中", "reason": "要求 3 年经验和框架能力"},
        },
        "requirements": [
            {
                "category": "硬性要求",
                "title": "前端经验",
                "detail": "3 年以上前端开发经验",
                "keywords": ["前端"],
                "evidence": "3年以上前端开发经验",
            },
            {
                "category": "硬性要求",
                "title": "框架能力",
                "detail": "精通 Vue 或 React",
                "keywords": ["Vue", "React"],
                "evidence": "精通 Vue/React",
            },
            {
                "category": "优先条件",
                "title": "跨团队协作",
                "detail": "有跨团队协作经验优先",
                "keywords": [],
                "evidence": "有跨团队协作经验优先",
            },
        ],
        "skills": [
            {"name": "Vue/React", "importance": "核心", "reason": "岗位明确要求"}
        ],
        "implicit_expectations": [
            {
                "text": "需要能独立负责模块",
                "evidence": "负责公司核心产品的前端开发",
            },
        ],
        "risks": [
            {
                "title": "薪资范围缺失",
                "severity": "低",
                "evidence": "JD 未提供薪资范围",
                "suggestion": "面试前确认薪资预算",
            },
        ],
        "interview_focus": [
            {
                "question": "如何设计复杂前端模块？",
                "why": "岗位要求参与技术方案设计",
                "preparation": "准备一个架构设计案例",
            }
        ],
        "recommendations": [
            "准备 2-3 个独立负责模块的案例",
            "熟悉该公司的技术栈和产品线",
        ],
        "summary": {
            "text": "偏资深的前端岗位，重视框架能力和方案设计",
            "tags": ["前端", "Vue", "React"],
        },
    }


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite engine."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create a DB session."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def mock_db(db_engine):
    """Patch JD async_session_factory to use test engine."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def mock_factory():
        async with factory() as session:
            yield session

    with patch("api.jd_analysis.async_session_factory", mock_factory, create=True):
        yield


class TestJdAnalyzeEndpoint:
    """Tests for POST /api/jd/analyze."""

    @pytest.mark.asyncio
    async def test_analyze_jd_success(
        self, mock_profile_loader, valid_jd_text, mock_llm_response
    ):
        """Successful JD analysis returns four-dimension JSON."""
        mock_result = structured_result(JdReport.model_validate(mock_llm_response))

        with (
            patch("api.jd_analysis.ProfileLoader") as mock_loader,
            patch(
                "api.jd_analysis.chat_structured_with_fallback",
                new=AsyncMock(return_value=mock_result),
            ),
            patch("builtins.open", MagicMock()),
        ):
            mock_loader.return_value.load_all.return_value = None
            mock_loader.return_value.get.return_value = mock_profile_loader

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/jd/analyze", json={"text": valid_jd_text}
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "requirements" in data
        assert "job" in data
        assert "skills" in data
        assert "risks" in data
        assert "interview_focus" in data
        assert "recommendations" in data
        assert len(data["requirements"]) == 3
        assert data["requirements"][0]["category"] == "硬性要求"

    @pytest.mark.asyncio
    async def test_analyze_jd_empty_text(self):
        """Empty text returns 422 (Pydantic validation)."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/jd/analyze", json={"text": ""})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_analyze_jd_llm_error(self, mock_profile_loader, valid_jd_text):
        """LLM call failure returns 502."""
        mock_result = structured_result(error="Rate limit exceeded")

        with (
            patch("api.jd_analysis.ProfileLoader") as mock_loader,
            patch(
                "api.jd_analysis.chat_structured_with_fallback",
                new=AsyncMock(return_value=mock_result),
            ),
            patch("builtins.open", MagicMock()),
        ):
            mock_loader.return_value.load_all.return_value = None
            mock_loader.return_value.get.return_value = mock_profile_loader

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/jd/analyze", json={"text": valid_jd_text}
                )

        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_analyze_jd_invalid_json(
        self, mock_profile_loader, valid_jd_text
    ):
        """LLM returning non-JSON returns a user-safe 502."""
        mock_result = structured_result(parse_error="invalid JSON")

        with (
            patch("api.jd_analysis.ProfileLoader") as mock_loader,
            patch(
                "api.jd_analysis.chat_structured_with_fallback",
                new=AsyncMock(return_value=mock_result),
            ),
            patch("builtins.open", MagicMock()),
        ):
            mock_loader.return_value.load_all.return_value = None
            mock_loader.return_value.get.return_value = mock_profile_loader

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/jd/analyze", json={"text": valid_jd_text}
                )

        assert resp.status_code == 502
        assert "JSON" not in resp.json()["detail"]


class TestJdHistoryEndpoints:
    """Tests for stored JD analysis history."""

    @pytest.mark.asyncio
    async def test_analyze_jd_persists_history(
        self, mock_db, mock_profile_loader, valid_jd_text, mock_llm_response
    ):
        """Successful JD analysis is listed in history with metadata."""
        mock_result = structured_result(JdReport.model_validate(mock_llm_response))

        with (
            patch("api.jd_analysis.ProfileLoader") as mock_loader,
            patch(
                "api.jd_analysis.chat_structured_with_fallback",
                new=AsyncMock(return_value=mock_result),
            ),
            patch("builtins.open", MagicMock()),
        ):
            mock_loader.return_value.load_all.return_value = None
            mock_loader.return_value.get.return_value = mock_profile_loader

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                post_resp = await client.post(
                    "/api/jd/analyze", json={"text": valid_jd_text, "user_id": "user-1"}
                )
                list_resp = await client.get(
                    "/api/jd/analyses", params={"user_id": "user-1"}
                )

        assert post_resp.status_code == 200
        created = post_resp.json()
        assert "id" in created
        assert "created_at" in created

        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) == 1
        assert items[0]["id"] == created["id"]
        assert items[0]["text"] == valid_jd_text
        assert items[0]["result"]["requirements"][0]["title"]

    @pytest.mark.asyncio
    async def test_delete_jd_history(self, mock_db, db_session):
        """Deleting a JD history row removes it from SQL history."""
        from storage.db.models import JdAnalysisRecord

        row = JdAnalysisRecord(
            id="jd-delete-1",
            user_id="user-1",
            text="Frontend engineer JD",
            result_json='{"requirements":[],"implicit_expectations":[],"red_flags":[],"suggestions":[]}',
        )
        db_session.add(row)
        await db_session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            delete_resp = await client.delete("/api/jd/analyses/jd-delete-1")

        assert delete_resp.status_code == 204
        result = await db_session.execute(
            select(JdAnalysisRecord).where(JdAnalysisRecord.id == "jd-delete-1")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_jd_history_not_found(self, mock_db):
        """Deleting a missing JD history row returns 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/jd/analyses/missing")

        assert resp.status_code == 404


class TestJdImageAnalyzeEndpoint:
    """Tests for JD image analysis API endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_jd_image_success(
        self, mock_db, mock_profile_loader, mock_llm_response
    ):
        """Uploaded JD image is sent as a multimodal message and persisted."""
        mock_result = structured_result(JdReport.model_validate(mock_llm_response))
        captured_messages = None

        async def fake_chat(llm_config, messages, schema):
            nonlocal captured_messages
            captured_messages = messages
            return mock_result

        with (
            patch("api.jd_analysis.ProfileLoader") as mock_loader,
            patch(
                "api.jd_analysis.chat_structured_with_fallback",
                new=AsyncMock(side_effect=fake_chat),
            ),
            patch("builtins.open", MagicMock()),
        ):
            mock_loader.return_value.load_all.return_value = None
            mock_loader.return_value.get.return_value = mock_profile_loader

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/jd/analyze-image",
                    files={"file": ("jd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
                    data={"user_id": "user-1"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["source_type"] == "image"
        assert captured_messages is not None
        user_message = captured_messages[1]
        assert isinstance(user_message["content"], list)
        assert user_message["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )

    @pytest.mark.asyncio
    async def test_analyze_jd_image_rejects_unsupported_type(self, mock_db):
        """Only PNG and JPEG JD screenshots are accepted."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/jd/analyze-image",
                files={"file": ("jd.txt", io.BytesIO(b"text"), "text/plain")},
            )

        assert resp.status_code == 400
