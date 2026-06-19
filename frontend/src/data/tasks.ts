import type { TaskCatalogItem } from "../types";

export const TASK_CATALOG: TaskCatalogItem[] = [
  { id: "HB_0001", label: "Station Forecast", bundlePath: "/bundles/HB_0001.json" },
  { id: "HB_0002", label: "Satellite Only", bundlePath: "/bundles/HB_0002.json" },
  { id: "HB_0003", label: "Gap Filling", bundlePath: "/bundles/HB_0003.json" },
];

export const SPECTRUM_BY_MODE: Record<string, string> = {
  station_aware_forecasting: "Soil Moisture Forecasting",
  "station-aware_forecasting": "Soil Moisture Forecasting",
  satellite_only_retrieval: "Satellite-Only Retrieval",
  "satellite-only_retrieval": "Satellite-Only Retrieval",
  "gap-filling": "Blocked Gap Filling",
};

export const METHOD_LABELS: Record<string, string> = {
  era5_baseline: "ERA5 baseline",
  water_balance: "Water balance",
  kalman_analysis: "Kalman analysis",
  persistence: "Persistence",
  climatology: "Climatology",
  linear_regression: "Linear regression",
};
