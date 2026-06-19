"""Leakage-resistant temporal and station holdout split definitions."""

from __future__ import annotations

from datetime import date


def leave_year_out(days: list[date], test_year: int) -> tuple[list[date], list[date]]:
    train = [day for day in days if day.year != test_year]
    test = [day for day in days if day.year == test_year]
    validate_split_integrity(train, test)
    if not train or not test:
        raise ValueError(f"leave-year-out requires non-empty train and test sets; test_year={test_year}")
    return train, test


def leave_station_out(station_ids: list[str], test_station: str) -> tuple[list[str], list[str]]:
    unique = sorted(set(station_ids))
    if test_station not in unique:
        raise ValueError(f"Unknown test station: {test_station}")
    train = [station for station in unique if station != test_station]
    test = [test_station]
    validate_split_integrity(train, test)
    if not train:
        raise ValueError("leave-station-out requires at least two stations.")
    return train, test


def validate_split_integrity(train: list, test: list) -> None:
    overlap = set(train) & set(test)
    if overlap:
        raise ValueError(f"Train/test leakage detected: {sorted(overlap)}")
