# Hydrologic Earth-Agent / Hydro-Bench

Hydro-Bench is a reproducible benchmark for evaluating tool-use agents in **soil moisture retrieval** and **hydrologic data assimilation**.

It evaluates:

* Hydrologic accuracy
* Tool-use trajectory
* Data leakage safety
* Quality control
* Physical consistency
* Scientific refusal
* Reproducibility

Current version: **Hydro-Bench v0.2.0**

A reproducible single-station benchmark MVP for soil moisture retrieval and hydrologic data assimilation using real ISMN and ERA5 data, with leakage auditing, tool trajectories, baselines, QC, metrics, provenance, and HTML reports.

## Scope

Hydro-Bench v0.2 defines leakage-safe task protocols for hydrologic agent evaluation.

| Task      | Mode                      | ISMN Access Policy                                                      |
| --------- | ------------------------- | ----------------------------------------------------------------------- |
| `HB_0001` | Station-aware forecasting | Historical ISMN allowed; current-day, future, and test labels forbidden |
| `HB_0002` | Satellite-only retrieval  | ISMN observations forbidden from the agent; labels are evaluator-only   |
| `HB_0003` | Blocked gap-filling       | Only pre-gap ISMN observations allowed                                  |

Each tool step records:

* `accessed_inputs`
* `execution_scope`

The leakage evaluator checks each step against task-level `allowed_inputs` and `forbidden_inputs`. Metric computation is evaluator-only, so hidden labels do not enter the agent trajectory.

## Baselines

| Mode                      | Legal Baselines                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------ |
| Station-aware forecasting | Persistence, climatology, linear regression, ERA5, water balance, Kalman                         |
| Satellite-only retrieval  | ERA5, water balance, Kalman                                                                      |
| Blocked gap-filling       | Pre-gap persistence, pre-gap climatology, pre-gap linear regression, ERA5, water balance, Kalman |

Reports rank methods by RMSE and show whether each method outperforms persistence when persistence is applicable.

## Implemented Features

Hydro-Bench v0.2 includes:

* Three benchmark tasks: `HB_0001`, `HB_0002`, `HB_0003`
* Ten benchmark tools for metadata, ISMN, ERA5, QC, matching, water balance, Kalman, baselines, uncertainty, and metrics
* Agent executor with trajectory logging
* Step-level leakage audit
* Evaluator-only hidden ground truth
* Tool-trajectory scoring
* Hydrologic metrics:

  * RMSE
  * Bias
  * ubRMSE
  * Correlation
  * 95% interval coverage
* SHA-256 data provenance
* Git, environment, GPU, config, and task snapshots
* HTML reasoning reports
* Offline SMAP L3 reader tests using a small real HDF5 fixture

## Run

```powershell
cd F:\hydrologic-earth-agent
$env:PYTHONPATH="$PWD\src"
$env:CUDA_VISIBLE_DEVICES="1"

python -m hydro_agent.benchmark.runner --root . --task hydro_bench\tasks\HB_0001.json
python -m hydro_agent.benchmark.runner --root . --task hydro_bench\tasks\HB_0002.json
python -m hydro_agent.benchmark.runner --root . --task hydro_bench\tasks\HB_0003.json
python -m hydro_agent.benchmark.suite --root .
pytest -q
```

Each run writes outputs to:

```text
outputs/runs/<run-id>/
```

Outputs include:

* `metrics.json`
* `trajectory.json`
* `daily_estimates.csv`
* leakage audit
* task/config snapshots
* data hashes
* Git/GPU metadata
* SVG figures
* HTML report

## Multi-Station Support

`station_catalog.csv` stores station-specific `ismn_path` and `era5_path`.

Implemented split support:

* Leave-year-out
* Leave-station-out integrity checks
* Blocked-gap evaluation
* Real-data readiness check

Run:

```powershell
python scripts\generate_station_tasks.py --root . --minimum-stations 30
```

The readiness checker validates whether local data meet the configured multi-station benchmark threshold.

## Reproducibility

Hydro-Bench records:

* `data_manifest.json`
* `configs/hydro_bench_v0.2.yaml`
* `environment.yml`
* `requirements.txt`
* Git commit
* GPU inventory
* `CUDA_VISIBLE_DEVICES`
* Runtime logs
* Config and task snapshots

Current numerical kernels are CPU scalar implementations. GPU binding is recorded for reproducibility.

## Roadmap

### v0.3: Multi-Source Integration

* Integrate SMAP L3 into the benchmark runner
* Add GLDAS/Noah reader, unit conversion, and QC
* Add SMAP footprint and GLDAS grid matching
* Add SMAP and GLDAS baselines
* Extend reports with station, footprint, and grid visualization

### v0.4: Multi-Station Benchmark

* Add at least 30 eligible ISMN stations
* Generate 50–100 real-station tasks
* Evaluate station-wise and climate-wise generalization
* Run true leave-station-out experiments

### v0.5: Research-Grade Assimilation

* Implement Ensemble Kalman Filter
* Add multi-source assimilation
* Add observation operators
* Add model and observation error covariance
* Add uncertainty calibration and ablation studies

## Scientific Positioning

Hydro-Bench v0.2 is a leakage-audited, reproducible benchmark prototype for hydrologic tool-use agents.

Its current contribution is the evaluation framework: task modes, leakage control, trajectory scoring, baseline ranking, scientific refusal, provenance tracking, and reproducible reporting.
