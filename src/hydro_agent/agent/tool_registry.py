"""Named tool registry with a small, testable execution contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ToolResult:
    output_summary: dict
    warnings: list[str] = field(default_factory=list)
    qc: str = "pass"
    accessed_inputs: list[str] = field(default_factory=list)
    execution_scope: str = "agent"


ToolFunction = Callable[[dict, dict, dict], ToolResult]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFunction] = {}

    def register(self, name: str, function: ToolFunction) -> None:
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = function

    def get(self, name: str) -> ToolFunction:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown Hydro-Bench tool: {name}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)
