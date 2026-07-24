"""Helpers for selecting and calling profile-configured LLMs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from trace import trace_llm_call

from pydantic import BaseModel

from agent.llm.base import BaseLLM, CompletionResult
from agent.llm.factory import LLMFactory
from agent.llm.structured import StructuredOutputError, validate_structured_output
from agent.profile import LLMConfig
from config.settings import settings


# Provider 429/5xx responses are often short-lived capacity spikes. Retrying
# the same request briefly gives the primary model a chance to recover before
# spending the fallback request on the same transient condition.
_STRUCTURED_RETRY_DELAYS = (5.0, 15.0)


@dataclass
class StructuredCompletionResult[StructuredModel: BaseModel]:
    """Validated structured value plus the underlying completion result."""

    value: StructuredModel | None
    completion: CompletionResult
    parse_error: str = ""


def create_llm(config: LLMConfig) -> BaseLLM:
    """Create an LLM from a profile config and the configured provider key."""
    return LLMFactory.create(
        config.provider,
        {
            "api_key": settings.get_api_key(config.provider),
            "model": config.model,
            "temperature": config.temperature,
        },
    )


async def _chat_once(
    config: LLMConfig,
    messages: list[dict],
    tools: list[dict] | None = None,
    *,
    is_fallback: bool = False,
) -> CompletionResult:
    """Call one configured model and record it as a Langfuse generation."""
    llm = create_llm(config)
    with trace_llm_call(
        model=config.model,
        messages=messages,
        provider=config.provider,
        tools_count=len(tools or []),
        is_fallback=is_fallback,
    ) as generation:
        result = await llm.chat(messages, tools)
        usage = result.usage
        generation.update(
            output=result.text or None,
            usage_details={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            metadata={
                "provider": config.provider,
                "fallback": str(is_fallback).lower(),
            },
            level="ERROR" if result.error else "DEFAULT",
            status_message=result.error or None,
        )
        return result


async def _chat_structured_with_retries(
    config: LLMConfig,
    messages: list[dict],
    *,
    is_fallback: bool = False,
) -> CompletionResult:
    """Retry transient provider capacity errors before returning to the caller."""
    result = await _chat_once(config, messages, is_fallback=is_fallback)
    for delay in _STRUCTURED_RETRY_DELAYS:
        if not result.error or not result.retryable:
            break
        await asyncio.sleep(delay)
        result = await _chat_once(config, messages, is_fallback=is_fallback)
    return result


async def chat_with_fallback(
    config: LLMConfig,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> CompletionResult:
    """Call the primary model and retry transient provider failures once."""
    result = await _chat_once(config, messages, tools)

    if not result.error or not result.retryable or config.fallback is None:
        return result

    try:
        return await _chat_once(config.fallback, messages, tools, is_fallback=True)
    except Exception:
        # Preserve the original provider error when fallback construction fails.
        return result


async def chat_structured_with_fallback[StructuredModel: BaseModel](
    config: LLMConfig,
    messages: list[dict],
    schema: type[StructuredModel],
) -> StructuredCompletionResult[StructuredModel]:
    """Call a model and fall back when provider or structured output fails."""
    primary = await _chat_structured_with_retries(config, messages)

    if not primary.error:
        try:
            value = validate_structured_output(primary.text, schema)
            return StructuredCompletionResult(value=value, completion=primary)
        except StructuredOutputError as exc:
            parse_error = str(exc)
    else:
        parse_error = ""

    should_fallback = config.fallback is not None and (
        not primary.error or primary.retryable
    )
    if not should_fallback:
        return StructuredCompletionResult(
            value=None,
            completion=primary,
            parse_error=parse_error,
        )

    try:
        fallback = await _chat_structured_with_retries(
            config.fallback,
            messages,
            is_fallback=True,
        )
    except Exception:
        return StructuredCompletionResult(
            value=None,
            completion=primary,
            parse_error=parse_error,
        )

    if fallback.error:
        return StructuredCompletionResult(value=None, completion=fallback)

    try:
        value = validate_structured_output(fallback.text, schema)
        return StructuredCompletionResult(value=value, completion=fallback)
    except StructuredOutputError as exc:
        return StructuredCompletionResult(
            value=None,
            completion=fallback,
            parse_error=str(exc),
        )
