"""Dataset discovery & listing endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..importer.scanner import list_datasets
from ..models import Dataset, Event, EventDatasetLink, ImportRun
from ..schemas import DatasetOut, DiscoveredDataset

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/discover", response_model=list[DiscoveredDataset])
def discover_datasets(db: Session = Depends(get_db)) -> list[DiscoveredDataset]:
    on_disk = list_datasets()
    known = {ds.name: ds for ds in db.query(Dataset).all()}

    # Counts per dataset
    count_rows = (
        db.query(EventDatasetLink.dataset_id, func.count(EventDatasetLink.id))
        .group_by(EventDatasetLink.dataset_id)
        .all()
    )
    count_map = {ds_id: c for ds_id, c in count_rows}

    out: list[DiscoveredDataset] = []
    seen_names: set[str] = set()
    for p in on_disk:
        ds = known.get(p.name)
        seen_names.add(p.name)
        events_count = count_map.get(ds.id, 0) if ds else 0
        errs = 0
        dups = 0
        if ds:
            last_run = (
                db.query(ImportRun)
                .filter_by(dataset_id=ds.id)
                .order_by(ImportRun.started_at.desc())
                .first()
            )
            if last_run:
                errs = last_run.error_count
                dups = last_run.duplicate_events_count
        out.append(
            DiscoveredDataset(
                name=p.name,
                relative_path=p.name,
                is_known=ds is not None,
                last_imported_at=ds.last_imported_at if ds else None,
                status=ds.status if ds else None,
                events_count=events_count,
                errors_count=errs,
                duplicates_count=dups,
            )
        )

    # Known datasets that no longer exist on disk
    for name, ds in known.items():
        if name in seen_names:
            continue
        out.append(
            DiscoveredDataset(
                name=name,
                relative_path=name,
                is_known=True,
                last_imported_at=ds.last_imported_at,
                status=f"{ds.status} (brak katalogu)",
                events_count=count_map.get(ds.id, 0),
            )
        )

    out.sort(key=lambda d: d.name)
    return out


@router.get("", response_model=list[DatasetOut])
def list_known_datasets(db: Session = Depends(get_db)) -> list[DatasetOut]:
    datasets = db.query(Dataset).order_by(Dataset.name).all()

    count_rows = (
        db.query(EventDatasetLink.dataset_id, func.count(EventDatasetLink.id))
        .group_by(EventDatasetLink.dataset_id)
        .all()
    )
    count_map = {ds_id: c for ds_id, c in count_rows}

    out: list[DatasetOut] = []
    for ds in datasets:
        dmin, dmax = (
            db.query(func.min(Event.timestamp), func.max(Event.timestamp))
            .join(EventDatasetLink, EventDatasetLink.event_id == Event.id)
            .filter(EventDatasetLink.dataset_id == ds.id)
            .one()
        )
        out.append(
            DatasetOut(
                id=ds.id,
                name=ds.name,
                relative_path=ds.relative_path,
                created_at=ds.created_at,
                last_imported_at=ds.last_imported_at,
                status=ds.status,
                events_count=count_map.get(ds.id, 0),
                date_min=dmin,
                date_max=dmax,
            )
        )
    return out


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> DatasetOut:
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono zrzutu.")
    count = (
        db.query(func.count(EventDatasetLink.id))
        .filter_by(dataset_id=ds.id)
        .scalar()
        or 0
    )
    dmin, dmax = (
        db.query(func.min(Event.timestamp), func.max(Event.timestamp))
        .join(EventDatasetLink, EventDatasetLink.event_id == Event.id)
        .filter(EventDatasetLink.dataset_id == ds.id)
        .one()
    )
    return DatasetOut(
        id=ds.id,
        name=ds.name,
        relative_path=ds.relative_path,
        created_at=ds.created_at,
        last_imported_at=ds.last_imported_at,
        status=ds.status,
        events_count=count,
        date_min=dmin,
        date_max=dmax,
    )
