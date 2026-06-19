"""Run every declared Hydro-Bench task and create a cross-task summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ..io import write_json
from ..report.render_html import render_benchmark_summary
from .runner import run_benchmark


def run_suite(project_root: Path, suite_id: str | None = None) -> Path:
    project_root = project_root.resolve()
    suite_id = suite_id or datetime.now(timezone.utc).strftime("suite_%Y%m%dT%H%M%SZ")
    suite_dir = project_root / "outputs" / "runs" / suite_id
    if suite_dir.exists():
        raise FileExistsError(f"Suite output already exists: {suite_dir}")
    task_root = suite_dir / "tasks"
    results = []
    for task_path in sorted((project_root / "hydro_bench" / "tasks").glob("HB_*.json")):
        run_dir = run_benchmark(project_root, task_path, run_id=task_path.stem, output_root=task_root)
        results.append(json.loads((run_dir / "metrics.json").read_text(encoding="utf-8")))
    if not results:
        raise RuntimeError("No Hydro-Bench tasks found.")
    summary = {
        "suite_id": suite_id,
        "task_count": len(results),
        "modes": sorted({item["mode"] for item in results}),
        "mean_trajectory_e2e": sum(item["trajectory_score"]["end_to_end"] for item in results) / len(results),
        "all_leakage_audits_passed": all(item["trajectory_score"]["leakage_audit"]["passed"] for item in results),
        "tasks": [
            {
                "task_id": item["task_id"], "mode": item["mode"], "best_method": item["best_method"],
                "best_rmse": item["metrics"][item["best_method"]]["rmse"],
                "trajectory_e2e": item["trajectory_score"]["end_to_end"],
            }
            for item in results
        ],
    }
    write_json(suite_dir / "suite_metrics.json", summary)
    render_benchmark_summary(results, suite_dir / "benchmark_summary.html")
    return suite_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all Hydro-Bench tasks.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--suite-id")
    args = parser.parse_args()
    print(run_suite(args.root, args.suite_id))


if __name__ == "__main__":
    main()
