"""Refactored Day-1 AI functions with validated JSON responses."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from schemas.email import EmailDraftResponse
from schemas.extraction import DataExtractionResponse, build_extraction_response
from schemas.lead import LeadQualificationResponse
from schemas.support import SupportTicketResponse
from services.ai_client import AIClient
from utils.response_handler import ResponseValidationError, parse_and_validate

logger = logging.getLogger(__name__)

CONFIDENCE_INSTRUCTION = """
Always include a "confidence_score" field (float, 0.0–1.0) reflecting how
confident you are in the accuracy and completeness of this response.
Use lower scores when information is ambiguous, incomplete, or inferred.
Use higher scores when the answer is clearly supported by the input.
"""


class AIService:
    """
    Production-ready AI service porting all Day-1 functions to Python.

    Each public method returns a Pydantic-validated response that includes
    ``confidence_score`` and automatic human-review flagging.
    """

    def __init__(self, client: AIClient | None = None) -> None:
        """
        Initialize the service.

        Args:
            client: Optional AIClient instance for dependency injection.
        """
        self._client = client or AIClient()

    def _execute(
        self,
        *,
        system: str,
        user: str,
        temperature: float,
        schema: type[BaseModel],
        max_validation_attempts: int = 3,
    ) -> BaseModel:
        """
        Run a chat request and validate the response, retrying on bad output.

        Args:
            system: System prompt.
            user: User prompt.
            temperature: Model temperature.
            schema: Target Pydantic schema.
            max_validation_attempts: Retries when JSON fails validation.

        Returns:
            Validated response model.

        Raises:
            ResponseValidationError: After exhausting validation retries.
        """
        last_error: ResponseValidationError | None = None
        augmented_system = f"{system.strip()}\n\n{CONFIDENCE_INSTRUCTION.strip()}"

        for attempt in range(1, max_validation_attempts + 1):
            try:
                raw = self._client.chat(
                    system=augmented_system,
                    user=user,
                    temperature=temperature,
                )
                return parse_and_validate(raw, schema)
            except ResponseValidationError as exc:
                last_error = exc
                logger.warning(
                    "Validation attempt %d/%d failed: %s",
                    attempt,
                    max_validation_attempts,
                    exc,
                )

        assert last_error is not None
        raise last_error

    def qualify_lead(
        self,
        lead_info: str | dict[str, Any],
        temperature: float = 0.1,
    ) -> LeadQualificationResponse:
        """
        Evaluate a sales lead and return a validated qualification report.

        Args:
            lead_info: Raw lead text or structured lead fields.
            temperature: Model temperature (default 0.1 for consistency).

        Returns:
            Validated ``LeadQualificationResponse``.
        """
        lead_text = (
            lead_info
            if isinstance(lead_info, str)
            else json.dumps(lead_info, indent=2)
        )

        system = """You are a B2B sales lead qualification assistant.
Analyze the lead and respond with valid JSON only using this schema:
{
  "qualified": boolean,
  "score": number (0-100),
  "priority": "high" | "medium" | "low",
  "reasoning": string,
  "recommendedNextStep": string,
  "keySignals": string[],
  "confidence_score": number (0.0-1.0)
}
Score based on budget fit, urgency, decision-maker access, and product fit."""

        user = f"Qualify this lead:\n\n{lead_text}"
        result = self._execute(
            system=system,
            user=user,
            temperature=temperature,
            schema=LeadQualificationResponse,
        )
        return result  # type: ignore[return-value]

    def classify_support_ticket(
        self,
        ticket_text: str,
        temperature: float = 0.0,
    ) -> SupportTicketResponse:
        """
        Classify a support ticket by category, priority, and sentiment.

        Args:
            ticket_text: Raw support ticket content.
            temperature: Model temperature (default 0.0 for consistency).

        Returns:
            Validated ``SupportTicketResponse``.
        """
        system = """You are a customer support triage assistant.
Classify the ticket and respond with valid JSON only using this schema:
{
  "category": "billing" | "technical" | "account" | "shipping" | "feature_request" | "other",
  "priority": "critical" | "high" | "medium" | "low",
  "sentiment": "angry" | "frustrated" | "neutral" | "positive",
  "summary": string,
  "suggestedTeam": string,
  "requiresEscalation": boolean,
  "confidence_score": number (0.0-1.0)
}"""

        user = f"Classify this support ticket:\n\n{ticket_text}"
        result = self._execute(
            system=system,
            user=user,
            temperature=temperature,
            schema=SupportTicketResponse,
        )
        return result  # type: ignore[return-value]

    def draft_email(
        self,
        *,
        purpose: str,
        audience: str,
        context: str,
        tone: str = "professional",
        temperature: float = 0.7,
    ) -> EmailDraftResponse:
        """
        Draft a professional email with subject and body.

        Args:
            purpose: Goal of the email.
            audience: Intended recipient description.
            context: Background details to include.
            tone: Desired writing tone.
            temperature: Creativity level (higher = more creative).

        Returns:
            Validated ``EmailDraftResponse``.
        """
        system = """You are an expert business email writer.
Write a clear, concise email with a subject line.
Return valid JSON only using this schema:
{
  "subject": string,
  "body": string,
  "confidence_score": number (0.0-1.0)
}
Match the requested tone. Do not invent facts not provided in the context."""

        user = (
            f"Purpose: {purpose}\n"
            f"Audience: {audience}\n"
            f"Tone: {tone}\n"
            f"Context:\n{context}"
        )
        result = self._execute(
            system=system,
            user=user,
            temperature=temperature,
            schema=EmailDraftResponse,
        )
        return result  # type: ignore[return-value]

    def extract_data(
        self,
        raw_text: str,
        fields: list[str] | dict[str, Any],
        temperature: float = 0.0,
    ) -> DataExtractionResponse:
        """
        Extract structured data from unstructured text.

        Args:
            raw_text: Source text to parse.
            fields: Field names or schema describing what to extract.
            temperature: Model temperature (default 0.0 for precision).

        Returns:
            Validated ``DataExtractionResponse`` with extracted key-value pairs.
        """
        field_description = (
            ", ".join(fields)
            if isinstance(fields, list)
            else json.dumps(fields, indent=2)
        )
        field_names = fields if isinstance(fields, list) else list(fields.keys())

        system = """You are a precise data extraction assistant.
Extract the requested fields from the text.
Return valid JSON only. Use null for missing values.
Do not guess or fabricate data that is not present in the source text.
Always include "confidence_score" (0.0-1.0) reflecting extraction certainty."""

        user = (
            f"Extract these fields:\n{field_description}\n\n"
            f"Source text:\n{raw_text}"
        )

        dynamic_schema = build_extraction_response(field_names)
        validated = self._execute(
            system=system,
            user=user,
            temperature=temperature,
            schema=dynamic_schema,
        )
        raw_dict = validated.model_dump(by_alias=True)
        return DataExtractionResponse.from_raw(raw_dict)

    def run_custom_prompt(
        self,
        prompt: str,
        temperature: float,
    ) -> DataExtractionResponse:
        """
        Execute an arbitrary user prompt and return a structured JSON answer.

        Args:
            prompt: Free-form user instruction or question.
            temperature: Model sampling temperature.

        Returns:
            Validated response with ``answer`` and metadata fields.
        """
        system = """You are a helpful AI assistant.
Respond to the user's request with valid JSON only using this schema:
{
  "answer": string,
  "confidence_score": number (0.0-1.0)
}
Be concise, accurate, and honest about uncertainty."""

        validated = self._execute(
            system=system,
            user=prompt,
            temperature=temperature,
            schema=build_extraction_response(["answer"]),
        )
        raw_dict = validated.model_dump(by_alias=True)
        return DataExtractionResponse.from_raw(raw_dict)
