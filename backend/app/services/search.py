"""Event listing + LIKE-based search.

For MVP we use SQL LIKE on title/description/url. FTS5 can be added later
without changing the API.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import or_, func, distinct
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Dataset, Event, EventDatasetLink


def _maybe_json(value: Optional[str]) -> Optional[Any]:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def list_events(
    db: Session,
    *,
    dataset_id: Optional[int] = None,
    dataset_name: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    type_: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    include_duplicates: bool = False,
    limit: int = 50,
    offset: int = 0,
    sort: str = "-timestamp",
) -> dict:
    limit = max(1, min(limit, settings.page_size_max))
    offset = max(0, offset)

    if dataset_name and not dataset_id:
        ds = db.query(Dataset).filter_by(name=dataset_name).one_or_none()
        if ds is None:
            return {"total": 0, "limit": limit, "offset": offset, "items": []}
        dataset_id = ds.id

    # Filter via EventDatasetLink so we can show events that appeared in
    # a specific dataset even if their canonical row points elsewhere.
    base = db.query(Event)
    if dataset_id is not None:
        base = base.join(EventDatasetLink, EventDatasetLink.event_id == Event.id).filter(
            EventDatasetLink.dataset_id == dataset_id
        )

    if source:
        base = base.filter(Event.source == source)
    if category:
        base = base.filter(Event.category == category)
    if type_:
        base = base.filter(Event.type == type_)
    if date_from:
        base = base.filter(Event.timestamp >= date_from)
    if date_to:
        base = base.filter(Event.timestamp <= date_to)
    if q:
        pat = f"%{q}%"
        base = base.filter(
            or_(
                Event.title.ilike(pat),
                Event.description.ilike(pat),
                Event.url.ilike(pat),
            )
        )

    if not include_duplicates and dataset_id is None:
        # default global view shows unique events
        pass  # we already select distinct Event rows

    total = base.with_entities(func.count(distinct(Event.id))).scalar() or 0

    order_col = Event.timestamp.desc() if sort.startswith("-") else Event.timestamp.asc()
    rows = (
        base.order_by(order_col, Event.id.desc())
        .group_by(Event.id)
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Build dataset list per event
    items = []
    if rows:
        event_ids = [r.id for r in rows]
        ds_map = _datasets_per_event(db, event_ids)
        primary_ds_map = {
            ds.id: ds.name for ds in db.query(Dataset).filter(Dataset.id.in_({r.dataset_id for r in rows})).all()
        }
        for r in rows:
            ds_names = ds_map.get(r.id, [])
            items.append(
                {
                    "id": r.id,
                    "source": r.source,
                    "service": r.service,
                    "category": r.category,
                    "type": r.type,
                    "title": r.title,
                    "description": r.description,
                    "timestamp": r.timestamp,
                    "end_timestamp": r.end_timestamp,
                    "url": r.url,
                    "people": _maybe_json(r.people_json),
                    "location": _maybe_json(r.location_json),
                    "metadata": _maybe_json(r.metadata_json),
                    "raw_path": r.raw_path,
                    "dataset_id": r.dataset_id,
                    "dataset_name": primary_ds_map.get(r.dataset_id, ""),
                    "datasets": ds_names,
                    "is_duplicate_across_datasets": len(ds_names) > 1,
                }
            )

    return {"total": total, "limit": limit, "offset": offset, "items": items}


def _datasets_per_event(db: Session, event_ids: list[int]) -> dict[int, list[str]]:
    if not event_ids:
        return {}
    rows = (
        db.query(EventDatasetLink.event_id, Dataset.name)
        .join(Dataset, Dataset.id == EventDatasetLink.dataset_id)
        .filter(EventDatasetLink.event_id.in_(event_ids))
        .order_by(Dataset.name)
        .all()
    )
    out: dict[int, list[str]] = {}
    for eid, name in rows:
        out.setdefault(eid, []).append(name)
    return out


def get_event_detail(db: Session, event_id: int) -> Optional[dict]:
    ev = db.get(Event, event_id)
    if ev is None:
        return None
    ds_map = _datasets_per_event(db, [ev.id])
    primary = db.get(Dataset, ev.dataset_id)
    return {
        "id": ev.id,
        "source": ev.source,
        "service": ev.service,
        "category": ev.category,
        "type": ev.type,
        "title": ev.title,
        "description": ev.description,
        "timestamp": ev.timestamp,
        "end_timestamp": ev.end_timestamp,
        "url": ev.url,
        "people": _maybe_json(ev.people_json),
        "location": _maybe_json(ev.location_json),
        "metadata": _maybe_json(ev.metadata_json),
        "raw_path": ev.raw_path,
        "raw_json": _maybe_json(ev.raw_json),
        "dataset_id": ev.dataset_id,
        "dataset_name": primary.name if primary else "",
        "datasets": ds_map.get(ev.id, []),
        "is_duplicate_across_datasets": len(ds_map.get(ev.id, [])) > 1,
    }
