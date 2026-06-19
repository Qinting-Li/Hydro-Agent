import { polyline, seriesRange } from "../lib/charts";
import type { DailyRow, RunBundle } from "../types";
import { METHOD_LABELS } from "../data/tasks";

type Props = { bundle: RunBundle | null };

const SERIES = [
  { key: "ismn_truth_m3m3", label: "ISMN truth", color: "#111827" },
  { key: "era5_m3m3", label: "ERA5", color: "#d97706" },
  { key: "water_balance_m3m3", label: "Water balance", color: "#2563eb" },
  { key: "analysis_m3m3", label: "Kalman", color: "#047857" },
  { key: "persistence_m3m3", label: "Persistence", color: "#7c3aed" },
] as const;

function TimeSeriesChart({ rows }: { rows: DailyRow[] }) {
  const width = 900;
  const height = 260;
  const seriesData = SERIES.map((s) => ({
    ...s,
    values: rows.map((r) => r[s.key as keyof DailyRow] as number | undefined).filter((v): v is number => v !== undefined),
  })).filter((s) => s.values.length === rows.length && s.values.length > 0);

  const [low, high] = seriesRange(seriesData.map((s) => s.values));

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[600px]" role="img" aria-label="Soil moisture time series">
        <rect width={width} height={height} fill="#f8fafc" rx="8" />
        <text x="16" y="22" className="fill-gray-900 text-[13px] font-bold">
          Daily soil moisture (m³/m³) · sampled display
        </text>
        {[0.1, 0.2, 0.3, 0.4].map((v) => {
          const y = 15 + ((high - v) * (height - 40)) / Math.max(high - low, 1e-12);
          return (
            <g key={v}>
              <line x1="40" y1={y} x2={width - 10} y2={y} stroke="#e2e8f0" strokeDasharray="4 4" />
              <text x="8" y={y + 4} className="fill-gray-400 text-[9px]">
                {v.toFixed(1)}
              </text>
            </g>
          );
        })}
        {seriesData.map((s) => (
          <polyline
            key={s.key}
            fill="none"
            stroke={s.color}
            strokeWidth="1.8"
            points={polyline(s.values, width, height, low, high)}
          />
        ))}
        <g transform={`translate(16, ${height - 12})`}>
          {seriesData.map((s, i) => (
            <g key={s.key} transform={`translate(${i * 130}, 0)`}>
              <rect width="10" height="3" fill={s.color} y="-2" />
              <text x="14" y="0" className="fill-gray-600 text-[10px]">
                {s.label}
              </text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}

function ScatterChart({ rows }: { rows: DailyRow[] }) {
  const pairs = rows.filter((r) => r.ismn_truth_m3m3 !== undefined && r.analysis_m3m3 !== undefined);
  const width = 360;
  const height = 340;
  const low = 0.05;
  const high = 0.5;
  const sx = (v: number) => 50 + ((v - low) * 280) / (high - low);
  const sy = (v: number) => 300 - ((v - low) * 250) / (high - low);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Kalman vs ISMN scatter">
      <rect width={width} height={height} fill="#f8fafc" rx="8" />
      <text x="16" y="22" className="fill-gray-900 text-[13px] font-bold">
        Kalman vs ISMN
      </text>
      <line x1={sx(low)} y1={sy(low)} x2={sx(high)} y2={sy(high)} stroke="#94a3b8" strokeDasharray="5 4" />
      {pairs.map((r) => (
        <circle
          key={r.date}
          cx={sx(r.ismn_truth_m3m3!)}
          cy={sy(r.analysis_m3m3!)}
          r="3"
          fill="#047857"
          opacity="0.65"
        />
      ))}
    </svg>
  );
}

export function HydrologicPanel({ bundle }: Props) {
  if (!bundle?.daily_rows?.length) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-5 text-sm text-gray-500">
        No daily estimate rows in bundle. Re-export with <code className="rounded bg-gray-100 px-1">export_run_bundle.py</code>.
      </section>
    );
  }

  const ranked = Object.entries(bundle.metrics.metrics).sort((a, b) => a[1].rmse - b[1].rmse);

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-4 text-lg font-bold text-gray-900">Hydrologic evidence</h2>
        <div className="grid gap-4 xl:grid-cols-[1.4fr_0.6fr]">
          <TimeSeriesChart rows={bundle.daily_rows} />
          <ScatterChart rows={bundle.daily_rows} />
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="mb-3 text-base font-bold text-gray-900">Held-out method ranking</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="py-2">Rank</th>
                <th className="py-2">Method</th>
                <th className="py-2 text-right">RMSE</th>
                <th className="py-2 text-right">Bias</th>
                <th className="py-2 text-right">R</th>
                <th className="py-2 text-right">NSE</th>
                <th className="py-2 text-right">KGE</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map(([name, m], index) => (
                <tr
                  key={name}
                  className={`border-b border-gray-100 ${name === bundle.metrics.best_method ? "bg-emerald-50 font-semibold" : ""}`}
                >
                  <td className="py-2">{index + 1}</td>
                  <td className="py-2">{METHOD_LABELS[name] ?? name}</td>
                  <td className="py-2 text-right font-mono">{m.rmse.toFixed(4)}</td>
                  <td className="py-2 text-right font-mono">{m.bias.toFixed(4)}</td>
                  <td className="py-2 text-right font-mono">{m.correlation.toFixed(3)}</td>
                  <td className="py-2 text-right font-mono">{m.nse.toFixed(3)}</td>
                  <td className="py-2 text-right font-mono">{m.kge.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {bundle.metrics.evaluation_period && (
          <p className="mt-3 text-xs text-gray-500">
            Evaluation: {bundle.metrics.evaluation_period.start} → {bundle.metrics.evaluation_period.end}
          </p>
        )}
      </div>
    </section>
  );
}
