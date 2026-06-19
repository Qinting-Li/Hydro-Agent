export type ToolStep = {
  step: number;
  tool_name: string;
  input: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  status: string;
  runtime_ms: number;
  qc: string;
  accessed_inputs: string[];
  execution_scope: string;
  warnings?: string[];
};

export type DailyRow = {
  date: string;
  precipitation_mm?: number;
  et0_mm?: number;
  era5_m3m3?: number;
  water_balance_m3m3?: number;
  analysis_m3m3?: number;
  analysis_sigma_m3m3?: number;
  persistence_m3m3?: number;
  climatology_m3m3?: number;
  linear_regression_m3m3?: number;
  ismn_truth_m3m3?: number;
};

export type MetricValue = {
  n: number;
  rmse: number;
  bias: number;
  correlation: number;
  ubrmse: number;
  nse: number;
  kge: number;
  coverage_95?: number;
};

export type AgentBackbone = {
  id: string;
  name: string;
  logo: string;
  color: string;
  passed: boolean;
  finalAnswer: string;
  toolPath: string[];
  metrics: {
    TAO: number;
    TIO: number;
    TEM: number;
    Param: number;
    Efficiency: number;
    Accuracy: number;
    "Hydro-QC"?: number;
    "Phys-Consistency"?: number;
    "Leakage-Safety"?: number;
  };
  traceSteps: Array<{
    label: string;
    input: Record<string, unknown>;
    output: Record<string, unknown>;
  }>;
};

export type DemoPayload = {
  taskId: string;
  spectrum: string;
  mode: string;
  stationId: string;
  question: string;
  choices: Array<{ key: string; label: string; correct: boolean }>;
  dataPreview: Array<{ label: string; count: string; color: string }>;
  groundTruthPath: string[];
  toolLegend: Record<string, string>;
  selectedBackboneId: string;
  backbones: AgentBackbone[];
};

export type LeakageAudit = {
  passed: boolean;
  violations: number;
  score: number;
  step_audits: Array<{
    step: number;
    tool_name: string;
    execution_scope: string;
    accessed_inputs: string[];
    forbidden_hits: string[];
    passed: boolean;
  }>;
};

export type RunBundle = {
  trajectory: {
    steps: ToolStep[];
    evaluation: {
      ground_truth_path: string[];
      agent_path: string[];
      step_by_step: Record<string, number>;
      end_to_end: number;
      leakage_audit?: LeakageAudit;
    };
  };
  metrics: {
    task_id: string;
    mode: string;
    best_method: string;
    evaluation_period?: { start: string; end: string };
    matched_days_test?: number;
    metrics: Record<string, MetricValue>;
    physical_checks?: Record<string, boolean>;
    baseline_eligibility?: { eligible: string[]; excluded: Record<string, string> };
  };
  task?: {
    question: string;
    mode: string;
    station_id: string;
    allowed_inputs?: string[];
    forbidden_inputs?: string[];
    time_range?: string[];
  };
  daily_rows?: DailyRow[];
};

export type AppTab = "overview" | "trajectory" | "science" | "leakage";

export type TaskCatalogItem = {
  id: string;
  label: string;
  bundlePath: string;
};
