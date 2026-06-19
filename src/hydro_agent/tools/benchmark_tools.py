"""Mode-aware real-data tools for Hydro-Bench.

Ground-truth labels live in ``context['evaluator_labels']`` and are loaded by the
benchmark harness, not an agent tool. Agent tools declare every data class they
access; the evaluator audits those declarations against each task policy.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

from ..agent.tool_registry import ToolRegistry, ToolResult
from ..assimilation import kalman_update
from ..io import read_era5_open_meteo, read_ismn_ceop, read_json
from ..metrics import evaluate
from ..model import water_balance_step
from ..qc import aligned_days, require_coverage
from ..benchmark.splits import leave_year_out


def _between(values: dict[date, object], start: str, end: str) -> dict:
    low, high = date.fromisoformat(start), date.fromisoformat(end)
    return {day: value for day, value in values.items() if low <= day <= high}


def load_station_catalog(project_root: Path) -> list[dict]:
    with (project_root / "hydro_bench" / "station_catalog.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def load_evaluator_labels(project_root: Path, station: dict, task: dict) -> dict[date, float]:
    path = project_root / station["ismn_path"]
    return _between(read_ismn_ceop(path), task["time_range"][0], task["time_range"][1])


def get_station_metadata(context: dict, task: dict, parameters: dict) -> ToolResult:
    station = next((row for row in context["station_catalog"] if row["station_id"] == parameters["station_id"]), None)
    if station is None:
        raise KeyError(f"Station not found: {parameters['station_id']}")
    context["station"] = station
    return ToolResult(
        {
            "station_id": station["station_id"], "network": station["network"],
            "lat": float(station["lat"]), "lon": float(station["lon"]),
            "depth_m": [float(station["depth_min_m"]), float(station["depth_max_m"])],
            "climate_zone": station["climate_zone"], "land_cover": station["land_cover"],
        },
        accessed_inputs=["station_metadata"],
    )


def load_station_history(context: dict, task: dict, parameters: dict) -> ToolResult:
    labels = context["evaluator_labels"]
    if task["mode"] == "station-aware_forecasting":
        test_year = int(task["split"]["test_year"])
        history = {day: value for day, value in labels.items() if day.year != test_year}
        access = "historical_ISMN"
    elif task["mode"] == "gap-filling":
        gap_start = date.fromisoformat(task["gap"][0])
        history = {day: value for day, value in labels.items() if day < gap_start}
        access = "pre_gap_ISMN"
    else:
        raise ValueError("Satellite-only retrieval cannot load station soil-moisture history.")
    if not history:
        raise ValueError("No legal station history is available for this task.")
    context["station_history"] = history
    return ToolResult(
        {"history_days": len(history), "last_history_date": max(history).isoformat(), "label_visibility": access},
        accessed_inputs=[access],
    )


def load_era5_forcing(context: dict, task: dict, parameters: dict) -> ToolResult:
    path = context["project_root"] / context["station"]["era5_path"]
    forcing = _between(read_era5_open_meteo(path), parameters["start"], parameters["end"])
    context["forcing"] = forcing
    return ToolResult(
        {"path": str(path.relative_to(context["project_root"])), "valid_daily_observations": len(forcing),
         "variables": ["precipitation_mm", "temperature_c", "et0_mm", "era5_soil_moisture"]},
        qc="pass" if forcing else "fail", accessed_inputs=["ERA5"],
    )


def match_footprint(context: dict, task: dict, parameters: dict) -> ToolResult:
    days = aligned_days(context["evaluator_labels"], context["forcing"])
    context["days"] = days
    context["matching"] = {
        "temporal_rule": parameters["temporal_rule"], "depth_rule": parameters["depth_rule"],
        "spatial_rule": "station-to-ERA5 point; SMAP/GLDAS footprint unavailable in v0.2",
    }
    warnings = ["SMAP footprint and GLDAS grid matching remain unavailable; regional claims are prohibited."]
    if float(context["station"]["depth_max_m"]) > 0.10:
        warnings.append("Station support depth exceeds the preferred 0-0.10 m surface target.")
    return ToolResult(
        {"matched_days": len(days), **context["matching"]}, warnings=warnings, qc="warning",
        accessed_inputs=["ERA5", "station_metadata", "ISMN_availability_metadata"],
    )


def reject_if_unreliable(context: dict, task: dict, parameters: dict) -> ToolResult:
    start, end = (date.fromisoformat(value) for value in task["time_range"])
    expected = (end - start).days + 1
    validation = context["experiment_config"]["validation"]
    require_coverage(expected, len(context["days"]), validation["minimum_pairs"], validation["maximum_missing_fraction"])
    missing_fraction = 1.0 - len(context["days"]) / expected
    context["qc"] = {"accepted": True, "matched_days": len(context["days"]), "missing_fraction": missing_fraction}
    return ToolResult(context["qc"], accessed_inputs=["ISMN_availability_metadata"])


def _water_step(previous: float, meteorology: dict, config: dict) -> float:
    soil, model = config["soil"], config["model"]
    return water_balance_step(
        previous, meteorology["precipitation_mm"], meteorology["et0_mm"],
        depth_m=soil["depth_m"], wilting_point=soil["wilting_point"], field_capacity=soil["field_capacity"],
        saturation=soil["saturation"], infiltration_efficiency=model["infiltration_efficiency"],
        et_fraction=model["et_fraction"], drainage_fraction=model["daily_drainage_fraction"],
    )


def compute_water_balance(context: dict, task: dict, parameters: dict) -> ToolResult:
    state = context["experiment_config"]["model"]["initial_moisture"]
    values = {}
    for day in context["days"]:
        state = _water_step(state, context["forcing"][day], context["experiment_config"])
        values[day] = state
    context["water_balance"] = values
    soil = context["experiment_config"]["soil"]
    bounded = all(soil["wilting_point"] <= value <= soil["saturation"] for value in values.values())
    context.setdefault("physical_checks", {})["water_balance_bounds"] = bounded
    return ToolResult(
        {"days": len(values), "minimum": min(values.values()), "maximum": max(values.values()), "bounded": bounded},
        qc="pass" if bounded else "fail", accessed_inputs=["ERA5", "model_config"],
    )


def run_kalman_assimilation(context: dict, task: dict, parameters: dict) -> ToolResult:
    config = context["experiment_config"]
    soil, model, assimilation = config["soil"], config["model"], config["assimilation"]
    state, variance = model["initial_moisture"], assimilation["initial_variance"]
    rows = []
    for index, day in enumerate(context["days"]):
        meteorology = context["forcing"][day]
        forecast = _water_step(state, meteorology, config)
        forecast_variance = variance + model["process_variance"]
        used = index % assimilation["observation_interval_days"] == 0
        gain = innovation = 0.0
        if used:
            state, variance, gain, innovation = kalman_update(
                forecast, forecast_variance, meteorology["era5_soil_moisture"], assimilation["observation_variance"],
                soil["wilting_point"], soil["saturation"],
            )
        else:
            state, variance = forecast, forecast_variance
        rows.append({
            "date": day.isoformat(),
            "precipitation_mm": round(meteorology["precipitation_mm"], 4), "et0_mm": round(meteorology["et0_mm"], 4),
            "era5_m3m3": round(meteorology["era5_soil_moisture"], 6),
            "water_balance_m3m3": round(context["water_balance"][day], 6),
            "kalman_forecast_m3m3": round(forecast, 6), "analysis_m3m3": round(state, 6),
            "analysis_sigma_m3m3": round(math.sqrt(variance), 6), "observation_used": int(used),
            "kalman_gain": round(gain, 6), "innovation_m3m3": round(innovation, 6),
        })
    context["rows"] = rows
    bounded = all(soil["wilting_point"] <= row["analysis_m3m3"] <= soil["saturation"] for row in rows)
    positive = all(row["analysis_sigma_m3m3"] > 0 for row in rows)
    context.setdefault("physical_checks", {}).update({"analysis_bounds": bounded, "positive_uncertainty": positive})
    return ToolResult(
        {"days": len(rows), "observations_assimilated": sum(row["observation_used"] for row in rows),
         "state_bounded": bounded, "uncertainty_positive": positive},
        accessed_inputs=["ERA5", "model_config"],
    )


def _fit_linear(history: dict[date, float], forcing: dict[date, dict]) -> tuple[float, float]:
    pairs = [(forcing[day]["era5_soil_moisture"], value) for day, value in history.items() if day in forcing]
    mean_x = sum(x for x, _ in pairs) / len(pairs)
    mean_y = sum(y for _, y in pairs) / len(pairs)
    denominator = sum((x - mean_x) ** 2 for x, _ in pairs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in pairs) / denominator if denominator else 0.0
    return mean_y - slope * mean_x, slope


def compute_baselines(context: dict, task: dict, parameters: dict) -> ToolResult:
    eligible = ["era5_baseline", "water_balance", "kalman_analysis"]
    excluded = {}
    accessed = ["ERA5"]
    if task["mode"] == "satellite-only_retrieval":
        excluded = {
            "persistence": "forbidden: station observations are unavailable at inference",
            "climatology": "forbidden: no station-specific ISMN training labels",
            "linear_regression": "forbidden: no station-specific ISMN training labels",
        }
    else:
        history = context["station_history"]
        access = "historical_ISMN" if task["mode"] == "station-aware_forecasting" else "pre_gap_ISMN"
        accessed.append(access)
        monthly = defaultdict(list)
        for day, value in history.items():
            monthly[day.month].append(value)
        overall = sum(history.values()) / len(history)
        intercept, slope = _fit_linear(history, context["forcing"])
        ordered_days = context["days"]
        previous_observation = None
        if task["mode"] == "gap-filling":
            previous_observation = history[max(history)]
        for index, row in enumerate(context["rows"]):
            day = date.fromisoformat(row["date"])
            if task["mode"] == "station-aware_forecasting":
                previous_day = ordered_days[index - 1] if index else None
                previous_observation = context["evaluator_labels"].get(previous_day, overall) if previous_day else overall
            row["persistence_m3m3"] = round(previous_observation, 6)
            row["climatology_m3m3"] = round(sum(monthly[day.month]) / len(monthly[day.month]) if monthly[day.month] else overall, 6)
            row["linear_regression_m3m3"] = round(intercept + slope * row["era5_m3m3"], 6)
        eligible.extend(["persistence", "climatology", "linear_regression"])
        context["baseline_model"] = {"linear_intercept": intercept, "linear_slope": slope, "history_days": len(history)}
    context["baseline_eligibility"] = {"eligible": eligible, "excluded": excluded}
    return ToolResult(
        {
            "eligible": eligible,
            "excluded": excluded,
            "linear_model": context.get("baseline_model"),
            "persistence_rule": (
                "rolling t-1 observation only" if task["mode"] == "station-aware_forecasting"
                else "last pre-gap observation held through gap" if task["mode"] == "gap-filling"
                else "not applicable"
            ),
        },
        accessed_inputs=accessed,
    )


def _training_rows(context: dict, task: dict) -> tuple[list[dict], str | None]:
    if task["mode"] == "station-aware_forecasting":
        year = int(task["split"]["test_year"])
        return [row for row in context["rows"] if date.fromisoformat(row["date"]).year != year], "historical_ISMN"
    if task["mode"] == "gap-filling":
        gap_start = date.fromisoformat(task["gap"][0])
        return [row for row in context["rows"] if date.fromisoformat(row["date"]) < gap_start], "pre_gap_ISMN"
    return [], None


def compute_uncertainty(context: dict, task: dict, parameters: dict) -> ToolResult:
    training, access = _training_rows(context, task)
    if training:
        mse = sum(
            (row["analysis_m3m3"] - context["evaluator_labels"][date.fromisoformat(row["date"])]) ** 2
            for row in training
        ) / len(training)
        spread = sum(row["analysis_sigma_m3m3"] ** 2 for row in training) / len(training)
        scale = math.sqrt(mse / max(spread, 1e-12))
        method = "legal-history RMSE-to-spread scaling"
    else:
        scale, method = 1.0, "uncalibrated model spread; ISMN labels forbidden"
    for row in context["rows"]:
        row["calibrated_sigma_m3m3"] = round(row["analysis_sigma_m3m3"] * scale, 6)
    context["uncertainty"] = {"method": method, "training_days": len(training), "scale_factor": scale}
    return ToolResult(context["uncertainty"], accessed_inputs=[access] if access else ["model_config"])


def _evaluation_rows(context: dict, task: dict) -> list[dict]:
    if task["mode"] == "gap-filling":
        start, end = (date.fromisoformat(value) for value in task["gap"])
        return [row for row in context["rows"] if start <= date.fromisoformat(row["date"]) <= end]
    if task["split"]["type"] == "leave-year-out":
        _, test_days = leave_year_out(context["days"], int(task["split"]["test_year"]))
        test_set = set(test_days)
        return [row for row in context["rows"] if date.fromisoformat(row["date"]) in test_set]
    raise ValueError(f"Unsupported split: {task['split']}")


def compute_metrics(context: dict, task: dict, parameters: dict) -> ToolResult:
    test_rows = _evaluation_rows(context, task)
    for row in context["rows"]:
        row["ismn_truth_m3m3"] = round(context["evaluator_labels"][date.fromisoformat(row["date"])], 6)
    reference = [row["ismn_truth_m3m3"] for row in test_rows]
    metrics = {
        "era5_baseline": evaluate(reference, [row["era5_m3m3"] for row in test_rows]),
        "water_balance": evaluate(reference, [row["water_balance_m3m3"] for row in test_rows]),
        "kalman_analysis": evaluate(reference, [row["analysis_m3m3"] for row in test_rows], [row["calibrated_sigma_m3m3"] for row in test_rows]),
    }
    if "persistence" in context["baseline_eligibility"]["eligible"]:
        metrics.update({
            "persistence": evaluate(reference, [row["persistence_m3m3"] for row in test_rows]),
            "climatology": evaluate(reference, [row["climatology_m3m3"] for row in test_rows]),
            "linear_regression": evaluate(reference, [row["linear_regression_m3m3"] for row in test_rows]),
        })
    best = min(metrics, key=lambda name: metrics[name]["rmse"])
    context["metrics"] = metrics
    context["final_result"] = {
        "experiment": context["experiment_config"]["experiment"], "task_id": task["task_id"], "mode": task["mode"],
        "evaluation_period": {"start": test_rows[0]["date"], "end": test_rows[-1]["date"]},
        "matched_days_total": len(context["rows"]), "matched_days_test": len(test_rows), "best_method": best,
        "metrics": metrics, "baseline_eligibility": context["baseline_eligibility"],
        "uncertainty_calibration": context["uncertainty"], "quality_control": context["qc"],
        "matching": context["matching"], "physical_checks": context["physical_checks"], "split": task["split"],
        "limitations": [
            "Hydro-Bench v0.2 currently has one real station; leave-station-out generalisation is not claimable.",
            "SMAP and GLDAS are unavailable; no satellite footprint claim is made.",
            "ISMN is hidden evaluator ground truth; only mode-permitted history can enter agent baselines.",
        ],
    }
    return ToolResult(
        {"test_days": len(test_rows), "best_method": best, "best_rmse": metrics[best]["rmse"],
         "kalman_coverage_95": metrics["kalman_analysis"]["coverage_95"]},
        accessed_inputs=["test_label"], execution_scope="evaluator",
    )


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for function in (
        get_station_metadata, load_station_history, load_era5_forcing, match_footprint,
        reject_if_unreliable, compute_water_balance, run_kalman_assimilation,
        compute_baselines, compute_uncertainty, compute_metrics,
    ):
        registry.register(function.__name__, function)
    return registry


def load_experiment_config(project_root: Path) -> dict:
    return read_json(project_root / "configs" / "arm1_demo.json")
