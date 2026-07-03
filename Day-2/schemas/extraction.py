"""Schema for data extraction responses."""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import Field, create_model

from schemas.base import BaseAIResponse


def build_extraction_response(
    field_names: list[str],
) -> type[BaseAIResponse]:
    """
    Dynamically build a Pydantic model for extracted fields.

    Each requested field becomes an optional attribute (value or null).
    The model still inherits confidence_score and review flagging.
    """
    field_definitions: dict[str, Any] = {
        name: (
            Optional[Union[str, int, float, bool]],
            Field(default=None),
        )
        for name in field_names
    }

    return create_model(
        "DynamicExtractionResponse",
        __base__=BaseAIResponse,
        **field_definitions,
    )


class DataExtractionResponse(BaseAIResponse):
    """
    Generic extraction response when field names are not known ahead of time.

    Extracted key-value pairs are stored in `extracted_fields`.
    """

    extracted_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value map of extracted data.",
    )

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "DataExtractionResponse":
        """Separate metadata fields from extracted data fields."""
        metadata_keys = {
            "confidence_score",
            "requires_human_review",
            "confidenceScore",
        }

        extracted = {
            k: v for k, v in raw.items()
            if k not in metadata_keys
        }

        confidence = raw.get(
            "confidence_score",
            raw.get("confidenceScore", 0.5),
        )

        return cls(
            confidence_score=float(confidence),
            extracted_fields=extracted,
        )