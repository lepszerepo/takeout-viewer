import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { httpGet } from "../api";

interface Topic {
  id: number;
  cluster_id: number;
  label: string | null;
  size: number;
  algorithm: string;
}

interface TopicMail {
  id: number;
  event_id: number;
  subject: string | null;
  folder: string | null;
  has_attachments: boolean;
}

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selected, setSelected] = useState<Topic | null>(null);
  const [mails, setMails] = useState<TopicMail[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = () =>
    httpGet<Topic[]>(`/api/topics`).then(setTopics).catch(() => setTopics([]));

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selected) {
      setMails([]);
      return;
    }
    httpGet<{ items: TopicMail[] }>(`/api/topics/${selected.cluster_id}/mails?limit=100`)
      .then((d) => setMails(d.items))
      .catch(() => setMails([]));
  }, [selected]);

  const startBuild = async () => {
    setBusy(true);
    await fetch(`http://localhost:8001/api/topics/build`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ n_clusters: 40 }),
    });
    setTimeout(() => {
      refresh();
      setBusy(false);
    }, 2000);
  };

  const max = topics[0]?.size || 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Tematy (klastry semantyczne)</h2>
        <button
          onClick={startBuild}
          disabled={busy}
          className="px-3 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50"
        >
          {busy ? "Trwa..." : "▶︎ Zbuduj 40 tematów"}
        </button>
      </div>
      <div className="text-xs text-slate-500">
        K-means na 100k embeddingach + etykiety od Bielik 11B (lokalnie).
      </div>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-5 bg-white border border-slate-200 rounded overflow-y-auto max-h-[600px]">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left">Temat (AI)</th>
                <th className="px-3 py-2 text-right w-20">Rozmiar</th>
                <th className="px-3 py-2 w-32"></th>
              </tr>
            </thead>
            <tbody>
              {topics.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className={`border-t border-slate-100 cursor-pointer ${
                    selected?.id === t.id ? "bg-indigo-50" : "hover:bg-slate-50"
                  }`}
                >
                  <td className="px-3 py-2 truncate">
                    {t.label || <span className="text-slate-400">— bez etykiety —</span>}
                  </td>
                  <td className="px-3 py-2 text-right">{t.size.toLocaleString("pl-PL")}</td>
                  <td className="px-3 py-2">
                    <div className="h-2 bg-indigo-500 rounded" style={{ width: `${Math.max(2, (t.size / max) * 100)}%` }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="col-span-7 bg-white border border-slate-200 rounded p-3 overflow-y-auto max-h-[600px]">
          {!selected && <div className="text-slate-400 text-sm">Wybierz temat, aby zobaczyć maile.</div>}
          {selected && (
            <>
              <div className="font-medium mb-2">{selected.label}</div>
              <div className="text-xs text-slate-500 mb-3">
                klaster #{selected.cluster_id} · {selected.size.toLocaleString("pl-PL")} maili
              </div>
              <ul className="space-y-1 text-sm">
                {mails.map((m) => (
                  <li key={m.id} className="border-b border-slate-100 pb-1">
                    <Link to={`/mail?mail=${m.id}`} className="block hover:bg-slate-50 px-1 rounded">
                      <div className="flex justify-between text-xs text-slate-500">
                        <span>{m.folder}</span>
                        {m.has_attachments && <span>📎</span>}
                      </div>
                      <div className="truncate">{m.subject || "(bez tematu)"}</div>
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
