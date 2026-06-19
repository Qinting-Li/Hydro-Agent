import { demoPayload, buildBackboneFromRun } from "../data/demo";
import { METHOD_LABELS, SPECTRUM_BY_MODE } from "../data/tasks";
import type { DemoPayload, RunBundle, ToolStep } from "../types";

const TOOL_SHORT: Record<string, string> = {
  get_station_metadata: "T1",
  load_station_history: "T2",
  load_era5_forcing: "T3",
  match_footprint: "T4",
  reject_if_unreliable: "T5",
  compute_water_balance: "T6",
  run_kalman_assimilation: "T7",
  compute_baselines: "T8",
  compute_uncertainty: "T9",
  compute_metrics: "T10",
};

const TOOL_FULL: Record<string, string> = Object.fromEntries(
  Object.entries(TOOL_SHORT).map(([full, short]) => [short, full]),
);

export function toolPathToShort(toolNames: string[]): string[] {
  return toolNames.map((name) => TOOL_SHORT[name] ?? name);
}

export function buildToolLegend(path: string[]): Record<string, string> {
  const legend: Record<string, string> = {};
  for (const short of path) {
    if (TOOL_FULL[short]) legend[short] = TOOL_FULL[short];
  }
  return legend;
}

export function traceFromRun(steps: ToolStep[]) {
  const groups: Array<{ label: string; input: Record<string, unknown>; output: Record<string, unknown> }> = [];
  const pick = (index: number) => steps[index];

  for (const step of steps) {
    groups.push({
      label: `Step ${step.step}`,
      input: { name: step.tool_name, ...step.input },
      output: {
        ...step.output_summary,
        status: step.status,
        qc: step.qc,
        runtime_ms: step.runtime_ms,
        accessed_inputs: step.accessed_inputs,
      },
    });
  }

  const last = pick(steps.length - 1);
  if (last) {
    groups.push({
      label: "Final",
      input: { scope: last.execution_scope, tool: last.tool_name },
      output: last.output_summary,
    });
  }
  return groups;
}

function answerKeyFromMethod(method: string): string {
  const order = ["era5_baseline", "water_balance", "persistence", "climatology", "linear_regression", "kalman_analysis"];
  const index = order.indexOf(method);
  const keys = ["A", "B", "C", "D", "E", "F"];
  return index >= 0 ? keys[index] : "?";
}

function buildChoices(bundle: RunBundle): DemoPayload["choices"] {
  const ranked = Object.entries(bundle.metrics.metrics)
    .sort((a, b) => a[1].rmse - b[1].rmse)
    .slice(0, 4);
  const keys = ["A", "B", "C", "D"];
  return ranked.map(([name, value], index) => ({
    key: keys[index],
    label: `${METHOD_LABELS[name] ?? name.replaceAll("_", " ")} (RMSE ${value.rmse.toFixed(3)})`,
    correct: name === bundle.metrics.best_method,
  }));
}

function buildDataPreview(bundle: RunBundle): DemoPayload["dataPreview"] {
  const historyStep = bundle.trajectory.steps.find((s) => s.tool_name === "load_station_history");
  const era5Step = bundle.trajectory.steps.find((s) => s.tool_name === "load_era5_forcing");
  const preview: DemoPayload["dataPreview"] = [
    {
      label: "ERA5 forcing",
      count: `${era5Step?.output_summary.valid_daily_observations ?? "—"} d`,
      color: "#d97706",
    },
    {
      label: "Test window",
      count: `${bundle.metrics.matched_days_test ?? "—"} d`,
      color: "#047857",
    },
  ];
  if (historyStep) {
    preview.unshift({
      label: "ISMN history",
      count: `${historyStep.output_summary.history_days} d`,
      color: "#111827",
    });
  } else {
    preview.unshift({
      label: "ISMN to agent",
      count: "hidden",
      color: "#6b7280",
    });
  }
  return preview;
}

export function payloadFromRun(bundle: RunBundle): DemoPayload {
  const eval_ = bundle.trajectory.evaluation;
  const metrics = bundle.metrics;
  const best = metrics.best_method;
  const answerKey = answerKeyFromMethod(best);
  const stepMetrics = eval_.step_by_step;
  const gtPath = toolPathToShort(eval_.ground_truth_path);

  const hydroBackbone = buildBackboneFromRun(
    "hydro-agent",
    "Hydro-Agent",
    "HA",
    "#047857",
    traceFromRun(bundle.trajectory.steps),
    toolPathToShort(eval_.agent_path),
    {
      TAO: stepMetrics.TAO ?? 0,
      TIO: stepMetrics.TIO ?? 0,
      TEM: stepMetrics.TEM ?? 0,
      Param: stepMetrics.Param ?? 0,
      Efficiency: stepMetrics.Efficiency ?? 0,
      Accuracy: stepMetrics.Accuracy ?? 0,
      "Hydro-QC": stepMetrics["Hydro-QC"],
      "Phys-Consistency": stepMetrics["Phys-Consistency"],
      "Leakage-Safety": stepMetrics["Leakage-Safety"],
    },
    eval_.end_to_end >= 0.9 && (eval_.leakage_audit?.passed ?? true),
    answerKey,
  );

  const mockBackbones = demoPayload.backbones
    .filter((b) => b.id !== "hydro-agent")
    .map((b) => ({
      ...b,
      toolPath: b.toolPath.filter((t) => gtPath.includes(t) || !["T2", "T8"].includes(t) || gtPath.includes("T2")),
    }));

  return {
    taskId: metrics.task_id,
    spectrum: SPECTRUM_BY_MODE[metrics.mode] ?? metrics.mode,
    mode: metrics.mode,
    stationId: bundle.task?.station_id ?? "US_COSMOS_ARM1",
    question: bundle.task?.question ?? demoPayload.question,
    choices: buildChoices(bundle),
    dataPreview: buildDataPreview(bundle),
    groundTruthPath: gtPath,
    toolLegend: buildToolLegend(gtPath),
    selectedBackboneId: "hydro-agent",
    backbones: [hydroBackbone, ...mockBackbones],
  };
}

export async function fetchRunBundle(path: string): Promise<RunBundle> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Failed to load ${path}`);
  return response.json() as Promise<RunBundle>;
}
