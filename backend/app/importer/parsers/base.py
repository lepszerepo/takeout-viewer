"""Shared parser utilities: streaming JSON, HTML helpers, timestamp parsing."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional


_HTML_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    # MyActivity HTML / Google long form, e.g. "Jan 22, 2025, 7:21:03 AM UTC"
    "%b %d, %Y, %I:%M:%S %p %Z",
    "%b %d, %Y, %I:%M:%S %p",
    "%b %d, %Y, %H:%M:%S %Z",
    "%b %d, %Y, %H:%M:%S",
    "%B %d, %Y, %I:%M:%S %p %Z",
    "%B %d, %Y, %I:%M:%S %p",
)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    # Replace non-breaking spaces frequently found in Takeout HTML
    s = s.replace(" ", " ").replace("\xa0", " ")
    # Normalize trailing Z
    if s.endswith("Z") and "T" in s:
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = None
        for fmt in _HTML_DATE_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def from_unix_micros(value: Any) -> Optional[datetime]:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    if v > 10_000_000_000_000:  # microseconds
        return datetime.utcfromtimestamp(v / 1_000_000)
    if v > 10_000_000_000:  # milliseconds
        return datetime.utcfromtimestamp(v / 1_000)
    return datetime.utcfromtimestamp(v)


def stream_json_array(path: Path) -> Iterator[Any]:
    """Best-effort streaming for top-level JSON arrays.

    For Takeout, files are typically arrays of records; using ijson would be
    lighter, but for the MVP this falls back to json.load which is fine for
    files up to a few hundred MB and still cleanly raises on malformed input.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        yield from data
    elif isinstance(data, dict):
        # Some Google JSONs wrap the array in a top-level object
        for key in ("locations", "items", "data", "events", "entries"):
            if key in data and isinstance(data[key], list):
                yield from data[key]
                return
        yield data
    else:
        return


def first_url(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    import re

    m = re.search(r"https?://[^\s\"<>)]+", text)
    return m.group(0) if m else None
