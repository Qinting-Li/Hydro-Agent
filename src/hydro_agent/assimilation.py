"""Scalar Kalman update with bounded soil-water state and explicit variance."""

from __future__ import annotations


def kalman_update(
    forecast: float,
    forecast_variance: float,
    observation: float,
    observation_variance: float,
    low: float,
    high: float,
) -> tuple[float, float, float, float]:
    innovation = observation - forecast
    innovation_variance = forecast_variance + observation_variance
    gain = forecast_variance / innovation_variance
    analysis = min(high, max(low, forecast + gain * innovation))
    analysis_variance = max((1.0 - gain) * forecast_variance, 1e-12)
    return analysis, analysis_variance, gain, innovation
