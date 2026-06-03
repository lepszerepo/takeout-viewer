"""Importer orchestrator.

Run order for a single dataset:
1. resolve dataset path safely
2. open or create Dataset row
3. create ImportRun (status=running)
4. scan files
5. for each file with a parser: parse → normalize → dedupe → insert
6. commit progress periodically
7. write summary
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from ..config import settings
from ..logging_setup import setup_logging
from ..models import (
    Contact,
    Dataset,
    DriveFile,
    Event,
    EventDatasetLink,
    ImportError as ImportErrorRow,
    ImportRun,
    MailMessage,
    SourceFile,
)
from .. import search_index
from .dedupe import stable_hash
from .normalizer import NormalizedEvent
from .paths import resolve_dataset_path
from .registry import find_parser
from .scanner import scan_dataset

logger = setup_logging()


COMMIT_EVERY = 500


def _ensure_dataset(db: Session, dataset_name: str, abs_path: Path) -> Dataset:
    ds = db.query(Dataset).filter_by(name=dataset_name).one_or_none()
    if ds is None:
        ds = Dataset(
            name=dataset_name,
            relative_path=dataset_name,
            absolute_path_internal=str(abs_path),
            status="discovered",
        )
        db.add(ds)
        db.flush()
    return ds


def import_dataset(db: Session, dataset_name: str) -> ImportRun:
    abs_path = resolve_dataset_path(dataset_name)
    dataset = _ensure_dataset(db, dataset_name, abs_path)
    db.commit()  # persist dataset before per-file work that may rollback
    db.refresh(dataset)

    run = ImportRun(dataset_id=dataset.id, status="running")
    db.add(run)
    db.commit()  # persist run too — rollback() during file import must not lose it
    db.refresh(run)

    logger.info("Import started: %s (run=%s)", dataset_name, run.id)

    scanned_count = 0
    supported_count = 0
    imported_count = 0
    duplicate_count = 0
    error_count = 0
    unsupported_types: set[str] = set()
    # Pre-load global hashes of events already in this dataset to skip
    # work on a re-import.
    seen_in_dataset: set[str] = {
        h for (h,) in db.query(Event.global_stable_hash).filter_by(dataset_id=dataset.id).all()
    }

    try:
        for sf in scan_dataset(abs_path):
            scanned_count += 1
            sf_row = SourceFile(
                dataset_id=dataset.id,
                import_run_id=run.id,
                relative_path=sf.relative_path,
                size=sf.size,
                extension=sf.extension,
                guessed_service=sf.guessed_service,
                guessed_type=sf.guessed_type,
                parser_available=sf.parser_available,
                status="pending",
            )
            db.add(sf_row)
            db.flush()

            if not sf.parser_available:
                if sf.guessed_service and sf.guessed_type:
                    unsupported_types.add(f"{sf.guessed_service}:{sf.guessed_type}")
                sf_row.status = "skipped"
                continue

            supported_count += 1
            parser = find_parser(sf.guessed_service, sf.guessed_type)
            if parser is None:  # safety net
                sf_row.status = "skipped"
                continue

            full_path = abs_path / sf.relative_path
            try:
                inserted, dups = _import_file(
                    db,
                    dataset=dataset,
                    run=run,
                    source_file=sf_row,
                    iterator=parser(full_path, sf.relative_path),
                    seen_in_dataset=seen_in_dataset,
                )
                imported_count += inserted
                duplicate_count += dups
                sf_row.status = "ok"
            except Exception as exc:
                error_count += 1
                msg = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Parser error for %s/%s: %s",
                    dataset_name,
                    sf.relative_path,
                    msg,
                )
                # Roll back the poisoned transaction so the next file's
                # inserts can proceed, then re-fetch fresh references for
                # the rows we still need to keep updating.
                db.rollback()
                dataset = db.get(Dataset, dataset.id)
                run = db.get(ImportRun, run.id)
                sf_row = db.get(SourceFile, sf_row.id)
                if sf_row is not None:
                    sf_row.status = "error"
                db.add(
                    ImportErrorRow(
                        import_run_id=run.id,
                        relative_path=sf.relative_path,
                        parser=f"{sf.guessed_service}:{sf.guessed_type}",
                        message=msg[:4000],
                    )
                )
                db.commit()

            if scanned_count % COMMIT_EVERY == 0:
                run.scanned_files_count = scanned_count
                run.imported_events_count = imported_count
                run.duplicate_events_count = duplicate_count
                run.error_count = error_count
                db.commit()

    except Exception as exc:  # catastrophic failure of the whole scan
        error_count += 1
        db.add(
            ImportErrorRow(
                import_run_id=run.id,
                relative_path=None,
                parser="scanner",
                message=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:3000]}",
            )
        )
        run.status = "failed"
    else:
        run.status = "ok" if error_count == 0 else "ok_with_errors"

    run.finished_at = datetime.utcnow()
    run.scanned_files_count = scanned_count
    run.supported_files_count = supported_count
    run.imported_events_count = imported_count
    run.duplicate_events_count = duplicate_count
    run.error_count = error_count
    run.summary = json.dumps({"unsupported_types": sorted(unsupported_types)}, ensure_ascii=False)

    dataset.last_imported_at = run.finished_at
    dataset.status = run.status

    db.commit()
    logger.info(
        "Import finished: %s imported=%s duplicates=%s errors=%s",
        dataset_name,
        imported_count,
        duplicate_count,
        error_count,
    )
    return run


def _import_file(
    db: Session,
    *,
    dataset: Dataset,
    run: ImportRun,
    source_file: SourceFile,
    iterator: Iterable[NormalizedEvent],
    seen_in_dataset: set[str],
) -> tuple[int, int]:
    inserted = 0
    duplicates = 0
    batch = 0
    for norm in iterator:
        # Contacts → also persist into contacts table
        if norm.source == "contacts" and norm.type == "contact":
            _persist_contact(db, dataset=dataset, run=run, norm=norm)

        global_hash = norm.compute_hash()
        local_hash = stable_hash(
            source=norm.source,
            type_=norm.type,
            timestamp=norm.timestamp,
            title=norm.title,
            url=norm.url,
            raw_path=norm.raw_path,
        )

        # Same event already seen within THIS dataset import? Skip entirely
        # (this is what was causing UNIQUE constraint failures before — the
        # same MyActivity entry can appear in multiple HTML files inside a
        # single Takeout split).
        if global_hash in seen_in_dataset:
            # If this is a mail message with new attachment data (sha256),
            # patch the existing mail_messages row so download links work.
            if norm.source == "mail" and norm.type == "mail_message" and norm.extra:
                _patch_existing_mail(db, global_hash=global_hash, norm=norm)
            duplicates += 1
            batch += 1
            if batch >= COMMIT_EVERY:
                db.commit()
                batch = 0
            continue

        existing = (
            db.query(Event).filter(Event.global_stable_hash == global_hash).one_or_none()
        )
        if existing is not None:
            # Duplicate across datasets — add a link the first time we see
            # this event from a new dataset. Guard with an existence check
            # AND with seen_in_dataset to be safe.
            link_exists = (
                db.query(EventDatasetLink)
                .filter_by(event_id=existing.id, dataset_id=dataset.id)
                .one_or_none()
            )
            if link_exists is None:
                db.add(
                    EventDatasetLink(
                        event_id=existing.id,
                        dataset_id=dataset.id,
                        source_file_id=source_file.id,
                        import_run_id=run.id,
                    )
                )
            duplicates += 1
        else:
            event = Event(
                stable_hash=local_hash,
                global_stable_hash=global_hash,
                dataset_id=dataset.id,
                import_run_id=run.id,
                source_file_id=source_file.id,
                source=norm.source,
                service=norm.service,
                category=norm.category,
                type=norm.type,
                title=norm.title,
                description=norm.description,
                timestamp=norm.timestamp,
                end_timestamp=norm.end_timestamp,
                url=norm.url,
                people_json=norm.people_json(),
                location_json=norm.location_json(),
                metadata_json=norm.metadata_json(),
                raw_path=norm.raw_path,
                raw_json=norm.raw_json(settings.max_raw_json_bytes),
            )
            db.add(event)
            db.flush()
            db.add(
                EventDatasetLink(
                    event_id=event.id,
                    dataset_id=dataset.id,
                    source_file_id=source_file.id,
                    import_run_id=run.id,
                )
            )
            # Mail messages: persist full payload to mail_messages table
            mail_body = None
            if norm.source == "mail" and norm.type == "mail_message" and norm.extra:
                _persist_mail(db, event=event, dataset=dataset, norm=norm)
                mail_body = (norm.extra or {}).get("mail_body_text")
                # Concatenate attachment texts into the FTS body so the
                # full message + attachments are searchable as one row
                atts = (norm.extra or {}).get("mail_attachments") or []
                att_texts = [a.get("text") for a in atts if isinstance(a, dict) and a.get("text")]
                if att_texts:
                    mail_body = (mail_body or "") + "\n\n--- Załączniki ---\n" + "\n\n".join(att_texts)
            # Drive files: persist extracted text + info sidecar
            drive_text = None
            if norm.source == "drive" and norm.type == "drive_file" and norm.extra:
                _persist_drive(db, event=event, dataset=dataset, norm=norm)
                drive_text = (norm.extra or {}).get("drive_extracted_text")
            # Push into FTS5 index
            people_text = ""
            if norm.people:
                try:
                    if isinstance(norm.people, dict):
                        flat: list[str] = []
                        for k in ("from", "to", "cc", "bcc"):
                            v = norm.people.get(k) or []
                            if isinstance(v, list):
                                flat.extend(str(x) for x in v)
                        people_text = " ".join(flat)
                    elif isinstance(norm.people, list):
                        people_text = " ".join(str(x) for x in norm.people)
                except Exception:
                    people_text = ""
            folder_val = None
            if isinstance(norm.metadata, dict):
                folder_val = norm.metadata.get("folder")
            search_index.index_event(
                db.connection(),
                event_id=event.id,
                title=norm.title,
                description=norm.description,
                body=mail_body or drive_text,
                people_text=people_text,
                folder=folder_val,
                source=norm.source,
                type_=norm.type,
                dataset_name=dataset.name,
                timestamp=norm.timestamp.isoformat() if norm.timestamp else None,
            )
            inserted += 1

        seen_in_dataset.add(global_hash)

        batch += 1
        if batch >= COMMIT_EVERY:
            db.commit()
            batch = 0

    if batch > 0:
        db.commit()
    return inserted, duplicates


def _patch_existing_mail(db: Session, *, global_hash: str, norm: NormalizedEvent) -> None:
    """For re-imports: refresh attachments_json/body fields on an existing
    mail_messages row so newly-introduced fields (sha256 attachment digests,
    longer body limits, etc.) become available without inserting a new event.
    """
    ev = db.query(Event).filter(Event.global_stable_hash == global_hash).one_or_none()
    if ev is None:
        return
    m = db.query(MailMessage).filter_by(event_id=ev.id).one_or_none()
    if m is None:
        return
    extra = norm.extra or {}
    atts = extra.get("mail_attachments") or []
    if atts:
        m.attachments_json = json.dumps(atts, ensure_ascii=False)
        m.has_attachments = True
    # Update body too if the new parser yielded more text than was stored
    new_body = extra.get("mail_body_text")
    if new_body and (not m.body_text or len(new_body) > len(m.body_text)):
        m.body_text = new_body
    new_html = extra.get("mail_body_html")
    if new_html and (not m.body_html or len(new_html) > len(m.body_html)):
        m.body_html = new_html


def _persist_drive(db: Session, *, event: Event, dataset: Dataset, norm: NormalizedEvent) -> None:
    extra = norm.extra or {}
    info = extra.get("drive_info_json")
    db.add(
        DriveFile(
            event_id=event.id,
            dataset_id=dataset.id,
            file_name=extra.get("drive_file_name"),
            relative_path=extra.get("drive_relative_path") or norm.raw_path or "",
            extension=extra.get("drive_extension"),
            size_bytes=extra.get("drive_size_bytes") or 0,
            mime_type=None,
            extracted_text=extra.get("drive_extracted_text"),
            extraction_status=extra.get("drive_extraction_status") or "unsupported",
            info_json=json.dumps(info, ensure_ascii=False) if info else None,
        )
    )


def _persist_mail(db: Session, *, event: Event, dataset: Dataset, norm: NormalizedEvent) -> None:
    extra = norm.extra or {}
    db.add(
        MailMessage(
            event_id=event.id,
            dataset_id=dataset.id,
            message_id=extra.get("mail_message_id"),
            in_reply_to=extra.get("mail_in_reply_to"),
            references_header=json.dumps(extra.get("mail_references") or [], ensure_ascii=False),
            thread_id=extra.get("mail_thread_id"),
            folder=extra.get("mail_folder"),
            labels=json.dumps(extra.get("mail_labels") or [], ensure_ascii=False),
            from_addr=json.dumps(extra.get("mail_from") or [], ensure_ascii=False),
            to_addrs=json.dumps(extra.get("mail_to") or [], ensure_ascii=False),
            cc_addrs=json.dumps(extra.get("mail_cc") or [], ensure_ascii=False),
            bcc_addrs=json.dumps(extra.get("mail_bcc") or [], ensure_ascii=False),
            reply_to=json.dumps(extra.get("mail_reply_to") or [], ensure_ascii=False),
            subject=extra.get("mail_subject_raw"),
            body_text=extra.get("mail_body_text"),
            body_html=extra.get("mail_body_html"),
            size_bytes=extra.get("mail_size_bytes") or 0,
            has_attachments=bool(extra.get("mail_attachments")),
            attachments_json=json.dumps(extra.get("mail_attachments") or [], ensure_ascii=False),
            headers_json=json.dumps(extra.get("mail_headers") or {}, ensure_ascii=False),
        )
    )


def _persist_contact(db: Session, *, dataset: Dataset, run: ImportRun, norm: NormalizedEvent) -> None:
    emails = norm.people if isinstance(norm.people, list) else None
    phones = (norm.metadata or {}).get("phones") if isinstance(norm.metadata, dict) else None
    chash = stable_hash(
        source="contacts",
        type_="contact",
        timestamp=None,
        title=norm.title,
        url=None,
        raw_path=norm.raw_path,
    )
    exists = (
        db.query(Contact)
        .filter_by(dataset_id=dataset.id, stable_hash=chash)
        .one_or_none()
    )
    if exists is not None:
        return
    db.add(
        Contact(
            dataset_id=dataset.id,
            import_run_id=run.id,
            stable_hash=chash,
            display_name=norm.title,
            emails_json=json.dumps(emails, ensure_ascii=False) if emails else None,
            phones_json=json.dumps(phones, ensure_ascii=False) if phones else None,
            raw_path=norm.raw_path,
            metadata_json=norm.metadata_json(),
        )
    )
