"""Pydantic schemas for validated AI responses."""

from schemas.base import BaseAIResponse
from schemas.email import EmailDraftResponse
from schemas.extraction import DataExtractionResponse
from schemas.lead import LeadQualificationResponse
from schemas.support import SupportTicketResponse

__all__ = [
    "BaseAIResponse",
    "LeadQualificationResponse",
    "SupportTicketResponse",
    "EmailDraftResponse",
    "DataExtractionResponse",
]
