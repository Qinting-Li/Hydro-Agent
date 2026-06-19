import type { AgentBackbone } from "../types";

type Props = {
  backbone: AgentBackbone;
};

function JsonBlock({ data }: { data: Record<string, unknown> }) {
  return (
    <pre className="mono overflow-x-auto rounded-lg bg-gray-50 p-3 text-[11px] leading-relaxed text-gray-800">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export function AgentTrace({ backbone }: Props) {
  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-3">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-lg text-xs font-bold text-white"
          style={{ backgroundColor: backbone.color }}
        >
          {backbone.logo}
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">{backbone.name}</h2>
          <p className="text-xs text-gray-500">Agent execution trace</p>
        </div>
        <span
          className={`ml-auto rounded-full px-3 py-1 text-xs font-bold ${
            backbone.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"
          }`}
        >
          {backbone.passed ? "PASS" : "FAIL"}
        </span>
      </div>

      <div className="space-y-3">
        {backbone.traceSteps.map((step, index) => (
          <div key={`${step.label}-${index}`} className="grid gap-2 md:grid-cols-[88px_1fr]">
            <div className="flex items-start justify-center pt-2">
              <span className="rounded-md bg-orange-100 px-2 py-1 text-[11px] font-bold text-orange-800">
                {step.label}
              </span>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="rounded-xl border border-gray-200 bg-white p-3">
                <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase text-gray-500">
                  <span className="text-base">🤖</span> Input / tool call
                </div>
                <JsonBlock data={step.input} />
              </div>
              <div className="rounded-xl border border-gray-200 bg-white p-3">
                <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase text-gray-500">
                  <span className="text-base">📤</span> Output / result
                </div>
                <JsonBlock data={step.output} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
