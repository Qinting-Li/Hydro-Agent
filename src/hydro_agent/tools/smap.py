"""Offline reader for NASA SMAP SPL3SMP HDF5 granules and real fixtures."""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import h5py
import numpy as np

from ..schema import validate_observation_table


SMAP_EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
RECOMMENDED_RETRIEVAL_FLAGS = {0, 8}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _mapping(pass_name: str) -> dict[str, str]:
    suffix = "" if pass_name == "AM" else "_pm"
    return {
        "group": f"Soil_Moisture_Retrieval_Data_{pass_name}",
        "soil": f"soil_moisture{suffix}", "lat": f"latitude{suffix}",
        "lon": f"longitude{suffix}", "quality": f"retrieval_qual_flag{suffix}",
        "surface": f"surface_flag{suffix}", "freeze": f"freeze_thaw_fraction{suffix}",
        "tb_h": f"tb_qual_flag_h{suffix}", "tb_v": f"tb_qual_flag_v{suffix}",
        "time": f"tb_time_seconds{suffix}", "row": f"EASE_row_index{suffix}",
        "col": f"EASE_column_index{suffix}",
    }


def _is_fill(value, dataset) -> bool:
    fill = dataset.attrs.get("_FillValue")
    return fill is not None and value == fill


def _qc_reasons(soil: float, quality: int, surface: int, tb_h: int, tb_v: int, dataset) -> list[str]:
    reasons = []
    if _is_fill(soil, dataset) or not math.isfinite(soil):
        reasons.append("fill_or_nan")
    else:
        valid_min = float(dataset.attrs.get("valid_min", 0.0))
        valid_max = float(dataset.attrs.get("valid_max", 0.8))
        if not valid_min <= soil <= valid_max:
            reasons.append("soil_moisture_out_of_range")
    if quality not in RECOMMENDED_RETRIEVAL_FLAGS:
        reasons.append("retrieval_not_recommended")
    if surface & (1 | 2):
        reasons.append("water_body")
    if surface & (32 | 64):
        reasons.append("snow_or_ice")
    if surface & (128 | 256):
        reasons.append("frozen_ground")
    if (tb_h | tb_v) & (4 | 16384):
        reasons.append("rfi_contamination")
    return reasons


def read_smap_l3(path: Path, pass_name: str = "AM", station_id: str = "UNMATCHED", split_id: str = "fixture") -> tuple[list[dict], dict]:
    pass_name = pass_name.upper()
    if pass_name not in {"AM", "PM"}:
        raise ValueError("SMAP pass_name must be AM or PM.")
    names = _mapping(pass_name)
    rows = []
    rejection_counts: dict[str, int] = {}
    with h5py.File(path, "r") as source:
        group = source[names["group"]]
        required = set(names.values()) - {names["group"]}
        missing = sorted(required - set(group.keys()))
        if missing:
            raise ValueError(f"SMAP group missing required datasets: {missing}")
        source_digest = _text(source.attrs.get("source_sha256", sha256(path))).lower()
        source_file = _text(source.attrs.get("source_file", path.name))
        native_unit = _text(group[names["soil"]].attrs.get("units", ""))
        match = re.search(r"_(\d{8})_", source_file)
        fallback_date = datetime.strptime(match.group(1), "%Y%m%d").date().isoformat() if match else None
        shape = group[names["soil"]].shape
        for local_row in range(shape[0]):
            for local_col in range(shape[1]):
                soil = float(group[names["soil"]][local_row, local_col])
                latitude = float(group[names["lat"]][local_row, local_col])
                longitude = float(group[names["lon"]][local_row, local_col])
                quality = int(group[names["quality"]][local_row, local_col])
                surface = int(group[names["surface"]][local_row, local_col])
                freeze = float(group[names["freeze"]][local_row, local_col])
                tb_h = int(group[names["tb_h"]][local_row, local_col])
                tb_v = int(group[names["tb_v"]][local_row, local_col])
                seconds = float(group[names["time"]][local_row, local_col])
                grid_row = int(group[names["row"]][local_row, local_col])
                grid_col = int(group[names["col"]][local_row, local_col])
                reasons = _qc_reasons(soil, quality, surface, tb_h, tb_v, group[names["soil"]])
                if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                    reasons.append("invalid_coordinate")
                for reason in set(reasons):
                    rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
                timestamp = fallback_date
                if seconds >= 0 and math.isfinite(seconds):
                    timestamp = (SMAP_EPOCH + timedelta(seconds=seconds)).date().isoformat()
                qc_pass = not reasons
                rows.append(
                    {
                        "date": timestamp, "station_id": station_id, "lat": latitude, "lon": longitude,
                        "source_name": "NASA SMAP SPL3SMP V009", "source_file": source_file,
                        "source_sha256": source_digest,
                        "native_variable": f"/{names['group']}/{names['soil']}", "native_unit": native_unit,
                        "target_variable": "soil_moisture", "target_unit": "m3/m3", "value_raw": soil,
                        "value_converted": soil if qc_pass else None,
                        "conversion_formula": "m3/m3 = cm3/cm3 (identity volumetric ratio)", "depth_m": 0.05,
                        "grid_row": grid_row, "grid_col": grid_col, "pixel_center_lat": latitude,
                        "pixel_center_lon": longitude, "distance_km": None, "qc_pass": qc_pass,
                        "qc_flags": {"retrieval_qual_flag": quality, "surface_flag": surface,
                                     "freeze_thaw_fraction": freeze, "tb_qual_flag_h": tb_h, "tb_qual_flag_v": tb_v},
                        "rejection_reasons": sorted(set(reasons)), "access_level": "agent_input", "split_id": split_id,
                    }
                )
    validate_observation_table(rows)
    summary = {
        "total": len(rows), "accepted": sum(row["qc_pass"] for row in rows),
        "rejected": sum(not row["qc_pass"] for row in rows), "rejection_counts": rejection_counts,
        "source_sha256": rows[0]["source_sha256"], "pass": pass_name,
    }
    return rows, summary


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(((lon2 - lon1 + 180.0) % 360.0) - 180.0)
    value = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def match_station_to_smap(rows: list[dict], station_id: str, lat: float, lon: float, maximum_distance_km: float = 36.0) -> dict:
    candidates = [row for row in rows if -90 <= row["pixel_center_lat"] <= 90 and -180 <= row["pixel_center_lon"] <= 180]
    if not candidates:
        raise ValueError("SMAP fixture contains no valid pixel coordinates.")
    ranked = sorted(
        ((_haversine_km(lat, lon, row["pixel_center_lat"], row["pixel_center_lon"]), row) for row in candidates),
        key=lambda item: (item[0], item[1]["grid_row"], item[1]["grid_col"]),
    )
    distance, selected = ranked[0]
    matched = dict(selected)
    matched.update({"station_id": station_id, "lat": lat, "lon": lon, "distance_km": distance})
    if distance > maximum_distance_km:
        matched["qc_pass"] = False
        matched["value_converted"] = None
        matched["rejection_reasons"] = sorted(set(matched["rejection_reasons"] + ["distance_threshold_exceeded"]))
    return matched
