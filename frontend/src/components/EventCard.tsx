import { EventOut } from "../types";

interface Props {
  event: EventOut;
  typeLabel: (t?: string | null) => string;
  sourceLabel: (s?: string | null) => string;
  onOpen: () => void;
}

function fmt(d?: string | null) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("pl-PL");
  } catch {
    return d;
  }
}

export default function EventCard({ event, typeLabel, sourceLabel, onOpen }: Props) {
  return (
    <button
      onClick={onOpen}
      className="w-full text-left bg-white border border-slate-200 rounded-lg p-3 hover:border-slate-400 hover:shadow-sm transition flex gap-3"
    >
      <div className="flex flex-col items-center pt-1 min-w-[80px]">
        <div className="text-xs text-slate-500">{fmt(event.timestamp).split(",")[0]}</div>
        <div className="text-xs text-slate-400">{fmt(event.timestamp).split(",")[1] ?? ""}</div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-xs mb-1">
          <span className="inline-block px-2 py-0.5 bg-slate-100 text-slate-700 rounded">
            {sourceLabel(event.source)}
          </span>
          <span className="inline-block px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
            {typeLabel(event.type)}
          </span>
          {event.is_duplicate_across_datasets && (
            <span className="inline-block px-2 py-0.5 bg-amber-50 text-amber-700 rounded">
              Duplikat między zrzutami
            </span>
          )}
        </div>
        <div className="font-medium text-slate-900 truncate">{event.title || "(bez tytułu)"}</div>
        {event.description && (
          <div className="text-sm text-slate-600 mt-1 line-clamp-2">{event.description}</div>
        )}
        <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
          <span>Zrzuty:</span>
          {event.datasets.map((d) => (
            <span key={d} className="bg-slate-100 px-1.5 py-0.5 rounded">{d}</span>
          ))}
        </div>
      </div>
    </button>
  );
}
