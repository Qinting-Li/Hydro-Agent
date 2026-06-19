"""Command-line entry point. Boring commands are reproducible commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a verifiable soil-moisture experiment.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("configs/arm1_demo.json"))
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else args.root / args.config
    report = run_experiment(args.root, config)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
