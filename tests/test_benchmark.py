import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from hydro_agent.agent.tool_registry import ToolResult
from hydro_agent.agent.trajectory_logger import TrajectoryLogger
from hydro_agent.benchmark.leakage import audit_leakage
from hydro_agent.benchmark.runner import run_benchmark
from hydro_agent.benchmark.suite import run_suite
from hydro_agent.benchmark.splits import leave_station_out, leave_year_out, validate_split_integrity
from hydro_agent.benchmark.task_loader import load_task


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_three_task_modes_and_input_policies():
    tasks = [load_task(PROJECT_ROOT / "hydro_bench" / "tasks" / f"HB_000{index}.json") for index in range(1, 4)]
    assert {task["mode"] for task in tasks} == {
        "station-aware_forecasting", "satellite-only_retrieval", "gap-filling"
    }
    satellite = tasks[1]
    assert "test_label" in satellite["forbidden_inputs"]
    assert not {"historical_ISMN", "pre_gap_ISMN", "current_day_ISMN", "future_ISMN", "test_label"} & set(satellite["allowed_inputs"])
    assert "load_station_history" not in satellite["required_tools"]


def test_trajectory_logger_records_access_evidence():
    logger = TrajectoryLogger("HB_TEST")
    result = logger.execute(
        "demo", {"station_id": "X"},
        lambda: ToolResult({"rows": 3}, accessed_inputs=["ERA5"]),
    )
    assert result.output_summary["rows"] == 3
    step = logger.as_dict()["steps"][0]
    assert step["status"] == "success"
    assert step["accessed_inputs"] == ["ERA5"]


def test_leakage_audit_catches_forbidden_agent_access():
    task = {"allowed_inputs": ["ERA5"], "forbidden_inputs": ["test_label"]}
    trajectory = {"steps": [{
        "step": 1, "tool_name": "bad_tool", "execution_scope": "agent",
        "accessed_inputs": ["ERA5", "test_label"],
    }]}
    audit = audit_leakage(task, trajectory)
    assert not audit["passed"]
    assert audit["violations"] == 1
    assert audit["step_audits"][0]["forbidden_hits"] == ["test_label"]


def test_evaluator_label_access_is_not_agent_leakage():
    task = {"allowed_inputs": ["ERA5"], "forbidden_inputs": ["test_label"]}
    trajectory = {"steps": [{
        "step": 1, "tool_name": "compute_metrics", "execution_scope": "evaluator",
        "accessed_inputs": ["test_label"],
    }]}
    assert audit_leakage(task, trajectory)["passed"]


def test_split_integrity():
    days = [date(2017, 12, 31), date(2018, 1, 1), date(2018, 1, 2)]
    train, test = leave_year_out(days, 2018)
    assert train == [date(2017, 12, 31)]
    assert test == [date(2018, 1, 1), date(2018, 1, 2)]
    assert leave_station_out(["A", "B"], "B") == (["A"], ["B"])
    with pytest.raises(ValueError, match="leakage"):
        validate_split_integrity(["A"], ["A"])
    with pytest.raises(ValueError, match="at least two"):
        leave_station_out(["A"], "A")


@pytest.mark.parametrize(
    ("task_id", "expected_steps", "expected_baseline", "excluded_baseline"),
    [
        ("HB_0001", 10, "persistence", None),
        ("HB_0002", 9, "water_balance", "persistence"),
        ("HB_0003", 10, None, None),
    ],
)
def test_hydro_bench_modes_end_to_end(tmp_path, task_id, expected_steps, expected_baseline, excluded_baseline):
    project = tmp_path / task_id
    shutil.copytree(PROJECT_ROOT, project, ignore=shutil.ignore_patterns("outputs", ".git", ".pytest_cache", "__pycache__"))
    (project / "outputs").mkdir()
    task_path = project / "hydro_bench" / "tasks" / f"{task_id}.json"
    run_dir = run_benchmark(project, task_path, run_id="test_run")
    expected = {
        "metrics.json", "trajectory.json", "daily_estimates.csv", "report.html",
        "benchmark_summary.html", "data_manifest_evidence.json", "environment.json",
    }
    assert expected <= {path.name for path in run_dir.iterdir()}
    trajectory = json.loads((run_dir / "trajectory.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert len(trajectory["steps"]) == expected_steps
    assert trajectory["evaluation"]["all_required_tools_executed"]
    assert trajectory["evaluation"]["leakage_audit"]["passed"]
    assert trajectory["evaluation"]["step_by_step"]["Leakage-Safety"] == 1.0
    assert metrics["physical_checks"]["analysis_bounds"]
    if expected_baseline:
        assert metrics["best_method"] == expected_baseline
    if excluded_baseline:
        assert excluded_baseline in metrics["baseline_eligibility"]["excluded"]
        assert excluded_baseline not in metrics["metrics"]


def test_suite_aggregates_all_modes(tmp_path):
    project = tmp_path / "suite_project"
    shutil.copytree(PROJECT_ROOT, project, ignore=shutil.ignore_patterns("outputs", ".git", ".pytest_cache", "__pycache__"))
    (project / "outputs").mkdir()
    suite_dir = run_suite(project, "test_suite")
    summary = json.loads((suite_dir / "suite_metrics.json").read_text(encoding="utf-8"))
    assert summary["task_count"] == 3
    assert summary["all_leakage_audits_passed"]
    assert set(summary["modes"]) == {"station-aware_forecasting", "satellite-only_retrieval", "gap-filling"}
    assert (suite_dir / "benchmark_summary.html").exists()
