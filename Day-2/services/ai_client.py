"""OpenAI-compatible client with automatic retry support."""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from config.settings import Settings, get_settings
from utils.retry import with_retry

logger = logging.getLogger(__name__)


class AIClient:
    """Thin wrapper around the OpenAI SDK with retry-enabled chat completions."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the client using application settings.

        Args:
            settings: Optional settings override. Defaults to environment config.
        """
        self._settings = settings or get_settings()
        self._client = OpenAI(
            api_key=self._settings.api_key,
            base_url=self._settings.base_url,
        )
        self.model = self._settings.model

    def _create_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """
        Execute a single chat completion request.

        Args:
            messages: Chat message history.
            temperature: Sampling temperature for the model.
            response_format: Optional response format directive.

        Returns:
            Trimmed text content from the model response.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": messages,
        }
        if response_format:
            kwargs["response_format"] = response_format

        logger.debug(
            "Requesting completion (model=%s, temperature=%.2f)",
            self.model,
            temperature,
        )
        response = self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return content.strip()

    def chat(
        self,
        *,
        system: str,
        user: str,
        temperature: float,
        json_mode: bool = True,
    ) -> str:
        """
        Send a system + user prompt and return the model's text response.

        Automatically retries up to ``max_retries`` times on transient failures.

        Args:
            system: System prompt defining behavior and output schema.
            user: User prompt with task-specific input.
            temperature: Sampling temperature (0.0–2.0).
            json_mode: When True, request JSON object output from the provider.

        Returns:
            Raw model response text.
        """
        response_format = {"type": "json_object"} if json_mode else None
        retry_attempts = self._settings.max_retries

        @with_retry(max_attempts=retry_attempts)
        def _call() -> str:
            return self._create_completion(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                response_format=response_format,
            )

        return _call()
