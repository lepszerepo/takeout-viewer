"""Anomaly / signal endpoints — purely statistical, no LLM."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Dataset, Event, MailMessage

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


_INTERNAL_DOMAINS = {"zondacrypto.com"}  # treat as internal — used as default reference


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


def _is_external(addr: str, internal_domain: str) -> bool:
    if not addr or "@" not in addr:
        return False
    return not addr.lower().endswith("@" + internal_domain)


@router.get("/off-hours")
def off_hours(
    start_hour: int = Query(22, ge=0, le=23),
    end_hour: int = Query(6, ge=0, le=23),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """Mails sent in unusual hours (default 22:00–06:00)."""
    rows = (
        db.query(MailMessage.id, MailMessage.subject, MailMessage.from_addr, MailMessage.dataset_id, Event.timestamp, Event.id)
        .join(Event, Event.id == MailMessage.event_id)
        .filter(Event.timestamp.isnot(None))
        .order_by(Event.timestamp.desc())
        .limit(50_000)
        .all()
    )
    flagged = []
    for mid, subj, fa, ds_id, ts, eid in rows:
        if ts is None:
            continue
        h = ts.hour
        # interval can wrap midnight
        in_range = (h >= start_hour or h < end_hour) if start_hour > end_hour else (start_hour <= h < end_hour)
        if not in_range:
            continue
        froms = _addrs(fa)
        flagged.append({
            "mail_id": mid,
            "event_id": eid,
            "dataset_id": ds_id,
            "subject": subj,
            "from": froms,
            "timestamp": ts.isoformat(),
        })
        if len(flagged) >= limit:
            break
    return {"window": f"{start_hour:02d}:00 → {end_hour:02d}:00", "items": flagged}


@router.get("/large-external")
def large_external(
    min_size: int = Query(5_000_000, ge=100_000, description="Min total attachment size in bytes"),
    internal_domain: str = Query("zondacrypto.com"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Mails with large attachments sent to external recipients."""
    rows = (
        db.query(MailMessage.id, MailMessage.subject, MailMessage.from_addr,
                 MailMessage.to_addrs, MailMessage.cc_addrs, MailMessage.attachments_json,
                 MailMessage.dataset_id, MailMessage.event_id)
        .filter(MailMessage.has_attachments.is_(True))
        .all()
    )
    flagged = []
    for mid, subj, fa, ta, ca, aj, ds, eid in rows:
        try:
            atts = json.loads(aj) if aj else []
        except (TypeError, ValueError):
            atts = []
        total_size = sum((a.get("size") or 0) for a in atts if isinstance(a, dict))
        if total_size < min_size:
            continue
        froms = _addrs(fa)
        tos = _addrs(ta) + _addrs(ca)
        # Only flag if SENDER is internal and AT LEAST ONE recipient external
        from_internal = any(addr.endswith("@" + internal_domain) for addr in froms)
        to_external = any(_is_external(addr, internal_domain) for addr in tos)
        if not (from_internal and to_external):
            continue
        flagged.append({
            "mail_id": mid,
            "event_id": eid,
            "dataset_id": ds,
            "subject": subj,
            "from": froms,
            "to": tos,
            "total_attachment_size": total_size,
            "attachments": [
                {"name": a.get("name"), "size": a.get("size")}
                for a in atts if isinstance(a, dict)
            ][:10],
        })
    flagged.sort(key=lambda x: -x["total_attachment_size"])
    return {"items": flagged[:limit], "min_size": min_size, "internal_domain": internal_domain}


@router.get("/new-domains")
def new_domains(
    days: int = Query(30, ge=1, le=365, description="Look-back window for 'new' contacts"),
    internal_domain: str = Query("zondacrypto.com"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """External domains that appeared only in the last N days."""
    cutoff = datetime.utcnow().replace(microsecond=0)
    cutoff_days = cutoff.toordinal() - days

    first_seen: dict[str, datetime] = {}
    counts: dict[str, int] = defaultdict(int)
    rows = (
        db.query(MailMessage.to_addrs, MailMessage.cc_addrs, MailMessage.from_addr, Event.timestamp)
        .join(Event, Event.id == MailMessage.event_id)
        .filter(Event.timestamp.isnot(None))
        .all()
    )
    for ta, ca, fa, ts in rows:
        addrs = set(_addrs(fa)) | set(_addrs(ta)) | set(_addrs(ca))
        for a in addrs:
            if "@" not in a:
                continue
            dom = a.split("@", 1)[1]
            if dom == internal_domain:
                continue
            counts[dom] += 1
            if dom not in first_seen or ts < first_seen[dom]:
                first_seen[dom] = ts
    out = []
    for dom, ts in first_seen.items():
        if ts.toordinal() < cutoff_days:
            continue
        out.append({"domain": dom, "first_seen": ts.isoformat(), "count": counts[dom]})
    out.sort(key=lambda x: x["first_seen"], reverse=True)
    return {"window_days": days, "internal_domain": internal_domain, "items": out[:limit]}
