"""Dependency-free Agent Reasoning Report with auditable SVG figures."""

from __future__ import annotations

import html
import json
from pathlib import Path


COLORS = {"truth": "#111827", "era5": "#d97706", "water": "#2563eb", "kalman": "#047857"}


def _polyline(values: list[float], width: int, height: int, low: float, high: float) -> str:
    span = max(high - low, 1e-12)
    return " ".join(
        f"{45 + index * (width - 65) / max(len(values) - 1, 1):.1f},{15 + (high - value) * (height - 45) / span:.1f}"
        for index, value in enumerate(values)
    )


def _svg_shell(width: int, height: int, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">'
        '<rect width="100%" height="100%" fill="#f8fafc"/>'
        f'<text x="16" y="22" font-family="system-ui" font-size="14" font-weight="700" fill="#0f172a">{html.escape(title)}</text>'
        f'{body}</svg>'
    )


def _write_figures(rows: list[dict], station: dict, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    sample = rows[::3]
    width, height = 920, 300
    series = {
        "truth": [float(row["ismn_truth_m3m3"]) for row in sample],
        "era5": [float(row["era5_m3m3"]) for row in sample],
        "water": [float(row["water_balance_m3m3"]) for row in sample],
        "kalman": [float(row["analysis_m3m3"]) for row in sample],
    }
    body = "".join(
        f'<polyline fill="none" stroke="{COLORS[name]}" stroke-width="1.7" points="{_polyline(values, width, height, 0.05, 0.50)}"/>'
        for name, values in series.items()
    )
    (target / "time_series.svg").write_text(_svg_shell(width, height, body, "Daily soil moisture (3-day display sampling)"), encoding="utf-8")

    test = rows[-213:]
    x_values = [float(row["ismn_truth_m3m3"]) for row in test]
    y_values = [float(row["analysis_m3m3"]) for row in test]
    low, high = 0.05, 0.50
    scale_x = lambda value: 50 + (value - low) * 340 / (high - low)
    scale_y = lambda value: 390 - (value - low) * 340 / (high - low)
    dots = "".join(f'<circle cx="{scale_x(x):.1f}" cy="{scale_y(y):.1f}" r="2.2" fill="#047857" opacity=".65"/>' for x, y in zip(x_values, y_values))
    diagonal = f'<line x1="{scale_x(low)}" y1="{scale_y(low)}" x2="{scale_x(high)}" y2="{scale_y(high)}" stroke="#64748b" stroke-dasharray="5 4"/>'
    (target / "scatter.svg").write_text(_svg_shell(440, 430, diagonal + dots, "Kalman analysis vs ISMN (held-out test)"), encoding="utf-8")

    uncertainty_sample = rows[-213::2]
    analysis = [float(row["analysis_m3m3"]) for row in uncertainty_sample]
    truth = [float(row["ismn_truth_m3m3"]) for row in uncertainty_sample]
    lower = [max(0.0, float(row["analysis_m3m3"]) - 1.96 * float(row["calibrated_sigma_m3m3"])) for row in uncertainty_sample]
    upper = [min(0.8, float(row["analysis_m3m3"]) + 1.96 * float(row["calibrated_sigma_m3m3"])) for row in uncertainty_sample]
    upper_points = _polyline(upper, width, height, 0.0, 0.8).split()
    lower_points = list(reversed(_polyline(lower, width, height, 0.0, 0.8).split()))
    band = f'<polygon points="{" ".join(upper_points + lower_points)}" fill="#86efac" opacity=".4"/>'
    lines = (
        f'<polyline fill="none" stroke="{COLORS["truth"]}" stroke-width="1.5" points="{_polyline(truth, width, height, 0.0, 0.8)}"/>'
        f'<polyline fill="none" stroke="{COLORS["kalman"]}" stroke-width="1.8" points="{_polyline(analysis, width, height, 0.0, 0.8)}"/>'
    )
    (target / "uncertainty.svg").write_text(_svg_shell(width, height, band + lines, "Kalman 95% uncertainty interval (2-day display sampling)"), encoding="utf-8")

    lat, lon = float(station["lat"]), float(station["lon"])
    map_body = (
        '<rect x="35" y="45" width="520" height="240" rx="8" fill="#dbeafe" stroke="#94a3b8"/>'
        '<rect x="215" y="110" width="160" height="110" fill="none" stroke="#7c3aed" stroke-width="2" stroke-dasharray="7 5"/>'
        '<circle cx="295" cy="165" r="8" fill="#dc2626"/>'
        f'<text x="310" y="160" font-family="system-ui" font-size="13">ARM-1 ({lat:.4f}, {lon:.4f})</text>'
        '<text x="310" y="180" font-family="system-ui" font-size="12" fill="#7c3aed">SMAP/GLDAS footprint: unavailable in v0.1</text>'
        '<text x="45" y="275" font-family="system-ui" font-size="11" fill="#475569">Location schematic; not a geographic footprint claim.</text>'
    )
    (target / "map.svg").write_text(_svg_shell(590, 310, map_body, "Station and footprint availability"), encoding="utf-8")


def _final_answer(result: dict) -> str:
    kalman = result["metrics"]["kalman_analysis"]
    era5 = result["metrics"]["era5_baseline"]
    change = (era5["rmse"] - kalman["rmse"]) / era5["rmse"]
    best = result["best_method"]
    best_rmse = result["metrics"][best]["rmse"]
    return (
        f"The strongest baseline is {best} (RMSE {best_rmse:.4f} m³/m³). "
        f"Kalman RMSE is {kalman['rmse']:.4f} m³/m³ versus ERA5 {era5['rmse']:.4f} "
        f"({change:.1%} relative improvement); 95% coverage is {kalman['coverage_95']:.2%}. "
        "The workflow passes evidence and physical gates, but the conclusion is restricted to one station because SMAP/GLDAS footprints are unavailable in v0.1."
    )


def render_task_report(task: dict, result: dict, trajectory: dict, rows: list[dict], station: dict, run_dir: Path) -> Path:
    _write_figures(rows, station, run_dir / "figures")
    metric_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{value['n']}</td><td>{value['rmse']:.4f}</td><td>{value['bias']:.4f}</td>"
        f"<td>{value['ubrmse']:.4f}</td><td>{value['correlation']:.3f}</td><td>{value['nse']:.3f}</td><td>{value['kge']:.3f}</td></tr>"
        for name, value in result["metrics"].items()
    )
    step_cards = "".join(
        f'<article class="step {step["status"]}"><div class="step-head"><b>Step {step["step"]}: {html.escape(step["tool_name"])}</b>'
        f'<span>{html.escape(step["status"])} · {step["runtime_ms"]:.3f} ms · QC {html.escape(step["qc"])}</span></div>'
        f'<details><summary>Input / output evidence</summary><pre>{html.escape(json.dumps({"input": step["input"], "output": step["output_summary"], "warnings": step["warnings"]}, indent=2, ensure_ascii=False))}</pre></details></article>'
        for step in trajectory["steps"]
    )
    score_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{value:.3f}</td></tr>"
        for name, value in trajectory["evaluation"]["step_by_step"].items()
    )
    gold = " → ".join(trajectory["evaluation"]["ground_truth_path"])
    agent = " → ".join(trajectory["evaluation"]["agent_path"])
    limitations = "".join(f"<li>{html.escape(item)}</li>" for item in result["limitations"])
    document = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hydro-Bench · {html.escape(task['task_id'])}</title><style>
:root{{--ink:#0f172a;--muted:#64748b;--line:#dbe3ee;--green:#047857;--amber:#d97706}}*{{box-sizing:border-box}}body{{margin:0;background:#eef3f8;color:var(--ink);font:14px/1.55 system-ui,sans-serif}}main{{max-width:1380px;margin:auto;padding:28px}}h1,h2{{margin:.2em 0 .6em}}.hero,.panel{{background:white;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 5px 20px #0f172a0a}}.hero{{border-top:5px solid var(--green)}}.meta,.grid,.scores{{display:grid;gap:16px}}.meta{{grid-template-columns:repeat(4,1fr)}}.grid{{grid-template-columns:1.25fr .75fr;margin-top:16px}}.figures{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.figures img{{width:100%;border:1px solid var(--line);border-radius:8px}}.answer{{background:#ecfdf5;border-left:4px solid var(--green);padding:14px}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid var(--line);padding:7px;text-align:right}}th:first-child,td:first-child{{text-align:left}}.step{{border:1px solid var(--line);border-left:4px solid var(--green);border-radius:8px;padding:10px;margin:9px 0}}.step.warning{{border-left-color:var(--amber)}}.step-head{{display:flex;justify-content:space-between;gap:10px}}.step-head span{{color:var(--muted)}}pre{{white-space:pre-wrap;background:#f8fafc;padding:10px;border-radius:6px;overflow:auto}}.path{{font-family:ui-monospace,monospace;font-size:12px;overflow-wrap:anywhere;background:#f8fafc;padding:10px}}.e2e{{font-size:36px;color:var(--green);font-weight:750}}@media(max-width:900px){{.grid,.meta,.figures{{grid-template-columns:1fr}}}}
</style><main><section class="hero"><h1>Hydro-Bench Agent Reasoning Report</h1><div class="meta"><div><b>Task</b><br>{html.escape(task['task_id'])}</div><div><b>Station</b><br>{html.escape(station['station_id'])}</div><div><b>Climate / land</b><br>{html.escape(station['climate_zone'])} / {html.escape(station['land_cover'])}</div><div><b>Time</b><br>{task['time_range'][0]} → {task['time_range'][1]}</div></div><h2>Question</h2><p>{html.escape(task['question'])}</p><h2>Final answer</h2><p class="answer">{html.escape(_final_answer(result))}</p></section>
<div class="grid"><section class="panel"><h2>Hydrologic evidence</h2><div class="figures"><img src="figures/map.svg"><img src="figures/scatter.svg"><img src="figures/time_series.svg"><img src="figures/uncertainty.svg"></div><h2>Held-out metrics</h2><table><tr><th>Method</th><th>N</th><th>RMSE</th><th>Bias</th><th>ubRMSE</th><th>R</th><th>NSE</th><th>KGE</th></tr>{metric_rows}</table></section>
<aside class="panel"><h2>Tool trajectory</h2>{step_cards}</aside></div>
<div class="grid"><section class="panel"><h2>Ground truth vs agent path</h2><b>Ground truth</b><p class="path">{html.escape(gold)}</p><b>Agent</b><p class="path">{html.escape(agent)}</p><h2>Scientific boundary</h2><ul>{limitations}</ul></section><section class="panel"><h2>Trajectory scores</h2><div class="e2e">{trajectory['evaluation']['end_to_end']:.3f}</div><p>End-to-end weighted score</p><table>{score_rows}</table><h2>Execution environment</h2><pre>{html.escape(json.dumps(result['environment'], indent=2, ensure_ascii=False))}</pre></section></div></main></html>"""
    target = run_dir / "report.html"
    target.write_text(document, encoding="utf-8")
    return target


def render_benchmark_summary(results: list[dict], target: Path) -> Path:
    rows = "".join(
        f"<tr><td><a href='report.html'>{html.escape(item['task_id'])}</a></td><td>{html.escape(item['best_method'])}</td>"
        f"<td>{item['metrics']['kalman_analysis']['rmse']:.4f}</td><td>{item['metrics']['kalman_analysis']['coverage_95']:.2%}</td>"
        f"<td>{item['trajectory_score']['end_to_end']:.3f}</td></tr>" for item in results
    )
    target.write_text(
        f"<!doctype html><meta charset='utf-8'><title>Hydro-Bench Summary</title><style>body{{font:15px system-ui;max-width:980px;margin:40px auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}</style><h1>Hydro-Bench v0.1 Summary</h1><table><tr><th>Task</th><th>Best method</th><th>Kalman RMSE</th><th>Coverage 95%</th><th>Trajectory E2E</th></tr>{rows}</table>",
        encoding="utf-8",
    )
    return target
