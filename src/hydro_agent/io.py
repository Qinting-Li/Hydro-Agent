"""Small, explicit readers. Silent unit conversion is forbidden here."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_ismn_ceop(path: Path) -> dict[date, float]:
    """Read ISMN CEOP rows and return daily valid mean in m3/m3."""
    daily: dict[date, list[float]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            fields = line.split()
            if len(fields) < 15:
                continue
            day = datetime.strptime(fields[0], "%Y/%m/%d").date()
            value = float(fields[12])
            quality_flag = fields[13]
            if quality_flag == "G" and 0.0 <= value <= 0.8:
                daily[day].append(value)
    return {day: sum(values) / len(values) for day, values in daily.items() if values}


def read_era5_open_meteo(path: Path) -> dict[date, dict[str, float]]:
    """Aggregate Open-Meteo's ERA5 hourly response to hydrologic daily inputs."""
    payload = read_json(path)
    hourly = payload["hourly"]
    buckets: dict[date, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    variables = (
        "temperature_2m",
        "precipitation",
        "et0_fao_evapotranspiration",
        "soil_moisture_0_to_7cm",
    )
    for index, stamp in enumerate(hourly["time"]):
        day = datetime.fromisoformat(stamp).date()
        for name in variables:
            value = hourly[name][index]
            if value is not None:
                buckets[day][name].append(float(value))

    result: dict[date, dict[str, float]] = {}
    for day, values in buckets.items():
        if not all(values.get(name) for name in variables):
            continue
        result[day] = {
            "temperature_c": _mean(values["temperature_2m"]),
            "precipitation_mm": sum(values["precipitation"]),
            "et0_mm": sum(values["et0_fao_evapotranspiration"]),
            "era5_soil_moisture": _mean(values["soil_moisture_0_to_7cm"]),
        }
    return result


def write_rows(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)
