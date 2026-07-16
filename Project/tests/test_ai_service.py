import unittest
from unittest.mock import patch

import httpx
from openai import AuthenticationError, RateLimitError

from backend.ai_service import classify_ticket
from backend.agent import run_agent
from backend.config import settings


class AiServiceTests(unittest.TestCase):
    def test_classify_ticket_handles_rate_limit_error(self):
        response = httpx.Response(
            429,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )
        err = RateLimitError("Rate limit reached", response=response, body=None)

        with patch("backend.ai_service._call_llm", side_effect=err):
            result = classify_ticket("I was charged twice")

        self.assertEqual(result.category, "unknown")
        self.assertEqual(result.urgency, "low")
        self.assertTrue(result.flagged_for_review)
        self.assertEqual(result.retry_count, 0)
        self.assertIn("LLM request failed", result.error or "")

    def test_run_agent_handles_authentication_error(self):
        response = httpx.Response(
            401,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
            json={"error": {"message": "Invalid API Key", "type": "invalid_request_error", "code": "invalid_api_key"}},
        )
        err = AuthenticationError("Invalid API Key", response=response, body=None)

        with patch("backend.agent.get_client", side_effect=err):
            response_text, action, trace = run_agent("I need help", "billing")

        self.assertIn("unavailable", response_text.lower())
        self.assertIsNone(action)
        self.assertTrue(trace)


if __name__ == "__main__":
    unittest.main()
