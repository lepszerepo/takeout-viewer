import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { httpGet } from "../api";
import { DatasetOut } from "../types";
import { FtsResultItem } from "../types_mail";

function fmtDate(s: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return s;
  }
}

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [items, setItems] = useState<FtsResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<DatasetOut[]>([]);
  const [datasetName, setDatasetName] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [mode, setMode] = useState<"fts" | "semantic">("fts");
  const [semanticItems, setSemanticItems] = useState<any[]>([]);

  useEffect(() => {
    httpGet<DatasetOut[]>(`/api/datasets`).then(setDatasets).catch(() => setDatasets([]));
  }, []);

  useEffect(() => {
    if (!submittedQ) return;
    setLoading(true);
    setError(null);
    if (mode === "fts") {
      const params = new URLSearchParams({ q: submittedQ, limit: "100" });
      if (datasetName) params.set("dataset_name", datasetName);
      if (source) params.set("source", source);
      httpGet<{ items: FtsResultItem[] }>(`/api/search/fts?${params}`)
        .then((d) => {
          setItems(d.items);
          setSemanticItems([]);
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    } else {
      fetch("http://localhost:8001/api/llm/search/semantic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q: submittedQ, k: 50 }),
      })
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((d) => {
          setSemanticItems(d.items);
          setItems([]);
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
  }, [submittedQ, datasetName, source, mode]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittedQ(q.trim());
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Wyszukiwanie</h2>
      <div className="flex gap-2">
        <button
          onClick={() => setMode("fts")}
          className={`px-3 py-1.5 rounded text-sm ${mode === "fts" ? "bg-slate-900 text-white" : "border border-slate-300"}`}
        >
          Pełnotekstowe (FTS5)
        </button>
        <button
          onClick={() => setMode("semantic")}
          className={`px-3 py-1.5 rounded text-sm ${mode === "semantic" ? "bg-indigo-600 text-white" : "border border-indigo-300 text-indigo-700"}`}
        >
          ✨ Semantyczne (Bielik + bge-m3)
        </button>
      </div>
      <form onSubmit={submit} className="bg-white border border-slate-200 rounded-lg p-3 flex gap-2">
        <input
          autoFocus
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="np. umowa, malinowska, regulamin, &quot;okręgowy sąd&quot;..."
          className="flex-1 border border-slate-300 rounded px-3 py-2 text-sm"
        />
        <select
          value={datasetName}
          onChange={(e) => setDatasetName(e.target.value)}
          className="border border-slate-300 rounded px-2 py-2 text-sm"
        >
          <option value="">wszystkie zrzuty</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.name}>
              {d.name}
            </option>
          ))}
        </select>
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="border border-slate-300 rounded px-2 py-2 text-sm"
        >
          <option value="">wszystkie źródła</option>
          <option value="mail">poczta</option>
          <option value="calendar">kalendarz</option>
          <option value="drive">drive</option>
          <option value="my_activity">aktywność Google</option>
          <option value="tasks">tasks</option>
          <option value="meet">meet</option>
          <option value="contacts">kontakty</option>
        </select>
        <button type="submit" className="bg-slate-900 text-white rounded px-4 text-sm">
          Szukaj
        </button>
      </form>

      <div className="text-xs text-slate-500">
        Operatory FTS5: <code>AND OR NOT</code>, <code>"fraza dokładna"</code>,{" "}
        <code>słowo*</code>, <code>NEAR/N</code>. BM25 ranking.
      </div>

      {error && <div className="text-rose-700 text-sm">{error}</div>}
      {loading && <div className="text-slate-500 text-sm">Szukam...</div>}

      <div className="space-y-2">
        {items.map((r) => (
          <Link
            key={`${r.event_id}`}
            to={
              r.source === "mail"
                ? `/mail?event=${r.event_id}&q=${encodeURIComponent(submittedQ)}`
                : `/events?focus=${r.event_id}&q=${encodeURIComponent(submittedQ)}`
            }
            className="block bg-white border border-slate-200 rounded p-3 hover:border-slate-400"
          >
            <div className="flex justify-between text-xs text-slate-500">
              <span>
                <span className="bg-slate-100 px-1.5 rounded mr-1">{r.source}</span>
                <span className="bg-slate-100 px-1.5 rounded mr-1">{r.dataset_name}</span>
                {r.folder && <span className="bg-indigo-50 text-indigo-700 px-1.5 rounded mr-1">{r.folder}</span>}
              </span>
              <span>{fmtDate(r.timestamp)}</span>
            </div>
            <div className="font-medium mt-1">{r.title}</div>
            {r.snippet && (
              <div
                className="text-sm text-slate-600 mt-1"
                dangerouslySetInnerHTML={{ __html: r.snippet }}
              />
            )}
          </Link>
        ))}
        {mode === "semantic" &&
          semanticItems.map((r) => (
            <Link
              key={`sem-${r.mail_id}`}
              to={`/mail?mail=${r.mail_id}&q=${encodeURIComponent(submittedQ)}`}
              className="block bg-white border border-indigo-200 rounded p-3 hover:border-indigo-400"
            >
              <div className="flex justify-between text-xs text-slate-500">
                <span>
                  <span className="bg-indigo-50 text-indigo-700 px-1.5 rounded mr-1">✨ semantic</span>
                  {r.from && r.from[0] && (
                    <span className="bg-slate-100 px-1.5 rounded mr-1">{r.from[0].email}</span>
                  )}
                  {r.folder && <span className="bg-slate-100 px-1.5 rounded mr-1">{r.folder}</span>}
                </span>
                <span>
                  {fmtDate(r.timestamp)} · distance {r.distance?.toFixed(3)}
                </span>
              </div>
              <div className="font-medium mt-1">{r.subject || "(bez tematu)"}</div>
              {r.snippet && <div className="text-sm text-slate-600 mt-1">{r.snippet}</div>}
            </Link>
          ))}
        {submittedQ && !loading && items.length === 0 && semanticItems.length === 0 && (
          <div className="text-slate-500 text-sm">Brak wyników dla „{submittedQ}".</div>
        )}
      </div>
    </div>
  );
}
