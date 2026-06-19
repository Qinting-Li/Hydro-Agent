"""Strict task-schema loading for Hydro-Bench."""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {"task_id", "category", "station_id", "time_range", "question", "required_tools", "gold_answer", "scoring"}


def load_task(path: Path) -> dict:
    task = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_FIELDS - set(task)
    if missing:
        raise ValueError(f"Task {path.name} is missing fields: {sorted(missing)}")
    if len(task["time_range"]) != 2 or task["time_range"][0] > task["time_range"][1]:
        raise ValueError(f"Task {path.name} has an invalid time_range.")
    if not task["required_tools"] or len(task["required_tools"]) != len(set(task["required_tools"])):
        raise ValueError(f"Task {path.name} requires a non-empty, duplicate-free tool path.")
    return task
