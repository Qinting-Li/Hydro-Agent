"""A conservative planner: follow the benchmark-declared scientific tool contract."""

from __future__ import annotations


def plan_task(task: dict, available_tools: tuple[str, ...]) -> list[str]:
    plan = list(task["required_tools"])
    unknown = [name for name in plan if name not in available_tools]
    if unknown:
        raise ValueError(f"Task requires unavailable tools: {unknown}")
    return plan
