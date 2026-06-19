import type { TaskCatalogItem } from "../types";

type Props = {
  tasks: TaskCatalogItem[];
  activeId: string;
  loading: boolean;
  onSelect: (id: string) => void;
};

export function TaskSwitcher({ tasks, activeId, loading, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {tasks.map((task) => {
        const active = task.id === activeId;
        return (
          <button
            key={task.id}
            type="button"
            disabled={loading}
            onClick={() => onSelect(task.id)}
            className={`rounded-xl border px-4 py-2 text-sm font-semibold transition-colors ${
              active
                ? "border-orange-400 bg-orange-500 text-white shadow-sm"
                : "border-gray-200 bg-white text-gray-700 hover:border-orange-200 hover:bg-orange-50"
            } ${loading ? "opacity-60" : ""}`}
          >
            <span className="block text-[10px] font-bold uppercase tracking-wide opacity-80">{task.id}</span>
            {task.label}
          </button>
        );
      })}
    </div>
  );
}
