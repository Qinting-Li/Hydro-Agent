import type { DemoPayload } from "../types";

type Props = { payload: DemoPayload };

export function Header({ payload }: Props) {
  return (
    <header className="rounded-2xl border-2 border-orange-300 bg-[var(--surface)] px-6 py-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-500 text-lg font-bold text-white">
            H
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900 md:text-2xl">
              HYDRO-AGENT WITH DIFFERENT LLM BACKBONES
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              Spectrum: <span className="font-semibold text-orange-700">[{payload.spectrum}]</span>
            </p>
          </div>
        </div>
        <span className="rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-orange-700">
          Autonomous Planning
        </span>
      </div>
    </header>
  );
}
