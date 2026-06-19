"""Crop small offline fixtures from authenticated NASA source granules."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py


SMAP_DATASETS = (
    "soil_moisture", "latitude", "longitude", "retrieval_qual_flag", "surface_flag",
    "freeze_thaw_fraction", "tb_qual_flag_h", "tb_qual_flag_v", "tb_time_seconds",
    "EASE_row_index", "EASE_column_index",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_smap(source_path: Path, output_root: Path) -> tuple[Path, Path]:
    fixture_path = output_root / "smap" / "smap_l3_tiny.h5"
    expected_path = output_root / "expected" / "smap_arm1_match.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    expected_path.parent.mkdir(parents=True, exist_ok=True)
    source_digest = sha256(source_path)
    row_slice, col_slice = slice(79, 84), slice(218, 223)
    with h5py.File(source_path, "r") as source, h5py.File(fixture_path, "w") as target:
        source_group = source["Soil_Moisture_Retrieval_Data_AM"]
        target_group = target.create_group("Soil_Moisture_Retrieval_Data_AM")
        for key, value in source.attrs.items():
            target.attrs[key] = value
        target.attrs["source_file"] = source_path.name
        target.attrs["source_sha256"] = source_digest
        target.attrs["source_collection"] = "C2938664585-NSIDC_CPRD"
        target.attrs["source_granule"] = "G3087485017-NSIDC_CPRD"
        target.attrs["crop_origin_row"] = row_slice.start
        target.attrs["crop_origin_col"] = col_slice.start
        for name in SMAP_DATASETS:
            source_dataset = source_group[name]
            dataset = target_group.create_dataset(name, data=source_dataset[row_slice, col_slice], compression="gzip")
            for key, value in source_dataset.attrs.items():
                dataset.attrs[key] = value
    expected = {
        "source_file": source_path.name,
        "source_sha256": source_digest,
        "fixture_sha256": sha256(fixture_path),
        "station_id": "US_COSMOS_ARM1",
        "station_lat": 36.6054,
        "station_lon": -97.4878,
        "pass": "AM",
        "expected_grid_row": 81,
        "expected_grid_col": 220,
        "expected_pixel_center_lat": 36.72578048706055,
        "expected_pixel_center_lon": -97.65560150146484,
        "expected_soil_moisture_raw": 0.2580757737159729,
        "expected_retrieval_qual_flag": 8,
        "expected_surface_flag": 128,
        "expected_qc_pass": False,
        "expected_rejection_reasons": ["frozen_ground"],
    }
    expected_path.write_text(json.dumps(expected, indent=2), encoding="utf-8")
    return fixture_path, expected_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smap-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("fixtures"))
    args = parser.parse_args()
    fixture, expected = build_smap(args.smap_source, args.output_root)
    print(fixture)
    print(expected)


if __name__ == "__main__":
    main()
