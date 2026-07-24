"""Structured-output parsing helpers for LLM responses."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel


class StructuredOutputError(ValueError):
    """Raised when an LLM response cannot be parsed or validated."""


def extract_json_object(text: str) -> dict:
    """Extract the first valid JSON object from a model response.

    Models sometimes wrap JSON in markdown fences or add a short preface. The
    decoder-based scan accepts those harmless variations without attempting to
    guess at genuinely malformed data.
    """
    cleaned = text.strip().lstrip("\ufeff")
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise StructuredOutputError("response does not contain a valid JSON object")


def validate_structured_output[StructuredModel: BaseModel](
    text: str,
    schema: type[StructuredModel],
) -> StructuredModel:
    """Parse an LLM response and validate it against a Pydantic schema."""
    try:
        return schema.model_validate(extract_json_object(text))
    except StructuredOutputError:
        raise
    except Exception as exc:
        raise StructuredOutputError("response JSON does not match the expected schema") from exc
