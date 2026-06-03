"""Mail-specific endpoints: list, detail (with full body), thread."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Dataset, Event, EventDatasetLink, MailMessage

router = APIRouter(prefix="/api/mail", tags=["mail"])


def _maybe_json(v):
    if v is None:
        return None
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return v


@router.get("/folders")
def list_folders(
    dataset_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(MailMessage.folder, func.count(MailMessage.id))
    if dataset_id is not None:
        q = q.filter(MailMessage.dataset_id == dataset_id)
    q = q.group_by(MailMessage.folder).order_by(func.count(MailMessage.id).desc())
    return [{"folder": f or "Mail", "count": c} for f, c in q.all()]


@router.get("/messages")
def list_messages(
    folder: Optional[str] = None,
    dataset_id: Optional[int] = None,
    dataset_name: Optional[str] = None,
    q: Optional[str] = None,
    address: Optional[str] = None,
    has_attachments: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if dataset_name and not dataset_id:
        ds = db.query(Dataset).filter_by(name=dataset_name).one_or_none()
        if ds is None:
            return {"total": 0, "items": [], "limit": limit, "offset": offset}
        dataset_id = ds.id

    base = db.query(MailMessage).join(Event, MailMessage.event_id == Event.id)
    if dataset_id is not None:
        base = base.filter(MailMessage.dataset_id == dataset_id)
    if folder:
        base = base.filter(MailMessage.folder == folder)
    if has_attachments is True:
        base = base.filter(MailMessage.has_attachments.is_(True))
    if q:
        pat = f"%{q}%"
        base = base.filter(or_(MailMessage.subject.ilike(pat), MailMessage.from_addr.ilike(pat), MailMessage.to_addrs.ilike(pat)))
    if address:
        pat = f"%{address}%"
        base = base.filter(or_(MailMessage.from_addr.ilike(pat), MailMessage.to_addrs.ilike(pat), MailMessage.cc_addrs.ilike(pat)))

    total = base.with_entities(func.count(MailMessage.id)).scalar() or 0
    rows = (
        base.order_by(Event.timestamp.desc().nulls_last(), MailMessage.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    ds_map = {d.id: d.name for d in db.query(Dataset).all()}
    items = []
    for m in rows:
        ev = db.get(Event, m.event_id)
        items.append({
            "id": m.id,
            "event_id": m.event_id,
            "dataset_id": m.dataset_id,
            "dataset_name": ds_map.get(m.dataset_id),
            "folder": m.folder,
            "subject": m.subject,
            "from": _maybe_json(m.from_addr),
            "to": _maybe_json(m.to_addrs),
            "cc": _maybe_json(m.cc_addrs),
            "labels": _maybe_json(m.labels),
            "timestamp": ev.timestamp.isoformat() if ev and ev.timestamp else None,
            "size_bytes": m.size_bytes,
            "has_attachments": m.has_attachments,
            "thread_id": m.thread_id,
            "snippet": (ev.description if ev else None),
        })
    return {"total": total, "items": items, "limit": limit, "offset": offset}


@router.get("/by_event/{event_id}")
def get_by_event(event_id: int, db: Session = Depends(get_db)):
    """Return mail_id for a given event_id (1:1)."""
    m = db.query(MailMessage).filter_by(event_id=event_id).one_or_none()
    if m is None:
        raise HTTPException(404, "Brak wiadomości dla tego event_id.")
    return {"mail_id": m.id, "event_id": event_id}


@router.get("/messages/{mail_id}")
def get_message(mail_id: int, db: Session = Depends(get_db)):
    m = db.get(MailMessage, mail_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono wiadomości.")
    ev = db.get(Event, m.event_id)
    ds = db.get(Dataset, m.dataset_id)
    # Find all datasets containing the same event (cross-dataset dedup)
    links = (
        db.query(EventDatasetLink.dataset_id)
        .filter_by(event_id=m.event_id)
        .all()
    )
    dataset_ids = [l.dataset_id for l in links]
    ds_names = [
        d.name
        for d in db.query(Dataset).filter(Dataset.id.in_(dataset_ids)).all()
    ]
    return {
        "id": m.id,
        "event_id": m.event_id,
        "dataset_id": m.dataset_id,
        "dataset_name": ds.name if ds else None,
        "datasets": ds_names,
        "folder": m.folder,
        "subject": m.subject,
        "from": _maybe_json(m.from_addr),
        "to": _maybe_json(m.to_addrs),
        "cc": _maybe_json(m.cc_addrs),
        "bcc": _maybe_json(m.bcc_addrs),
        "reply_to": _maybe_json(m.reply_to),
        "labels": _maybe_json(m.labels),
        "headers": _maybe_json(m.headers_json),
        "attachments": _maybe_json(m.attachments_json),
        "message_id": m.message_id,
        "in_reply_to": m.in_reply_to,
        "references": _maybe_json(m.references_header),
        "thread_id": m.thread_id,
        "body_text": m.body_text,
        "body_html": m.body_html,
        "size_bytes": m.size_bytes,
        "timestamp": ev.timestamp.isoformat() if ev and ev.timestamp else None,
    }


@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(MailMessage)
        .filter(MailMessage.thread_id == thread_id)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Brak wątku.")
    msgs = []
    for m in rows:
        ev = db.get(Event, m.event_id)
        msgs.append({
            "id": m.id,
            "subject": m.subject,
            "from": _maybe_json(m.from_addr),
            "to": _maybe_json(m.to_addrs),
            "timestamp": ev.timestamp.isoformat() if ev and ev.timestamp else None,
            "snippet": ev.description if ev else None,
            "dataset_id": m.dataset_id,
        })
    msgs.sort(key=lambda x: x.get("timestamp") or "")
    return {"thread_id": thread_id, "messages": msgs, "count": len(msgs)}


@router.get("/messages/{mail_id}/attachments/{idx}")
def download_attachment(mail_id: int, idx: int, db: Session = Depends(get_db)):
    """Stream a previously saved attachment binary by its position in the mail."""
    m = db.get(MailMessage, mail_id)
    if m is None:
        raise HTTPException(404, "Brak wiadomości.")
    atts = _maybe_json(m.attachments_json) or []
    if not isinstance(atts, list) or idx < 0 or idx >= len(atts):
        raise HTTPException(404, "Nie ma takiego załącznika.")
    a = atts[idx]
    sha = (a or {}).get("sha256")
    name = (a or {}).get("name") or "attachment"
    ctype = (a or {}).get("content_type") or "application/octet-stream"
    if not sha:
        raise HTTPException(404, "Treść tego załącznika nie została zapisana.")
    base = settings.data_dir / "attachments" / sha[:2] / sha[2:]
    if not base.exists():
        raise HTTPException(404, "Plik załącznika nie istnieje.")
    return FileResponse(
        path=str(base),
        media_type=ctype,
        filename=name,
    )


@router.get("/people/top")
def top_correspondents(
    dataset_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Aggregate top from/to addresses across mail. Returns counts."""
    rows = db.query(MailMessage.from_addr, MailMessage.to_addrs)
    if dataset_id is not None:
        rows = rows.filter(MailMessage.dataset_id == dataset_id)
    counts: dict[str, int] = {}
    for from_json, to_json in rows.all():
        for blob in (from_json, to_json):
            if not blob:
                continue
            try:
                lst = json.loads(blob)
            except (TypeError, ValueError):
                continue
            if not isinstance(lst, list):
                continue
            for entry in lst:
                email = (entry.get("email") if isinstance(entry, dict) else None) or ""
                email = email.lower().strip()
                if not email:
                    continue
                counts[email] = counts.get(email, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [{"email": e, "count": c} for e, c in top]
