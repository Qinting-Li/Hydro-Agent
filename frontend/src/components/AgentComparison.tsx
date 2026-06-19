import type { AgentBackbone, DemoPayload } from "../types";
import { toolLabel } from "../data/demo";

type Props = {
  payload: DemoPayload;
  selectedId: string;
  onSelect: (id: string) => void;
};

function FlowNode({ label, tone }: { label: string; tone: "gt" | "agent" | "fail" }) {
  const styles = {
    gt: "bg-gray-800 text-white",
    agent: "bg-emerald-600 text-white",
    fail: "bg-red-500 text-white",
  };
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-1 text-[11px] font-semibold ${styles[tone]}`}>
      {label}
    </span>
  );
}

function ToolFlow({ path, passed }: { path: string[]; passed: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {path.map((tool, index) => (
        <span key={`${tool}-${index}`} className="flex items-center gap-1.5">
          <FlowNode label={tool} tone={passed ? "agent" : index === path.length - 1 && !passed ? "fail" : "gt"} />
          {index < path.length - 1 && <span className="text-gray-400">→</span>}
        </span>
      ))}
      <span className="ml-1 text-gray-400">→</span>
      <FlowNode label={passed ? "✓" : "✗"} tone={passed ? "agent" : "fail"} />
    </div>
  );
}

export function AgentComparison({ payload, selectedId, onSelect }: Props) {
  const selected = payload.backbones.find((b) => b.id === selectedId) ?? payload.backbones[0];

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-bold text-gray-900">Ground truth vs agent tool flow</h2>

      <div className="mb-4 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4">
        <div className="mb-2 text-xs font-bold uppercase text-gray-500">Ground truth (GT)</div>
        <ToolFlow path={payload.groundTruthPath} passed />
      </div>

      <div className="mb-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        {Object.entries(payload.toolLegend).map(([short, full]) => (
          <div key={short} className="rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-[11px]">
            <span className="font-bold text-orange-700">{short}</span>
            <span className="text-gray-500">: {full}</span>
          </div>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="py-2 pr-4">Agent</th>
              <th className="py-2 pr-4">Tool sequence</th>
              <th className="py-2 pr-4">Answer</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {payload.backbones.map((backbone: AgentBackbone) => (
              <tr
                key={backbone.id}
                onClick={() => onSelect(backbone.id)}
                className={`cursor-pointer border-b border-gray-100 transition-colors ${
                  selected.id === backbone.id ? "bg-orange-50" : "hover:bg-gray-50"
                }`}
              >
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2 font-semibold">
                    <span
                      className="flex h-7 w-7 items-center justify-center rounded-md text-[10px] font-bold text-white"
                      style={{ backgroundColor: backbone.color }}
                    >
                      {backbone.logo}
                    </span>
                    {backbone.name}
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <ToolFlow path={backbone.toolPath} passed={backbone.passed} />
                </td>
                <td className="py-3 pr-4 font-mono font-bold">{backbone.finalAnswer}</td>
                <td className="py-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-bold ${
                      backbone.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"
                    }`}
                  >
                    {backbone.passed ? "PASS" : "FAIL"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Selected: <strong>{selected.name}</strong> · final tool{" "}
        <code className="rounded bg-gray-100 px-1">{toolLabel(selected.toolPath.at(-1) ?? "")}</code>
      </p>
    </section>
  );
}
