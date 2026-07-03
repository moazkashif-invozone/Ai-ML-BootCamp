#!/usr/bin/env python3
"""Interactive CLI for the Day-2 AI service."""

from __future__ import annotations

import logging
import sys

from config.settings import get_settings
from services.ai_service import AIService
from utils.display import display_response
from utils.validators import TemperatureValidationError, validate_temperature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MENU = """
╔══════════════════════════════════════════════════════════╗
║           Day-2 AI Service — Interactive CLI             ║
╠══════════════════════════════════════════════════════════╣
║  1. Lead Qualification    (qualifyLead)                  ║
║  2. Support Ticket        (classifySupportTicket)        ║
║  3. Email Draft           (draftEmail)                   ║
║  4. Data Extraction       (extractData)                  ║
║  5. Custom Prompt         (free-form request)            ║
║  0. Exit                                                 ║
╚══════════════════════════════════════════════════════════╝
"""


def prompt_multiline(message: str) -> str:
    """Read a multi-line prompt until the user enters a blank line."""
    print(message)
    print("(Press Enter on an empty line when finished)")
    lines: list[str] = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def prompt_temperature() -> float:
    """Ask the user for temperature and validate the input."""
    while True:
        raw = input("\nEnter model temperature (0.0–2.0): ").strip()
        try:
            return validate_temperature(raw)
        except TemperatureValidationError as exc:
            print(f"\nError: {exc}\n")


def run_lead_qualification(service: AIService) -> None:
    """Collect lead input and run qualification."""
    lead_text = prompt_multiline("\nEnter lead information:")
    if not lead_text:
        print("Lead information cannot be empty.")
        return
    temperature = prompt_temperature()
    response = service.qualify_lead(lead_text, temperature=temperature)
    display_response(response, title="Lead Qualification Result")


def run_ticket_classification(service: AIService) -> None:
    """Collect ticket text and run classification."""
    ticket_text = prompt_multiline("\nEnter support ticket text:")
    if not ticket_text:
        print("Ticket text cannot be empty.")
        return
    temperature = prompt_temperature()
    response = service.classify_support_ticket(ticket_text, temperature=temperature)
    display_response(response, title="Support Ticket Classification")


def run_email_draft(service: AIService) -> None:
    """Collect email parameters and draft an email."""
    purpose = input("\nEmail purpose (e.g. follow up, apology): ").strip()
    audience = input("Audience (e.g. Prospect CTO): ").strip()
    tone = input("Tone [professional]: ").strip() or "professional"
    context = prompt_multiline("Context / background details:")
    if not purpose or not audience or not context:
        print("Purpose, audience, and context are all required.")
        return
    temperature = prompt_temperature()
    response = service.draft_email(
        purpose=purpose,
        audience=audience,
        context=context,
        tone=tone,
        temperature=temperature,
    )
    display_response(response, title="Email Draft")


def run_data_extraction(service: AIService) -> None:
    """Collect source text and field list, then extract data."""
    raw_text = prompt_multiline("\nEnter source text to extract from:")
    if not raw_text:
        print("Source text cannot be empty.")
        return
    fields_raw = input(
        "Fields to extract (comma-separated, e.g. name,email,phone): "
    ).strip()
    fields = [field.strip() for field in fields_raw.split(",") if field.strip()]
    if not fields:
        print("At least one field name is required.")
        return
    temperature = prompt_temperature()
    response = service.extract_data(raw_text, fields, temperature=temperature)
    display_response(response, title="Extracted Data")


def run_custom_prompt(service: AIService) -> None:
    """Run a free-form user prompt."""
    user_prompt = prompt_multiline("\nEnter your prompt:")
    if not user_prompt:
        print("Prompt cannot be empty.")
        return
    temperature = prompt_temperature()
    response = service.run_custom_prompt(user_prompt, temperature=temperature)
    display_response(response, title="Custom Prompt Response")


def main() -> None:
    """Entry point for the interactive CLI."""
    try:
        settings = get_settings()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)

    print(MENU)
    print(
        f"Model: {settings.model}  |  "
        f"Confidence threshold: {settings.confidence_threshold}  |  "
        f"Max retries: {settings.max_retries}"
    )

    service = AIService()
    handlers = {
        "1": run_lead_qualification,
        "2": run_ticket_classification,
        "3": run_email_draft,
        "4": run_data_extraction,
        "5": run_custom_prompt,
    }

    while True:
        choice = input("\nSelect a task (0–5): ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        handler = handlers.get(choice)
        if handler is None:
            print("Invalid choice. Please enter a number between 0 and 5.")
            continue

        try:
            handler(service)
        except Exception as exc:
            logger.exception("Request failed")
            print(f"\nError: {exc}\n")


if __name__ == "__main__":
    main()
