"""Base schema shared by all AI model responses."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class BaseAIResponse(BaseModel):
    """
    Base response envelope for every model output.

    All task-specific schemas inherit from this class so that
    ``confidence_score`` and human-review flagging are enforced uniformly.
    """

    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model self-assessed confidence for this response (0.0–1.0).",
    )
    requires_human_review: bool = Field(
        default=False,
        description="True when confidence is below the configured threshold.",
    )

    @field_validator("confidence_score", mode="before")
    @classmethod
    def coerce_confidence(cls, value: Any) -> float:
        """Coerce numeric strings and clamp out-of-range values."""
        if isinstance(value, str):
            value = float(value.strip())
        score = float(value)
        return max(0.0, min(1.0, score))

    @model_validator(mode="after")
    def apply_review_flag(self) -> BaseAIResponse:
        """Flag low-confidence responses for human review at validation time."""
        threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
        if self.confidence_score < threshold:
            self.requires_human_review = True
        return self

    def to_display_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict suitable for console display."""
        return self.model_dump(mode="json")
