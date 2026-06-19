"""Export a benchmark run directory into a JSON bundle for the frontend."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _sample_daily_rows(run_dir: Path, stride: int = 3, limit: int = 120) -> list[dict]:
    csv_path = run_dir / "daily_estimates.csv"
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    sampled = rows[::stride][:limit]
    numeric = (
        "precipitation_mm", "et0_mm", "era5_m3m3", "water_balance_m3m3",
        "analysis_m3m3", "analysis_sigma_m3m3", "persistence_m3m3",
        "climatology_m3m3", "linear_regression_m3m3", "ismn_truth_m3m3",
    )
    cleaned: list[dict] = []
    for row in sampled:
        item = {"date": row["date"]}
        for key in numeric:
            if key in row and row[key] not in ("", None):
                try:
                    item[key] = round(float(row[key]), 6)
                except ValueError:
                    pass
        cleaned.append(item)
    return cleaned


def export_bundle(root: Path, run_dir: Path, output: Path, task_path: Path | None = None) -> Path:
    trajectory = json.loads((run_dir / "trajectory.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    task_id = metrics["task_id"]
    resolved_task = task_path or (root / "hydro_bench" / "tasks" / f"{task_id}.json")
    task = json.loads(resolved_task.read_text(encoding="utf-8")) if resolved_task.exists() else None
    bundle = {
        "trajectory": trajectory,
        "metrics": metrics,
        "task": task,
        "daily_rows": _sample_daily_rows(run_dir),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Hydro-Bench run artefacts for the React UI.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-dir", type=Path, required=True, help="Path to outputs/runs/<run-id>")
    parser.add_argument(
        "--task",
        type=Path,
        help="Optional task JSON; defaults to hydro_bench/tasks/<task_id>.json from metrics.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path; defaults to frontend/public/bundles/<task_id>.json",
    )
    args = parser.parse_args()

    run_dir = args.run_dir if args.run_dir.is_absolute() else args.root / args.run_dir
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    default_output = args.root / "frontend" / "public" / "bundles" / f"{metrics['task_id']}.json"
    output = args.output if args.output else default_output
    if not output.is_absolute():
        output = args.root / output
    path = export_bundle(args.root, run_dir, output, args.task)
    print(path)


if __name__ == "__main__":
    main()
