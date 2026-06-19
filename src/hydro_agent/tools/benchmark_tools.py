"""Real-data tools used by Hydro-Bench v0.1.

Each tool mutates an explicit run context and returns a compact audit summary.
Unavailable satellite products are not substituted with synthetic values.
"""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from ..agent.tool_registry import ToolRegistry, ToolResult
from ..assimilation import kalman_update
from ..io import read_era5_open_meteo, read_ismn_ceop, read_json
from ..metrics import evaluate
from ..model import water_balance_step
from ..qc import aligned_days, require_coverage


def _between(values: dict[date, object], start: str, end: str) -> dict:
    low, high = date.fromisoformat(start), date.fromisoformat(end)
    return {day: value for day, value in values.items() if low <= day <= high}


def get_station_metadata(context: dict, task: dict, parameters: dict) -> ToolResult:
    catalog = context["project_root"] / "hydro_bench" / "station_catalog.csv"
    with catalog.open(encoding="utf-8", newline="") as stream:
        station = next(
            (row for row in csv.DictReader(stream) if row["station_id"] == parameters["station_id"]),
            None,
        )
    if station is None:
        raise KeyError(f"Station not found: {parameters['station_id']}")
    context["station"] = station
    return ToolResult(
        {
            "station_id": station["station_id"],
            "network": station["network"],
            "lat": float(station["lat"]),
            "lon": float(station["lon"]),
            "depth_m": [float(station["depth_min_m"]), float(station["depth_max_m"])],
            "climate_zone": station["climate_zone"],
            "land_cover": station["land_cover"],
        }
    )


def load_ismn_soil_moisture(context: dict, task: dict, parameters: dict) -> ToolResult:
    path = context["project_root"] / "data" / "raw" / "ismn_arm1.stm"
    truth = _between(read_ismn_ceop(path), parameters["start"], parameters["end"])
    context["truth"] = truth
    return ToolResult(
        {"path": str(path.relative_to(context["project_root"])), "valid_daily_observations": len(truth), "units": "m3/m3", "quality_flag": "G only"},
        qc="pass" if truth else "fail",
    )


def load_era5_forcing(context: dict, task: dict, parameters: dict) -> ToolResult:
    path = context["project_root"] / "data" / "raw" / "era5_arm1.json"
    forcing = _between(read_era5_open_meteo(path), parameters["start"], parameters["end"])
    context["forcing"] = forcing
    return ToolResult(
        {
            "path": str(path.relative_to(context["project_root"])),
            "valid_daily_observations": len(forcing),
            "variables": ["precipitation_mm", "temperature_c", "et0_mm", "era5_soil_moisture"],
        },
        qc="pass" if forcing else "fail",
    )


def match_footprint(context: dict, task: dict, parameters: dict) -> ToolResult:
    days = aligned_days(context["truth"], context["forcing"])
    context["days"] = days
    context["matching"] = {
        "temporal_rule": parameters["temporal_rule"],
        "depth_rule": parameters["depth_rule"],
        "spatial_rule": "station-to-ERA5 point; no satellite footprint in v0.1",
    }
    warnings = ["SMAP footprint and GLDAS grid matching are unavailable in v0.1; regional claims are prohibited."]
    if float(context["station"]["depth_max_m"]) > 0.10:
        warnings.append("ISMN ARM-1 support depth extends to 0.19 m, deeper than the preferred 0-0.10 m surface benchmark target.")
    return ToolResult(
        {"matched_days": len(days), **context["matching"]},
        warnings=warnings,
        qc="warning",
    )


def reject_if_unreliable(context: dict, task: dict, parameters: dict) -> ToolResult:
    config = context["experiment_config"]
    start, end = (date.fromisoformat(value) for value in task["time_range"])
    expected = (end - start).days + 1
    validation = config["validation"]
    require_coverage(expected, len(context["days"]), validation["minimum_pairs"], validation["maximum_missing_fraction"])
    missing_fraction = 1.0 - len(context["days"]) / expected
    context["qc"] = {"accepted": True, "matched_days": len(context["days"]), "missing_fraction": missing_fraction}
    return ToolResult(context["qc"])


def _water_step(previous: float, meteorology: dict, config: dict) -> float:
    soil, model = config["soil"], config["model"]
    return water_balance_step(
        previous,
        meteorology["precipitation_mm"],
        meteorology["et0_mm"],
        depth_m=soil["depth_m"],
        wilting_point=soil["wilting_point"],
        field_capacity=soil["field_capacity"],
        saturation=soil["saturation"],
        infiltration_efficiency=model["infiltration_efficiency"],
        et_fraction=model["et_fraction"],
        drainage_fraction=model["daily_drainage_fraction"],
    )


def compute_water_balance(context: dict, task: dict, parameters: dict) -> ToolResult:
    state = context["experiment_config"]["model"]["initial_moisture"]
    values: dict[date, float] = {}
    for day in context["days"]:
        state = _water_step(state, context["forcing"][day], context["experiment_config"])
        values[day] = state
    context["water_balance"] = values
    soil = context["experiment_config"]["soil"]
    bounded = all(soil["wilting_point"] <= value <= soil["saturation"] for value in values.values())
    context.setdefault("physical_checks", {})["water_balance_bounds"] = bounded
    return ToolResult({"days": len(values), "minimum": min(values.values()), "maximum": max(values.values()), "bounded": bounded}, qc="pass" if bounded else "fail")


def run_kalman_assimilation(context: dict, task: dict, parameters: dict) -> ToolResult:
    config = context["experiment_config"]
    soil, model, assimilation = config["soil"], config["model"], config["assimilation"]
    state = model["initial_moisture"]
    variance = assimilation["initial_variance"]
    rows: list[dict] = []
    for index, day in enumerate(context["days"]):
        meteorology = context["forcing"][day]
        forecast = _water_step(state, meteorology, config)
        forecast_variance = variance + model["process_variance"]
        observation_used = index % assimilation["observation_interval_days"] == 0
        gain = innovation = 0.0
        if observation_used:
            state, variance, gain, innovation = kalman_update(
                forecast, forecast_variance, meteorology["era5_soil_moisture"],
                assimilation["observation_variance"], soil["wilting_point"], soil["saturation"],
            )
        else:
            state, variance = forecast, forecast_variance
        rows.append(
            {
                "date": day.isoformat(),
                "ismn_truth_m3m3": round(context["truth"][day], 6),
                "precipitation_mm": round(meteorology["precipitation_mm"], 4),
                "et0_mm": round(meteorology["et0_mm"], 4),
                "era5_m3m3": round(meteorology["era5_soil_moisture"], 6),
                "persistence_m3m3": round(context["truth"][context["days"][index - 1]] if index else model["initial_moisture"], 6),
                "water_balance_m3m3": round(context["water_balance"][day], 6),
                "kalman_forecast_m3m3": round(forecast, 6),
                "analysis_m3m3": round(state, 6),
                "analysis_sigma_m3m3": round(math.sqrt(variance), 6),
                "observation_used": int(observation_used),
                "kalman_gain": round(gain, 6),
                "innovation_m3m3": round(innovation, 6),
            }
        )
    context["rows"] = rows
    bounded = all(soil["wilting_point"] <= row["analysis_m3m3"] <= soil["saturation"] for row in rows)
    positive_variance = all(row["analysis_sigma_m3m3"] > 0 for row in rows)
    context.setdefault("physical_checks", {}).update({"analysis_bounds": bounded, "positive_uncertainty": positive_variance})
    return ToolResult({"days": len(rows), "observations_assimilated": sum(row["observation_used"] for row in rows), "state_bounded": bounded, "uncertainty_positive": positive_variance})


def compute_uncertainty(context: dict, task: dict, parameters: dict) -> ToolResult:
    test_start = date.fromisoformat(context["experiment_config"]["validation"]["test_start"])
    training = [row for row in context["rows"] if date.fromisoformat(row["date"]) < test_start]
    if not training:
        raise ValueError("Uncertainty calibration requires a non-empty training window.")
    mse = sum((row["analysis_m3m3"] - row["ismn_truth_m3m3"]) ** 2 for row in training) / len(training)
    spread = sum(row["analysis_sigma_m3m3"] ** 2 for row in training) / len(training)
    scale = math.sqrt(mse / max(spread, 1e-12))
    for row in context["rows"]:
        row["calibrated_sigma_m3m3"] = round(row["analysis_sigma_m3m3"] * scale, 6)
    context["uncertainty"] = {"method": "training-window RMSE-to-spread scaling", "training_days": len(training), "scale_factor": scale}
    return ToolResult(context["uncertainty"])


def compute_metrics(context: dict, task: dict, parameters: dict) -> ToolResult:
    config = context["experiment_config"]
    test_start = date.fromisoformat(config["validation"]["test_start"])
    test_rows = [row for row in context["rows"] if date.fromisoformat(row["date"]) >= test_start]
    reference = [row["ismn_truth_m3m3"] for row in test_rows]
    metrics = {
        "last_observation_persistence": evaluate(reference, [row["persistence_m3m3"] for row in test_rows]),
        "era5_baseline": evaluate(reference, [row["era5_m3m3"] for row in test_rows]),
        "water_balance": evaluate(reference, [row["water_balance_m3m3"] for row in test_rows]),
        "kalman_analysis": evaluate(reference, [row["analysis_m3m3"] for row in test_rows], [row["calibrated_sigma_m3m3"] for row in test_rows]),
    }
    best = min(metrics, key=lambda name: metrics[name]["rmse"])
    context["metrics"] = metrics
    context["final_result"] = {
        "experiment": config["experiment"],
        "task_id": task["task_id"],
        "evaluation_period": {"start": test_start.isoformat(), "end": task["time_range"][1]},
        "matched_days_total": len(context["rows"]),
        "matched_days_test": len(test_rows),
        "best_method": best,
        "metrics": metrics,
        "uncertainty_calibration": context["uncertainty"],
        "quality_control": context["qc"],
        "matching": context["matching"],
        "physical_checks": context["physical_checks"],
        "limitations": [
            "Hydro-Bench v0.1 contains one station and does not establish regional generalisation.",
            "SMAP and GLDAS are unavailable in v0.1; no satellite footprint claim is made.",
            "ERA5 surface soil moisture is the sparse assimilation observation and a baseline.",
            "ISMN is reserved for validation except for the explicitly labelled persistence baseline.",
        ],
    }
    return ToolResult({"test_days": len(test_rows), "best_method": best, "best_rmse": metrics[best]["rmse"], "kalman_coverage_95": metrics["kalman_analysis"]["coverage_95"]})


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for function in (
        get_station_metadata,
        load_ismn_soil_moisture,
        load_era5_forcing,
        match_footprint,
        reject_if_unreliable,
        compute_water_balance,
        run_kalman_assimilation,
        compute_uncertainty,
        compute_metrics,
    ):
        registry.register(function.__name__, function)
    return registry


def load_experiment_config(project_root: Path) -> dict:
    return read_json(project_root / "configs" / "arm1_demo.json")
