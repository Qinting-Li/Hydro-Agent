from copy import deepcopy

import pytest

from hydro_agent.schema import validate_observation
from hydro_agent.tools.smap import read_smap_l3


def _valid_row():
    rows, _ = read_smap_l3(__import__("pathlib").Path("fixtures/smap/smap_l3_tiny.h5"))
    return next(row for row in rows if row["qc_pass"])


def test_canonical_schema_accepts_real_smap_row():
    validate_observation(_valid_row())


@pytest.mark.parametrize("field", ["source_sha256", "qc_flags", "rejection_reasons", "conversion_formula", "native_unit"])
def test_canonical_schema_rejects_missing_required_evidence(field):
    row = _valid_row()
    del row[field]
    with pytest.raises(ValueError, match="missing fields"):
        validate_observation(row)


def test_canonical_schema_rejects_unknown_unit():
    row = _valid_row()
    row["native_unit"] = "mystery_unit"
    with pytest.raises(ValueError, match="Unknown"):
        validate_observation(row)


def test_canonical_schema_rejects_invalid_sha256():
    row = _valid_row()
    row["source_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="sha256"):
        validate_observation(row)
