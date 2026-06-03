import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { httpGet } from "../api";

interface Profile {
  email: string;
  mail: { sent: number; received: number; threads: number };
  top_correspondents: { email: string; count: number }[];
  top_domains: { domain: string; count: number }[];
  activity_heatmap: { dow: number; hour: number; count: number }[];
  activity_by_month: { month: string; count: number }[];
  ner_mentions_as_email: number;
  person_entities: { id: number; label: string; count: number }[];
}

const DOW_LABELS = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nie"];

function Heatmap({ data }: { data: Profile["activity_heatmap"] }) {
  const max = data.reduce((m, c) => Math.max(m, c.count), 0) || 1;
  const grid: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
  data.forEach((c) => {
    grid[c.dow][c.hour] = c.count;
  });
  return (
    <div className="bg-white border border-slate-200 rounded p-3">
      <div className="text-xs text-slate-500 mb-2">
        Aktywność (dzień tygodnia × godzina) — kolor proporcjonalny do liczby
      </div>
      <div className="inline-block">
        <div className="flex">
          <div className="w-10"></div>
          {Array.from({ length: 24 }, (_, h) => (
            <div key={h} className="w-5 text-[10px] text-slate-400 text-center">
              {h % 6 === 0 ? h : ""}
            </div>
          ))}
        </div>
        {grid.map((row, dow) => (
          <div key={dow} className="flex items-center">
            <div className="w-10 text-xs text-slate-600">{DOW_LABELS[dow]}</div>
            {row.map((val, h) => {
              const opacity = max > 0 ? val / max : 0;
              return (
                <div
                  key={h}
                  title={`${DOW_LABELS[dow]} ${h}:00 — ${val}`}
                  className="w-5 h-5 m-px rounded-sm"
                  style={{
                    backgroundColor: `rgba(79, 70, 229, ${0.05 + opacity * 0.85})`,
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function MonthlyChart({ data }: { data: Profile["activity_by_month"] }) {
  if (!data.length) return null;
  const max = data.reduce((m, c) => Math.max(m, c.count), 0) || 1;
  return (
    <div className="bg-white border border-slate-200 rounded p-3">
      <div className="text-xs text-slate-500 mb-2">Aktywność miesięczna</div>
      <div className="flex items-end gap-px h-32">
        {data.map((m) => (
          <div key={m.month} title={`${m.month}: ${m.count}`} className="flex-1 bg-indigo-500" style={{ height: `${(m.count / max) * 100}%`, minHeight: 2 }} />
        ))}
      </div>
      <div className="text-xs text-slate-400 mt-1 flex justify-between">
        <span>{data[0]?.month}</span>
        <span>{data[data.length - 1]?.month}</span>
      </div>
    </div>
  );
}

export default function PersonPage() {
  const { email } = useParams<{ email: string }>();
  const [data, setData] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    setLoading(true);
    setError(null);
    httpGet<Profile>(`/api/person/${encodeURIComponent(email)}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [email]);

  if (loading) return <div className="text-slate-500">Ładuję profil...</div>;
  if (error) return <div className="text-rose-700">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold font-mono">{data.email}</h2>
        <div className="flex gap-2 text-sm">
          <Link to={`/graph?person=${encodeURIComponent(data.email)}`} className="text-indigo-700 underline">
            Pokaż graf →
          </Link>
          <Link to={`/mail?q=${encodeURIComponent(data.email)}`} className="text-indigo-700 underline">
            Maile →
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="text-xs text-slate-500">Wysłane</div>
          <div className="text-2xl font-semibold">{data.mail.sent.toLocaleString("pl-PL")}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="text-xs text-slate-500">Otrzymane</div>
          <div className="text-2xl font-semibold">{data.mail.received.toLocaleString("pl-PL")}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="text-xs text-slate-500">Wątki</div>
          <div className="text-2xl font-semibold">{data.mail.threads.toLocaleString("pl-PL")}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="text-xs text-slate-500">Wzmianki w treści</div>
          <div className="text-2xl font-semibold">{data.ner_mentions_as_email.toLocaleString("pl-PL")}</div>
        </div>
      </div>

      <Heatmap data={data.activity_heatmap} />
      <MonthlyChart data={data.activity_by_month} />

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="font-medium mb-2">Najczęstsi korespondenci</div>
          <ul className="text-sm space-y-1">
            {data.top_correspondents.map((c) => (
              <li key={c.email} className="flex justify-between">
                <Link to={`/person/${encodeURIComponent(c.email)}`} className="font-mono text-xs hover:underline">
                  {c.email}
                </Link>
                <span className="text-slate-500">{c.count}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="font-medium mb-2">Top domeny</div>
          <ul className="text-sm space-y-1">
            {data.top_domains.map((d) => (
              <li key={d.domain} className="flex justify-between">
                <span className="font-mono text-xs">{d.domain}</span>
                <span className="text-slate-500">{d.count}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {data.person_entities.length > 0 && (
        <div className="bg-white border border-slate-200 rounded p-3">
          <div className="font-medium mb-2">Dopasowane encje PERSON (z NER)</div>
          <ul className="text-sm">
            {data.person_entities.map((e) => (
              <li key={e.id}>
                <Link to={`/entities`} className="text-indigo-700 underline">
                  {e.label}
                </Link>
                <span className="text-slate-500 ml-2">{e.count} wzmianek</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
