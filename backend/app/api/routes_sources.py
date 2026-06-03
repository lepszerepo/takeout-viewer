"""Source summaries and stats endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..labels import label_for_source, label_for_type
from ..schemas import SourceSummaryOut, StatsOut
from ..services.stats import overall_stats, per_source_summary

router = APIRouter(tags=["sources"])


@router.get("/api/sources", response_model=list[SourceSummaryOut])
def sources_list(
    dataset_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> list[SourceSummaryOut]:
    rows = per_source_summary(db, dataset_id=dataset_id)
    return [
        SourceSummaryOut(
            source=r["source"],
            label=label_for_source(r["source"]),
            events_count=r["events_count"],
            date_min=r["date_min"],
            date_max=r["date_max"],
            sample_types=[label_for_type(t) for t in r["sample_types"]],
        )
        for r in rows
    ]


@router.get("/api/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)) -> StatsOut:
    raw = overall_stats(db)
    raw["top_types"] = [
        {"type": t["type"], "label": label_for_type(t["type"]), "count": t["count"]}
        for t in raw["top_types"]
    ]
    return StatsOut(**raw)


@router.get("/api/labels")
def labels_endpoint() -> dict:
    from ..labels import EVENT_TYPE_LABELS, SOURCE_LABELS
    return {"types": EVENT_TYPE_LABELS, "sources": SOURCE_LABELS}
