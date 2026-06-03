import {
  DatasetOut,
  DiscoveredDataset,
  EventDetail,
  EventsPage,
  ImportBatchResultItem,
  ImportRunDetail,
  ImportRunOut,
  LabelsBundle,
  SourceSummaryOut,
  StatsOut,
} from "./types";

const API_BASE: string = (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail: string;
    try {
      const body = await res.json();
      detail = body?.detail ?? JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(detail || `Błąd HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => http<{ status: string }>("/health"),
  discoverDatasets: () => http<DiscoveredDataset[]>("/api/datasets/discover"),
  listDatasets: () => http<DatasetOut[]>("/api/datasets"),
  importDataset: (name: string) =>
    http<ImportRunOut>(`/api/datasets/${encodeURIComponent(name)}/import`, { method: "POST" }),
  importBatch: (names: string[]) =>
    http<{ results: ImportBatchResultItem[] }>(`/api/import/batch`, {
      method: "POST",
      body: JSON.stringify({ dataset_names: names }),
    }),
  listImportRuns: () => http<ImportRunOut[]>("/api/import-runs"),
  getImportRun: (id: number) => http<ImportRunDetail>(`/api/import-runs/${id}`),
  listEvents: (params: Record<string, string | number | boolean | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.append(k, String(v));
    });
    return http<EventsPage>(`/api/events?${qs.toString()}`);
  },
  getEvent: (id: number) => http<EventDetail>(`/api/events/${id}`),
  listSources: (datasetId?: number) =>
    http<SourceSummaryOut[]>(
      datasetId ? `/api/sources?dataset_id=${datasetId}` : `/api/sources`,
    ),
  stats: () => http<StatsOut>("/api/stats"),
  labels: () => http<LabelsBundle>("/api/labels"),
};

export async function httpGet<T>(path: string): Promise<T> {
  return http<T>(path);
}

export const API_BASE_URL = API_BASE;
