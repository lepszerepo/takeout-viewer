import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card, CardBody, CardHeader, Stat } from "../components/Card";
import { ImportRunOut, StatsOut } from "../types";

function fmt(d?: string | null) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("pl-PL");
  } catch {
    return d;
  }
}

export default function Dashboard() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [runs, setRuns] = useState<ImportRunOut[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.stats(), api.listImportRuns()])
      .then(([s, r]) => {
        setStats(s);
        setRuns(r.slice(0, 5));
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Pulpit</h2>
        <Link
          to="/datasets"
          className="px-3 py-1.5 bg-slate-900 text-white rounded text-sm"
        >
          Zarządzaj zrzutami
        </Link>
      </div>

      {error && (
        <div className="bg-rose-50 text-rose-800 border border-rose-200 rounded px-3 py-2 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Zrzutów" value={stats?.datasets_count ?? "—"} />
        <Stat label="Unikalnych zdarzeń" value={stats?.unique_events_count ?? "—"} />
        <Stat label="Wszystkich wystąpień" value={stats?.events_count ?? "—"} />
        <Stat
          label="Zakres dat"
          value={
            stats?.date_min || stats?.date_max
              ? `${fmt(stats?.date_min).split(",")[0]} — ${fmt(stats?.date_max).split(",")[0]}`
              : "—"
          }
        />
      </div>

      <Card>
        <CardHeader>Najczęstsze typy aktywności</CardHeader>
        <CardBody>
          {stats?.top_types?.length ? (
            <ul className="text-sm space-y-1">
              {stats.top_types.map((t) => (
                <li key={t.type} className="flex justify-between border-b border-slate-100 py-1">
                  <span>{t.label || t.type}</span>
                  <span className="text-slate-500">{t.count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-slate-500 text-sm">Brak danych. Zaimportuj pierwszy zrzut.</div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Ostatnie importy</CardHeader>
        <CardBody>
          {runs.length === 0 ? (
            <div className="text-slate-500 text-sm">Brak importów. Przejdź do "Zrzuty", aby zacząć.</div>
          ) : (
            <ul className="text-sm space-y-1">
              {runs.map((r) => (
                <li key={r.id} className="border-b border-slate-100 py-1 flex justify-between gap-2">
                  <span className="font-medium">{r.dataset_name || "(brak)"}</span>
                  <span className="text-slate-500">{fmt(r.finished_at || r.started_at)}</span>
                  <span>
                    nowych: {r.imported_events_count}, duplikatów: {r.duplicate_events_count}, błędów: {r.error_count}
                  </span>
                  <span
                    className={
                      r.status === "ok"
                        ? "text-emerald-700"
                        : r.status === "failed"
                          ? "text-rose-700"
                          : "text-amber-700"
                    }
                  >
                    {r.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
