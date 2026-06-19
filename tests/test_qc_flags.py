from pathlib import Path

from hydro_agent.tools.smap import read_smap_l3


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "smap" / "smap_l3_tiny.h5"


def test_smap_qc_removes_bad_quality_and_physical_flags():
    rows, summary = read_smap_l3(FIXTURE, "AM")
    assert summary["accepted"] == 15
    assert summary["rejected"] == 10
    assert summary["rejection_counts"]["retrieval_not_recommended"] == 5
    assert summary["rejection_counts"]["frozen_ground"] == 6
    assert summary["rejection_counts"]["water_body"] == 2
    assert summary["rejection_counts"]["snow_or_ice"] == 1
    assert summary["rejection_counts"]["rfi_contamination"] == 3
    assert all(row["value_converted"] is None for row in rows if not row["qc_pass"])


def test_multiple_qc_failures_preserve_all_rejection_reasons():
    rows, _ = read_smap_l3(FIXTURE, "AM")
    multi = [row for row in rows if len(row["rejection_reasons"]) > 1]
    assert multi
    assert all(row["rejection_reasons"] == sorted(set(row["rejection_reasons"])) for row in multi)
