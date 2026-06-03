"""Sqlite-vec virtual table for mail embeddings.

Layout:
    mail_vec(mail_id INTEGER PRIMARY KEY, embedding FLOAT[N])
where N is the embedding dimension (e.g. 1024 for bge-m3, 768 for nomic).

On startup we try to load the sqlite-vec extension. If it isn't available,
semantic search endpoints will return 503 but the rest of the app works.
"""
from __future__ import annotations

import logging
import struct
from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from . import database

logger = logging.getLogger("takeout")


_DIM_CACHE: dict[Engine, int] = {}
_LOADED: dict[Engine, bool] = {}


def _load_extension(dbapi_conn) -> bool:
    try:
        import sqlite_vec  # type: ignore
    except Exception as exc:
        logger.warning("sqlite-vec not installed: %s", exc)
        return False
    try:
        dbapi_conn.enable_load_extension(True)
        sqlite_vec.load(dbapi_conn)
        dbapi_conn.enable_load_extension(False)
        return True
    except Exception as exc:
        logger.warning("sqlite-vec load failed: %s", exc)
        return False


def _attach_loader_once(engine: Engine) -> None:
    if _LOADED.get(engine):
        return

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _):  # pragma: no cover
        _load_extension(dbapi_conn)

    _LOADED[engine] = True


def ensure_vec_table(engine: Engine, dim: int) -> None:
    """Create the vec virtual table if needed. dim must be stable per DB."""
    _attach_loader_once(engine)
    with engine.connect() as conn:
        # Some SQLite builds emit a benign warning when re-creating; ignore.
        try:
            conn.execute(
                text(f"CREATE VIRTUAL TABLE IF NOT EXISTS mail_vec USING vec0(mail_id INTEGER PRIMARY KEY, embedding FLOAT[{dim}])")
            )
            conn.commit()
            _DIM_CACHE[engine] = dim
        except Exception as exc:
            logger.warning("vec table create failed: %s", exc)


def vec_table_ready(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='mail_vec'")).first()
            return bool(r)
    except Exception:
        return False


def pack_vector(vec: list[float]) -> bytes:
    """Pack a vector as float32 little-endian bytes (sqlite-vec format)."""
    return struct.pack(f"<{len(vec)}f", *vec)


def upsert_embedding(conn, mail_id: int, vec: list[float]) -> None:
    if not vec:
        return
    conn.execute(
        text("INSERT OR REPLACE INTO mail_vec(mail_id, embedding) VALUES (:id, :v)"),
        {"id": mail_id, "v": pack_vector(vec)},
    )


def knn_search(conn, query_vec: list[float], *, k: int = 20) -> list[tuple[int, float]]:
    if not query_vec:
        return []
    rows = conn.execute(
        text(
            "SELECT mail_id, distance FROM mail_vec"
            " WHERE embedding MATCH :v"
            " ORDER BY distance LIMIT :k"
        ),
        {"v": pack_vector(query_vec), "k": k},
    ).all()
    return [(r.mail_id, float(r.distance)) for r in rows]
