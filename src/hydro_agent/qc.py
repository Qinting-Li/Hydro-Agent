"""Failure gates: good science sometimes means declining to conclude."""

from __future__ import annotations

from datetime import date


class ScientificRefusal(RuntimeError):
    """Raised when evidence is too weak for a defensible result."""


def aligned_days(*series: dict[date, object]) -> list[date]:
    if not series:
        return []
    return sorted(set.intersection(*(set(item) for item in series)))


def require_coverage(
    expected_days: int,
    actual_days: int,
    minimum_pairs: int,
    maximum_missing_fraction: float,
) -> None:
    missing_fraction = 1.0 - actual_days / max(expected_days, 1)
    if actual_days < minimum_pairs:
        raise ScientificRefusal(
            f"Only {actual_days} matched days; at least {minimum_pairs} are required."
        )
    if missing_fraction > maximum_missing_fraction:
        raise ScientificRefusal(
            f"Missing fraction {missing_fraction:.1%} exceeds {maximum_missing_fraction:.1%}."
        )


def validate_bounds(value: float, low: float, high: float, label: str) -> float:
    if not low <= value <= high:
        raise ScientificRefusal(f"{label}={value:.4f} lies outside [{low:.4f}, {high:.4f}].")
    return value
