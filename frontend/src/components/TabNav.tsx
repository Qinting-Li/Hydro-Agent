import type { AppTab } from "../types";

const TABS: Array<{ id: AppTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "trajectory", label: "Trajectory" },
  { id: "science", label: "Science" },
  { id: "leakage", label: "Leakage Audit" },
];

type Props = {
  active: AppTab;
  onChange: (tab: AppTab) => void;
};

export function TabNav({ active, onChange }: Props) {
  return (
    <nav className="flex flex-wrap gap-1 rounded-xl border border-gray-200 bg-white p-1">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
            active === tab.id ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
