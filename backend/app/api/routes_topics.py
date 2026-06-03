"""Topic clustering on mail embeddings + LLM labels."""
from __future__ import annotations

import logging
import struct
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text as sql
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, engine, get_db
from ..models import MailMessage, Topic
from ..services import llm

router = APIRouter(prefix="/api/topics", tags=["topics"])
logger = logging.getLogger("takeout")


class ClusterRequest(BaseModel):
    n_clusters: int = 40
    sample_for_label: int = 6


@router.post("/build")
def build_clusters(body: ClusterRequest, bg: BackgroundTasks):
    bg.add_task(_cluster_loop, body.n_clusters, body.sample_for_label)
    return {"status": "started", "n_clusters": body.n_clusters}


def _load_vectors():
    import numpy as np
    rows = []
    with engine.connect() as conn:
        result = conn.execute(sql("SELECT mail_id, embedding FROM mail_vec"))
        for mid, blob in result:
            if not blob:
                continue
            # blob is bytes of float32; infer dim from length
            n = len(blob) // 4
            vec = struct.unpack(f"<{n}f", blob)
            rows.append((mid, vec))
    if not rows:
        return None, None
    ids = [r[0] for r in rows]
    mat = np.array([r[1] for r in rows], dtype="float32")
    return ids, mat


def _cluster_loop(n_clusters: int, sample_for_label: int) -> None:
    try:
        import numpy as np
        from sklearn.cluster import MiniBatchKMeans
    except Exception as exc:
        logger.error("sklearn missing: %s", exc)
        return

    ids, mat = _load_vectors()
    if mat is None:
        logger.warning("No vectors to cluster")
        return
    logger.info("Clustering: %d vectors, dim=%d, k=%d", mat.shape[0], mat.shape[1], n_clusters)

    km = MiniBatchKMeans(n_clusters=n_clusters, batch_size=4096, random_state=42, n_init="auto")
    labels = km.fit_predict(mat)
    logger.info("Clustering done")

    # Update mail_messages.cluster_id in batches
    with engine.begin() as conn:
        for cid in range(n_clusters):
            mail_ids = [str(ids[i]) for i in range(len(ids)) if labels[i] == cid]
            if not mail_ids:
                continue
            # SQLite IN-clause max 999 per statement, chunk
            for off in range(0, len(mail_ids), 800):
                chunk = ",".join(mail_ids[off:off+800])
                conn.execute(sql(f"UPDATE mail_messages SET cluster_id={cid} WHERE id IN ({chunk})"))
        conn.execute(sql("DELETE FROM topics"))

    # Save topics + label via LLM
    with SessionLocal() as db:
        for cid in range(n_clusters):
            mail_ids = [ids[i] for i in range(len(ids)) if labels[i] == cid]
            size = len(mail_ids)
            label = _label_cluster(db, mail_ids[:sample_for_label]) if size > 0 else None
            db.add(Topic(cluster_id=cid, algorithm="kmeans", label=label, size=size))
            db.commit()
            logger.info("Topic %d/%d size=%d label=%r", cid+1, n_clusters, size, label)
    logger.info("All %d topics labeled.", n_clusters)


def _label_cluster(db: Session, sample_ids: list[int]) -> Optional[str]:
    if not sample_ids:
        return None
    rows = db.query(MailMessage.subject, MailMessage.body_text).filter(MailMessage.id.in_(sample_ids)).all()
    pieces = []
    for subj, body in rows:
        snippet = (body or "")[:400]
        pieces.append(f"- Temat: {subj or '(brak)'}\n  Fragment: {snippet}")
    prompt = (
        "Poniżej kilka maili z jednej grupy tematycznej:\n\n"
        + "\n\n".join(pieces)
        + "\n\nW 3-6 słowach po polsku nazwij wspólny temat tej grupy. "
        + "Bez kropki na końcu, bez cudzysłowów, bez przedrostka 'Temat:'."
    )
    try:
        out = llm.chat(prompt, system="Klasyfikujesz tematycznie firmowe maile. Odpowiadasz JEDNĄ krótką frazą.")
    except llm.OllamaError:
        return None
    label = out.strip().splitlines()[0][:120] if out else None
    return label


@router.get("")
def list_topics(db: Session = Depends(get_db)):
    rows = db.query(Topic).order_by(Topic.size.desc()).all()
    return [
        {"id": t.id, "cluster_id": t.cluster_id, "label": t.label, "size": t.size, "algorithm": t.algorithm}
        for t in rows
    ]


@router.get("/{cluster_id}/mails")
def topic_mails(cluster_id: int, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    base = db.query(MailMessage).filter(MailMessage.cluster_id == cluster_id)
    total = base.with_entities(func.count(MailMessage.id)).scalar() or 0
    rows = base.order_by(MailMessage.id.desc()).offset(offset).limit(limit).all()
    return {
        "cluster_id": cluster_id,
        "total": total,
        "items": [
            {
                "id": m.id,
                "event_id": m.event_id,
                "subject": m.subject,
                "folder": m.folder,
                "size_bytes": m.size_bytes,
                "has_attachments": m.has_attachments,
            }
            for m in rows
        ],
    }
