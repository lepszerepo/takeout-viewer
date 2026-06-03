"""Entity / NER endpoints: process events, list entities, find mentions."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text as sql
from sqlalchemy.orm import Session

from ..database import SessionLocal, engine, get_db
from ..models import Dataset, Entity, EntityMention, Event, MailMessage, NerStatus
from ..services.ner import extract_entities, normalize_key

router = APIRouter(prefix="/api/entities", tags=["entities"])
logger = logging.getLogger("takeout")


def _text_for_event(db: Session, event_id: int) -> tuple[str, int]:
    """Return (text_to_analyze, dataset_id)."""
    ev = db.get(Event, event_id)
    if ev is None:
        return "", 0
    parts: list[str] = []
    if ev.title:
        parts.append(ev.title)
    if ev.description:
        parts.append(ev.description)
    # Mail body
    m = db.query(MailMessage).filter_by(event_id=event_id).one_or_none()
    if m and m.body_text:
        parts.append(m.body_text)
    return ("\n".join(parts), ev.dataset_id)


def _process_one(db: Session, event_id: int) -> int:
    text, ds_id = _text_for_event(db, event_id)
    if not text:
        return 0
    try:
        ents = extract_entities(text)
    except Exception as exc:
        db.merge(NerStatus(event_id=event_id, model="failed", error=str(exc)[:500]))
        db.commit()
        return 0
    inserted = 0
    for kind, key, label, span_text in ents:
        # Upsert entity
        ent = db.query(Entity).filter_by(kind=kind, key=key).one_or_none()
        if ent is None:
            ent = Entity(kind=kind, key=key, label=label, count=0)
            db.add(ent)
            db.flush()
        ent.count = (ent.count or 0) + 1
        if not ent.label or len(label) > len(ent.label):
            ent.label = label
        # Mention (don't duplicate per (entity, event))
        exists = (
            db.query(EntityMention.id)
            .filter_by(entity_id=ent.id, event_id=event_id)
            .first()
        )
        if exists is None:
            db.add(
                EntityMention(
                    entity_id=ent.id,
                    event_id=event_id,
                    dataset_id=ds_id,
                    span_text=span_text[:500] if span_text else None,
                )
            )
            inserted += 1
    db.merge(NerStatus(event_id=event_id, model="spacy"))
    db.commit()
    return inserted


class ProcessRequest(BaseModel):
    limit: Optional[int] = None
    only_unprocessed: bool = True
    source: Optional[str] = None  # filter by event source (e.g. 'mail', 'drive')


@router.post("/process")
def process_events(body: ProcessRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    bg.add_task(_process_loop, body.limit, body.only_unprocessed, body.source)
    return {"status": "started", "limit": body.limit, "only_unprocessed": body.only_unprocessed}


def _process_loop(limit: Optional[int], only_unprocessed: bool, source: Optional[str]) -> None:
    where = []
    if only_unprocessed:
        where.append("e.id NOT IN (SELECT event_id FROM ner_status)")
    if source:
        where.append(f"e.source = '{source}'")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    lim = f"LIMIT {int(limit)}" if limit else ""

    with engine.connect() as conn_read:
        ids = [r[0] for r in conn_read.execute(sql(f"SELECT e.id FROM events e {where_sql} ORDER BY e.id {lim}")).all()]
    total = len(ids)
    logger.info("NER loop: %d events to process", total)
    processed = 0
    with SessionLocal() as db:
        for eid in ids:
            try:
                _process_one(db, eid)
            except Exception as exc:
                logger.warning("NER error on %s: %s", eid, exc)
                db.rollback()
            processed += 1
            if processed % 100 == 0:
                logger.info("NER processed %d / %d", processed, total)
    logger.info("NER loop done: %d", processed)


@router.get("/status")
def ner_status(db: Session = Depends(get_db)):
    total_events = db.query(func.count(Event.id)).scalar() or 0
    processed = db.query(func.count(NerStatus.event_id)).scalar() or 0
    total_entities = db.query(func.count(Entity.id)).scalar() or 0
    total_mentions = db.query(func.count(EntityMention.id)).scalar() or 0
    by_kind = dict(
        db.query(Entity.kind, func.count(Entity.id))
        .group_by(Entity.kind).all()
    )
    return {
        "events_total": total_events,
        "events_processed": processed,
        "entities": total_entities,
        "mentions": total_mentions,
        "by_kind": by_kind,
    }


@router.get("/top")
def top_entities(
    kind: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    base = db.query(Entity)
    if kind:
        base = base.filter(Entity.kind == kind)
    if q:
        base = base.filter(Entity.key.ilike(f"%{q.lower()}%"))
    rows = base.order_by(Entity.count.desc()).limit(limit).all()
    return [
        {"id": e.id, "kind": e.kind, "key": e.key, "label": e.label, "count": e.count}
        for e in rows
    ]


@router.get("/{entity_id}/mentions")
def mentions(entity_id: int, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    ent = db.get(Entity, entity_id)
    if ent is None:
        raise HTTPException(404, "Brak encji.")
    rows = (
        db.query(EntityMention, Event)
        .join(Event, EntityMention.event_id == Event.id)
        .filter(EntityMention.entity_id == entity_id)
        .order_by(Event.timestamp.desc().nulls_last())
        .limit(limit)
        .all()
    )
    ds_map = {d.id: d.name for d in db.query(Dataset).all()}
    return {
        "entity": {"id": ent.id, "kind": ent.kind, "label": ent.label, "count": ent.count},
        "mentions": [
            {
                "event_id": ev.id,
                "title": ev.title,
                "source": ev.source,
                "type": ev.type,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "dataset_name": ds_map.get(ev.dataset_id),
                "span": m.span_text,
            }
            for m, ev in rows
        ],
    }
