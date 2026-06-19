# Hydrologic Earth-Agent / Hydro-Bench

Hydro-Bench 同时评估水文结果、工具轨迹、数据许可边界、QC、物理一致性和失败拒绝。

## v0.2：任务模式与泄漏审计

当前真实数据仍只有 COSMOS ARM-1 的 ISMN + ERA5，因此 v0.2 不声称多站泛化或卫星 footprint 验证。它先解决评测定义问题：

| Task | 模式 | ISMN 输入策略 |
|---|---|---|
| `HB_0001` | station-aware forecasting | 允许历史 ISMN；禁止当前日、未来和测试标签 |
| `HB_0002` | satellite-only retrieval | 禁止所有 ISMN 数值进入 agent；标签仅供 evaluator |
| `HB_0003` | blocked gap-filling | 只允许 gap 开始前的 ISMN |

每个 tool step 都记录 `accessed_inputs` 与 `execution_scope`。Leakage evaluator 逐步检查 `allowed_inputs` / `forbidden_inputs`；`compute_metrics` 属于 evaluator scope，隐藏测试标签不会进入 agent trajectory。

## Baseline 规则

- Station-aware：rolling persistence、训练期 climatology、训练期线性回归、ERA5、水量平衡、Kalman。
- Satellite-only：persistence、站点 climatology 和站点监督回归被明确排除；不是把它们算完再隐藏。
- Gap-filling：gap 前最后观测 persistence、gap 前 climatology/线性回归、ERA5、水量平衡、Kalman。

报告按 RMSE 排名，并显示是否超过 persistence。Satellite-only 中 persistence 显示为不适用。

## 一条命令运行

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

每次运行写入 `outputs/runs/<run-id>/`：指标、逐日表、trajectory/leakage audit、config/task 快照、数据哈希、Git/GPU 环境、四张 SVG 和 HTML 报告。

## 多站与 split 支持

`station_catalog.csv` 现在包含每站真实 `ismn_path` 和 `era5_path`，runner 不再硬编码 ARM-1 文件。已实现：

- leave-year-out split；
- leave-station-out split 与重叠检查；
- blocked-gap evaluation；
- `scripts/generate_station_tasks.py` 的真实数据门槛检查。

运行：

```powershell
python scripts\generate_station_tasks.py --root . --minimum-stations 30
```

当前会退出失败并生成 `hydro_bench/readiness.json`：ARM-1 不足两年，满足投稿门槛的站点为 0/30。该失败是预期科研保护，不会复制单站或制造假任务。

## 数据与复现

- `data_manifest.json` 固定原始文件大小和 SHA-256；
- `configs/hydro_bench_v0.2.yaml` 固定 benchmark 门槛和设备请求；
- `environment.yml` / `requirements.txt` 固定环境；
- Git commit、GPU inventory 和 `CUDA_VISIBLE_DEVICES` 写入每个 run；
- runtime 仍是 Python 标量 CPU。RTX 6000 绑定会记录，但不会虚报 CUDA 加速。

## 未完成的投稿门槛

- ≥30 个真实表层 ISMN 站、≥2 年、≥4 气候区；
- 50–100 个基于真实站点的任务；
- SMAP L3、GLDAS/Noah、ERA5-Land；
- SMAP footprint / GLDAS grid matching；
- leave-station-out 的真实跨站训练；
- EnKF、多源观测算子和误差协方差。

这些属于 v0.3+ 数据与同化工作，当前报告会明确标记为 unavailable。
