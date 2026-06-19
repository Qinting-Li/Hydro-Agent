"""Export all demo UI run bundles for the frontend."""

from __future__ import annotations

import argparse
from pathlib import Path

from export_run_bundle import export_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    mapping = {
        "HB_0001": "demo_ui",
        "HB_0002": "demo_ui_2",
        "HB_0003": "demo_ui_3",
    }
    for task_id, run_id in mapping.items():
        run_dir = args.root / "outputs" / "runs" / run_id
        output = args.root / "frontend" / "public" / "bundles" / f"{task_id}.json"
        if not run_dir.exists():
            raise FileNotFoundError(f"Missing run directory: {run_dir}")
        export_bundle(args.root, run_dir, output)
        print(output)


if __name__ == "__main__":
    main()
