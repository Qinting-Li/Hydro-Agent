"""Strict task-schema loading for Hydro-Bench."""

from __future__ import annotations

import json
from pathlib import Path


TASK_MODES = {"station-aware_forecasting", "satellite-only_retrieval", "gap-filling"}
REQUIRED_FIELDS = {
    "task_id", "category", "mode", "station_id", "time_range", "question",
    "allowed_inputs", "forbidden_inputs", "required_tools", "gold_answer", "scoring", "split",
}


def load_task(path: Path) -> dict:
    task = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_FIELDS - set(task)
    if missing:
        raise ValueError(f"Task {path.name} is missing fields: {sorted(missing)}")
    if len(task["time_range"]) != 2 or task["time_range"][0] > task["time_range"][1]:
        raise ValueError(f"Task {path.name} has an invalid time_range.")
    if not task["required_tools"] or len(task["required_tools"]) != len(set(task["required_tools"])):
        raise ValueError(f"Task {path.name} requires a non-empty, duplicate-free tool path.")
    if task["mode"] not in TASK_MODES:
        raise ValueError(f"Task {path.name} has unsupported mode: {task['mode']}")
    overlap = set(task["allowed_inputs"]) & set(task["forbidden_inputs"])
    if overlap:
        raise ValueError(f"Task {path.name} allows and forbids the same inputs: {sorted(overlap)}")
    label_bearing_inputs = {"historical_ISMN", "pre_gap_ISMN", "current_day_ISMN", "future_ISMN", "test_label"}
    if task["mode"] == "satellite-only_retrieval" and set(task["allowed_inputs"]) & label_bearing_inputs:
        raise ValueError("Satellite-only tasks cannot allow ISMN inputs to the agent.")
    if task["mode"] == "gap-filling" and "gap" not in task:
        raise ValueError("Gap-filling tasks require an explicit gap interval.")
    return task
