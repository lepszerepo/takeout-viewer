"""Stable hashing for deduplication."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _norm_ts(ts: Optional[datetime]) -> str:
    if not ts:
        return ""
    # Truncate to seconds, ignore timezone differences caused by parsing
    return ts.replace(microsecond=0).isoformat()


def stable_hash(
    source: str,
    type_: Optional[str],
    timestamp: Optional[datetime],
    title: Optional[str],
    url: Optional[str],
    raw_path: Optional[str] = None,
) -> str:
    """Hash an event in a way that's resilient to Takeout re-export quirks.

    If timestamp is missing, fallback uses raw_path to keep duplicates within
    the same file collapsing, but still distinguishes the same title/url
    across different files.
    """
    if timestamp:
        material = "|".join([
            _norm(source),
            _norm(type_),
            _norm_ts(timestamp),
            _norm(title),
            _norm(url),
        ])
    else:
        material = "|".join([
            _norm(source),
            _norm(type_),
            _norm(title),
            _norm(url),
            _norm(raw_path),
        ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
