import json
import re
from typing import Optional
from openai import OpenAI, APIStatusError, RateLimitError
from backend.config import settings
from backend.models import ClassificationResult, DraftReply, ExtractedData


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.xai_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


def _call_llm(system: str, user: str, temperature: float = 0.1) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.xai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=2048,
    )
    return resp.choices[0].message.content or ""


def _extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.+?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    # also try raw JSON between first { and last }
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        text = text[first : last + 1]
    return json.loads(text)


CLASSIFY_SYSTEM = """You are a support ticket classifier. You classify incoming tickets by category and urgency.

Categories: billing, technical, account, product, general
Urgency levels: low, medium, high, critical

Return ONLY valid JSON with this exact structure:
{
  "category": "string",
  "urgency": "string",
  "confidence": 0.0-1.0
}

Examples:
Ticket: "I was charged twice for my last order"
{"category": "billing", "urgency": "high", "confidence": 0.95}

Ticket: "How do I reset my password?"
{"category": "account", "urgency": "low", "confidence": 0.98}

Ticket: "The app crashes every time I try to upload a photo"
{"category": "technical", "urgency": "high", "confidence": 0.97}
"""


DRAFT_SYSTEM = """You are a support agent drafting replies to customer tickets.
Write professional, empathetic, and helpful replies.

Return ONLY valid JSON with this exact structure:
{
  "reply_text": "the full reply including greeting and signature",
  "confidence": 0.0-1.0
}

The reply should be warm, address the customer's specific issue, and provide clear next steps.
If provided with context from knowledge base documents, use that information to make the reply accurate.
"""


EXTRACT_SYSTEM = """You extract structured information from raw customer messages.

Return ONLY valid JSON with this exact structure:
{
  "name": "customer name or null if not found",
  "issue": "brief description of the issue or null if not clear",
  "order_id": "order ID if present or null if not found",
  "confidence": 0.0-1.0
}

Examples:
"hi my name is John and I need help with order #ORD-12345"
{"name": "John", "issue": "needs help with order", "order_id": "ORD-12345", "confidence": 0.98}

"the thing is broken"
{"name": null, "issue": "product is broken", "order_id": null, "confidence": 0.6}
"""


def _retry_with_validation(max_attempts: int, system_prompt: str, user_message: str,
                           temperature: float, parser_func) -> tuple[dict, int, Optional[str]]:
    for attempt in range(max_attempts):
        try:
            raw = _call_llm(system_prompt, user_message, temperature)
            parsed = parser_func(raw)
            return parsed, attempt, None
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
            if attempt < max_attempts - 1:
                user_message += f"\n\nPrevious attempt failed with error: {str(e)}\nPlease ensure you return ONLY valid JSON."
            continue
        except (APIStatusError, RateLimitError) as e:
            error_msg = f"LLM request failed: {e}"
            return {}, attempt, error_msg
    error_msg = f"All {max_attempts} attempts failed"
    return {}, max_attempts, error_msg


def classify_ticket(raw_text: str) -> ClassificationResult:
    parsed, retries, error = _retry_with_validation(
        max_attempts=settings.max_retries,
        system_prompt=CLASSIFY_SYSTEM,
        user_message=f"Classify this ticket:\n\n{raw_text}",
        temperature=0.0,
        parser_func=_extract_json,
    )
    if error or not parsed:
        return ClassificationResult(
            category="unknown", urgency="low", confidence=0.0,
            flagged_for_review=True, retry_count=retries, error=error,
        )
    confidence = min(max(float(parsed.get("confidence", 0.5)), 0.0), 1.0)
    return ClassificationResult(
        category=parsed.get("category", "unknown"),
        urgency=parsed.get("urgency", "low"),
        confidence=confidence,
        flagged_for_review=confidence < settings.confidence_threshold,
        retry_count=retries,
    )


def draft_reply(ticket_text: str, classification: ClassificationResult,
                context: str = "") -> DraftReply:
    user_msg = f"Ticket: {ticket_text}\nCategory: {classification.category}\nUrgency: {classification.urgency}"
    if context:
        user_msg += f"\n\nKnowledge base context:\n{context}"
    parsed, retries, error = _retry_with_validation(
        max_attempts=settings.max_retries,
        system_prompt=DRAFT_SYSTEM,
        user_message=user_msg,
        temperature=0.3,
        parser_func=_extract_json,
    )
    if error or not parsed:
        return DraftReply(
            reply_text="", confidence=0.0, flagged_for_review=True,
            retry_count=retries, error=error,
        )
    confidence = min(max(float(parsed.get("confidence", 0.5)), 0.0), 1.0)
    return DraftReply(
        reply_text=parsed.get("reply_text", ""),
        confidence=confidence,
        sources=[],
        flagged_for_review=confidence < settings.confidence_threshold,
        retry_count=retries,
    )


def extract_data(raw_text: str) -> ExtractedData:
    parsed, retries, error = _retry_with_validation(
        max_attempts=settings.max_retries,
        system_prompt=EXTRACT_SYSTEM,
        user_message=f"Extract data from:\n\n{raw_text}",
        temperature=0.0,
        parser_func=_extract_json,
    )
    if error or not parsed:
        return ExtractedData(
            name=None, issue=None, order_id=None, confidence=0.0,
            flagged_for_review=True, retry_count=retries, error=error,
        )
    confidence = min(max(float(parsed.get("confidence", 0.5)), 0.0), 1.0)
    return ExtractedData(
        name=parsed.get("name") or None,
        issue=parsed.get("issue") or None,
        order_id=parsed.get("order_id") or None,
        confidence=confidence,
        flagged_for_review=confidence < settings.confidence_threshold,
        retry_count=retries,
    )
