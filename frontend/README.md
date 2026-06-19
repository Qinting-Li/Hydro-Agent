# Hydro-Agent Frontend

参考 Earth-Agent「多 LLM Backbone 对比」布局的交互式前端，展示 Hydro-Bench 任务、工具轨迹、水文图表、泄漏审计与 Ground Truth 对比。

## 快速启动

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173

## 页面功能

| Tab | 内容 |
|-----|------|
| **Overview** | 任务问题、baseline 选择题、指标条、LLM backbone 对比表 |
| **Trajectory** | 选中 backbone 的执行 trace + 完整 10 步工具时间线 |
| **Science** | 土壤湿度时间序列 / 散点图、held-out 方法排名表 |
| **Leakage Audit** | allowed/forbidden inputs、逐步访问审计 |

顶部 **HB_0001 / HB_0002 / HB_0003** 按钮可切换三种任务模式（自动加载 `public/bundles/` 下的真实 benchmark 数据）。

## 更新 benchmark 数据

```powershell
# 1. 跑 benchmark（项目根目录）
$env:PYTHONPATH = "$PWD\src"
python -m hydro_agent.benchmark.runner --root . --task hydro_bench\tasks\HB_0001.json --run-id demo_ui
python -m hydro_agent.benchmark.runner --root . --task hydro_bench\tasks\HB_0002.json --run-id demo_ui_2
python -m hydro_agent.benchmark.runner --root . --task hydro_bench\tasks\HB_0003.json --run-id demo_ui_3

# 2. 导出三个 bundle（含 daily_rows 采样）
python scripts\export_all_bundles.py --root .
```

也可点击 **Import JSON** 加载单个 `export_run_bundle.py` 导出的文件。

## 构建静态站点

```powershell
cd frontend
npm run build
npm run preview
```

产物在 `frontend/dist/`。

## 技术栈

- React 19 + TypeScript
- Vite 6
- Tailwind CSS 4
- 无外部图表库（内联 SVG）
