"""Execute a declared tool plan and retain every intermediate result."""

from __future__ import annotations

from .planner import plan_task
from .tool_registry import ToolRegistry
from .trajectory_logger import TrajectoryLogger


class HydroAgentExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def run(self, task: dict, context: dict) -> tuple[dict, TrajectoryLogger]:
        logger = TrajectoryLogger(task["task_id"])
        required_parameters = task.get("scoring", {}).get("required_parameters", {})
        for tool_name in plan_task(task, self.registry.names):
            parameters = self._parameters(tool_name, task, required_parameters.get(tool_name, {}))
            function = self.registry.get(tool_name)
            logger.execute(tool_name, parameters, lambda fn=function, p=parameters: fn(context, task, p))
        return context, logger

    @staticmethod
    def _parameters(tool_name: str, task: dict, declared: dict) -> dict:
        parameters = dict(declared)
        if tool_name == "get_station_metadata":
            parameters.setdefault("station_id", task["station_id"])
        if tool_name in {"load_ismn_soil_moisture", "load_era5_forcing"}:
            parameters.setdefault("start", task["time_range"][0])
            parameters.setdefault("end", task["time_range"][1])
        return parameters
