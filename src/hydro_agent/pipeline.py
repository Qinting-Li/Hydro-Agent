"""Deterministic experiment orchestration; every row carries its provenance."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

from .assimilation import kalman_update
from .io import read_era5_open_meteo, read_ismn_ceop, read_json, write_json, write_rows
from .metrics import evaluate
from .model import water_balance_step
from .qc import aligned_days, require_coverage


def run_experiment(project_root: Path, config_path: Path) -> dict:
    config = read_json(config_path)
    raw = project_root / "data" / "raw"
    ismn_path = raw / "ismn_arm1.stm"
    era5_path = raw / "era5_arm1.json"
    if not ismn_path.exists() or not era5_path.exists():
        raise FileNotFoundError("Run scripts/download_demo.py before the experiment.")

    truth = read_ismn_ceop(ismn_path)
    forcing = read_era5_open_meteo(era5_path)
    days = aligned_days(truth, forcing)
    start = date.fromisoformat(config["start"])
    end = date.fromisoformat(config["end"])
    expected_days = (end - start).days + 1
    validation = config["validation"]
    require_coverage(
        expected_days,
        len(days),
        validation["minimum_pairs"],
        validation["maximum_missing_fraction"],
    )

    soil = config["soil"]
    model = config["model"]
    assimilation = config["assimilation"]
    state = model["initial_moisture"]
    variance = assimilation["initial_variance"]
    rows = []
    for index, day in enumerate(days):
        meteorology = forcing[day]
        forecast = water_balance_step(
            state,
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
        forecast_variance = variance + model["process_variance"]
        has_observation = index % assimilation["observation_interval_days"] == 0
        gain = 0.0
        innovation = 0.0
        if has_observation:
            state, variance, gain, innovation = kalman_update(
                forecast,
                forecast_variance,
                meteorology["era5_soil_moisture"],
                assimilation["observation_variance"],
                soil["wilting_point"],
                soil["saturation"],
            )
        else:
            state, variance = forecast, forecast_variance
        sigma = math.sqrt(variance)
        rows.append(
            {
                "date": day.isoformat(),
                "ismn_truth_m3m3": round(truth[day], 6),
                "precipitation_mm": round(meteorology["precipitation_mm"], 4),
                "et0_mm": round(meteorology["et0_mm"], 4),
                "era5_m3m3": round(meteorology["era5_soil_moisture"], 6),
                "bucket_forecast_m3m3": round(forecast, 6),
                "analysis_m3m3": round(state, 6),
                "analysis_sigma_m3m3": round(sigma, 6),
                "observation_used": int(has_observation),
                "kalman_gain": round(gain, 6),
                "innovation_m3m3": round(innovation, 6),
            }
        )

    test_start = date.fromisoformat(validation["test_start"])
    training_rows = [row for row in rows if date.fromisoformat(row["date"]) < test_start]
    # Learn one uncertainty scale on the training window; the held-out truth stays untouched.
    train_mse = sum(
        (row["analysis_m3m3"] - row["ismn_truth_m3m3"]) ** 2 for row in training_rows
    ) / len(training_rows)
    train_mean_variance = sum(
        row["analysis_sigma_m3m3"] ** 2 for row in training_rows
    ) / len(training_rows)
    uncertainty_scale = math.sqrt(train_mse / max(train_mean_variance, 1e-12))
    for row in rows:
        row["calibrated_sigma_m3m3"] = round(
            row["analysis_sigma_m3m3"] * uncertainty_scale, 6
        )
    test_rows = [row for row in rows if date.fromisoformat(row["date"]) >= test_start]
    reference = [row["ismn_truth_m3m3"] for row in test_rows]
    report = {
        "experiment": config["experiment"],
        "scientific_task": "daily surface soil moisture estimation with uncertainty",
        "evaluation_period": {"start": test_start.isoformat(), "end": end.isoformat()},
        "matched_days_total": len(rows),
        "matched_days_test": len(test_rows),
        "uncertainty_calibration": {
            "method": "training-window RMSE-to-spread scaling",
            "training_days": len(training_rows),
            "scale_factor": uncertainty_scale,
        },
        "data_status": {
            "ismn": "real open test data; ground truth only",
            "era5": "real ERA5 point series served by Open-Meteo",
            "smap": "not used: Earthdata credentials unavailable",
            "sentinel": "not used in point-scale MVP",
        },
        "metrics": {
            "era5_baseline": evaluate(reference, [row["era5_m3m3"] for row in test_rows]),
            "open_loop_bucket": evaluate(reference, [row["bucket_forecast_m3m3"] for row in test_rows]),
            "kalman_analysis": evaluate(
                reference,
                [row["analysis_m3m3"] for row in test_rows],
                [row["calibrated_sigma_m3m3"] for row in test_rows],
            ),
        },
        "limitations": [
            "Point-scale demonstration; satellite footprint mismatch is not resolved.",
            "ERA5-derived surface moisture acts as the sparse retrieval observation in this MVP.",
            "ISMN is never assimilated and is reserved for validation.",
            "A single station is evidence of pipeline correctness, not regional generalisation.",
        ],
    }
    output = project_root / "outputs"
    fieldnames = list(rows[0])
    write_rows(output / "daily_estimates.csv", rows, fieldnames)
    write_json(output / "metrics.json", report)
    return report
