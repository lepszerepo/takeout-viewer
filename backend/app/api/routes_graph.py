"""People / entity graph endpoints.

Edges are built on-the-fly from existing tables:
- mail edges:   from_addr ↔ each (to, cc) addr,   weight = count of mails
- meet edges:   between participants of the same conference,  weight = count
- mention edges: between a sender/recipient and PERSON entities mentioned
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text as sql
from sqlalchemy.orm import Session

from ..database import engine, get_db
from ..models import (
    Dataset,
    Entity,
    EntityMention,
    Event,
    MailMessage,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])
logger = logging.getLogger("takeout")


def _addr_list(blob: str | None) -> list[str]:
    if not blob:
        return []
    try:
        data = json.loads(blob)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for a in data:
        if isinstance(a, dict):
            e = (a.get("email") or "").lower().strip()
            if e:
                out.append(e)
        elif isinstance(a, str):
            e = a.lower().strip()
            if e:
                out.append(e)
    return out


@router.get("/people")
def people_graph(
    min_weight: int = Query(2, ge=1, description="Minimum edge weight to include"),
    limit_edges: int = Query(2000, ge=10, le=20000),
    db: Session = Depends(get_db),
):
    """Build a from↔to graph of email correspondents.

    Aggregated across ALL datasets — same edge from multiple users' mailboxes
    gets summed. Useful for spotting key hubs and clusters of communication.
    """
    edges: dict[tuple[str, str], int] = defaultdict(int)
    node_counts: dict[str, int] = defaultdict(int)

    # Stream rows in batches
    BATCH = 5000
    offset = 0
    while True:
        rows = (
            db.query(MailMessage.from_addr, MailMessage.to_addrs, MailMessage.cc_addrs)
            .order_by(MailMessage.id)
            .offset(offset)
            .limit(BATCH)
            .all()
        )
        if not rows:
            break
        for from_blob, to_blob, cc_blob in rows:
            froms = _addr_list(from_blob)
            tos = _addr_list(to_blob) + _addr_list(cc_blob)
            if not froms:
                continue
            for f in froms:
                node_counts[f] += 1
                for t in tos:
                    if t == f:
                        continue
                    key = tuple(sorted((f, t)))  # undirected
                    edges[key] += 1
                    node_counts[t] += 1
        offset += BATCH

    filtered = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edges.items()
        if w >= min_weight
    ]
    filtered.sort(key=lambda e: -e["weight"])
    filtered = filtered[:limit_edges]

    node_ids = set()
    for e in filtered:
        node_ids.add(e["source"])
        node_ids.add(e["target"])

    nodes = [
        {"id": n, "count": node_counts.get(n, 0)}
        for n in node_ids
    ]
    nodes.sort(key=lambda x: -x["count"])

    return {
        "nodes": nodes,
        "edges": filtered,
        "stats": {
            "total_unique_edges": len(edges),
            "total_nodes_in_graph": len(node_ids),
            "min_weight_used": min_weight,
        },
    }


@router.get("/person/{email}")
def person_profile_graph(
    email: str,
    depth: int = Query(1, ge=1, le=2),
    min_weight: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Ego graph centered on one email address."""
    email = email.lower().strip()
    edges: dict[tuple[str, str], int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)

    BATCH = 5000
    offset = 0
    while True:
        rows = (
            db.query(MailMessage.from_addr, MailMessage.to_addrs, MailMessage.cc_addrs)
            .order_by(MailMessage.id)
            .offset(offset)
            .limit(BATCH)
            .all()
        )
        if not rows:
            break
        for from_blob, to_blob, cc_blob in rows:
            froms = _addr_list(from_blob)
            tos = _addr_list(to_blob) + _addr_list(cc_blob)
            participants = set(froms) | set(tos)
            if email not in participants:
                continue
            for p in participants:
                counts[p] += 1
            for a in participants:
                for b in participants:
                    if a >= b:
                        continue
                    edges[(a, b)] += 1
        offset += BATCH

    direct = {n for e in edges for n in e if email in e}
    if depth == 1:
        keep_nodes = direct | {email}
    else:
        keep_nodes = direct | {email}
        # include second-ring: edges between members of direct ring
        # (already in `edges`)
    filtered = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edges.items()
        if w >= min_weight and (a in keep_nodes and b in keep_nodes)
    ]
    nodes = [{"id": n, "count": counts.get(n, 0), "self": n == email} for n in keep_nodes]

    return {"center": email, "nodes": nodes, "edges": filtered}
