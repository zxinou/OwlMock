"""Tests for structured LLM output parsing."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from agent.llm.structured import StructuredOutputError, validate_structured_output


class Payload(BaseModel):
    items: list[str]


@pytest.mark.parametrize(
    "text",
    [
        '{"items":["a"]}',
        '```json\n{"items":["a"]}\n```',
        '结果如下：\n{"items":["a"]}\n请查收。',
    ],
)
def test_validate_structured_output_accepts_common_model_wrappers(text: str) -> None:
    assert validate_structured_output(text, Payload) == Payload(items=["a"])


def test_validate_structured_output_rejects_wrong_schema() -> None:
    with pytest.raises(StructuredOutputError):
        validate_structured_output('{"wrong":[]}', Payload)
