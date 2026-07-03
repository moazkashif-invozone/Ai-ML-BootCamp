"""Input validation helpers."""

from __future__ import annotations


class TemperatureValidationError(ValueError):
    """Raised when a temperature value is outside the allowed range."""


def validate_temperature(value: str | float) -> float:
    """
    Validate and return a model temperature value.

    Args:
        value: User-provided temperature as a string or float.

    Returns:
        Parsed temperature within [0.0, 2.0].

    Raises:
        TemperatureValidationError: If the value cannot be parsed or is out of range.
    """
    try:
        temperature = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise TemperatureValidationError(
            f"Invalid temperature '{value}'. Please enter a numeric value between 0.0 and 2.0."
        ) from exc

    if not 0.0 <= temperature <= 2.0:
        raise TemperatureValidationError(
            f"Temperature {temperature} is out of range. "
            "Please enter a value between 0.0 and 2.0 (inclusive)."
        )

    return temperature
