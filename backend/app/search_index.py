"""SQLite FTS5 virtual table for full-text search across events and mail bodies.

We keep the FTS5 table as an "external content" mirror of the relevant text
fields. Triggers keep it in sync on INSERT/UPDATE/DELETE.

Columns we index:
- title (event subject / event title)
- description (snippet)
- body (full mail body if available, else empty)
- people_text (concatenated from/to/cc emails)
- folder (mail folder)
- source/type — stored unindexed for filtering via MATCH bareword
"""
from __future__ import annotations

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("takeout")


_CREATE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    title,
    description,
    body,
    people_text,
    folder,
    source UNINDEXED,
    type UNINDEXED,
    dataset_name UNINDEXED,
    event_id UNINDEXED,
    timestamp UNINDEXED,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


def ensure_fts(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(_CREATE_SQL))


def index_event(
    conn,
    *,
    event_id: int,
    title: str | None,
    description: str | None,
    body: str | None,
    people_text: str | None,
    folder: str | None,
    source: str | None,
    type_: str | None,
    dataset_name: str | None,
    timestamp: str | None,
) -> None:
    conn.execute(
        text(
            "INSERT INTO events_fts (title, description, body, people_text, folder,"
            " source, type, dataset_name, event_id, timestamp) VALUES"
            " (:title,:desc,:body,:ppl,:folder,:source,:type,:ds,:eid,:ts)"
        ),
        {
            "title": title or "",
            "desc": description or "",
            "body": body or "",
            "ppl": people_text or "",
            "folder": folder or "",
            "source": source or "",
            "type": type_ or "",
            "ds": dataset_name or "",
            "eid": event_id,
            "ts": timestamp or "",
        },
    )


def delete_event(conn, event_id: int) -> None:
    conn.execute(text("DELETE FROM events_fts WHERE event_id = :eid"), {"eid": event_id})


def search(
    conn,
    query: str,
    *,
    limit: int = 50,
    offset: int = 0,
    source: str | None = None,
    dataset_name: str | None = None,
) -> list[dict]:
    where = ["events_fts MATCH :q"]
    params: dict = {"q": query}
    if source:
        where.append("source = :source")
        params["source"] = source
    if dataset_name:
        where.append("dataset_name = :ds")
        params["ds"] = dataset_name

    sql = (
        "SELECT event_id, title, description, source, type, dataset_name, timestamp, folder,"
        " bm25(events_fts) AS rank,"
        " snippet(events_fts, 2, '<mark>', '</mark>', '…', 16) AS body_snippet"
        f" FROM events_fts WHERE {' AND '.join(where)}"
        " ORDER BY rank LIMIT :limit OFFSET :offset"
    )
    params["limit"] = limit
    params["offset"] = offset
    rows = conn.execute(text(sql), params).all()
    return [
        {
            "event_id": r.event_id,
            "title": r.title,
            "description": r.description,
            "source": r.source,
            "type": r.type,
            "dataset_name": r.dataset_name,
            "timestamp": r.timestamp,
            "folder": r.folder,
            "rank": r.rank,
            "snippet": r.body_snippet,
        }
        for r in rows
    ]
