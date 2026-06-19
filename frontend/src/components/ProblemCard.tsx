import type { DemoPayload } from "../types";

type Props = { payload: DemoPayload };

function MiniChart({ color, label }: { color: string; label: string }) {
  const bars = Array.from({ length: 12 }, (_, i) => 30 + ((i * 17) % 55));
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex h-14 w-20 items-end justify-center gap-0.5 rounded-md border border-gray-200 bg-white p-1">
        {bars.map((h, i) => (
          <div key={i} style={{ height: `${h}%`, backgroundColor: color }} className="w-1 rounded-sm opacity-80" />
        ))}
      </div>
      <span className="text-[10px] font-medium text-gray-500">{label}</span>
    </div>
  );
}

export function ProblemCard({ payload }: Props) {
  return (
    <section className="rounded-2xl border border-blue-200 bg-[var(--blue-soft)] p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-800">
        <span className="rounded bg-blue-100 px-2 py-0.5">{payload.taskId}</span>
        <span className="rounded bg-white px-2 py-0.5 text-gray-600">{payload.mode.replaceAll("_", " ")}</span>
        <span className="rounded bg-white px-2 py-0.5 text-gray-600">{payload.stationId}</span>
      </div>

      <p className="text-sm leading-relaxed text-gray-800 md:text-[15px]">{payload.question}</p>

      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {payload.choices.map((choice) => (
          <div
            key={choice.key}
            className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm ${
              choice.correct
                ? "border-red-300 bg-red-50 font-semibold text-red-800"
                : "border-gray-200 bg-white text-gray-700"
            }`}
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-current text-xs font-bold">
              {choice.key}
            </span>
            <span>{choice.label}</span>
            {choice.correct && <span className="ml-auto text-red-600">✓</span>}
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-4 border-t border-blue-200 pt-4">
        <span className="text-xs font-semibold uppercase text-gray-500">Data preview</span>
        {payload.dataPreview.map((item) => (
          <MiniChart key={item.label} color={item.color} label={`${item.label} · ${item.count}`} />
        ))}
      </div>
    </section>
  );
}
