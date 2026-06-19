import json
import shutil
from pathlib import Path

from hydro_agent.agent.tool_registry import ToolResult
from hydro_agent.agent.trajectory_logger import TrajectoryLogger
from hydro_agent.benchmark.runner import run_benchmark
from hydro_agent.benchmark.task_loader import load_task


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_task_loading_contract():
    task = load_task(PROJECT_ROOT / "hydro_bench" / "tasks" / "HB_0001.json")
    assert task["task_id"] == "HB_0001"
    assert len(task["required_tools"]) == 9
    assert "Phys-Consistency" in task["scoring"]["weights"]


def test_trajectory_logger_records_evidence():
    logger = TrajectoryLogger("HB_TEST")
    result = logger.execute("demo", {"station_id": "X"}, lambda: ToolResult({"rows": 3}))
    assert result.output_summary["rows"] == 3
    step = logger.as_dict()["steps"][0]
    assert step["status"] == "success"
    assert step["runtime_ms"] >= 0
    assert step["input"]["station_id"] == "X"


def test_hydro_bench_end_to_end(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(PROJECT_ROOT, project, ignore=shutil.ignore_patterns("outputs", ".git", ".pytest_cache", "__pycache__"))
    (project / "outputs").mkdir()
    task_path = project / "hydro_bench" / "tasks" / "HB_0001.json"
    run_dir = run_benchmark(project, task_path, run_id="test_run")
    expected = {
        "metrics.json", "trajectory.json", "daily_estimates.csv", "report.html",
        "benchmark_summary.html", "data_manifest_evidence.json", "environment.json",
    }
    assert expected <= {path.name for path in run_dir.iterdir()}
    trajectory = json.loads((run_dir / "trajectory.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert len(trajectory["steps"]) == 9
    assert trajectory["evaluation"]["all_required_tools_executed"]
    assert metrics["physical_checks"]["analysis_bounds"]
    assert metrics["metrics"]["kalman_analysis"]["coverage_95"] >= 0.90
    assert {path.name for path in (run_dir / "figures").iterdir()} == {
        "map.svg", "time_series.svg", "scatter.svg", "uncertainty.svg"
    }
