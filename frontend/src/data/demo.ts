import type { AgentBackbone, DemoPayload } from "../types";

const TOOL_LEGEND: Record<string, string> = {
  T1: "get_station_metadata",
  T2: "load_station_history",
  T3: "load_era5_forcing",
  T4: "match_footprint",
  T5: "reject_if_unreliable",
  T6: "compute_water_balance",
  T7: "run_kalman_assimilation",
  T8: "compute_baselines",
  T9: "compute_uncertainty",
  T10: "compute_metrics",
};

const GT_PATH = [
  "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10",
];

const hydroAgentTrace = [
  {
    label: "Step 1",
    input: { name: "get_station_metadata", station_id: "US_COSMOS_ARM1" },
    output: { network: "COSMOS", lat: 36.6054, lon: -97.4878, climate_zone: "temperate" },
  },
  {
    label: "Step 2",
    input: { name: "load_station_history", split: "leave-year-out", test_year: 2018 },
    output: { history_days: 142, label_visibility: "historical_ISMN" },
  },
  {
    label: "Step 3",
    input: { name: "load_era5_forcing", start: "2017-08-10", end: "2018-08-09" },
    output: { valid_daily_observations: 365, variables: ["precipitation_mm", "et0_mm", "era5_soil_moisture"] },
  },
  {
    label: "Step 4–5",
    input: { name: "match_footprint + reject_if_unreliable" },
    output: { matched_days: 333, missing_fraction: 0.088, qc: "accepted" },
  },
  {
    label: "Step 6–7",
    input: { name: "compute_water_balance + run_kalman_assimilation" },
    output: { days: 333, observations_assimilated: 111, state_bounded: true },
  },
  {
    label: "Step 8–10",
    input: { name: "compute_baselines + compute_uncertainty + compute_metrics" },
    output: { best_method: "persistence", best_rmse: 0.0231, kalman_coverage_95: "95.8%" },
  },
  {
    label: "Final",
    input: { evaluator_scope: "compute_metrics" },
    output: { final_answer: "C", best_baseline: "persistence", leakage_audit: "PASS" },
  },
];

const perfectMetrics = {
  TAO: 1.0,
  TIO: 1.0,
  TEM: 1.0,
  Param: 1.0,
  Efficiency: 1.0,
  Accuracy: 1.0,
};

export const demoPayload: DemoPayload = {
  taskId: "HB_0001",
  spectrum: "Soil Moisture Forecasting",
  mode: "station-aware_forecasting",
  stationId: "US_COSMOS_ARM1",
  question:
    "Forecast 2018 daily soil moisture at COSMOS ARM-1 with rolling access to prior station observations. " +
    "Compare legal station-aware baselines (persistence, climatology, linear regression, ERA5, water balance, Kalman) " +
    "and audit label leakage on the held-out year.",
  choices: [
    { key: "A", label: "ERA5 baseline (RMSE 0.110)", correct: false },
    { key: "B", label: "Water balance (RMSE 0.094)", correct: false },
    { key: "C", label: "Persistence (RMSE 0.023)", correct: true },
    { key: "D", label: "Kalman analysis (RMSE 0.105)", correct: false },
  ],
  dataPreview: [
    { label: "ISMN history", count: "142 d", color: "#111827" },
    { label: "ERA5 forcing", count: "365 d", color: "#d97706" },
    { label: "Test window", count: "191 d", color: "#047857" },
  ],
  groundTruthPath: GT_PATH,
  toolLegend: TOOL_LEGEND,
  selectedBackboneId: "hydro-agent",
  backbones: [
    {
      id: "hydro-agent",
      name: "Hydro-Agent",
      logo: "HA",
      color: "#047857",
      passed: true,
      finalAnswer: "C",
      toolPath: GT_PATH,
      metrics: perfectMetrics,
      traceSteps: hydroAgentTrace,
    },
    {
      id: "gpt-5",
      name: "GPT-5",
      logo: "G5",
      color: "#10a37f",
      passed: true,
      finalAnswer: "C",
      toolPath: GT_PATH,
      metrics: { ...perfectMetrics, Efficiency: 0.91 },
      traceSteps: hydroAgentTrace,
    },
    {
      id: "kimi-k2",
      name: "Kimi-K2",
      logo: "K2",
      color: "#6366f1",
      passed: false,
      finalAnswer: "D",
      toolPath: ["T1", "T2", "T3", "T8", "T10"],
      metrics: { TAO: 0.5, TIO: 0.7, TEM: 0.5, Param: 0.67, Efficiency: 0.5, Accuracy: 0.33 },
      traceSteps: [
        {
          label: "Step 1–3",
          input: { name: "metadata + history + era5" },
          output: { status: "ok" },
        },
        {
          label: "Step 4",
          input: { name: "compute_baselines", error: "skipped QC and model tools" },
          output: { warning: "illegal tool order" },
        },
        {
          label: "Final",
          input: { leakage: "accessed test_label in agent scope" },
          output: { final_answer: "D", status: "FAIL" },
        },
      ],
    },
    {
      id: "deepseek-v3",
      name: "DeepSeek V3.1",
      logo: "DS",
      color: "#2563eb",
      passed: false,
      finalAnswer: "B",
      toolPath: ["T1", "T3", "T6", "T7", "T10"],
      metrics: { TAO: 0.6, TIO: 0.6, TEM: 0.5, Param: 0.33, Efficiency: 0.5, Accuracy: 0.0 },
      traceSteps: [
        {
          label: "Step 1",
          input: { name: "get_station_metadata" },
          output: { station_id: "US_COSMOS_ARM1" },
        },
        {
          label: "Step 2",
          input: { name: "load_era5_forcing" },
          output: { skipped: "load_station_history" },
        },
        {
          label: "Final",
          input: { missing_tools: ["match_footprint", "reject_if_unreliable", "compute_baselines"] },
          output: { final_answer: "B", status: "FAIL" },
        },
      ],
    },
  ],
};

export function toolLabel(short: string): string {
  return TOOL_LEGEND[short] ?? short;
}

export function pathToShort(toolNames: string[]): string[] {
  const reverse = Object.fromEntries(Object.entries(TOOL_LEGEND).map(([k, v]) => [v, k]));
  return toolNames.map((name) => reverse[name] ?? name);
}

export function buildBackboneFromRun(
  id: string,
  name: string,
  logo: string,
  color: string,
  steps: DemoPayload["backbones"][0]["traceSteps"],
  toolPath: string[],
  metrics: AgentBackbone["metrics"],
  passed: boolean,
  finalAnswer: string,
): AgentBackbone {
  return { id, name, logo, color, passed, finalAnswer, toolPath, metrics, traceSteps: steps };
}
