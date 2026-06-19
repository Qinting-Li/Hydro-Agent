import type { AgentBackbone } from "../types";

type Props = {
  backbone: AgentBackbone;
  endToEnd?: number;
  stepByStep?: Record<string, number>;
};

const PRIMARY = ["TAO", "TIO", "TEM", "Param"] as const;
const HYDRO = ["Hydro-QC", "Phys-Consistency", "Leakage-Safety"] as const;

export function MetricsBar({ backbone, endToEnd, stepByStep }: Props) {
  const accuracyPct = Math.round(backbone.metrics.Accuracy * 100);

  return (
    <section className="rounded-2xl bg-orange-500 px-5 py-4 text-white shadow-md">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-bold uppercase tracking-widest text-orange-100">Trajectory scores</div>
        {endToEnd !== undefined && (
          <div className="rounded-lg bg-white/15 px-3 py-1 text-sm font-bold">E2E {endToEnd.toFixed(4)}</div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase text-orange-100">Step-by-step</div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {PRIMARY.map((name) => (
              <div key={name} className="rounded-lg bg-orange-600/50 px-3 py-2 text-center">
                <div className="text-[10px] font-semibold uppercase text-orange-100">{name}</div>
                <div className="text-lg font-bold">{(backbone.metrics[name] ?? stepByStep?.[name] ?? 0).toFixed(4)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="hidden h-16 w-px bg-orange-300 lg:block" />

        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase text-orange-100">End-to-end</div>
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-orange-600/50 px-4 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase text-orange-100">Efficiency</div>
              <div className="text-2xl font-bold">{backbone.metrics.Efficiency.toFixed(4)}</div>
            </div>
            <div className="rounded-lg bg-orange-600/50 px-4 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase text-orange-100">Accuracy</div>
              <div className="text-2xl font-bold">{accuracyPct}%</div>
            </div>
          </div>
        </div>
      </div>

      {HYDRO.some((k) => backbone.metrics[k] !== undefined || stepByStep?.[k] !== undefined) && (
        <div className="mt-4 border-t border-orange-400/50 pt-4">
          <div className="mb-2 text-[10px] font-semibold uppercase text-orange-100">Hydro-Bench gates</div>
          <div className="grid grid-cols-3 gap-2">
            {HYDRO.map((name) => (
              <div key={name} className="rounded-lg bg-orange-600/40 px-3 py-2 text-center">
                <div className="text-[10px] font-semibold text-orange-100">{name}</div>
                <div className="text-base font-bold">
                  {(backbone.metrics[name] ?? stepByStep?.[name] ?? 0).toFixed(4)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
