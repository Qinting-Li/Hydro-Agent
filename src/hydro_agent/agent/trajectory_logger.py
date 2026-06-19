"""JSON-serialisable tool trajectory with timing, QC and failure evidence."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable

from .tool_registry import ToolResult


class TrajectoryLogger:
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.steps: list[dict] = []

    def execute(self, tool_name: str, parameters: dict, function: Callable[[], ToolResult]) -> ToolResult:
        started = datetime.now(timezone.utc).isoformat()
        clock = time.perf_counter()
        try:
            result = function()
        except Exception as exc:
            self.steps.append(
                {
                    "step": len(self.steps) + 1,
                    "tool_name": tool_name,
                    "input": parameters,
                    "output_summary": {},
                    "started_utc": started,
                    "runtime_ms": round((time.perf_counter() - clock) * 1000.0, 3),
                    "status": "failed",
                    "warnings": [f"{type(exc).__name__}: {exc}"],
                    "qc": "fail",
                }
            )
            raise
        status = "warning" if result.warnings or result.qc == "warning" else "success"
        self.steps.append(
            {
                "step": len(self.steps) + 1,
                "tool_name": tool_name,
                "input": parameters,
                "output_summary": result.output_summary,
                "started_utc": started,
                "runtime_ms": round((time.perf_counter() - clock) * 1000.0, 3),
                "status": status,
                "warnings": result.warnings,
                "qc": result.qc,
            }
        )
        return result

    def as_dict(self) -> dict:
        return {"schema_version": "1.0", "task_id": self.task_id, "steps": self.steps}
