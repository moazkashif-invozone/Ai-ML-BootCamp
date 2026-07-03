#!/usr/bin/env python3
"""Runnable demo mirroring Day-1 examples with validated JSON responses."""

from __future__ import annotations

import logging
import sys

from config.settings import get_settings
from services.ai_service import AIService
from utils.display import display_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def run_demo() -> None:
    """Execute all four Day-1 functions and print validated results."""
    settings = get_settings()
    print(
        f"Running demo with model={settings.model}, "
        f"confidence_threshold={settings.confidence_threshold}"
    )

    service = AIService()

    print("\n=== Lead Qualification ===")
    lead = service.qualify_lead(
        {
            "name": "Jane Doe",
            "company": "Acme Corp",
            "role": "VP Engineering",
            "message": (
                "We need an enterprise plan for 200 seats by Q3. Budget approved."
            ),
        },
        temperature=0.1,
    )
    display_response(lead, title="Lead Qualification")

    print("=== Support Ticket Classifier ===")
    ticket = service.classify_support_ticket(
        "I was charged twice this month and cannot access my dashboard. "
        "This is urgent.",
        temperature=0.0,
    )
    display_response(ticket, title="Support Ticket")

    print("=== Email Drafter (low temperature) ===")
    formal_email = service.draft_email(
        purpose="Follow up after demo",
        audience="Prospect CTO",
        context="They liked the analytics dashboard but asked about SSO.",
        tone="professional",
        temperature=0.2,
    )
    display_response(formal_email, title="Formal Email (temp=0.2)")

    print("=== Email Drafter (high temperature) ===")
    creative_email = service.draft_email(
        purpose="Follow up after demo",
        audience="Prospect CTO",
        context="They liked the analytics dashboard but asked about SSO.",
        tone="warm and engaging",
        temperature=0.9,
    )
    display_response(creative_email, title="Creative Email (temp=0.9)")

    print("=== Data Extractor ===")
    extracted = service.extract_data(
        "Contact: John Smith, john@example.com, +1-555-0100. "
        "Order #48291 shipped on June 12.",
        ["name", "email", "phone", "orderId", "shipDate"],
        temperature=0.0,
    )
    display_response(extracted, title="Extracted Data")


if __name__ == "__main__":
    try:
        run_demo()
    except Exception as exc:
        print(f"Demo failed: {exc}", file=sys.stderr)
        sys.exit(1)
