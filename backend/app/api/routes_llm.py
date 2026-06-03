"""LLM + semantic search endpoints."""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import engine, get_db
from ..models import Event, MailMessage
from ..services import llm
from ..vector_index import ensure_vec_table, knn_search, upsert_embedding, vec_table_ready

router = APIRouter(prefix="/api/llm", tags=["llm"])
logger = logging.getLogger("takeout")


@router.get("/health")
def llm_health():
    try:
        models = llm.list_models()
    except llm.OllamaError as exc:
        return {"ok": False, "error": str(exc)}
    names = [m.get("name") for m in models]
    return {
        "ok": True,
        "ollama_url": settings.ollama_url,
        "llm_model": settings.llm_model,
        "embed_model": settings.embed_model,
        "llm_present": settings.llm_model in names,
        "embed_present": settings.embed_model in names,
        "available": names,
    }


@router.post("/summary/{mail_id}")
def summarize(mail_id: int, db: Session = Depends(get_db)):
    m = db.get(MailMessage, mail_id)
    if m is None:
        raise HTTPException(404, "Brak wiadomości.")
    body = m.body_text or ""
    try:
        from_ = json.loads(m.from_addr or "[]")
        to_ = json.loads(m.to_addrs or "[]")
    except (TypeError, ValueError):
        from_, to_ = [], []
    from_str = ", ".join(a.get("email", "") for a in from_ if isinstance(a, dict))
    to_str = ", ".join(a.get("email", "") for a in to_ if isinstance(a, dict))
    try:
        summary = llm.summarize_mail(m.subject or "", body, from_=from_str, to_=to_str)
    except llm.OllamaError as exc:
        raise HTTPException(503, str(exc))
    return {"mail_id": mail_id, "summary": summary, "model": settings.llm_model}


@router.post("/classify/{mail_id}")
def classify(mail_id: int, db: Session = Depends(get_db)):
    m = db.get(MailMessage, mail_id)
    if m is None:
        raise HTTPException(404, "Brak wiadomości.")
    try:
        category = llm.classify_mail(m.subject or "", m.body_text or "")
    except llm.OllamaError as exc:
        raise HTTPException(503, str(exc))
    return {"mail_id": mail_id, "category": category}


@router.post("/entities/{mail_id}")
def entities(mail_id: int, db: Session = Depends(get_db)):
    m = db.get(MailMessage, mail_id)
    if m is None:
        raise HTTPException(404, "Brak wiadomości.")
    try:
        text_raw = llm.extract_entities((m.subject or "") + "\n\n" + (m.body_text or ""))
    except llm.OllamaError as exc:
        raise HTTPException(503, str(exc))
    parsed = None
    try:
        # Try to extract JSON block
        s = text_raw.strip()
        if s.startswith("```"):
            s = s.strip("`")
            if s.lower().startswith("json"):
                s = s[4:].strip()
        parsed = json.loads(s)
    except (TypeError, ValueError):
        parsed = None
    return {"mail_id": mail_id, "raw": text_raw, "parsed": parsed}


class EmbedBuildRequest(BaseModel):
    limit: Optional[int] = None
    only_pending: bool = True


@router.post("/embeddings/build")
def build_embeddings(body: EmbedBuildRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start (or resume) embedding all mail messages. Runs in the background.

    Body content sent to embedding model: subject + first ~2000 chars of body_text.
    """
    # Determine embedding dim by probing the model
    try:
        sample = llm.embed("probe")
    except llm.OllamaError as exc:
        raise HTTPException(503, str(exc))
    dim = len(sample)
    if dim == 0:
        raise HTTPException(500, "Model embeddingów zwrócił pusty wektor.")
    ensure_vec_table(engine, dim)

    background_tasks.add_task(_embed_loop, body.limit, body.only_pending, dim)
    return {"status": "started", "dim": dim, "limit": body.limit, "only_pending": body.only_pending}


def _embed_loop(limit: Optional[int], only_pending: bool, dim: int) -> None:
    """Stream-batch embedding pipeline.

    Strategy:
    - Pull candidates in chunks of CHUNK rows via plain SQL (no ORM)
    - Parallelize Ollama calls with a thread pool (bound by N workers)
    - Buffer (mail_id, vec) pairs; flush to DB every BATCH inserts in a
      single transaction → drastically fewer commits, much faster overall
    """
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import text as sql

    CHUNK = 500
    BATCH = 200
    WORKERS = 8

    processed = 0
    where = "WHERE embedding_status = 'pending'" if only_pending else ""
    lim = f"LIMIT {int(limit)}" if limit else ""

    def embed_one(row):
        mid, subj, body = row
        text_in = (subj or "") + "\n\n" + ((body or "")[:2000])
        try:
            vec = llm.embed(text_in)
        except llm.OllamaError as exc:
            logger.warning("embed failed for %s: %s", mid, exc)
            return mid, None
        if not vec or len(vec) != dim:
            return mid, None
        return mid, vec

    with engine.connect() as conn_read:
        rows_all = conn_read.execute(
            sql(f"SELECT id, subject, body_text FROM mail_messages {where} ORDER BY id ASC {lim}")
        ).all()
    total = len(rows_all)
    logger.info("Embedding loop: %d candidates (dim=%d, workers=%d)", total, dim, WORKERS)

    pending_buf: list[tuple[int, list[float]]] = []

    def flush(buf):
        if not buf:
            return
        import time as _time
        for attempt in range(5):
            try:
                with engine.begin() as conn:
                    for mid, vec in buf:
                        upsert_embedding(conn, mid, vec)
                    ids = [str(m) for m, _ in buf]
                    conn.execute(sql(f"UPDATE mail_messages SET embedding_status='ok' WHERE id IN ({','.join(ids)})"))
                return
            except Exception as exc:
                logger.warning("flush attempt %d failed: %s", attempt + 1, exc)
                _time.sleep(2 ** attempt)
        logger.error("flush gave up after retries, %d vecs lost", len(buf))

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i in range(0, total, CHUNK):
            chunk = rows_all[i:i + CHUNK]
            for mid, vec in pool.map(embed_one, chunk):
                if vec is None:
                    continue
                pending_buf.append((mid, vec))
                processed += 1
                if len(pending_buf) >= BATCH:
                    flush(pending_buf)
                    pending_buf = []
            logger.info("Embedded %d / %d mails", processed, total)
        flush(pending_buf)
    logger.info("Embedding loop done: %d", processed)


@router.get("/embeddings/status")
def embeddings_status(db: Session = Depends(get_db)):
    counts = dict(
        db.query(MailMessage.embedding_status, func.count(MailMessage.id))
        .group_by(MailMessage.embedding_status)
        .all()
    )
    vec_ready = vec_table_ready(engine)
    return {"vec_ready": vec_ready, "by_status": counts}


class SemanticSearchRequest(BaseModel):
    q: str
    k: int = 25


@router.post("/search/semantic")
def semantic_search(body: SemanticSearchRequest, db: Session = Depends(get_db)):
    if not body.q.strip():
        return {"items": []}
    try:
        qv = llm.embed(body.q)
    except llm.OllamaError as exc:
        raise HTTPException(503, str(exc))
    if not qv:
        return {"items": []}
    with engine.connect() as conn:
        hits = knn_search(conn, qv, k=body.k)
    if not hits:
        return {"items": []}
    ids = [h[0] for h in hits]
    rows = db.query(MailMessage).filter(MailMessage.id.in_(ids)).all()
    by_id = {r.id: r for r in rows}
    items = []
    for mid, distance in hits:
        m = by_id.get(mid)
        if not m:
            continue
        ev = db.get(Event, m.event_id)
        items.append({
            "mail_id": m.id,
            "event_id": m.event_id,
            "subject": m.subject,
            "snippet": ev.description if ev else None,
            "from": json.loads(m.from_addr or "[]"),
            "folder": m.folder,
            "timestamp": ev.timestamp.isoformat() if ev and ev.timestamp else None,
            "distance": distance,
        })
    return {"items": items, "q": body.q}
