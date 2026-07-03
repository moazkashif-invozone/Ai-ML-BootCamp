"""Schema for support ticket classification responses."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from schemas.base import BaseAIResponse


class SupportTicketResponse(BaseAIResponse):
    """Validated output from the support ticket classifier."""

    category: Literal[
        "billing",
        "technical",
        "account",
        "shipping",
        "feature_request",
        "other",
    ] = Field(..., description="Primary ticket category.")
    priority: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Urgency level for resolution."
    )
    sentiment: Literal["angry", "frustrated", "neutral", "positive"] = Field(
        ..., description="Customer emotional tone."
    )
    summary: str = Field(..., min_length=1, description="One-line ticket summary.")
    suggested_team: str = Field(
        ...,
        min_length=1,
        alias="suggestedTeam",
        description="Team best suited to handle the ticket.",
    )
    requires_escalation: bool = Field(
        ...,
        alias="requiresEscalation",
        description="Whether the ticket should be escalated immediately.",
    )

    @field_validator("category", "priority", "sentiment", mode="before")
    @classmethod
    def normalize_enum(cls, value: str) -> str:
        """Normalize enum fields to lowercase."""
        return str(value).strip().lower()

    model_config = {"populate_by_name": True}
