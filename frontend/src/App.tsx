import { useCallback, useEffect, useMemo, useState } from "react";
import { AgentComparison } from "./components/AgentComparison";
import { AgentTrace } from "./components/AgentTrace";
import { Header } from "./components/Header";
import { HydrologicPanel } from "./components/HydrologicPanel";
import { LeakagePanel } from "./components/LeakagePanel";
import { MetricsBar } from "./components/MetricsBar";
import { ProblemCard } from "./components/ProblemCard";
import { StepTimeline } from "./components/StepTimeline";
import { TabNav } from "./components/TabNav";
import { TaskSwitcher } from "./components/TaskSwitcher";
import { demoPayload } from "./data/demo";
import { TASK_CATALOG } from "./data/tasks";
import { fetchRunBundle, payloadFromRun } from "./lib/transform";
import type { AppTab, DemoPayload, RunBundle } from "./types";

export default function App() {
  const [activeTaskId, setActiveTaskId] = useState("HB_0001");
  const [activeTab, setActiveTab] = useState<AppTab>("overview");
  const [payload, setPayload] = useState<DemoPayload>(demoPayload);
  const [bundle, setBundle] = useState<RunBundle | null>(null);
  const [selectedId, setSelectedId] = useState("hydro-agent");
  const [endToEnd, setEndToEnd] = useState<number | undefined>(1.0);
  const [sourceLabel, setSourceLabel] = useState("Built-in demo");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyBundle = useCallback((nextBundle: RunBundle, label: string) => {
    const nextPayload = payloadFromRun(nextBundle);
    setBundle(nextBundle);
    setPayload(nextPayload);
    setSelectedId("hydro-agent");
    setEndToEnd(nextBundle.trajectory.evaluation.end_to_end);
    setSourceLabel(label);
    setError(null);
  }, []);

  const loadTask = useCallback(async (taskId: string) => {
    const task = TASK_CATALOG.find((t) => t.id === taskId);
    if (!task) return;
    setLoading(true);
    setError(null);
    try {
      const nextBundle = await fetchRunBundle(task.bundlePath);
      applyBundle(nextBundle, `${task.id} · ${task.label}`);
      setActiveTaskId(taskId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load task bundle");
    } finally {
      setLoading(false);
    }
  }, [applyBundle]);

  useEffect(() => {
    loadTask("HB_0001").catch(() => {
      setPayload(demoPayload);
      setSourceLabel("Built-in demo (offline fallback)");
    });
  }, [loadTask]);

  const selected = useMemo(
    () => payload.backbones.find((b) => b.id === selectedId) ?? payload.backbones[0],
    [payload, selectedId],
  );

  async function onLoadFile(file: File) {
    const text = await file.text();
    const nextBundle = JSON.parse(text) as RunBundle;
    if (!nextBundle.trajectory?.steps || !nextBundle.metrics?.best_method) {
      throw new Error("Invalid run bundle: need trajectory.steps and metrics.best_method");
    }
    applyBundle(nextBundle, file.name);
    setActiveTaskId(nextBundle.metrics.task_id);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-5 px-4 py-6 md:px-6 md:py-8">
      <Header payload={payload} />

      <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TaskSwitcher
            tasks={TASK_CATALOG}
            activeId={activeTaskId}
            loading={loading}
            onSelect={(id) => loadTask(id)}
          />
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-orange-300 bg-orange-50 px-3 py-2 text-sm font-medium text-orange-800 hover:bg-orange-100">
            <input
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onLoadFile(file).catch((e: Error) => setError(e.message));
              }}
            />
            Import JSON
          </label>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-600">
          <span>
            Source: <strong className="text-gray-900">{sourceLabel}</strong>
            {loading && <span className="ml-2 text-orange-600">Loading…</span>}
          </span>
          {error && <span className="text-red-600">{error}</span>}
        </div>
        <TabNav active={activeTab} onChange={setActiveTab} />
      </div>

      {activeTab === "overview" && (
        <>
          <ProblemCard payload={payload} />
          <MetricsBar
            backbone={selected}
            endToEnd={selectedId === "hydro-agent" ? endToEnd : undefined}
            stepByStep={bundle?.trajectory.evaluation.step_by_step}
          />
          <AgentComparison payload={payload} selectedId={selectedId} onSelect={setSelectedId} />
        </>
      )}

      {activeTab === "trajectory" && (
        <>
          <AgentTrace backbone={selected} />
          <StepTimeline steps={bundle?.trajectory.steps ?? []} bundle={bundle} />
        </>
      )}

      {activeTab === "science" && <HydrologicPanel bundle={bundle} />}

      {activeTab === "leakage" && <LeakagePanel bundle={bundle} />}

      <footer className="pb-6 text-center text-xs text-gray-500">
        Hydro-Agent UI · Hydro-Bench v0.2 · {payload.taskId} · {payload.mode.replaceAll("_", " ")}
      </footer>
    </div>
  );
}
