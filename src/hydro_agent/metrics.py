"""Validation metrics commonly used for satellite soil moisture."""

from __future__ import annotations

import math


def evaluate(reference: list[float], estimate: list[float], sigma: list[float] | None = None) -> dict:
    if len(reference) != len(estimate) or len(reference) < 2:
        raise ValueError("Reference and estimate need equal length >= 2.")
    n = len(reference)
    errors = [prediction - truth for truth, prediction in zip(reference, estimate)]
    bias = sum(errors) / n
    rmse = math.sqrt(sum(error * error for error in errors) / n)
    ubrmse = math.sqrt(sum((error - bias) ** 2 for error in errors) / n)
    mean_ref = sum(reference) / n
    mean_est = sum(estimate) / n
    covariance = sum((x - mean_ref) * (y - mean_est) for x, y in zip(reference, estimate))
    spread_ref = math.sqrt(sum((x - mean_ref) ** 2 for x in reference))
    spread_est = math.sqrt(sum((y - mean_est) ** 2 for y in estimate))
    correlation = covariance / (spread_ref * spread_est) if spread_ref and spread_est else float("nan")
    squared_error = sum(error * error for error in errors)
    reference_variance = sum((value - mean_ref) ** 2 for value in reference)
    nse = 1.0 - squared_error / reference_variance if reference_variance else float("nan")
    std_ref = math.sqrt(reference_variance / n)
    std_est = math.sqrt(sum((value - mean_est) ** 2 for value in estimate) / n)
    alpha = std_est / std_ref if std_ref else float("nan")
    beta = mean_est / mean_ref if mean_ref else float("nan")
    kge = (
        1.0 - math.sqrt((correlation - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)
        if all(math.isfinite(value) for value in (correlation, alpha, beta))
        else float("nan")
    )
    result = {
        "n": n,
        "rmse": rmse,
        "bias": bias,
        "correlation": correlation,
        "ubrmse": ubrmse,
        "nse": nse,
        "kge": kge,
    }
    if sigma is not None:
        if len(sigma) != n:
            raise ValueError("Sigma must match the paired sample count.")
        safe_sigma = [max(value, 1e-9) for value in sigma]
        result["mean_predicted_sigma"] = sum(safe_sigma) / n
        result["coverage_95"] = sum(
            abs(error) <= 1.96 * uncertainty for error, uncertainty in zip(errors, safe_sigma)
        ) / n
        result["calibration_error_95"] = abs(result["coverage_95"] - 0.95)
    return result
