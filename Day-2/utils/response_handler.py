"""Parse raw model output and validate against Pydantic schemas."""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ResponseValidationError(ValueError):
    """Raised when model output cannot be parsed or fails schema validation."""


def _strip_code_fences(text: str) -> str:
    """Remove Markdown JSON code fences if present."""
    stripped = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", stripped, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return stripped


def parse_and_validate(raw_content: str, schema: type[T]) -> T:
    """
    Parse a JSON string and validate it against a Pydantic schema.

    Args:
        raw_content: Raw text returned by the language model.
        schema: Target Pydantic model class.

    Returns:
        Validated model instance.

    Raises:
        ResponseValidationError: On JSON parse failure or schema mismatch.
    """
    cleaned = _strip_code_fences(raw_content)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse model JSON: %s", exc)
        raise ResponseValidationError(
            f"Model returned invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise ResponseValidationError(
            "Model response must be a JSON object, "
            f"got {type(payload).__name__}."
        )

    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        logger.error("Schema validation failed: %s", exc)
        raise ResponseValidationError(
            f"Response failed schema validation:\n{exc}"
        ) from exc
