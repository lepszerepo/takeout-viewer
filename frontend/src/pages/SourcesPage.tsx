import { useEffect, useState } from "react";
import { api } from "../api";
import { Card, CardBody, CardHeader } from "../components/Card";
import Empty from "../components/Empty";
import { DatasetOut, SourceSummaryOut } from "../types";

function fmt(d?: string | null) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("pl-PL");
  } catch {
    return d;
  }
}

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceSummaryOut[]>([]);
  const [datasets, setDatasets] = useState<DatasetOut[]>([]);
  const [datasetId, setDatasetId] = useState<number | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDatasets().then(setDatasets).catch(() => setDatasets([]));
  }, []);

  useEffect(() => {
    api
      .listSources(datasetId)
      .then(setSources)
      .catch((e) => setError(e.message));
  }, [datasetId]);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Źródła danych</h2>
      <div className="flex gap-3 items-center text-sm">
        <label className="flex items-center gap-2">
          <span className="text-slate-600">Filtruj po zrzucie:</span>
          <select
            value={datasetId ?? ""}
            onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : undefined)}
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
      </div>
      {error && <div className="text-rose-700 text-sm">{error}</div>}
      {sources.length === 0 ? (
        <Empty title="Brak źródeł" hint="Zaimportuj zrzut, aby zobaczyć wykryte usługi Google." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sources.map((s) => (
            <Card key={s.source}>
              <CardHeader>{s.label}</CardHeader>
              <CardBody>
                <div className="text-sm space-y-1">
                  <div>
                    Rekordów: <span className="font-medium">{s.events_count}</span>
                  </div>
                  <div>
                    Zakres dat: {fmt(s.date_min)} — {fmt(s.date_max)}
                  </div>
                  {s.sample_types.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {s.sample_types.map((t) => (
                        <span key={t} className="px-2 py-0.5 bg-slate-100 rounded text-xs">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
