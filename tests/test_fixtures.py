import json
from pathlib import Path

import h5py

from hydro_agent.tools.smap import sha256


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "smap" / "smap_l3_tiny.h5"


def test_smap_fixture_is_real_hdf5_with_verified_provenance():
    manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8"))["fixtures"][0]
    assert FIXTURE.read_bytes()[:8] == b"\x89HDF\r\n\x1a\n"
    assert FIXTURE.stat().st_size == manifest["fixture_bytes"]
    assert sha256(FIXTURE) == manifest["fixture_sha256"]
    with h5py.File(FIXTURE, "r") as source:
        assert source.attrs["source_sha256"] == manifest["source_sha256"]
        assert source.attrs["source_collection"] == manifest["collection_concept_id"]
        assert source.attrs["source_granule"] == manifest["granule_concept_id"]
        assert source.attrs["crop_origin_row"] == 79
        assert source.attrs["crop_origin_col"] == 218


def test_fixture_manifest_forbids_network_dependent_ci():
    manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["offline_only"] is True
