"""Console display helpers for validated responses."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def display_response(response: BaseModel, title: str = "Response") -> None:
    """
    Print a validated Pydantic model as formatted JSON.

    Args:
        response: Validated response model.
        title: Heading shown above the output.
    """
    payload: dict[str, Any]
    if hasattr(response, "to_display_dict"):
        payload = response.to_display_dict()  # type: ignore[attr-defined]
    else:
        payload = response.model_dump(mode="json", by_alias=True)

    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if payload.get("requires_human_review"):
        print(f"\n{'!' * 60}")
        print("  FLAGGED FOR HUMAN REVIEW")
        print(
            f"  Confidence score ({payload.get('confidence_score')}) is below "
            "the configured threshold."
        )
        print(f"{'!' * 60}")

    print()
