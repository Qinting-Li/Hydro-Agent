"""Build a dependency-free HTML report; even the plot has an audit trail."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path


def polyline(values: list[float], width: int, height: int, low: float, high: float) -> str:
    span = max(high - low, 1e-9)
    points = []
    for index, value in enumerate(values):
        x = 45 + index * (width - 65) / max(len(values) - 1, 1)
        y = 15 + (high - value) * (height - 45) / span
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    metrics = json.loads((root / "outputs" / "metrics.json").read_text(encoding="utf-8"))
    with (root / "outputs" / "daily_estimates.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    sample = rows[::3]
    truth = [float(row["ismn_truth_m3m3"]) for row in sample]
    era5 = [float(row["era5_m3m3"]) for row in sample]
    analysis = [float(row["analysis_m3m3"]) for row in sample]
    low, high = 0.05, 0.50
    width, height = 920, 310
    lines = {
        "ISMN truth": ("#111827", polyline(truth, width, height, low, high)),
        "ERA5": ("#d97706", polyline(era5, width, height, low, high)),
        "Kalman analysis": ("#047857", polyline(analysis, width, height, low, high)),
    }
    metric_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{value['rmse']:.4f}</td>"
        f"<td>{value['bias']:.4f}</td><td>{value['correlation']:.3f}</td>"
        f"<td>{value['ubrmse']:.4f}</td></tr>"
        for name, value in metrics["metrics"].items()
    )
    polylines = "".join(
        f'<polyline fill="none" stroke="{color}" stroke-width="1.7" points="{points}"/>'
        for color, points in lines.values()
    )
    legend = "".join(
        f'<span style="color:{color}">●</span> {html.escape(name)} &nbsp;'
        for name, (color, _) in lines.items()
    )
    document = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>Hydrologic Earth-Agent · ARM-1</title>
<style>body{{font:15px/1.6 system-ui;max-width:980px;margin:36px auto;padding:0 18px;color:#1f2937}}
h1{{color:#064e3b}}table{{border-collapse:collapse;width:100%}}th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:right}}th:first-child,td:first-child{{text-align:left}}
.note{{background:#fffbeb;border-left:4px solid #d97706;padding:12px}}svg{{width:100%;background:#f8fafc;border:1px solid #e5e7eb}}</style>
<h1>Hydrologic Earth-Agent：ARM-1 验证报告</h1>
<p>任务：逐日表层土壤湿度估计、同化、不确定性与地面验证。测试期 {metrics['evaluation_period']['start']} 至 {metrics['evaluation_period']['end']}。</p>
<h2>测试集指标（m³/m³）</h2><table><tr><th>方法</th><th>RMSE</th><th>Bias</th><th>R</th><th>ubRMSE</th></tr>{metric_rows}</table>
<h2>时间序列（每三日抽样绘制）</h2><p>{legend}</p><svg viewBox="0 0 {width} {height}">{polylines}</svg>
<p>同化不确定性 95% 覆盖率：{metrics['metrics']['kalman_analysis']['coverage_95']:.2%}；校准误差：{metrics['metrics']['kalman_analysis']['calibration_error_95']:.2%}。</p>
<div class="note"><strong>结论边界：</strong>同化 RMSE 略优于两个基线，但单站点与尺度不匹配不支持区域泛化结论。高偏差仍需偏差订正、SMAP 真值检索和多站验证。</div>
</html>"""
    target = root / "outputs" / "report.html"
    target.write_text(document, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
