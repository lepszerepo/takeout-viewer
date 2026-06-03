import { useEffect, useState } from "react";
import { api } from "../api";
import { DatasetOut, SourceSummaryOut } from "../types";

export interface FiltersState {
  dataset_id?: number;
  source?: string;
  type?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  include_duplicates: boolean;
}

interface Props {
  value: FiltersState;
  onChange: (next: FiltersState) => void;
  typeLabels: Record<string, string>;
  sourceLabels: Record<string, string>;
}

export default function Filters({ value, onChange, typeLabels, sourceLabels }: Props) {
  const [datasets, setDatasets] = useState<DatasetOut[]>([]);
  const [sources, setSources] = useState<SourceSummaryOut[]>([]);

  useEffect(() => {
    api.listDatasets().then(setDatasets).catch(() => setDatasets([]));
    api.listSources().then(setSources).catch(() => setSources([]));
  }, []);

  const update = <K extends keyof FiltersState>(k: K, v: FiltersState[K]) =>
    onChange({ ...value, [k]: v });

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Wyszukaj</span>
        <input
          type="text"
          value={value.q ?? ""}
          onChange={(e) => update("q", e.target.value || undefined)}
          placeholder="słowo kluczowe..."
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Zrzut</span>
        <select
          value={value.dataset_id ?? ""}
          onChange={(e) =>
            update("dataset_id", e.target.value ? Number(e.target.value) : undefined)
          }
          className="border border-slate-300 rounded px-2 py-1"
        >
          <option value="">— wszystkie —</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Źródło</span>
        <select
          value={value.source ?? ""}
          onChange={(e) => update("source", e.target.value || undefined)}
          className="border border-slate-300 rounded px-2 py-1"
        >
          <option value="">— wszystkie —</option>
          {sources.map((s) => (
            <option key={s.source} value={s.source}>
              {sourceLabels[s.source] || s.label || s.source}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Typ</span>
        <select
          value={value.type ?? ""}
          onChange={(e) => update("type", e.target.value || undefined)}
          className="border border-slate-300 rounded px-2 py-1"
        >
          <option value="">— wszystkie —</option>
          {Object.entries(typeLabels).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Od daty</span>
        <input
          type="date"
          value={value.date_from ?? ""}
          onChange={(e) => update("date_from", e.target.value || undefined)}
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-xs text-slate-500">Do daty</span>
        <input
          type="date"
          value={value.date_to ?? ""}
          onChange={(e) => update("date_to", e.target.value || undefined)}
          className="border border-slate-300 rounded px-2 py-1"
        />
      </label>
      <label className="flex flex-row items-center gap-2 mt-5">
        <input
          type="checkbox"
          checked={value.include_duplicates}
          onChange={(e) => update("include_duplicates", e.target.checked)}
        />
        <span>Pokaż również duplikaty</span>
      </label>
      <button
        onClick={() =>
          onChange({
            dataset_id: undefined,
            source: undefined,
            type: undefined,
            q: undefined,
            date_from: undefined,
            date_to: undefined,
            include_duplicates: false,
          })
        }
        className="md:col-span-4 text-xs text-slate-500 hover:text-slate-900 underline justify-self-start"
      >
        Wyczyść filtry
      </button>
    </div>
  );
}
