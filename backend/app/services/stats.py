"""Aggregation helpers for /api/stats and source summaries."""
from __future__ import annotations

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from ..models import Dataset, Event, EventDatasetLink


def overall_stats(db: Session) -> dict:
    datasets_count = db.query(func.count(Dataset.id)).scalar() or 0
    events_count = db.query(func.count(Event.id)).scalar() or 0  # unique events
    links_count = db.query(func.count(EventDatasetLink.id)).scalar() or 0
    date_min, date_max = db.query(func.min(Event.timestamp), func.max(Event.timestamp)).one()

    top_types = (
        db.query(Event.type, func.count(Event.id))
        .group_by(Event.type)
        .order_by(func.count(Event.id).desc())
        .limit(10)
        .all()
    )

    # Activity by month — SQLite-only strftime; works fine for MVP.
    month_rows = (
        db.query(func.strftime("%Y-%m", Event.timestamp).label("ym"), func.count(Event.id))
        .filter(Event.timestamp.isnot(None))
        .group_by("ym")
        .order_by("ym")
        .all()
    )

    per_dataset = (
        db.query(
            Dataset.id,
            Dataset.name,
            func.count(distinct(EventDatasetLink.event_id)).label("events_count"),
        )
        .outerjoin(EventDatasetLink, EventDatasetLink.dataset_id == Dataset.id)
        .group_by(Dataset.id, Dataset.name)
        .order_by(Dataset.name)
        .all()
    )

    return {
        "datasets_count": datasets_count,
        "events_count": links_count,  # total observations across datasets
        "unique_events_count": events_count,
        "date_min": date_min,
        "date_max": date_max,
        "top_types": [{"type": t or "unknown", "count": c} for t, c in top_types],
        "activity_by_month": [{"month": ym, "count": c} for ym, c in month_rows],
        "per_dataset": [
            {"dataset_id": did, "dataset_name": name, "events_count": cnt}
            for did, name, cnt in per_dataset
        ],
    }


def per_source_summary(db: Session, dataset_id: int | None = None) -> list[dict]:
    q = db.query(
        Event.source,
        func.count(Event.id).label("events_count"),
        func.min(Event.timestamp).label("date_min"),
        func.max(Event.timestamp).label("date_max"),
    )
    if dataset_id is not None:
        q = q.join(EventDatasetLink, EventDatasetLink.event_id == Event.id).filter(
            EventDatasetLink.dataset_id == dataset_id
        )
    q = q.group_by(Event.source).order_by(func.count(Event.id).desc())
    out = []
    for source, count, dmin, dmax in q.all():
        type_rows = (
            db.query(Event.type, func.count(Event.id))
            .filter(Event.source == source)
            .group_by(Event.type)
            .order_by(func.count(Event.id).desc())
            .limit(5)
            .all()
        )
        out.append(
            {
                "source": source or "unknown",
                "events_count": count,
                "date_min": dmin,
                "date_max": dmax,
                "sample_types": [t for t, _ in type_rows if t],
            }
        )
    return out
