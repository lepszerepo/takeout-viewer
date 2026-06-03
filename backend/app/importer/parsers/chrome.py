"""Chrome BrowserHistory / Bookmarks parsers."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import from_unix_micros, parse_iso


def _history_from_json(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("Browser History") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return
    for rec in items:
        if not isinstance(rec, dict):
            continue
        url = rec.get("url")
        title = rec.get("title") or url
        ts = from_unix_micros(rec.get("time_usec")) or parse_iso(rec.get("time"))
        yield NormalizedEvent(
            source="chrome",
            service="Chrome",
            category="visit",
            type="chrome_visit",
            title=title,
            url=url,
            timestamp=ts,
            raw_path=rel,
            raw=rec,
        )


def _history_from_csv(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url") or row.get("URL")
            title = row.get("title") or row.get("Title") or url
            ts_raw = row.get("time_usec") or row.get("visit_time") or row.get("time")
            ts = from_unix_micros(ts_raw) if ts_raw and str(ts_raw).isdigit() else parse_iso(ts_raw)
            yield NormalizedEvent(
                source="chrome",
                service="Chrome",
                category="visit",
                type="chrome_visit",
                title=title,
                url=url,
                timestamp=ts,
                raw_path=rel,
            )


def history_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    ext = path.suffix.lower()
    if ext == ".json":
        yield from _history_from_json(path, rel)
    elif ext == ".csv":
        yield from _history_from_csv(path, rel)
    # HTML chrome history is uncommon; treat as unsupported


def bookmarks_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    if path.suffix.lower() != ".html":
        return
    from bs4 import BeautifulSoup

    with path.open("r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")
    for a in soup.find_all("a"):
        url = a.get("href")
        title = a.get_text(strip=True) or url
        ts = None
        if a.get("add_date"):
            try:
                ts = from_unix_micros(int(a["add_date"]) * 1_000_000)
            except ValueError:
                ts = None
        yield NormalizedEvent(
            source="chrome",
            service="Chrome",
            category="bookmark",
            type="chrome_bookmark",
            title=title,
            url=url,
            timestamp=ts,
            raw_path=rel,
        )


def register_parsers(register) -> None:
    register("chrome", "history", history_parser)
    register("chrome", "bookmarks", bookmarks_parser)
