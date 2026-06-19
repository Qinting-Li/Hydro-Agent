"""A transparent one-layer water-balance model, deliberately not magical."""

from __future__ import annotations


def water_balance_step(
    previous: float,
    precipitation_mm: float,
    et0_mm: float,
    *,
    depth_m: float,
    wilting_point: float,
    field_capacity: float,
    saturation: float,
    infiltration_efficiency: float,
    et_fraction: float,
    drainage_fraction: float,
) -> float:
    storage_mm = depth_m * 1000.0
    infiltration = infiltration_efficiency * max(precipitation_mm, 0.0) / storage_mm
    evapotranspiration = et_fraction * max(et0_mm, 0.0) / storage_mm
    drainage = drainage_fraction * max(previous - field_capacity, 0.0)
    predicted = previous + infiltration - evapotranspiration - drainage
    return min(saturation, max(wilting_point, predicted))
