# Hydrologic Earth-Agent / Hydro-Bench

Hydro-Bench 是一个可审计的水文遥感 agent 评测工具链。它同时评估最终水文结果和工具调用轨迹，并明确记录数据质量、物理边界、失败拒绝和复现信息。

## 当前版本：v0.1

v0.1 将真实 COSMOS ARM-1 / ISMN + ERA5 单站实验包装成第一个 benchmark 任务 `HB_0001`：

- 真实 ISMN 地面土壤湿度，仅作验证；
- ERA5 降雨、ET 和表层土壤湿度 forcing / baseline；
- persistence、独立 water-balance、Kalman assimilation baseline；
- 训练窗不确定性校准，测试窗 RMSE、Bias、ubRMSE、R、NSE、KGE 和 coverage；
- 9 步标准工具轨迹，记录输入、输出摘要、耗时、状态、warning 和 QC；
- TAO、TIO、TEM、Param、Efficiency、Accuracy、Hydro-QC、Phys-Consistency；
- 每次运行保存不可变 config、任务、数据哈希证据、环境、指标、轨迹、图和 HTML 报告。

v0.1 **不是**多站卫星 benchmark。SMAP、GLDAS、SMOS、Sentinel 尚未接入，报告会明确拒绝 footprint 和区域泛化结论，不会合成或冒充这些数据。

## 一条命令复现

Windows PowerShell：

```powershell
cd F:\hydrologic-earth-agent
$env:PYTHONPATH="$PWD\src"
$env:CUDA_VISIBLE_DEVICES="1"
python -m hydro_agent.benchmark.runner --root .
pytest -q
```

新运行写入 `outputs/runs/<UTC-run-id>/`：

```text
metrics.json                 final hydrologic metrics + environment
trajectory.json              tool calls + trajectory scores
daily_estimates.csv          row-level audit table
data_manifest_evidence.json  verified SHA-256 evidence
environment.json             Python/Git/GPU provenance
task.json                    immutable task snapshot
benchmark_config.yaml        immutable benchmark config snapshot
experiment_config.json       immutable experiment config snapshot
report.html                  per-task Agent Reasoning Report
benchmark_summary.html       benchmark summary
figures/                     map, time series, scatter, uncertainty
run.log                      compact run status
```

配置文件使用 JSON-compatible YAML，因此运行时仅依赖 Python 标准库。`pytest` 是唯一测试依赖。

## RTX 6000 说明

RTX 6000 是本机 GPU 1。命令通过 `CUDA_VISIBLE_DEVICES=1` 绑定进程，并在 `environment.json` 记录 GPU inventory。v0.1 数值内核是标量水量平衡和 Kalman 方程，没有 CUDA kernel，因此不会虚报 GPU 加速。后续 EnKF ensemble、栅格 SMAP/GLDAS 和 Sentinel 批处理才是合理的 GPU 工作负载。

## 工具路径

```text
get_station_metadata
→ load_ismn_soil_moisture
→ load_era5_forcing
→ match_footprint
→ reject_if_unreliable
→ compute_water_balance
→ run_kalman_assimilation
→ compute_uncertainty
→ compute_metrics
```

## 代码结构

```text
src/hydro_agent/
  tools/       real-data hydrologic tools and QC summaries
  agent/       planner, registry, executor, trajectory logger
  benchmark/   task loader, runner and scorer
  report/      dependency-free HTML/SVG report renderer
hydro_bench/
  station_catalog.csv
  tasks/HB_0001.json
configs/
  hydro_bench_v0.1.yaml
  arm1_demo.json
```

## 科学边界与下一里程碑

Hydro-Bench v0.2/v0.3 必须以真实许可和数据获取为前提完成：至少 30 个表层 ISMN 站、两年以上时段、SMAP L3、GLDAS/Noah、官方 QC、footprint/grid 匹配以及 50–100 个任务。没有这些证据前，本仓库只声称 v0.1 单站工具链与评测闭环成立。
