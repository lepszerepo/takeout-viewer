"""Event listing & detail endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import EventDetail, EventsPage
from ..services.search import get_event_detail, list_events

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=EventsPage)
def events_list(
    dataset_id: Optional[int] = None,
    dataset_name: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    type: Optional[str] = None,  # noqa: A002 (FastAPI param)
    q: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    include_duplicates: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-timestamp",
    db: Session = Depends(get_db),
) -> EventsPage:
    result = list_events(
        db,
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        source=source,
        category=category,
        type_=type,
        q=q,
        date_from=date_from,
        date_to=date_to,
        include_duplicates=include_duplicates,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    return EventsPage(**result)


@router.get("/{event_id}", response_model=EventDetail)
def event_detail(event_id: int, db: Session = Depends(get_db)) -> EventDetail:
    detail = get_event_detail(db, event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono rekordu.")
    return EventDetail(**detail)
