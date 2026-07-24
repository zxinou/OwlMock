"""Tests for profile-based LLM routing and fallback behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from agent.llm.base import CompletionResult
from agent.llm.router import chat_structured_with_fallback, chat_with_fallback
from agent.profile import LLMConfig


@pytest.mark.asyncio
async def test_chat_with_fallback_uses_backup_for_retryable_error() -> None:
    config = LLMConfig(
        provider="dashscope",
        model="qwen3-omni-flash",
        fallback=LLMConfig(provider="zhipu", model="glm-4.6v-flash"),
    )
    primary_result = MagicMock(error="rate limited", retryable=True)
    fallback_result = MagicMock(text="ok", error=None, retryable=False)
    primary = MagicMock(chat=AsyncMock(return_value=primary_result))
    fallback = MagicMock(chat=AsyncMock(return_value=fallback_result))

    with patch("agent.llm.router.create_llm", side_effect=[primary, fallback]) as create:
        result = await chat_with_fallback(config, [{"role": "user", "content": "hi"}])

    assert result is fallback_result
    assert create.call_count == 2
    primary.chat.assert_awaited_once()
    fallback.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_with_fallback_does_not_retry_non_retryable_error() -> None:
    config = LLMConfig(
        provider="dashscope",
        model="qwen3-omni-flash",
        fallback=LLMConfig(provider="zhipu", model="glm-4.6v-flash"),
    )
    primary_result = MagicMock(error="invalid request", retryable=False)
    primary = MagicMock(chat=AsyncMock(return_value=primary_result))

    with patch("agent.llm.router.create_llm", return_value=primary) as create:
        result = await chat_with_fallback(config, [{"role": "user", "content": "hi"}])

    assert result is primary_result
    create.assert_called_once_with(config)


def test_profile_loader_applies_per_scenario_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    profile_file = tmp_path / "resume-analyzer.yaml"
    profile_file.write_text(
        "id: resume-analyzer\n"
        "prompt_template: prompt.md\n"
        "llm:\n"
        "  provider: dashscope\n"
        "  model: qwen3-vl-flash\n"
        "  temperature: 1.0\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CAPYMOCK_RESUME_ANALYZER_PROVIDER", "zhipu")
    monkeypatch.setenv("CAPYMOCK_RESUME_ANALYZER_MODEL", "glm-4.6v-flash")

    from agent.profile_loader import ProfileLoader

    profile = ProfileLoader(str(tmp_path)).load_all()["resume-analyzer"]

    assert profile.llm.provider == "zhipu"
    assert profile.llm.model == "glm-4.6v-flash"


class SamplePayload(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_structured_chat_uses_fallback_for_invalid_primary_json() -> None:
    config = LLMConfig(
        provider="dashscope",
        model="qwen3-omni-flash",
        fallback=LLMConfig(provider="zhipu", model="glm-4.6v-flash"),
    )
    primary_result = MagicMock(text="not json", error=None, usage=None)
    fallback_result = MagicMock(text='```json\n{"answer":"ok"}\n```', error=None, usage=None)
    primary = MagicMock(chat=AsyncMock(return_value=primary_result))
    fallback = MagicMock(chat=AsyncMock(return_value=fallback_result))

    with patch("agent.llm.router.create_llm", side_effect=[primary, fallback]):
        result = await chat_structured_with_fallback(
            config,
            [{"role": "user", "content": "hi"}],
            SamplePayload,
        )

    assert result.value == SamplePayload(answer="ok")
    primary.chat.assert_awaited_once()
    fallback.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_structured_chat_retries_transient_primary_error() -> None:
    config = LLMConfig(
        provider="dashscope",
        model="qwen3.5-omni-plus-2026-03-15",
        fallback=LLMConfig(provider="zhipu", model="glm-4.6v-flash"),
    )
    primary_result = CompletionResult(
        text="",
        tool_calls=[],
        error="rate limited",
        error_code="429",
        retryable=True,
    )
    recovered_result = CompletionResult(
        text='{"answer":"ok"}',
        tool_calls=[],
    )
    primary = MagicMock(
        chat=AsyncMock(side_effect=[primary_result, recovered_result])
    )

    with (
        patch("agent.llm.router.create_llm", return_value=primary),
        patch("agent.llm.router.asyncio.sleep", new_callable=AsyncMock) as sleep,
    ):
        result = await chat_structured_with_fallback(
            config,
            [{"role": "user", "content": "hi"}],
            SamplePayload,
        )

    assert result.value == SamplePayload(answer="ok")
    assert primary.chat.await_count == 2
    sleep.assert_awaited_once_with(5.0)
