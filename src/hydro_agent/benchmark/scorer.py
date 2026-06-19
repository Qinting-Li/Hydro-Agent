"""Step-by-step and end-to-end scoring for Hydro-Bench trajectories."""

from __future__ import annotations


from .leakage import audit_leakage


METRIC_NAMES = ("TAO", "TIO", "TEM", "Param", "Efficiency", "Accuracy", "Hydro-QC", "Phys-Consistency", "Leakage-Safety")


def _lcs_length(left: list[str], right: list[str]) -> int:
    previous = [0] * (len(right) + 1)
    for item in left:
        current = [0]
        for index, other in enumerate(right, start=1):
            current.append(previous[index - 1] + 1 if item == other else max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def _parameter_score(task: dict, steps_by_name: dict[str, dict]) -> float:
    required = task.get("scoring", {}).get("required_parameters", {})
    checks: list[bool] = []
    for tool_name, parameters in required.items():
        actual = steps_by_name.get(tool_name, {}).get("input", {})
        checks.extend(actual.get(key) == value for key, value in parameters.items())
    return sum(checks) / len(checks) if checks else 1.0


def _accuracy_score(task: dict, result: dict) -> float:
    gold = task["gold_answer"]
    kalman = result["metrics"]["kalman_analysis"]
    checks = [
        result["best_method"] == gold["best_method"],
        kalman["rmse"] <= gold["rmse_max"],
        kalman["coverage_95"] >= gold["coverage_95_min"],
    ]
    return sum(checks) / len(checks)


def score_trajectory(task: dict, trajectory: dict, result: dict) -> dict:
    steps = trajectory["steps"]
    gold_path = task["required_tools"]
    agent_path = [step["tool_name"] for step in steps]
    steps_by_name = {step["tool_name"]: step for step in steps}
    required_set, executed_set = set(gold_path), set(agent_path)
    successful = [step for step in steps if step["status"] in {"success", "warning"}]
    tio_checks = [bool(step["output_summary"]) and step["status"] != "failed" for step in steps]
    qc_tools = {"load_era5_forcing", "match_footprint", "reject_if_unreliable"}
    if "load_station_history" in gold_path:
        qc_tools.add("load_station_history")
    qc_checks = [name in executed_set and steps_by_name[name]["qc"] != "fail" for name in qc_tools]
    physical_checks = list(result.get("physical_checks", {}).values())
    leakage = audit_leakage(task, trajectory)
    metrics = {
        "TAO": _lcs_length(agent_path, gold_path) / len(gold_path),
        "TIO": sum(tio_checks) / len(tio_checks) if tio_checks else 0.0,
        "TEM": len(required_set & executed_set) / len(required_set),
        "Param": _parameter_score(task, steps_by_name),
        "Efficiency": min(1.0, len(gold_path) / max(len(agent_path), 1)) * (len(successful) / max(len(steps), 1)),
        "Accuracy": _accuracy_score(task, result),
        "Hydro-QC": sum(qc_checks) / len(qc_checks),
        "Phys-Consistency": sum(bool(value) for value in physical_checks) / len(physical_checks) if physical_checks else 0.0,
        "Leakage-Safety": leakage["score"],
    }
    weights = task["scoring"]["weights"]
    weight_total = sum(weights.get(name, 0.0) for name in METRIC_NAMES)
    end_to_end = sum(metrics[name] * weights.get(name, 0.0) for name in METRIC_NAMES) / weight_total
    return {
        "schema_version": "1.0",
        "task_id": task["task_id"],
        "ground_truth_path": gold_path,
        "agent_path": agent_path,
        "step_by_step": {name: round(metrics[name], 6) for name in METRIC_NAMES},
        "end_to_end": round(end_to_end, 6),
        "all_required_tools_executed": required_set <= executed_set,
        "leakage_audit": leakage,
    }
