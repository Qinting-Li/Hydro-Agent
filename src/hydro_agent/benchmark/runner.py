"""One-command Hydro-Bench v0.2 runner with immutable run artefacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..agent.executor import HydroAgentExecutor
from ..io import read_json, write_json, write_rows
from ..report.render_html import render_benchmark_summary, render_task_report
from ..tools.benchmark_tools import (
    build_registry,
    load_evaluator_labels,
    load_experiment_config,
    load_station_catalog,
)
from .scorer import score_trajectory
from .task_loader import load_task


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(project_root: Path) -> list[dict]:
    manifest = read_json(project_root / "data_manifest.json")
    evidence = []
    for item in manifest["datasets"]:
        path = project_root / item["path"]
        actual = _sha256(path) if path.exists() else None
        valid = path.exists() and path.stat().st_size == item["bytes"] and actual == item["sha256"]
        evidence.append({"path": item["path"], "expected_sha256": item["sha256"], "actual_sha256": actual, "valid": valid})
    if not all(item["valid"] for item in evidence):
        raise RuntimeError("Data manifest verification failed; refusing a non-reproducible run.")
    return evidence


def _gpu_inventory() -> list[dict]:
    command = ["nvidia-smi", "--query-gpu=index,name,uuid,memory.total", "--format=csv,noheader,nounits"]
    try:
        output = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    inventory = []
    for line in output.splitlines():
        index, name, uuid, memory = (part.strip() for part in line.split(",", 3))
        inventory.append({"index": int(index), "name": name, "uuid": uuid, "memory_mib": int(memory)})
    return inventory


def _git_revision(project_root: Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _unique_run_dir(output_root: Path, run_id: str | None) -> Path:
    base = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = output_root / base
    suffix = 1
    while candidate.exists():
        candidate = output_root / f"{base}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def run_benchmark(project_root: Path, task_path: Path, run_id: str | None = None, output_root: Path | None = None) -> Path:
    project_root = project_root.resolve()
    task = load_task(task_path)
    bench_config_path = project_root / "configs" / "hydro_bench_v0.2.yaml"
    bench_config = read_json(bench_config_path)
    manifest_evidence = verify_manifest(project_root)
    run_dir = _unique_run_dir(output_root or project_root / bench_config["output_root"], run_id)
    environment = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "git_revision": _git_revision(project_root),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpu_inventory": _gpu_inventory(),
        "requested_device": bench_config["device"],
        "compute_backend": "python-standard-library-cpu",
        "gpu_note": "Process affinity is recorded; v0.2 contains no CUDA kernels and does not claim GPU acceleration.",
    }
    station_catalog = load_station_catalog(project_root)
    station = next((item for item in station_catalog if item["station_id"] == task["station_id"]), None)
    if station is None:
        raise KeyError(f"Station not found: {task['station_id']}")
    context = {
        "project_root": project_root,
        "run_dir": run_dir,
        "experiment_config": load_experiment_config(project_root),
        "station_catalog": station_catalog,
        "evaluator_labels": load_evaluator_labels(project_root, station, task),
    }
    context, logger = HydroAgentExecutor(build_registry()).run(task, context)
    trajectory = logger.as_dict()
    evaluation = score_trajectory(task, trajectory, context["final_result"])
    trajectory["evaluation"] = evaluation
    result = dict(context["final_result"])
    result.update({"run_id": run_dir.name, "trajectory_score": evaluation, "environment": environment})
    fieldnames = list(context["rows"][0])
    write_rows(run_dir / "daily_estimates.csv", context["rows"], fieldnames)
    write_json(run_dir / "metrics.json", result)
    write_json(run_dir / "trajectory.json", trajectory)
    write_json(run_dir / "environment.json", environment)
    write_json(run_dir / "data_manifest_evidence.json", {"files": manifest_evidence})
    shutil.copy2(task_path, run_dir / "task.json")
    shutil.copy2(bench_config_path, run_dir / "benchmark_config.yaml")
    shutil.copy2(project_root / "configs" / "arm1_demo.json", run_dir / "experiment_config.json")
    render_task_report(task, result, trajectory, context["rows"], context["station"], run_dir)
    render_benchmark_summary([result], run_dir / "benchmark_summary.html")
    (run_dir / "run.log").write_text(
        f"task={task['task_id']}\nstatus=success\nsteps={len(trajectory['steps'])}\nend_to_end={evaluation['end_to_end']:.6f}\n",
        encoding="utf-8",
    )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hydro-Bench with trajectory and outcome scoring.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--task", type=Path, default=Path("hydro_bench/tasks/HB_0001.json"))
    parser.add_argument("--run-id")
    args = parser.parse_args()
    task_path = args.task if args.task.is_absolute() else args.root / args.task
    run_dir = run_benchmark(args.root, task_path, args.run_id)
    print(run_dir)


if __name__ == "__main__":
    main()
