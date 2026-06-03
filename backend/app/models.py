"""SQLAlchemy ORM models for Takeout Viewer.

Design choice for MVP: an event lives in a single dataset row, but every
event also stores a `global_stable_hash` so we can detect that the same
event was already imported from a different dataset. When that happens
we create an `EventDatasetLink` row pointing at the *original* event
instead of inserting a duplicate.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    BigInteger,
    Boolean,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    relative_path = Column(String(1024), nullable=False)
    absolute_path_internal = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    last_imported_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="discovered", nullable=False)
    notes = Column(Text, nullable=True)

    events = relationship("Event", back_populates="dataset", cascade="all,delete-orphan")
    import_runs = relationship("ImportRun", back_populates="dataset", cascade="all,delete-orphan")


class ImportRun(Base):
    __tablename__ = "import_runs"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    started_at = Column(DateTime, default=_utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="running", nullable=False)
    scanned_files_count = Column(Integer, default=0, nullable=False)
    supported_files_count = Column(Integer, default=0, nullable=False)
    imported_events_count = Column(Integer, default=0, nullable=False)
    duplicate_events_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    summary = Column(Text, nullable=True)

    dataset = relationship("Dataset", back_populates="import_runs")
    errors = relationship("ImportError", back_populates="import_run", cascade="all,delete-orphan")
    source_files = relationship("SourceFile", back_populates="import_run", cascade="all,delete-orphan")


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path = Column(String(1024), nullable=False)
    size = Column(BigInteger, default=0, nullable=False)
    extension = Column(String(32), nullable=True)
    guessed_service = Column(String(64), nullable=True, index=True)
    guessed_type = Column(String(64), nullable=True, index=True)
    parser_available = Column(Boolean, default=False, nullable=False)
    file_hash = Column(String(64), nullable=True)
    status = Column(String(32), default="pending", nullable=False)

    import_run = relationship("ImportRun", back_populates="source_files")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    stable_hash = Column(String(64), nullable=False, index=True)
    global_stable_hash = Column(String(64), nullable=False, unique=True, index=True)

    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    source_file_id = Column(Integer, ForeignKey("source_files.id", ondelete="SET NULL"), nullable=True, index=True)

    source = Column(String(64), nullable=False, index=True)
    service = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=True, index=True)
    type = Column(String(64), nullable=True, index=True)
    title = Column(String(1024), nullable=True, index=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=True, index=True)
    end_timestamp = Column(DateTime, nullable=True)
    url = Column(Text, nullable=True)
    people_json = Column(Text, nullable=True)
    location_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    raw_path = Column(String(1024), nullable=True)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="events")
    links = relationship("EventDatasetLink", back_populates="event", cascade="all,delete-orphan")

    __table_args__ = (
        Index("ix_events_source_type_ts", "source", "type", "timestamp"),
    )


class EventDatasetLink(Base):
    """Tracks every dataset in which a given event was observed.

    The 'primary' dataset is also stored on Event.dataset_id; this table
    additionally records other datasets that contained the same event.
    """
    __tablename__ = "event_dataset_links"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    source_file_id = Column(Integer, ForeignKey("source_files.id", ondelete="SET NULL"), nullable=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    event = relationship("Event", back_populates="links")

    __table_args__ = (
        UniqueConstraint("event_id", "dataset_id", name="uq_event_dataset"),
    )


class ImportError(Base):
    __tablename__ = "import_errors"

    id = Column(Integer, primary_key=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_path = Column(String(1024), nullable=True)
    parser = Column(String(64), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    import_run = relationship("ImportRun", back_populates="errors")


class MailMessage(Base):
    """Full email payload — body, HTML, threading. One row per Event(mail_message)."""
    __tablename__ = "mail_messages"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String(512), nullable=True, index=True)
    in_reply_to = Column(String(512), nullable=True, index=True)
    references_header = Column(Text, nullable=True)
    thread_id = Column(String(512), nullable=True, index=True)  # derived
    folder = Column(String(64), nullable=True, index=True)
    labels = Column(Text, nullable=True)  # JSON list
    from_addr = Column(Text, nullable=True)
    to_addrs = Column(Text, nullable=True)  # JSON list
    cc_addrs = Column(Text, nullable=True)
    bcc_addrs = Column(Text, nullable=True)
    reply_to = Column(Text, nullable=True)
    subject = Column(Text, nullable=True, index=True)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    size_bytes = Column(Integer, default=0, nullable=False)
    has_attachments = Column(Boolean, default=False, nullable=False)
    attachments_json = Column(Text, nullable=True)  # filenames + sizes
    headers_json = Column(Text, nullable=True)  # selected raw headers
    embedding_status = Column(String(16), default="pending", nullable=False, index=True)
    cluster_id = Column(Integer, nullable=True, index=True)
    ai_summary = Column(Text, nullable=True)
    ai_category = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class MailEmbedding(Base):
    """Vector embedding storage. Vectors live in sqlite-vec virtual table; this
    row tracks one-to-one mapping + model used."""
    __tablename__ = "mail_embeddings"

    id = Column(Integer, primary_key=True)
    mail_id = Column(Integer, ForeignKey("mail_messages.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    model = Column(String(128), nullable=False)
    dim = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class DriveFile(Base):
    """Drive file metadata + extracted text. One row per file in Takeout/Drive."""
    __tablename__ = "drive_files"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(512), nullable=True, index=True)
    relative_path = Column(Text, nullable=False)
    extension = Column(String(32), nullable=True, index=True)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    mime_type = Column(String(128), nullable=True)
    extracted_text = Column(Text, nullable=True)
    extraction_status = Column(String(16), default="pending", nullable=False, index=True)
    info_json = Column(Text, nullable=True)  # paired .json-info content if any
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class Topic(Base):
    """A discovered topic cluster (KMeans/HDBSCAN). Label generated by LLM."""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, nullable=False, unique=True, index=True)
    algorithm = Column(String(32), default="kmeans", nullable=False)
    label = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    size = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class Entity(Base):
    """Unique extracted entity (person, organization, money, date, location).

    Normalization rule: `key` = lower-cased text with whitespace collapsed,
    so 'Aleksandra Górka' and 'aleksandra górka' merge into one row.
    """
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    kind = Column(String(32), nullable=False, index=True)  # PERSON / ORG / GPE / LOC / MONEY / DATE / EMAIL / URL
    key = Column(String(512), nullable=False, index=True)
    label = Column(String(512), nullable=True)  # display text (best-cased)
    count = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("kind", "key", name="uq_entity_kind_key"),
        Index("ix_entities_kind_count", "kind", "count"),
    )


class EntityMention(Base):
    """A mention of an entity inside a specific event's text."""
    __tablename__ = "entity_mentions"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    span_text = Column(String(512), nullable=True)
    context = Column(Text, nullable=True)  # short surrounding text snippet
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class NerStatus(Base):
    """Tracks whether each event has been processed by NER."""
    __tablename__ = "ner_status"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    processed_at = Column(DateTime, default=_utcnow, nullable=False)
    model = Column(String(64), nullable=True)
    error = Column(Text, nullable=True)


class GraphEdge(Base):
    """Weighted edge between two graph nodes.

    Node references are kept as strings (e.g. email addresses or
    entity_id-prefixed identifiers) to allow mixing different node types.
    """
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True)
    src = Column(String(256), nullable=False, index=True)
    dst = Column(String(256), nullable=False, index=True)
    relation = Column(String(64), nullable=False, index=True)  # mail / meet / mention / shared_doc
    weight = Column(Integer, default=1, nullable=False)
    last_seen = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("src", "dst", "relation", name="uq_graph_edge"),
    )


class Contact(Base):
    """Optional separate entity for Contacts service."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="SET NULL"), nullable=True)
    stable_hash = Column(String(64), nullable=False, index=True)
    display_name = Column(String(512), nullable=True)
    emails_json = Column(Text, nullable=True)
    phones_json = Column(Text, nullable=True)
    raw_path = Column(String(1024), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("dataset_id", "stable_hash", name="uq_contact_dataset_hash"),
    )
