import { useEffect, useState } from "react";
import { api } from "../api";
import { DiscoveredDataset, ImportBatchResultItem } from "../types";
import Empty from "./Empty";

function fmt(d?: string | null) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("pl-PL");
  } catch {
    return d;
  }
}

export default function ImportManager() {
  const [items, setItems] = useState<DiscoveredDataset[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastBatch, setLastBatch] = useState<ImportBatchResultItem[] | null>(null);

  const refresh = async () => {
    setError(null);
    try {
      const list = await api.discoverDatasets();
      setItems(list);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const runImport = async (names: string[]) => {
    if (!names.length) return;
    setBusy(true);
    setLastBatch(null);
    setError(null);
    try {
      const res = await api.importBatch(names);
      setLastBatch(res.results);
      await refresh();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (items.length === 0) {
    return (
      <Empty
        title="Nie znaleziono żadnych zrzutów"
        hint={
          "Rozpakuj archiwum Google Takeout do katalogu data/imports/NAZWA_ZRZUTU\n" +
          "na hoście (np. data/imports/takeout_2024_01), a następnie kliknij \"Odśwież\"."
        }
      >
        <button
          onClick={refresh}
          className="px-3 py-1.5 bg-slate-900 text-white rounded text-sm"
        >
          Odśwież
        </button>
      </Empty>
    );
  }

  const selectedNames = Object.keys(selected).filter((k) => selected[k]);

  return (
    <div className="space-y-3">
      {error && (
        <div className="bg-rose-50 text-rose-800 border border-rose-200 rounded px-3 py-2 text-sm">
          {error}
        </div>
      )}
      <div className="flex items-center gap-2">
        <button
          onClick={refresh}
          disabled={busy}
          className="px-3 py-1.5 border border-slate-300 rounded text-sm hover:bg-slate-100"
        >
          Odśwież
        </button>
        <button
          onClick={() => runImport(selectedNames)}
          disabled={busy || !selectedNames.length}
          className="px-3 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50"
        >
          {busy ? "Importowanie..." : `Importuj zaznaczone (${selectedNames.length})`}
        </button>
      </div>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 w-8"></th>
              <th className="px-3 py-2 text-left">Nazwa zrzutu</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-right">Rekordy</th>
              <th className="px-3 py-2 text-right">Duplikaty</th>
              <th className="px-3 py-2 text-right">Błędy</th>
              <th className="px-3 py-2 text-left">Ostatni import</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((d) => (
              <tr key={d.name} className="border-t border-slate-100">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={!!selected[d.name]}
                    onChange={(e) =>
                      setSelected({ ...selected, [d.name]: e.target.checked })
                    }
                  />
                </td>
                <td className="px-3 py-2 font-medium">{d.name}</td>
                <td className="px-3 py-2">
                  {d.is_known ? (
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-xs">
                      {d.status || "zaimportowany"}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-xs">
                      nowy
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">{d.events_count}</td>
                <td className="px-3 py-2 text-right">{d.duplicates_count}</td>
                <td className="px-3 py-2 text-right">{d.errors_count}</td>
                <td className="px-3 py-2">{fmt(d.last_imported_at)}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => runImport([d.name])}
                    disabled={busy}
                    className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100"
                  >
                    Importuj
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {lastBatch && (
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="font-medium mb-2">Wynik ostatniego importu</div>
          <ul className="text-sm space-y-1">
            {lastBatch.map((r) => (
              <li key={r.dataset_name}>
                <strong>{r.dataset_name}</strong> — {r.status}
                {r.message ? ` (${r.message})` : ""} · nowych:{" "}
                {r.imported}, duplikatów: {r.duplicates}, błędów: {r.errors}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
