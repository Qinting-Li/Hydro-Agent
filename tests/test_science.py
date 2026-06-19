from hydro_agent.assimilation import kalman_update
from hydro_agent.io import read_ismn_ceop
from hydro_agent.metrics import evaluate
from hydro_agent.model import water_balance_step
from hydro_agent.qc import ScientificRefusal, require_coverage


def test_rain_wets_and_bounds_hold():
    wet = water_balance_step(
        0.2, 10.0, 0.0, depth_m=0.1, wilting_point=0.08,
        field_capacity=0.32, saturation=0.46, infiltration_efficiency=0.8,
        et_fraction=0.3, drainage_fraction=0.1,
    )
    assert 0.2 < wet <= 0.46


def test_kalman_update_moves_toward_observation():
    analysis, variance, gain, innovation = kalman_update(0.15, 0.01, 0.25, 0.01, 0.08, 0.46)
    assert 0.15 < analysis < 0.25
    assert variance < 0.01
    assert gain == 0.5
    assert innovation == 0.1


def test_metrics_known_values():
    result = evaluate([0.1, 0.2, 0.3], [0.2, 0.3, 0.4])
    assert abs(result["bias"] - 0.1) < 1e-12
    assert abs(result["ubrmse"]) < 1e-12
    assert abs(result["correlation"] - 1.0) < 1e-12


def test_coverage_gate_refuses_sparse_evidence():
    try:
        require_coverage(100, 20, 60, 0.2)
    except ScientificRefusal:
        pass
    else:
        raise AssertionError("Sparse evidence must be refused")


def test_ismn_ceop_column_mapping(tmp_path):
    sample = tmp_path / "sample.stm"
    sample.write_text(
        "2017/08/10 00:00 2017/08/10 00:00 COSMOS COSMOS ARM-1 "
        "36.60540 -97.48780 322.00 0.00 0.19 0.1410 G M\n",
        encoding="utf-8",
    )
    values = read_ismn_ceop(sample)
    assert list(values.values()) == [0.141]
