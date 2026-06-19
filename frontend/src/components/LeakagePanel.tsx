import type { RunBundle } from "../types";

type Props = { bundle: RunBundle | null };

export function LeakagePanel({ bundle }: Props) {
  const audit = bundle?.trajectory.evaluation.leakage_audit;
  const task = bundle?.task;

  if (!audit || !task) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-5 text-sm text-gray-500">
        Leakage audit data not available in this bundle.
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-gray-900">Leakage / allowed-input audit</h2>
          <span
            className={`rounded-full px-4 py-1.5 text-sm font-bold ${
              audit.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"
            }`}
          >
            {audit.passed ? "PASS" : "FAIL"} · violations={audit.violations}
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <h3 className="mb-2 text-xs font-bold uppercase text-emerald-800">Allowed inputs</h3>
            <div className="flex flex-wrap gap-1.5">
              {(task.allowed_inputs ?? []).map((item) => (
                <span key={item} className="rounded-md bg-white px-2 py-1 text-xs font-medium text-emerald-900">
                  {item}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4">
            <h3 className="mb-2 text-xs font-bold uppercase text-red-800">Forbidden inputs</h3>
            <div className="flex flex-wrap gap-1.5">
              {(task.forbidden_inputs ?? []).map((item) => (
                <span key={item} className="rounded-md bg-white px-2 py-1 text-xs font-medium text-red-900">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="mb-3 text-base font-bold text-gray-900">Step-by-step access audit</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="py-2">Step</th>
                <th className="py-2">Tool</th>
                <th className="py-2">Scope</th>
                <th className="py-2">Accessed</th>
                <th className="py-2">Forbidden hits</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {audit.step_audits.map((row) => (
                <tr key={row.step} className={`border-b border-gray-100 ${!row.passed ? "bg-red-50" : ""}`}>
                  <td className="py-2 font-mono">{row.step}</td>
                  <td className="py-2 font-mono text-xs">{row.tool_name}</td>
                  <td className="py-2 text-xs">{row.execution_scope}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {row.accessed_inputs.map((a) => (
                        <span key={a} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px]">
                          {a}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2 text-red-700">
                    {row.forbidden_hits.length ? row.forbidden_hits.join(", ") : "—"}
                  </td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                        row.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {row.passed ? "OK" : "VIOLATION"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          Leakage-Safety score: <strong>{audit.score.toFixed(4)}</strong>. Evaluator-scope{" "}
          <code className="rounded bg-gray-100 px-1">compute_metrics</code> may access hidden test labels; agent-scope
          tools may not.
        </p>
      </div>
    </section>
  );
}
