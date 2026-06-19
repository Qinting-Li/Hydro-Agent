import type { RunBundle, ToolStep } from "../types";

type Props = {
  steps: ToolStep[];
  bundle: RunBundle | null;
};

const STATUS_STYLES: Record<string, string> = {
  success: "border-emerald-400 bg-emerald-50 text-emerald-800",
  warning: "border-amber-400 bg-amber-50 text-amber-800",
  failed: "border-red-400 bg-red-50 text-red-700",
};

export function StepTimeline({ steps, bundle }: Props) {
  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-bold text-gray-900">Full tool timeline</h2>
      <div className="relative space-y-0">
        {steps.map((step, index) => (
          <div key={step.step} className="grid gap-3 md:grid-cols-[72px_1fr]">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-xs font-bold ${
                  STATUS_STYLES[step.status] ?? "border-gray-300 bg-gray-50"
                }`}
              >
                {step.step}
              </div>
              {index < steps.length - 1 && <div className="my-1 w-0.5 flex-1 bg-gray-200" />}
            </div>
            <article className={`mb-4 rounded-xl border p-4 ${STATUS_STYLES[step.status] ?? "border-gray-200"}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-mono text-sm font-bold">{step.tool_name}</h3>
                <div className="flex gap-2 text-[11px] font-semibold uppercase">
                  <span>{step.status}</span>
                  <span>·</span>
                  <span>QC {step.qc}</span>
                  <span>·</span>
                  <span>{step.runtime_ms.toFixed(2)} ms</span>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {step.accessed_inputs.map((input) => (
                  <span key={input} className="rounded bg-white/70 px-2 py-0.5 text-[10px] font-medium text-gray-700">
                    {input}
                  </span>
                ))}
                <span className="rounded bg-gray-900/10 px-2 py-0.5 text-[10px] font-medium">{step.execution_scope}</span>
              </div>
              {step.warnings && step.warnings.length > 0 && (
                <ul className="mt-2 list-disc pl-4 text-xs text-amber-900">
                  {step.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
              <details className="mt-3">
                <summary className="cursor-pointer text-xs font-semibold text-gray-600">Input / output JSON</summary>
                <pre className="mono mt-2 overflow-x-auto rounded-lg bg-white/80 p-3 text-[10px]">
                  {JSON.stringify({ input: step.input, output: step.output_summary }, null, 2)}
                </pre>
              </details>
            </article>
          </div>
        ))}
      </div>

      {bundle?.metrics.physical_checks && (
        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <h3 className="mb-2 text-sm font-bold text-gray-800">Physical consistency checks</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(bundle.metrics.physical_checks).map(([key, ok]) => (
              <span
                key={key}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${ok ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"}`}
              >
                {key}: {ok ? "PASS" : "FAIL"}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
