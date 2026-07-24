"""Regression tests for active LLM provider subclass behaviors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.llm.events import (
    TextDelta,
    ThinkingDelta,
)
from agent.llm.providers.dashscope_compat import DashScopeCompatLLM
from agent.llm.providers.zhipu import ZhipuLLM
from config.settings import settings
from tests.test_openai_compatible import MockAsyncIterator, make_mock_chunk


class TestDashScopeCompatLLM:
    """Test DashScope-specific behaviors."""

    @pytest.fixture
    def llm(self) -> DashScopeCompatLLM:
        """Create a DashScopeCompatLLM instance with a mock client."""
        llm = DashScopeCompatLLM(
            api_key="test-key",
            model="qwen-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return llm

    @pytest.fixture
    def llm_with_thinking(self) -> DashScopeCompatLLM:
        """Create a DashScopeCompatLLM instance with enable_thinking."""
        llm = DashScopeCompatLLM(
            api_key="test-key",
            model="qwen-max",
            enable_thinking=True,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return llm

    @pytest.mark.asyncio
    async def test_thinking_model(self, llm_with_thinking: DashScopeCompatLLM) -> None:
        """Test: DashScope thinking models map reasoning_content to ThinkingDelta."""
        usage_mock = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        chunks = [
            make_mock_chunk(reasoning_content="Analyzing the question..."),
            make_mock_chunk(content="The answer is 42"),
            make_mock_chunk(content="", finish_reason="stop", usage=usage_mock),
        ]

        llm_with_thinking.client.chat.completions.create = AsyncMock(
            return_value=MockAsyncIterator(chunks)
        )

        events = []
        async for event in llm_with_thinking.stream([{"role": "user", "content": "Test"}]):
            events.append(event)

        assert len(events) == 4
        assert isinstance(events[0], ThinkingDelta)
        assert isinstance(events[1], TextDelta)

    def test_model_name(self, llm: DashScopeCompatLLM) -> None:
        """Test: get_model_name returns the configured model."""
        assert llm.get_model_name() == "qwen-max"

    def test_base_url(self, llm: DashScopeCompatLLM) -> None:
        """Test: base_url is set to DashScope compatible API."""
        assert str(llm.client.base_url).rstrip("/") == "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def test_extra_params_no_thinking(self, llm: DashScopeCompatLLM) -> None:
        """Test: no extra params when enable_thinking is False."""
        params = llm._extra_request_params()
        assert params == {}

    def test_extra_params_with_thinking(self, llm_with_thinking: DashScopeCompatLLM) -> None:
        """Test: extra params include enable_thinking when enabled."""
        params = llm_with_thinking._extra_request_params()
        assert params == {"extra_body": {"enable_thinking": True}}

    def test_base_url_uses_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test: base_url can be configured through settings."""
        monkeypatch.setattr(
            settings,
            "DASHSCOPE_BASE_URL",
            "https://workspace.example.com/compatible-mode/v1",
        )

        llm = DashScopeCompatLLM(api_key="test-key", model="qwen-max")

        assert str(llm.client.base_url).rstrip("/") == "https://workspace.example.com/compatible-mode/v1"


class TestZhipuLLM:
    """Test Zhipu provider behavior."""

    @pytest.fixture
    def llm(self) -> ZhipuLLM:
        """Create a ZhipuLLM instance with a mock client."""
        llm = ZhipuLLM(api_key="test-key", model="glm-4.6v-flash")
        return llm

    def test_model_name(self, llm: ZhipuLLM) -> None:
        """Test: get_model_name returns the configured model."""
        assert llm.get_model_name() == "glm-4.6v-flash"

    def test_base_url(self, llm: ZhipuLLM) -> None:
        """Test: base_url is set to Zhipu OpenAI-compatible API."""
        assert str(llm.client.base_url).rstrip("/") == "https://open.bigmodel.cn/api/paas/v4"
