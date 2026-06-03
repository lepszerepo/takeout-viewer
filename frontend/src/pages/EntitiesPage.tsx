import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { httpGet } from "../api";

interface Entity {
  id: number;
  kind: string;
  key: string;
  label: string;
  count: number;
}

interface Mention {
  event_id: number;
  title: string;
  source: string;
  type: string;
  timestamp: string | null;
  dataset_name: string;
  span: string | null;
}

const KIND_LABELS: Record<string, string> = {
  PERSON: "Osoby",
  ORG: "Organizacje",
  GPE: "Miejsca / kraje",
  LOC: "Lokalizacje",
  MONEY: "Kwoty",
  DATE: "Daty",
  PERCENT: "Procenty",
  EMAIL: "Adresy e-mail",
  URL: "Linki",
  LAW: "Akty prawne",
  EVENT: "Wydarzenia",
  PRODUCT: "Produkty",
  WORK: "Dzieła",
};

function fmtDate(s: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return s;
  }
}

export default function EntitiesPage() {
  const [kind, setKind] = useState("PERSON");
  const [q, setQ] = useState("");
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    httpGet<any>(`/api/entities/status`).then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ kind, limit: "200" });
    if (q) params.set("q", q);
    httpGet<Entity[]>(`/api/entities/top?${params}`)
      .then(setEntities)
      .finally(() => setLoading(false));
  }, [kind, q]);

  useEffect(() => {
    if (!selected) {
      setMentions([]);
      return;
    }
    httpGet<{ mentions: Mention[] }>(`/api/entities/${selected.id}/mentions?limit=100`)
      .then((d) => setMentions(d.mentions))
      .catch(() => setMentions([]));
  }, [selected]);

  const startProcess = async () => {
    await fetch(`http://localhost:8001/api/entities/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ only_unprocessed: true }),
    });
    setTimeout(() => httpGet<any>(`/api/entities/status`).then(setStatus), 1000);
  };

  const max = entities[0]?.count || 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Encje (NER)</h2>
        <button
          onClick={startProcess}
          className="px-3 py-1.5 bg-slate-900 text-white rounded text-sm"
        >
          ▶︎ Uruchom analizę NER
        </button>
      </div>

      {status && (
        <div className="bg-white border border-slate-200 rounded p-3 text-sm flex flex-wrap gap-4">
          <span>
            Przetworzone: <strong>{status.events_processed?.toLocaleString("pl-PL")}</strong> /{" "}
            {status.events_total?.toLocaleString("pl-PL")}
          </span>
          <span>
            Encji unikatów: <strong>{status.entities?.toLocaleString("pl-PL")}</strong>
          </span>
          <span>
            Wzmianek: <strong>{status.mentions?.toLocaleString("pl-PL")}</strong>
          </span>
          {status.by_kind && (
            <span className="text-slate-500">
              {Object.entries(status.by_kind).map(([k, v]) => `${KIND_LABELS[k] || k}: ${v as number}`).join(" · ")}
            </span>
          )}
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {Object.entries(KIND_LABELS).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setKind(k)}
            className={`px-3 py-1.5 rounded text-sm ${
              kind === k ? "bg-slate-900 text-white" : "border border-slate-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <input
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Filtruj..."
        className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
      />

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-5 bg-white border border-slate-200 rounded overflow-y-auto max-h-[600px]">
          {loading && <div className="p-3 text-slate-500 text-sm">Ładuję...</div>}
          <table className="w-full text-sm">
            <thead className="bg-slate-50 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left">Encja</th>
                <th className="px-3 py-2 text-right w-24">Wzmianek</th>
                <th className="px-3 py-2 w-32"></th>
              </tr>
            </thead>
            <tbody>
              {entities.map((e) => (
                <tr
                  key={e.id}
                  onClick={() => setSelected(e)}
                  className={`border-t border-slate-100 cursor-pointer ${
                    selected?.id === e.id ? "bg-indigo-50" : "hover:bg-slate-50"
                  }`}
                >
                  <td className="px-3 py-2 truncate">{e.label}</td>
                  <td className="px-3 py-2 text-right">{e.count.toLocaleString("pl-PL")}</td>
                  <td className="px-3 py-2">
                    <div
                      className="h-2 bg-indigo-500 rounded"
                      style={{ width: `${Math.max(2, (e.count / max) * 100)}%` }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="col-span-7 bg-white border border-slate-200 rounded p-3 overflow-y-auto max-h-[600px]">
          {!selected && <div className="text-slate-400 text-sm">Wybierz encję, aby zobaczyć wzmianki.</div>}
          {selected && (
            <>
              <div className="font-medium mb-2">{selected.label}</div>
              <div className="text-xs text-slate-500 mb-3">
                {selected.kind} · {selected.count.toLocaleString("pl-PL")} wzmianek
              </div>
              <ul className="space-y-2">
                {mentions.map((m) => (
                  <li key={m.event_id} className="border-b border-slate-100 pb-2">
                    <Link
                      to={m.source === "mail" ? `/mail?event=${m.event_id}` : `/events?focus=${m.event_id}`}
                      className="block hover:bg-slate-50 rounded p-1"
                    >
                      <div className="flex justify-between text-xs text-slate-500">
                        <span>
                          {m.source} · {m.dataset_name}
                        </span>
                        <span>{fmtDate(m.timestamp)}</span>
                      </div>
                      <div className="text-sm font-medium truncate">{m.title}</div>
                      {m.span && <div className="text-xs text-slate-600 italic">„{m.span}"</div>}
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
