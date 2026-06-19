"""Generate mode-specific tasks only for catalog rows backed by real local data."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path


def eligible_stations(root: Path) -> tuple[list[dict], list[dict]]:
    with (root / "hydro_bench" / "station_catalog.csv").open(encoding="utf-8", newline="") as stream:
        stations = list(csv.DictReader(stream))
    eligible, rejected = [], []
    for station in stations:
        span = (date.fromisoformat(station["end_date"]) - date.fromisoformat(station["start_date"])).days + 1
        reasons = []
        if span < 730:
            reasons.append("less_than_two_years")
        if not (root / station["ismn_path"]).exists():
            reasons.append("missing_ismn_file")
        if not (root / station["era5_path"]).exists():
            reasons.append("missing_era5_file")
        if reasons:
            rejected.append({"station_id": station["station_id"], "reasons": reasons})
        else:
            eligible.append(station)
    return eligible, rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--minimum-stations", type=int, default=30)
    args = parser.parse_args()
    eligible, rejected = eligible_stations(args.root)
    climate_zones = sorted({station["climate_zone"] for station in eligible})
    report = {
        "eligible_station_count": len(eligible),
        "minimum_station_target": args.minimum_stations,
        "climate_zones": climate_zones,
        "publication_ready": len(eligible) >= args.minimum_stations and len(climate_zones) >= 4,
        "eligible_station_ids": [station["station_id"] for station in eligible],
        "rejected": rejected,
        "generated_tasks": 0,
        "note": "No task is generated from missing or sub-threshold data; acquire real observations first.",
    }
    target = args.root / "hydro_bench" / "readiness.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(target)
    if not report["publication_ready"]:
        raise SystemExit(
            f"Hydro-Bench data threshold not met: {len(eligible)}/{args.minimum_stations} eligible stations, "
            f"{len(climate_zones)}/4 climate zones. Refusing to fabricate tasks."
        )


if __name__ == "__main__":
    main()
