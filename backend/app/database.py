"""SQLAlchemy engine + session helpers.

SQLite is used in MVP, but the layer is built so swapping to PostgreSQL
is just a matter of changing the DB URL and removing the SQLite pragmas.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import settings

_connect_args: dict = {}
if settings.db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.db_url,
    echo=False,
    connect_args=_connect_args,
    future=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _):  # pragma: no cover
    if not settings.db_url.startswith("sqlite"):
        return
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    # Retry up to 30s instead of returning 'database is locked' immediately
    cur.execute("PRAGMA busy_timeout=120000;")
    cur.close()
    # Load sqlite-vec extension on every new connection. Without this
    # the pool can hand out connections that don't have the vec0 module.
    try:
        import sqlite_vec  # type: ignore
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)
    except Exception:
        # Extension not available — semantic-search endpoints will 500
        # but everything else continues to work.
        pass


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

Base = declarative_base()


def get_db() -> Session:  # FastAPI dependency
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables (+ FTS5 index) if they don't yet exist."""
    from . import models  # noqa: F401  ensure models are registered
    from . import search_index

    settings.ensure_dirs()
    Base.metadata.create_all(bind=engine)
    search_index.ensure_fts(engine)
