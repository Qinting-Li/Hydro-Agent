"""Canonical observation contract shared by all Hydro-Bench data sources."""

from __future__ import annotations

import math
import re


CANONICAL_OBSERVATION_FIELDS = (
    "date", "station_id", "lat", "lon", "source_name", "source_file",
    "source_sha256", "native_variable", "native_unit", "target_variable",
    "target_unit", "value_raw", "value_converted", "conversion_formula",
    "depth_m", "grid_row", "grid_col", "pixel_center_lat",
    "pixel_center_lon", "distance_km", "qc_pass", "qc_flags",
    "rejection_reasons", "access_level", "split_id",
)

KNOWN_SOIL_MOISTURE_UNITS = {"m3/m3", "m³/m³", "cm**3/cm**3", "cm3/cm3"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_observation(row: dict) -> None:
    missing = [field for field in CANONICAL_OBSERVATION_FIELDS if field not in row]
    if missing:
        raise ValueError(f"Canonical observation missing fields: {missing}")
    if not SHA256_PATTERN.fullmatch(str(row["source_sha256"]).lower()):
        raise ValueError("source_sha256 must be a 64-character hexadecimal digest.")
    if row["target_variable"] == "soil_moisture" and row["target_unit"] != "m3/m3":
        raise ValueError("Canonical soil moisture must use m3/m3.")
    if row["native_unit"] not in KNOWN_SOIL_MOISTURE_UNITS:
        raise ValueError(f"Unknown soil-moisture unit: {row['native_unit']}")
    if not isinstance(row["qc_pass"], bool):
        raise ValueError("qc_pass must be boolean.")
    if not isinstance(row["qc_flags"], dict) or not isinstance(row["rejection_reasons"], list):
        raise ValueError("QC flags and rejection reasons must be structured values.")
    if not row["source_file"] or not row["native_variable"] or not row["conversion_formula"]:
        raise ValueError("Source provenance and conversion formula are mandatory.")
    value = row["value_converted"]
    if row["qc_pass"] and (value is None or not math.isfinite(float(value))):
        raise ValueError("QC-passing observations require a finite converted value.")


def validate_observation_table(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Observation table cannot be empty.")
    for row in rows:
        validate_observation(row)
