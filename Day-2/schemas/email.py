"""Schema for email draft responses."""

from __future__ import annotations

from pydantic import Field

from schemas.base import BaseAIResponse


class EmailDraftResponse(BaseAIResponse):
    """Validated output from the email drafting function."""

    subject: str = Field(..., min_length=1, description="Email subject line.")
    body: str = Field(..., min_length=1, description="Full email body text.")
