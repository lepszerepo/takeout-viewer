import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { httpGet } from "../api";
import { DatasetOut } from "../types";
import { FolderCount, MailDetail, MailListItem } from "../types_mail";

function fmtDate(s?: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return s;
  }
}

function addrsLabel(addrs: { name?: string; email: string }[] | null | undefined): string {
  if (!addrs || !addrs.length) return "(brak)";
  return addrs
    .map((a) => (a.name && a.name !== a.email ? `${a.name} <${a.email}>` : a.email))
    .join(", ");
}

const PAGE_SIZE = 50;

export default function MailPage() {
  const [searchParams] = useSearchParams();
  const [datasets, setDatasets] = useState<DatasetOut[]>([]);
  const [datasetId, setDatasetId] = useState<number | undefined>(undefined);
  const [folders, setFolders] = useState<FolderCount[]>([]);
  const [folder, setFolder] = useState<string | undefined>(undefined);
  const [query, setQuery] = useState("");
  const [address, setAddress] = useState("");
  const [hasAttachments, setHasAttachments] = useState(false);

  const [messages, setMessages] = useState<MailListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<MailDetail | null>(null);
  const [showHtml, setShowHtml] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiCategory, setAiCategory] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);

  useEffect(() => {
    httpGet<DatasetOut[]>(`/api/datasets`).then(setDatasets).catch(() => setDatasets([]));
  }, []);

  // Deep-link support: ?mail=<id> opens that message directly;
  //                    ?event=<id> resolves to mail by event_id
  useEffect(() => {
    const mid = searchParams.get("mail");
    const eid = searchParams.get("event");
    if (mid) {
      const n = parseInt(mid, 10);
      if (!Number.isNaN(n)) setSelectedId(n);
      return;
    }
    if (eid) {
      httpGet<{ mail_id: number }>(`/api/mail/by_event/${eid}`)
        .then((r) => setSelectedId(r.mail_id))
        .catch(() => {});
    }
  }, [searchParams]);

  useEffect(() => {
    const qs = datasetId ? `?dataset_id=${datasetId}` : "";
    httpGet<FolderCount[]>(`/api/mail/folders${qs}`).then(setFolders).catch(() => setFolders([]));
  }, [datasetId]);

  const params = useMemo(() => {
    const p = new URLSearchParams();
    if (datasetId) p.set("dataset_id", String(datasetId));
    if (folder) p.set("folder", folder);
    if (query) p.set("q", query);
    if (address) p.set("address", address);
    if (hasAttachments) p.set("has_attachments", "true");
    p.set("limit", String(PAGE_SIZE));
    p.set("offset", String(offset));
    return p.toString();
  }, [datasetId, folder, query, address, hasAttachments, offset]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    httpGet<{ total: number; items: MailListItem[] }>(`/api/mail/messages?${params}`)
      .then((d) => {
        setMessages(d.items);
        setTotal(d.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [params]);

  useEffect(() => setOffset(0), [datasetId, folder, query, address, hasAttachments]);

  useEffect(() => {
    if (selectedId == null) {
      setDetail(null);
      setAiSummary(null);
      setAiCategory(null);
      return;
    }
    setAiSummary(null);
    setAiCategory(null);
    httpGet<MailDetail>(`/api/mail/messages/${selectedId}`)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [selectedId]);

  const runAi = async (kind: "summary" | "classify") => {
    if (selectedId == null) return;
    setAiBusy(true);
    try {
      const url =
        kind === "summary" ? `/api/llm/summary/${selectedId}` : `/api/llm/classify/${selectedId}`;
      const res = await fetch(`http://localhost:8001${url}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (kind === "summary") setAiSummary(data.summary);
      else setAiCategory(data.category);
    } catch (e: any) {
      setError(`LLM: ${e.message}`);
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-12 gap-3 h-[calc(100vh-180px)]">
      {/* Sidebar: datasets + folders */}
      <aside className="col-span-2 bg-white border border-slate-200 rounded-lg p-3 overflow-y-auto text-sm">
        <div className="font-medium mb-2 text-slate-700">Zrzut</div>
        <select
          value={datasetId ?? ""}
          onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : undefined)}
          className="w-full border border-slate-300 rounded px-2 py-1 mb-3"
        >
          <option value="">— wszystkie —</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>

        <div className="font-medium mb-2 text-slate-700">Foldery</div>
        <button
          onClick={() => setFolder(undefined)}
          className={`block w-full text-left px-2 py-1 rounded ${
            !folder ? "bg-slate-900 text-white" : "hover:bg-slate-100"
          }`}
        >
          Wszystkie ({folders.reduce((a, b) => a + b.count, 0)})
        </button>
        {folders.map((f) => (
          <button
            key={f.folder}
            onClick={() => setFolder(f.folder)}
            className={`block w-full text-left px-2 py-1 rounded mt-1 ${
              folder === f.folder ? "bg-slate-900 text-white" : "hover:bg-slate-100"
            }`}
          >
            {f.folder} ({f.count})
          </button>
        ))}
      </aside>

      {/* Message list */}
      <section className="col-span-4 bg-white border border-slate-200 rounded-lg flex flex-col overflow-hidden">
        <div className="p-2 border-b border-slate-200 space-y-1">
          <input
            type="text"
            placeholder="Szukaj w tematach..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
          />
          <div className="flex gap-1">
            <input
              type="text"
              placeholder="Adres e-mail..."
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="flex-1 border border-slate-300 rounded px-2 py-1 text-xs"
            />
            <label className="flex items-center text-xs gap-1 px-2">
              <input
                type="checkbox"
                checked={hasAttachments}
                onChange={(e) => setHasAttachments(e.target.checked)}
              />
              <span>Załączniki</span>
            </label>
          </div>
        </div>
        <div className="text-xs px-2 py-1 text-slate-500 border-b border-slate-100">
          {loading ? "ładowanie..." : `${total.toLocaleString("pl-PL")} wiadomości`}
        </div>
        <div className="flex-1 overflow-y-auto">
          {error && <div className="p-2 text-rose-700 text-sm">{error}</div>}
          {messages.map((m) => (
            <button
              key={m.id}
              onClick={() => setSelectedId(m.id)}
              className={`w-full text-left px-3 py-2 border-b border-slate-100 ${
                selectedId === m.id ? "bg-slate-100" : "hover:bg-slate-50"
              }`}
            >
              <div className="flex justify-between items-center text-xs text-slate-500">
                <span className="truncate">
                  {(m.from && m.from[0]?.name) ||
                    (m.from && m.from[0]?.email) ||
                    "—"}
                </span>
                <span>{fmtDate(m.timestamp)}</span>
              </div>
              <div className="text-sm font-medium truncate">{m.subject || "(bez tematu)"}</div>
              <div className="text-xs text-slate-500 truncate">{m.snippet}</div>
              <div className="flex gap-1 mt-1">
                {m.has_attachments && (
                  <span className="bg-amber-50 text-amber-700 text-[10px] rounded px-1.5">📎</span>
                )}
                <span className="bg-slate-100 text-slate-600 text-[10px] rounded px-1.5">
                  {m.dataset_name}
                </span>
                <span className="bg-indigo-50 text-indigo-700 text-[10px] rounded px-1.5">
                  {m.folder}
                </span>
              </div>
            </button>
          ))}
        </div>
        <div className="border-t border-slate-200 p-2 flex justify-between text-xs">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
            className="px-2 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            ← Poprzednie
          </button>
          <span className="text-slate-500">
            strona {Math.floor(offset / PAGE_SIZE) + 1} / {Math.max(1, Math.ceil(total / PAGE_SIZE))}
          </span>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
            className="px-2 py-1 border border-slate-300 rounded disabled:opacity-40"
          >
            Następne →
          </button>
        </div>
      </section>

      {/* Detail */}
      <section className="col-span-6 bg-white border border-slate-200 rounded-lg overflow-y-auto">
        {!detail && <div className="p-6 text-slate-400 text-sm">Wybierz wiadomość, aby zobaczyć treść.</div>}
        {detail && (
          <div className="p-4 space-y-3">
            <div>
              <div className="text-lg font-semibold text-slate-900">
                {detail.subject || "(bez tematu)"}
              </div>
              <div className="text-xs text-slate-500 mt-1 space-y-0.5">
                <div>
                  <span className="font-medium text-slate-600">Od:</span> {addrsLabel(detail.from)}
                </div>
                <div>
                  <span className="font-medium text-slate-600">Do:</span> {addrsLabel(detail.to)}
                </div>
                {detail.cc && detail.cc.length > 0 && (
                  <div>
                    <span className="font-medium text-slate-600">DW:</span> {addrsLabel(detail.cc)}
                  </div>
                )}
                <div>
                  <span className="font-medium text-slate-600">Data:</span> {fmtDate(detail.timestamp)}{" "}
                  · <span className="font-medium text-slate-600">Folder:</span> {detail.folder}
                </div>
                {detail.labels && detail.labels.length > 0 && (
                  <div>
                    <span className="font-medium text-slate-600">Etykiety:</span>{" "}
                    {detail.labels.map((l) => (
                      <span key={l} className="inline-block bg-indigo-50 text-indigo-700 rounded px-1.5 mr-1">
                        {l}
                      </span>
                    ))}
                  </div>
                )}
                <div>
                  <span className="font-medium text-slate-600">Występuje u:</span>{" "}
                  {detail.datasets.map((d) => (
                    <span key={d} className="inline-block bg-slate-100 rounded px-1.5 mr-1">
                      {d}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {detail.attachments && detail.attachments.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded p-2 text-xs">
                <div className="font-medium text-amber-900 mb-1">Załączniki ({detail.attachments.length})</div>
                <ul className="space-y-0.5">
                  {detail.attachments.map((a: any, i) => {
                    const hasFile = !!a.sha256;
                    const href = `http://localhost:8001/api/mail/messages/${detail.id}/attachments/${i}`;
                    return (
                      <li key={i} className="flex justify-between items-center gap-2">
                        <span className="truncate flex-1">📎 {a.name}</span>
                        <span className="text-amber-700 whitespace-nowrap">
                          {a.size ? `${Math.round((a.size || 0) / 1024)} KB` : ""}
                        </span>
                        {hasFile ? (
                          <a
                            href={href}
                            download={a.name}
                            className="text-indigo-700 underline whitespace-nowrap"
                          >
                            Pobierz
                          </a>
                        ) : (
                          <span className="text-slate-400 whitespace-nowrap">brak treści</span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            <div className="flex gap-2 text-xs items-center flex-wrap">
              <button
                onClick={() => setShowHtml(false)}
                className={`px-2 py-1 rounded ${!showHtml ? "bg-slate-900 text-white" : "border border-slate-300"}`}
              >
                Tekst
              </button>
              {detail.body_html && (
                <button
                  onClick={() => setShowHtml(true)}
                  className={`px-2 py-1 rounded ${showHtml ? "bg-slate-900 text-white" : "border border-slate-300"}`}
                >
                  HTML
                </button>
              )}
              <span className="text-slate-300">|</span>
              <button
                onClick={() => runAi("summary")}
                disabled={aiBusy}
                className="px-2 py-1 rounded bg-indigo-600 text-white disabled:opacity-50"
              >
                ✨ Streszczenie AI
              </button>
              <button
                onClick={() => runAi("classify")}
                disabled={aiBusy}
                className="px-2 py-1 rounded border border-indigo-300 text-indigo-700 disabled:opacity-50"
              >
                🏷️ Kategoria AI
              </button>
              {aiCategory && (
                <span className="bg-indigo-50 text-indigo-700 rounded px-2 py-1">
                  {aiCategory}
                </span>
              )}
            </div>
            {aiBusy && <div className="text-xs text-slate-500">Analizuję lokalnie (Bielik 11b)...</div>}
            {aiSummary && (
              <div className="bg-indigo-50 border border-indigo-200 rounded p-3 text-sm">
                <div className="font-medium text-indigo-900 mb-1">Streszczenie (Bielik 11b, lokalnie)</div>
                <div className="whitespace-pre-wrap text-slate-800">{aiSummary}</div>
              </div>
            )}

            <div className="border-t border-slate-200 pt-3">
              {showHtml && detail.body_html ? (
                <iframe
                  title="Mail body"
                  srcDoc={detail.body_html}
                  sandbox=""
                  className="w-full min-h-[400px] bg-white border border-slate-200 rounded"
                />
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-800">
                  {detail.body_text || "(brak treści tekstowej)"}
                </pre>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
