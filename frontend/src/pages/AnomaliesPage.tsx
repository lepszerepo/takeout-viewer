import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { httpGet } from "../api";

type Tab = "off-hours" | "large-external" | "new-domains";

function fmtSize(b: number) {
  if (b >= 1_000_000) return `${(b / 1_000_000).toFixed(1)} MB`;
  if (b >= 1_000) return `${Math.round(b / 1_000)} KB`;
  return `${b} B`;
}

function fmtDate(s?: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("pl-PL");
  } catch {
    return s;
  }
}

export default function AnomaliesPage() {
  const [tab, setTab] = useState<Tab>("off-hours");
  const [data, setData] = useState<any>(null);
  const [domain, setDomain] = useState("zondacrypto.com");
  const [days, setDays] = useState(30);
  const [minSize, setMinSize] = useState(5_000_000);
  const [startHour, setStartHour] = useState(22);
  const [endHour, setEndHour] = useState(6);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    let url = "";
    if (tab === "off-hours") {
      url = `/api/anomalies/off-hours?start_hour=${startHour}&end_hour=${endHour}&limit=300`;
    } else if (tab === "large-external") {
      url = `/api/anomalies/large-external?min_size=${minSize}&internal_domain=${domain}&limit=200`;
    } else {
      url = `/api/anomalies/new-domains?days=${days}&internal_domain=${domain}&limit=200`;
    }
    httpGet<any>(url).then(setData).finally(() => setLoading(false));
  }, [tab, domain, days, minSize, startHour, endHour]);

  return (
    <div className="space-y-3">
      <h2 className="text-xl font-semibold">Sygnały / anomalie</h2>
      <div className="flex gap-2 flex-wrap">
        {[
          { k: "off-hours" as Tab, label: "Maile w nietypowych godzinach" },
          { k: "large-external" as Tab, label: "Duże załączniki na zewnątrz" },
          { k: "new-domains" as Tab, label: "Nowe domeny kontaktów" },
        ].map((t) => (
          <button
            key={t.k}
            onClick={() => setTab(t.k)}
            className={`px-3 py-1.5 rounded text-sm ${tab === t.k ? "bg-slate-900 text-white" : "border border-slate-300"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded p-3 flex gap-3 flex-wrap text-sm">
        <label>Domena wewnętrzna:&nbsp;
          <input value={domain} onChange={(e) => setDomain(e.target.value)} className="border border-slate-300 rounded px-2 py-1 font-mono" />
        </label>
        {tab === "off-hours" && (
          <>
            <label>Od:&nbsp;<input type="number" min={0} max={23} value={startHour} onChange={(e) => setStartHour(Number(e.target.value))} className="w-16 border border-slate-300 rounded px-2 py-1" /></label>
            <label>Do:&nbsp;<input type="number" min={0} max={23} value={endHour} onChange={(e) => setEndHour(Number(e.target.value))} className="w-16 border border-slate-300 rounded px-2 py-1" /></label>
          </>
        )}
        {tab === "large-external" && (
          <label>Min rozmiar (MB):&nbsp;
            <input type="number" min={0.1} step={0.1} value={minSize / 1_000_000} onChange={(e) => setMinSize(Number(e.target.value) * 1_000_000)} className="w-24 border border-slate-300 rounded px-2 py-1" />
          </label>
        )}
        {tab === "new-domains" && (
          <label>Okres (dni):&nbsp;
            <input type="number" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-20 border border-slate-300 rounded px-2 py-1" />
          </label>
        )}
      </div>

      {loading && <div className="text-slate-500 text-sm">Ładuję...</div>}

      {!loading && data && tab === "off-hours" && (
        <div className="bg-white border border-slate-200 rounded">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left">Czas</th>
                <th className="px-3 py-2 text-left">Od</th>
                <th className="px-3 py-2 text-left">Temat</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it: any) => (
                <tr key={it.mail_id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 whitespace-nowrap">{fmtDate(it.timestamp)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{(it.from || []).join(", ")}</td>
                  <td className="px-3 py-2"><Link to={`/mail?mail=${it.mail_id}`} className="text-indigo-700 hover:underline">{it.subject || "(brak)"}</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && data && tab === "large-external" && (
        <div className="bg-white border border-slate-200 rounded">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left">Rozmiar</th>
                <th className="px-3 py-2 text-left">Od → Do</th>
                <th className="px-3 py-2 text-left">Temat / załączniki</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it: any) => (
                <tr key={it.mail_id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 font-medium">{fmtSize(it.total_attachment_size)}</td>
                  <td className="px-3 py-2 text-xs">
                    <div className="font-mono">{(it.from || []).join(", ")}</div>
                    <div className="text-slate-500 font-mono">→ {(it.to || []).join(", ")}</div>
                  </td>
                  <td className="px-3 py-2">
                    <Link to={`/mail?mail=${it.mail_id}`} className="text-indigo-700 hover:underline">{it.subject || "(brak)"}</Link>
                    <div className="text-xs text-slate-500 mt-1">
                      {(it.attachments || []).map((a: any, i: number) => (
                        <span key={i} className="bg-amber-50 text-amber-700 rounded px-1.5 mr-1">{a.name} ({fmtSize(a.size || 0)})</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && data && tab === "new-domains" && (
        <div className="bg-white border border-slate-200 rounded">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left">Pierwszy raz</th>
                <th className="px-3 py-2 text-left">Domena</th>
                <th className="px-3 py-2 text-right">Wystąpień</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it: any) => (
                <tr key={it.domain} className="border-t border-slate-100">
                  <td className="px-3 py-2 whitespace-nowrap">{fmtDate(it.first_seen)}</td>
                  <td className="px-3 py-2 font-mono">{it.domain}</td>
                  <td className="px-3 py-2 text-right">{it.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
