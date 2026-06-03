"""Full-text + (later) semantic search."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..search_index import search as fts_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/fts")
def fts(
    q: str = Query(..., min_length=1),
    source: Optional[str] = None,
    dataset_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """FTS5 full-text search.

    Query examples:
    - `umowa OR porozumienie`
    - `subject:malinowska` (use a column prefix)
    - `umowa NEAR/5 zlecenia`
    """
    rows = fts_search(
        db.connection(),
        q,
        limit=limit,
        offset=offset,
        source=source,
        dataset_name=dataset_name,
    )
    return {"q": q, "count": len(rows), "items": rows}
