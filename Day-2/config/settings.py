"""Centralized application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv  # type: ignore

load_dotenv()
load_dotenv(".env.example", override=False)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the AI service."""

    api_key: str
    model: str
    base_url: str
    confidence_threshold: float
    max_retries: int

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from environment variables with sensible defaults."""
        api_key = (
            os.getenv("GROQ_API_KEY")
            or os.getenv("GROK_API_KEY")
            or os.getenv("XAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        model = (
            os.getenv("GROQ_MODEL")
            or os.getenv("GROK_MODEL")
            or os.getenv("XAI_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "llama-3.1-8b-instant"
        )
        base_url = (
            os.getenv("GROQ_BASE_URL")
            or os.getenv("GROK_BASE_URL")
            or os.getenv("XAI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.groq.com/openai/v1"
        )
        confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
        max_retries = int(os.getenv("MAX_RETRIES", "3"))

        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            confidence_threshold=confidence_threshold,
            max_retries=max_retries,
        )

    def validate(self) -> None:
        """Raise ValueError when required credentials are missing."""
        if not self.api_key:
            raise ValueError(
                "An API key is required. Set GROQ_API_KEY, GROK_API_KEY, "
                "XAI_API_KEY, or OPENAI_API_KEY in your .env file."
            )
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"CONFIDENCE_THRESHOLD must be between 0.0 and 1.0, "
                f"got {self.confidence_threshold}."
            )
        if self.max_retries < 1:
            raise ValueError(
                f"MAX_RETRIES must be at least 1, got {self.max_retries}."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings.from_env()
    settings.validate()
    return settings
