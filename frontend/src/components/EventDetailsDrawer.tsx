import { useEffect, useState } from "react";
import { api } from "../api";
import { EventDetail } from "../types";

interface Props {
  eventId: number | null;
  onClose: () => void;
  typeLabel: (t?: string | null) => string;
  sourceLabel: (s?: string | null) => string;
}

function fmt(d?: string | null) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("pl-PL");
  } catch {
    return d;
  }
}

export default function EventDetailsDrawer({ eventId, onClose, typeLabel, sourceLabel }: Props) {
  const [data, setData] = useState<EventDetail | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setShowRaw(false);
    setError(null);
    if (eventId == null) return;
    api
      .getEvent(eventId)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [eventId]);

  if (eventId == null) return null;

  return (
    <div className="fixed inset-0 z-30 flex">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div className="ml-auto w-full max-w-xl bg-white shadow-xl h-full overflow-y-auto relative">
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <div className="font-medium">Szczegóły zdarzenia</div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-900">✕</button>
        </div>
        <div className="p-4 space-y-3">
          {error && <div className="text-rose-600 text-sm">{error}</div>}
          {!data && !error && <div className="text-slate-500">Ładowanie...</div>}
          {data && (
            <>
              <div>
                <div className="text-xs text-slate-500">Tytuł</div>
                <div className="font-medium">{data.title || "(brak)"}</div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <Field label="Źródło" value={sourceLabel(data.source)} />
                <Field label="Typ" value={typeLabel(data.type)} />
                <Field label="Czas początku" value={fmt(data.timestamp)} />
                <Field label="Czas końca" value={fmt(data.end_timestamp)} />
                <Field label="Kategoria" value={data.category || "—"} />
                <Field label="Usługa" value={data.service || "—"} />
              </div>
              {data.url && (
                <div>
                  <div className="text-xs text-slate-500">Link</div>
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:underline break-all"
                  >
                    {data.url}
                  </a>
                </div>
              )}
              {data.description && (
                <div>
                  <div className="text-xs text-slate-500">Opis</div>
                  <div className="text-sm whitespace-pre-wrap">{data.description}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-slate-500">Występuje w zrzutach</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {data.datasets.map((d) => (
                    <span key={d} className="bg-slate-100 px-2 py-0.5 rounded text-xs">{d}</span>
                  ))}
                </div>
              </div>
              {!!data.metadata && (
                <Field
                  label="Metadane"
                  value={<pre className="bg-slate-50 p-2 rounded text-xs whitespace-pre-wrap">{JSON.stringify(data.metadata, null, 2)}</pre>}
                />
              )}
              {!!data.location && (
                <Field
                  label="Lokalizacja"
                  value={<pre className="bg-slate-50 p-2 rounded text-xs whitespace-pre-wrap">{JSON.stringify(data.location, null, 2)}</pre>}
                />
              )}
              {!!data.people && (
                <Field
                  label="Osoby"
                  value={<pre className="bg-slate-50 p-2 rounded text-xs whitespace-pre-wrap">{JSON.stringify(data.people, null, 2)}</pre>}
                />
              )}
              <div className="pt-2 border-t border-slate-200">
                <button
                  onClick={() => setShowRaw((v) => !v)}
                  className="text-sm text-slate-600 hover:text-slate-900 underline"
                >
                  {showRaw ? "Ukryj dane techniczne" : "Pokaż dane techniczne"}
                </button>
                {showRaw && (
                  <pre className="mt-2 bg-slate-900 text-slate-100 text-xs p-3 rounded overflow-x-auto">
{JSON.stringify(
  {
    id: data.id,
    source: data.source,
    type: data.type,
    raw_path: data.raw_path,
    raw_json: data.raw_json ?? "(brak zapisanego rekordu źródłowego)",
  },
  null,
  2,
)}
                  </pre>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-slate-900">{value}</div>
    </div>
  );
}
