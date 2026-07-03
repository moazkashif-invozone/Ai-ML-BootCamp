"""Schema for lead qualification responses."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from schemas.base import BaseAIResponse


class LeadQualificationResponse(BaseAIResponse):
    """Validated output from the lead qualification function."""

    qualified: bool = Field(..., description="Whether the lead meets qualification criteria.")
    score: int = Field(..., ge=0, le=100, description="Lead quality score from 0 to 100.")
    priority: Literal["high", "medium", "low"] = Field(
        ..., description="Recommended follow-up priority."
    )
    reasoning: str = Field(..., min_length=1, description="Explanation of the qualification decision.")
    recommended_next_step: str = Field(
        ...,
        min_length=1,
        alias="recommendedNextStep",
        description="Suggested next action for the sales team.",
    )
    key_signals: list[str] = Field(
        ...,
        alias="keySignals",
        description="Notable buying signals detected in the lead data.",
    )

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        """Normalize priority to lowercase enum values."""
        return str(value).strip().lower()

    model_config = {"populate_by_name": True}
