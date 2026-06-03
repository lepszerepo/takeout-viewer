"""Import endpoints (per-dataset and batch)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..importer.importer import import_dataset
from ..importer.paths import UnsafeDatasetName
from ..models import Dataset, ImportError as ImportErrorRow, ImportRun
from ..schemas import (
    ImportBatchRequest,
    ImportBatchResult,
    ImportBatchResultItem,
    ImportErrorOut,
    ImportRunDetail,
    ImportRunOut,
)

router = APIRouter(tags=["imports"])


def _run_to_out(run: ImportRun, dataset_name: str | None) -> ImportRunOut:
    return ImportRunOut(
        id=run.id,
        dataset_id=run.dataset_id,
        dataset_name=dataset_name,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        scanned_files_count=run.scanned_files_count,
        supported_files_count=run.supported_files_count,
        imported_events_count=run.imported_events_count,
        duplicate_events_count=run.duplicate_events_count,
        error_count=run.error_count,
        summary=run.summary,
    )


@router.post("/api/datasets/{dataset_name}/import", response_model=ImportRunOut)
def import_one(dataset_name: str, db: Session = Depends(get_db)) -> ImportRunOut:
    try:
        run = import_dataset(db, dataset_name)
    except UnsafeDatasetName as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _run_to_out(run, dataset_name)


@router.post("/api/import/batch", response_model=ImportBatchResult)
def import_many(body: ImportBatchRequest, db: Session = Depends(get_db)) -> ImportBatchResult:
    results: list[ImportBatchResultItem] = []
    for name in body.dataset_names:
        try:
            run = import_dataset(db, name)
            results.append(
                ImportBatchResultItem(
                    dataset_name=name,
                    status=run.status,
                    imported=run.imported_events_count,
                    duplicates=run.duplicate_events_count,
                    errors=run.error_count,
                    import_run_id=run.id,
                )
            )
        except UnsafeDatasetName as exc:
            results.append(
                ImportBatchResultItem(
                    dataset_name=name,
                    status="rejected",
                    message=str(exc),
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                ImportBatchResultItem(
                    dataset_name=name,
                    status="failed",
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
    return ImportBatchResult(results=results)


@router.get("/api/import-runs", response_model=list[ImportRunOut])
def list_runs(db: Session = Depends(get_db)) -> list[ImportRunOut]:
    runs = (
        db.query(ImportRun)
        .order_by(ImportRun.started_at.desc())
        .limit(200)
        .all()
    )
    ds_names = {ds.id: ds.name for ds in db.query(Dataset).all()}
    return [_run_to_out(r, ds_names.get(r.dataset_id)) for r in runs]


@router.get("/api/import-runs/{run_id}", response_model=ImportRunDetail)
def get_run(run_id: int, db: Session = Depends(get_db)) -> ImportRunDetail:
    run = db.get(ImportRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono uruchomienia importu.")
    ds = db.get(Dataset, run.dataset_id) if run.dataset_id else None

    errors = (
        db.query(ImportErrorRow)
        .filter_by(import_run_id=run.id)
        .order_by(ImportErrorRow.created_at.asc())
        .limit(500)
        .all()
    )
    summary = {}
    if run.summary:
        try:
            summary = json.loads(run.summary)
        except (TypeError, ValueError):
            summary = {}

    return ImportRunDetail(
        id=run.id,
        dataset_id=run.dataset_id,
        dataset_name=ds.name if ds else None,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        scanned_files_count=run.scanned_files_count,
        supported_files_count=run.supported_files_count,
        imported_events_count=run.imported_events_count,
        duplicate_events_count=run.duplicate_events_count,
        error_count=run.error_count,
        summary=run.summary,
        errors=[ImportErrorOut.model_validate(e) for e in errors],
        unsupported_types=summary.get("unsupported_types", []),
    )
