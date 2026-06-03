"""Person profile: cross-source aggregate for one email address.

Combines:
- mail counts (sent / received)
- calendar attendance (people list contains the email)
- google meet conferences (counterparts contains the email)
- entity mentions where the entity is PERSON or EMAIL matching this email
- activity heatmap (day-of-week × hour-of-day) from event timestamps
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Dataset, Entity, EntityMention, Event, MailMessage

router = APIRouter(prefix="/api/person", tags=["person"])


def _addrs(blob: Optional[str]) -> list[str]:
    if not blob:
        return []
    try:
        d = json.loads(blob)
    except (TypeError, ValueError):
        return []
    out = []
    for a in d if isinstance(d, list) else []:
        if isinstance(a, dict):
            e = (a.get("email") or "").lower().strip()
            if e:
                out.append(e)
        elif isinstance(a, str):
            e = a.lower().strip()
            if e:
                out.append(e)
    return out


@router.get("/{email}")
def person_profile(email: str, db: Session = Depends(get_db)):
    email = email.lower().strip()

    # Mail aggregates
    sent = 0
    received = 0
    threads: set[str] = set()
    domains: dict[str, int] = defaultdict(int)
    top_correspondents: dict[str, int] = defaultdict(int)
    activity: dict[tuple[int, int], int] = defaultdict(int)  # (dow, hour)
    months: dict[str, int] = defaultdict(int)
    BATCH = 5000
    offset = 0
    while True:
        rows = (
            db.query(MailMessage.id, MailMessage.from_addr, MailMessage.to_addrs,
                     MailMessage.cc_addrs, MailMessage.thread_id, MailMessage.event_id)
            .order_by(MailMessage.id).offset(offset).limit(BATCH).all()
        )
        if not rows:
            break
        ev_ids = [r[5] for r in rows]
        ev_times = dict(
            db.query(Event.id, Event.timestamp).filter(Event.id.in_(ev_ids)).all()
        )
        for mid, fb, tb, cb, tid, eid in rows:
            froms = _addrs(fb)
            tos = _addrs(tb) + _addrs(cb)
            is_sender = email in froms
            is_recipient = email in tos
            if not (is_sender or is_recipient):
                continue
            if is_sender:
                sent += 1
            if is_recipient:
                received += 1
            if tid:
                threads.add(tid)
            others = (set(froms) | set(tos)) - {email}
            for o in others:
                top_correspondents[o] += 1
                _, _, dom = o.partition("@")
                if dom:
                    domains[dom] += 1
            ts = ev_times.get(eid)
            if ts is not None:
                activity[(ts.weekday(), ts.hour)] += 1
                months[ts.strftime("%Y-%m")] += 1
        offset += BATCH

    top = sorted(top_correspondents.items(), key=lambda x: -x[1])[:30]
    top_domains = sorted(domains.items(), key=lambda x: -x[1])[:20]

    # Mentions of this person from NER
    mention_count_email = (
        db.query(func.count(EntityMention.id))
        .join(Entity, Entity.id == EntityMention.entity_id)
        .filter(Entity.kind == "EMAIL", Entity.key == email)
        .scalar() or 0
    )

    # PERSON entities matching the local-part heuristic — best-effort
    local = email.split("@", 1)[0].replace(".", " ")
    person_matches = (
        db.query(Entity).filter(Entity.kind == "PERSON", Entity.key.ilike(f"%{local}%"))
        .order_by(Entity.count.desc()).limit(5).all()
    )

    return {
        "email": email,
        "mail": {
            "sent": sent,
            "received": received,
            "threads": len(threads),
        },
        "top_correspondents": [
            {"email": e, "count": c} for e, c in top
        ],
        "top_domains": [
            {"domain": d, "count": c} for d, c in top_domains
        ],
        "activity_heatmap": [
            {"dow": dow, "hour": hour, "count": cnt}
            for (dow, hour), cnt in sorted(activity.items())
        ],
        "activity_by_month": [
            {"month": m, "count": c} for m, c in sorted(months.items())
        ],
        "ner_mentions_as_email": mention_count_email,
        "person_entities": [
            {"id": p.id, "label": p.label, "count": p.count}
            for p in person_matches
        ],
    }
