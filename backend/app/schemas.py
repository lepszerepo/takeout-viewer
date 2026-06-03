"""Pydantic schemas for API I/O."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class DiscoveredDataset(BaseModel):
    name: str
    relative_path: str
    is_known: bool
    last_imported_at: Optional[datetime] = None
    status: Optional[str] = None
    events_count: int = 0
    errors_count: int = 0
    duplicates_count: int = 0


class DatasetOut(BaseModel):
    id: int
    name: str
    relative_path: str
    created_at: datetime
    last_imported_at: Optional[datetime]
    status: str
    events_count: int = 0
    date_min: Optional[datetime] = None
    date_max: Optional[datetime] = None

    class Config:
        from_attributes = True


class ImportRunOut(BaseModel):
    id: int
    dataset_id: Optional[int]
    dataset_name: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    scanned_files_count: int
    supported_files_count: int
    imported_events_count: int
    duplicate_events_count: int
    error_count: int
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class ImportErrorOut(BaseModel):
    id: int
    relative_path: Optional[str]
    parser: Optional[str]
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class ImportRunDetail(ImportRunOut):
    errors: List[ImportErrorOut] = []
    unsupported_types: List[str] = []


class EventOut(BaseModel):
    id: int
    source: str
    service: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    url: Optional[str] = None
    people: Optional[Any] = None
    location: Optional[Any] = None
    metadata: Optional[Any] = None
    raw_path: Optional[str] = None
    dataset_id: int
    dataset_name: str
    datasets: List[str] = []
    is_duplicate_across_datasets: bool = False

    class Config:
        from_attributes = True


class EventDetail(EventOut):
    raw_json: Optional[Any] = None


class EventsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[EventOut]


class ImportBatchRequest(BaseModel):
    dataset_names: List[str] = Field(default_factory=list)


class ImportBatchResultItem(BaseModel):
    dataset_name: str
    status: str
    imported: int = 0
    duplicates: int = 0
    errors: int = 0
    message: Optional[str] = None
    import_run_id: Optional[int] = None


class ImportBatchResult(BaseModel):
    results: List[ImportBatchResultItem]


class SourceSummaryOut(BaseModel):
    source: str
    label: str
    events_count: int
    date_min: Optional[datetime] = None
    date_max: Optional[datetime] = None
    sample_types: List[str] = []


class StatsOut(BaseModel):
    datasets_count: int
    events_count: int
    unique_events_count: int
    date_min: Optional[datetime] = None
    date_max: Optional[datetime] = None
    top_types: List[dict] = []
    activity_by_month: List[dict] = []
    per_dataset: List[dict] = []
