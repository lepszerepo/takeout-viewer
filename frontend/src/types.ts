export interface DiscoveredDataset {
  name: string;
  relative_path: string;
  is_known: boolean;
  last_imported_at: string | null;
  status: string | null;
  events_count: number;
  errors_count: number;
  duplicates_count: number;
}

export interface DatasetOut {
  id: number;
  name: string;
  relative_path: string;
  created_at: string;
  last_imported_at: string | null;
  status: string;
  events_count: number;
  date_min: string | null;
  date_max: string | null;
}

export interface ImportRunOut {
  id: number;
  dataset_id: number | null;
  dataset_name: string | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  scanned_files_count: number;
  supported_files_count: number;
  imported_events_count: number;
  duplicate_events_count: number;
  error_count: number;
  summary: string | null;
}

export interface ImportErrorOut {
  id: number;
  relative_path: string | null;
  parser: string | null;
  message: string;
  created_at: string;
}

export interface ImportRunDetail extends ImportRunOut {
  errors: ImportErrorOut[];
  unsupported_types: string[];
}

export interface EventOut {
  id: number;
  source: string;
  service?: string | null;
  category?: string | null;
  type?: string | null;
  title?: string | null;
  description?: string | null;
  timestamp?: string | null;
  end_timestamp?: string | null;
  url?: string | null;
  people?: unknown;
  location?: unknown;
  metadata?: unknown;
  raw_path?: string | null;
  dataset_id: number;
  dataset_name: string;
  datasets: string[];
  is_duplicate_across_datasets: boolean;
}

export interface EventDetail extends EventOut {
  raw_json?: unknown;
}

export interface EventsPage {
  total: number;
  limit: number;
  offset: number;
  items: EventOut[];
}

export interface SourceSummaryOut {
  source: string;
  label: string;
  events_count: number;
  date_min: string | null;
  date_max: string | null;
  sample_types: string[];
}

export interface StatsOut {
  datasets_count: number;
  events_count: number;
  unique_events_count: number;
  date_min: string | null;
  date_max: string | null;
  top_types: { type: string; label?: string; count: number }[];
  activity_by_month: { month: string; count: number }[];
  per_dataset: { dataset_id: number; dataset_name: string; events_count: number }[];
}

export interface ImportBatchResultItem {
  dataset_name: string;
  status: string;
  imported: number;
  duplicates: number;
  errors: number;
  message?: string | null;
  import_run_id?: number | null;
}

export interface LabelsBundle {
  types: Record<string, string>;
  sources: Record<string, string>;
}
