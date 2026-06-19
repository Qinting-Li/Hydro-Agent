"""Self-contained Hydro-Bench HTML and SVG reporting."""

from .render_html import render_benchmark_summary, render_task_report

__all__ = ["render_task_report", "render_benchmark_summary"]
