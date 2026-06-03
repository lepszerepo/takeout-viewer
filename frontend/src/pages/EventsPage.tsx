import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import Empty from "../components/Empty";
import EventCard from "../components/EventCard";
import EventDetailsDrawer from "../components/EventDetailsDrawer";
import Filters, { FiltersState } from "../components/Filters";
import { EventsPage as EventsPageDto, LabelsBundle } from "../types";

const PAGE_SIZE = 50;

export default function EventsPage() {
  const [filters, setFilters] = useState<FiltersState>({ include_duplicates: false });
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<EventsPageDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [labels, setLabels] = useState<LabelsBundle>({ types: {}, sources: {} });
  const [openId, setOpenId] = useState<number | null>(null);

  useEffect(() => {
    api.labels().then(setLabels).catch(() => setLabels({ types: {}, sources: {} }));
  }, []);

  const params = useMemo(
    () => ({
      ...filters,
      limit: PAGE_SIZE,
      offset,
    }),
    [filters, offset],
  );

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .listEvents(params as any)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [params]);

  useEffect(() => {
    setOffset(0);
  }, [filters]);

  const typeLabel = (t?: string | null) => (t && labels.types[t]) || t || "Inne";
  const sourceLabel = (s?: string | null) => (s && labels.sources[s]) || s || "Inne";

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Oś czasu</h2>
      <Filters
        value={filters}
        onChange={setFilters}
        typeLabels={labels.types}
        sourceLabels={labels.sources}
      />
      {error && (
        <div className="bg-rose-50 text-rose-800 border border-rose-200 rounded px-3 py-2 text-sm">
          {error}
        </div>
      )}
      {loading && <div className="text-slate-500 text-sm">Ładowanie...</div>}
      {!loading && data && data.items.length === 0 && (
        <Empty
          title="Brak wyników"
          hint={"Spróbuj zmienić filtry lub zaimportuj nowy zrzut Google Takeout."}
        />
      )}
      {data && data.items.length > 0 && (
        <>
          <div className="text-xs text-slate-500">
            Wyświetlono {data.items.length} z {data.total} zdarzeń
          </div>
          <div className="space-y-2">
            {data.items.map((e) => (
              <EventCard
                key={e.id}
                event={e}
                typeLabel={typeLabel}
                sourceLabel={sourceLabel}
                onOpen={() => setOpenId(e.id)}
              />
            ))}
          </div>
          <div className="flex items-center justify-between pt-2">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="px-3 py-1.5 border border-slate-300 rounded text-sm disabled:opacity-40"
            >
              ← Poprzednie
            </button>
            <div className="text-xs text-slate-500">
              strona {Math.floor(offset / PAGE_SIZE) + 1} z{" "}
              {Math.max(1, Math.ceil(data.total / PAGE_SIZE))}
            </div>
            <button
              disabled={offset + PAGE_SIZE >= data.total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="px-3 py-1.5 border border-slate-300 rounded text-sm disabled:opacity-40"
            >
              Następne →
            </button>
          </div>
        </>
      )}
      <EventDetailsDrawer
        eventId={openId}
        onClose={() => setOpenId(null)}
        typeLabel={typeLabel}
        sourceLabel={sourceLabel}
      />
    </div>
  );
}
