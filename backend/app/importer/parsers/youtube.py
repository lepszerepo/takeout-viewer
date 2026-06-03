"""YouTube watch / search history parsers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import parse_iso, stream_json_array


def _watch_from_json(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    for rec in stream_json_array(path):
        if not isinstance(rec, dict):
            continue
        title = rec.get("title") or ""
        # YouTube watch entries usually have title like "Watched <video title>"
        clean_title = title.removeprefix("Watched ").strip() or title or None
        url = None
        subtitles = rec.get("subtitles") or []
        channel = None
        if subtitles and isinstance(subtitles, list):
            channel = subtitles[0].get("name") if isinstance(subtitles[0], dict) else None
        title_urls = rec.get("titleUrl")
        if isinstance(title_urls, str):
            url = title_urls
        meta = {k: v for k, v in rec.items() if k in {"products", "header", "activityControls"}}
        if channel:
            meta["channel"] = channel
        yield NormalizedEvent(
            source="youtube",
            service="YouTube",
            category="watch",
            type="youtube_watch",
            title=clean_title,
            description=f"Kanał: {channel}" if channel else None,
            timestamp=parse_iso(rec.get("time")),
            url=url,
            metadata=meta or None,
            raw_path=rel,
            raw=rec,
        )


def _search_from_json(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    for rec in stream_json_array(path):
        if not isinstance(rec, dict):
            continue
        title = rec.get("title") or ""
        query = title.removeprefix("Searched for ").strip() or title or None
        url = rec.get("titleUrl") if isinstance(rec.get("titleUrl"), str) else None
        yield NormalizedEvent(
            source="youtube",
            service="YouTube",
            category="search",
            type="youtube_search",
            title=query,
            timestamp=parse_iso(rec.get("time")),
            url=url,
            raw_path=rel,
            raw=rec,
        )


def _iter_outer_cells(path: Path):
    """Yield (body_text_lines, body_link_or_None) for each outer-cell entry."""
    from bs4 import BeautifulSoup

    with path.open("r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")
    for outer in soup.select("div.outer-cell"):
        body = None
        for c in outer.select("div.content-cell"):
            classes = c.get("class") or []
            if "mdl-typography--body-1" in classes:
                body = c
                break
        if body is None:
            cells = outer.select("div.content-cell")
            body = cells[1] if len(cells) > 1 else (cells[0] if cells else None)
        if body is None:
            continue
        text = body.get_text("\n", strip=True)
        if not text:
            continue
        lines = [ln for ln in text.split("\n") if ln]
        link = body.find("a")
        yield lines, link


def _watch_from_html(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    for lines, link in _iter_outer_cells(path):
        if not lines:
            continue
        action = lines[0]
        url = link.get("href") if link else None
        title = link.get_text(strip=True) if link else (lines[1] if len(lines) > 1 else action)
        if action.lower().startswith("watched"):
            title = title.removeprefix("Watched ").strip()
        timestamp = None
        for ln in reversed(lines):
            ts = parse_iso(ln)
            if ts:
                timestamp = ts
                break
        yield NormalizedEvent(
            source="youtube",
            service="YouTube",
            category="watch",
            type="youtube_watch",
            title=title,
            timestamp=timestamp,
            url=url,
            raw_path=rel,
        )


def _search_from_html(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    for lines, link in _iter_outer_cells(path):
        if not lines:
            continue
        action = lines[0]
        if "search" not in action.lower():
            continue
        url = link.get("href") if link else None
        query = link.get_text(strip=True) if link else (lines[1] if len(lines) > 1 else action)
        timestamp = None
        for ln in reversed(lines):
            ts = parse_iso(ln)
            if ts:
                timestamp = ts
                break
        yield NormalizedEvent(
            source="youtube",
            service="YouTube",
            category="search",
            type="youtube_search",
            title=query,
            timestamp=timestamp,
            url=url,
            raw_path=rel,
        )


def watch_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    if path.suffix.lower() == ".json":
        yield from _watch_from_json(path, rel)
    else:
        yield from _watch_from_html(path, rel)


def search_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    if path.suffix.lower() == ".json":
        yield from _search_from_json(path, rel)
    else:
        yield from _search_from_html(path, rel)


def register_parsers(register) -> None:
    register("youtube", "watch", watch_parser)
    register("youtube", "search", search_parser)
