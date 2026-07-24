"""Langfuse observability helpers (SDK v4, official context-manager pattern)."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

from config.settings import settings

# Suppress noisy OpenTelemetry "Failed to detach context" warnings
# that occur when async generators are garbage-collected in a different
# async context than where the span was created.
logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

_client_initialized = False
_MAX_STRING_LENGTH = 1200
_MAX_LIST_ITEMS = 12
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "base64",
    "b64",
    "credential",
    "image_url",
    "key",
    "password",
    "secret",
    "token",
)


class SpanHandle(Protocol):
    def update(self, **kwargs: Any) -> Any: ...


class _NoopSpan:
    def update(self, **kwargs: Any) -> _NoopSpan:
        return self


def _truncate_text(value: str, limit: int = _MAX_STRING_LENGTH) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... [truncated {len(value) - limit} chars]"


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def sanitize_for_langfuse(value: Any, *, depth: int = 0) -> Any:
    """Redact secrets/large payloads before sending data to Langfuse."""
    if depth > 5:
        return "[max-depth]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        if value.startswith("data:") and ";base64," in value:
            return "[redacted data-url]"
        return _truncate_text(value)
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if _is_sensitive_key(key_str):
                clean[key_str] = "[redacted]"
            else:
                clean[key_str] = sanitize_for_langfuse(item, depth=depth + 1)
        return clean
    if isinstance(value, list | tuple):
        clean_items = [
            sanitize_for_langfuse(item, depth=depth + 1)
            for item in list(value)[:_MAX_LIST_ITEMS]
        ]
        if len(value) > _MAX_LIST_ITEMS:
            clean_items.append(f"[truncated {len(value) - _MAX_LIST_ITEMS} items]")
        return clean_items
    return _truncate_text(str(value))


def _metadata(values: dict[str, Any]) -> dict[str, str]:
    """Langfuse v4 metadata values should be short strings."""
    clean: dict[str, str] = {}
    for key, value in values.items():
        if value is None or value == "":
            continue
        clean[str(key)] = _truncate_text(str(value), limit=500)
    return clean


def is_tracing_enabled() -> bool:
    return (
        settings.TRACER == "langfuse"
        and bool(settings.LANGFUSE_PUBLIC_KEY)
        and bool(settings.LANGFUSE_SECRET_KEY)
    )


def _is_client_ready() -> bool:
    return is_tracing_enabled() and _client_initialized


def init_tracing() -> None:
    """Initialize Langfuse client singleton (no-op when tracing disabled)."""
    global _client_initialized
    if not is_tracing_enabled() or _client_initialized:
        return

    try:
        from langfuse import Langfuse, get_client

        if getattr(settings, "LANGFUSE_TRACING_ENVIRONMENT", ""):
            os.environ.setdefault(
                "LANGFUSE_TRACING_ENVIRONMENT",
                settings.LANGFUSE_TRACING_ENVIRONMENT,
            )

        Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            base_url=settings.langfuse_base_url,
        )
        if not get_client().auth_check():
            logger.warning("Langfuse auth_check failed; verify keys and LANGFUSE_BASE_URL")
        _client_initialized = True
    except Exception as e:
        logger.warning("Failed to initialize Langfuse tracing: %s", e)


def shutdown_tracing() -> None:
    """Flush pending Langfuse events."""
    if not _is_client_ready():
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception as e:
        logger.warning("Failed to flush Langfuse client: %s", e)


@contextmanager
def trace_agent_turn(
    *,
    session_id: str,
    user_id: str,
    user_input: str,
    profile_id: str = "",
) -> Iterator[SpanHandle]:
    """Root span: one user message / agent.run() invocation."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client, propagate_attributes

    metadata = _metadata({"profile_id": profile_id, "feature": "agent"})

    with propagate_attributes(
        trace_name="run-agent-turn",
        session_id=session_id,
        user_id=user_id,
        tags=["agent", "interview"],
        metadata=metadata or None,
    ):
        with get_client().start_as_current_observation(
            as_type="span",
            name="run-agent-turn",
            input={"user_input": sanitize_for_langfuse(user_input)},
            metadata=metadata or None,
        ) as turn:
            yield turn


@contextmanager
def trace_react_step(*, step: int) -> Iterator[SpanHandle]:
    """Span for one ReAct loop iteration."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client

    with get_client().start_as_current_observation(
        as_type="span",
        name="run-react-step",
        metadata=_metadata({"step": step}),
    ) as step_span:
        yield step_span


@contextmanager
def trace_compaction() -> Iterator[SpanHandle]:
    """Span for context compaction."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client

    with get_client().start_as_current_observation(
        as_type="span",
        name="compact-context",
    ) as span:
        yield span


@contextmanager
def trace_llm_call(
    *,
    model: str,
    messages: list[dict],
    provider: str = "",
    tools_count: int = 0,
    is_fallback: bool = False,
) -> Iterator[SpanHandle]:
    """Generation span covering the full LLM stream."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client

    metadata = _metadata(
        {
            "provider": provider,
            "tools_count": tools_count,
            "fallback": is_fallback,
        }
    )
    with get_client().start_as_current_observation(
        as_type="generation",
        name="call-llm",
        model=model,
        input=sanitize_for_langfuse(messages),
        metadata=metadata or None,
    ) as generation:
        yield generation


@contextmanager
def trace_tool(*, name: str, args: dict[str, Any]) -> Iterator[SpanHandle]:
    """Tool span for a single tool invocation."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client

    with get_client().start_as_current_observation(
        as_type="tool",
        name=name,
        input=sanitize_for_langfuse(args),
    ) as tool_span:
        yield tool_span


@contextmanager
def trace_analysis_request(
    *,
    kind: str,
    user_id: str = "default",
    input_summary: dict[str, Any] | None = None,
) -> Iterator[SpanHandle]:
    """Root span for one structured analysis API request."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client, propagate_attributes

    metadata = _metadata({"feature": "analysis", "analysis_kind": kind})
    with propagate_attributes(
        trace_name=f"analyze-{kind}",
        user_id=user_id,
        tags=["analysis", kind],
        metadata=metadata or None,
    ):
        with get_client().start_as_current_observation(
            as_type="span",
            name=f"analyze-{kind}",
            input=sanitize_for_langfuse(input_summary or {}),
            metadata=metadata or None,
        ) as span:
            yield span


def tool_result_output(result: Any) -> dict[str, Any]:
    """Serialize ToolResult for Langfuse output."""
    status = getattr(result, "status", "unknown")
    payload: dict[str, Any] = {"status": status}
    if status == "ok":
        payload["data"] = getattr(result, "data", None)
    else:
        payload["error"] = getattr(result, "error", None)
        payload["summary"] = getattr(result, "summary", None)
    return payload


def span_level_for_result(result: Any) -> str:
    return "ERROR" if getattr(result, "status", "") != "ok" else "DEFAULT"


@contextmanager
def trace_realtime_session(
    *,
    session_id: str,
    user_id: str,
    profile_id: str = "",
    provider: str = "",
    model: str = "",
    voice: str = "",
) -> Iterator[SpanHandle]:
    """Root span: one RealtimeAgent.run() invocation."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client, propagate_attributes

    metadata = _metadata(
        {
            "profile_id": profile_id,
            "provider": provider,
            "model": model,
            "voice": voice,
            "feature": "voice-interview",
        }
    )

    with propagate_attributes(
        trace_name="run-realtime-session",
        session_id=session_id,
        user_id=user_id,
        tags=["voice-interview", "realtime"],
        metadata=metadata or None,
    ):
        with get_client().start_as_current_observation(
            as_type="span",
            name="run-realtime-session",
            metadata=metadata or None,
        ) as span:
            yield span


def record_realtime_usage(
    span: SpanHandle,
    audio_in_tokens: int = 0,
    audio_out_tokens: int = 0,
    text_in_tokens: int = 0,
    text_out_tokens: int = 0,
    cost_usd: float | None = None,
) -> None:
    """Record realtime usage metrics (called per ResponseDone)."""
    usage: dict[str, Any] = {
        "audio_in_tokens": audio_in_tokens,
        "audio_out_tokens": audio_out_tokens,
        "text_in_tokens": text_in_tokens,
        "text_out_tokens": text_out_tokens,
    }
    if cost_usd is not None:
        usage["cost_usd"] = cost_usd
    span.update(output=usage)


@contextmanager
def trace_realtime_midsummary(parent_span: SpanHandle) -> Iterator[SpanHandle]:
    """Sub-span: one MidSummary subagent invocation."""
    if not _is_client_ready():
        yield _NoopSpan()
        return

    from langfuse import get_client

    with get_client().start_as_current_observation(
        as_type="span",
        name="summarize-realtime-context",
    ) as span:
        yield span
