import json
from pathlib import Path

import pytest

from hydro_agent.tools.smap import match_station_to_smap, read_smap_l3


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "smap" / "smap_l3_tiny.h5"
EXPECTED = json.loads((ROOT / "fixtures" / "expected" / "smap_arm1_match.json").read_text(encoding="utf-8"))


def test_real_smap_reader_preserves_native_variables_units_and_provenance():
    rows, summary = read_smap_l3(FIXTURE, "AM")
    assert len(rows) == 25
    assert summary["source_sha256"] == EXPECTED["source_sha256"]
    assert {row["native_unit"] for row in rows} == {"cm**3/cm**3"}
    assert {row["target_unit"] for row in rows} == {"m3/m3"}
    assert {row["native_variable"] for row in rows} == {
        "/Soil_Moisture_Retrieval_Data_AM/soil_moisture"
    }
    assert all(row["source_file"] == EXPECTED["source_file"] for row in rows)


def test_arm1_matches_exact_expected_smap_pixel():
    rows, _ = read_smap_l3(FIXTURE, "AM")
    match = match_station_to_smap(
        rows, EXPECTED["station_id"], EXPECTED["station_lat"], EXPECTED["station_lon"]
    )
    assert (match["grid_row"], match["grid_col"]) == (
        EXPECTED["expected_grid_row"], EXPECTED["expected_grid_col"]
    )
    assert match["pixel_center_lat"] == pytest.approx(EXPECTED["expected_pixel_center_lat"])
    assert match["pixel_center_lon"] == pytest.approx(EXPECTED["expected_pixel_center_lon"])
    assert match["value_raw"] == pytest.approx(EXPECTED["expected_soil_moisture_raw"])
    assert match["distance_km"] == pytest.approx(20.0793890659)
    assert match["qc_flags"]["retrieval_qual_flag"] == EXPECTED["expected_retrieval_qual_flag"]
    assert match["qc_flags"]["surface_flag"] == EXPECTED["expected_surface_flag"]
    assert match["qc_pass"] is EXPECTED["expected_qc_pass"]
    assert match["rejection_reasons"] == EXPECTED["expected_rejection_reasons"]


def test_distance_threshold_rejects_otherwise_nearest_pixel():
    rows, _ = read_smap_l3(FIXTURE, "AM")
    match = match_station_to_smap(rows, "TOO_FAR", 0.0, 0.0, maximum_distance_km=1.0)
    assert not match["qc_pass"]
    assert "distance_threshold_exceeded" in match["rejection_reasons"]
