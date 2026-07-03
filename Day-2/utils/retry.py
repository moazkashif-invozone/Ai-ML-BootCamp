"""Automatic retry logic for transient API failures."""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIStatusError,
)


def _is_retryable_status_error(exc: APIStatusError) -> bool:
    """Return True for server-side or rate-limit HTTP errors."""
    return exc.status_code is None or exc.status_code >= 500 or exc.status_code == 429


def with_retry(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that retries a callable up to ``max_attempts`` times.

    Retries on connection errors, timeouts, rate limits, and 5xx responses.
    Uses exponential backoff between attempts.

    Args:
        max_attempts: Maximum number of attempts before raising the last error.
        base_delay_seconds: Initial delay between retries (doubles each attempt).

    Returns:
        Decorated function with retry behavior.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except RETRYABLE_EXCEPTIONS as exc:
                    if isinstance(exc, APIStatusError) and not _is_retryable_status_error(exc):
                        raise

                    last_error = exc
                    if attempt == max_attempts:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_attempts,
                            func.__name__,
                            exc,
                        )
                        raise

                    delay = base_delay_seconds * (2 ** (attempt - 1))
                    logger.warning(
                        "Attempt %d/%d for %s failed (%s). Retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
