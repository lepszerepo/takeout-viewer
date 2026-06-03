"""Google My Activity parser. Handles both JSON and HTML exports."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import parse_iso, stream_json_array


def _product_to_service(product: str | None) -> tuple[str, str]:
    """Map MyActivity product string → (source, service)."""
    p = (product or "").lower()
    if "youtube" in p:
        return ("youtube", "YouTube")
    if "chrome" in p:
        return ("chrome", "Chrome")
    if "search" in p:
        return ("search", "Wyszukiwarka Google")
    if "maps" in p:
        return ("maps", "Mapy Google")
    if "assistant" in p:
        return ("assistant", "Asystent Google")
    if "ads" in p:
        return ("ads", "Reklamy Google")
    if "play" in p:
        return ("play", "Google Play")
    if "image" in p:
        return ("search", "Wyszukiwarka grafik")
    if "discover" in p:
        return ("search", "Google Discover")
    if "news" in p:
        return ("search", "Google News")
    return ("my_activity", product or "Aktywność Google")


def _activity_from_json(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    for rec in stream_json_array(path):
        if not isinstance(rec, dict):
            continue
        product = rec.get("header") or rec.get("product")
        source, service = _product_to_service(product if isinstance(product, str) else None)
        title = rec.get("title") or ""
        url = rec.get("titleUrl") if isinstance(rec.get("titleUrl"), str) else None
        details = rec.get("details") or []
        description = None
        if isinstance(details, list) and details:
            description = ", ".join(
                d.get("name", "") for d in details if isinstance(d, dict) and d.get("name")
            ) or None
        # Pick a sensible activity type for known patterns
        activity_type = "my_activity"
        if source == "youtube" and title.startswith("Watched "):
            activity_type = "youtube_watch"
            title = title.removeprefix("Watched ").strip()
        elif source == "youtube" and title.startswith("Searched for "):
            activity_type = "youtube_search"
            title = title.removeprefix("Searched for ").strip()
        elif source == "chrome" and title.startswith("Visited "):
            activity_type = "chrome_visit"
            title = title.removeprefix("Visited ").strip()
        elif source == "search" and title.startswith("Searched for "):
            activity_type = "search_query"
            title = title.removeprefix("Searched for ").strip()
        elif source == "assistant":
            activity_type = "assistant_activity"
        elif source == "maps":
            activity_type = "maps_place"
        elif source == "play":
            activity_type = "play_install"
        elif source == "ads":
            activity_type = "ads_activity"

        yield NormalizedEvent(
            source=source,
            service=service,
            category="activity",
            type=activity_type,
            title=title or None,
            description=description,
            timestamp=parse_iso(rec.get("time")),
            url=url,
            raw_path=rel,
            raw=rec,
        )


def _activity_from_html(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    from bs4 import BeautifulSoup

    # MyActivity HTML files can be hundreds of MB; BeautifulSoup loads the
    # whole document into memory. For MVP this is acceptable — the importer
    # reports an ImportError if parsing fails.
    with path.open("r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    # Each activity entry lives in a single div.outer-cell. The product
    # ("Gmail", "YouTube", "Chrome"...) is in the page-level header-cell.
    header_div = soup.find("div", class_="header-cell")
    product = header_div.get_text(strip=True) if header_div else None
    source, service = _product_to_service(product)

    for outer in soup.select("div.outer-cell"):
        # The main content cell has class mdl-typography--body-1 (or the
        # first content-cell with non-empty link). Caption cell has class
        # mdl-typography--caption and contains "Products:" / "Why is this".
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
        url = link.get("href") if link else None
        # First line is the action verb (e.g. "Searched for", "Visited"),
        # next line(s) are the subject, last line is the date.
        action = lines[0] if lines else ""
        title = link.get_text(strip=True) if link else (lines[1] if len(lines) > 1 else action)

        timestamp = None
        for ln in reversed(lines):
            ts = parse_iso(ln)
            if ts:
                timestamp = ts
                break

        # Map the action verb to a richer type
        activity_type = "my_activity"
        action_lc = action.lower()
        if source == "youtube" and action_lc.startswith("watched"):
            activity_type = "youtube_watch"
        elif source == "youtube" and action_lc.startswith("searched"):
            activity_type = "youtube_search"
        elif source == "chrome" and action_lc.startswith("visited"):
            activity_type = "chrome_visit"
        elif source == "search" and action_lc.startswith("searched"):
            activity_type = "search_query"
        elif source == "assistant":
            activity_type = "assistant_activity"
        elif source == "maps":
            activity_type = "maps_place"
        elif source == "play":
            activity_type = "play_install"
        elif source == "ads":
            activity_type = "ads_activity"
        elif source == "my_activity" and action_lc.startswith("searched"):
            activity_type = "search_query"

        yield NormalizedEvent(
            source=source,
            service=service,
            category="activity",
            type=activity_type,
            title=title,
            description=action or None,
            timestamp=timestamp,
            url=url,
            raw_path=rel,
        )


def activity_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    if path.suffix.lower() == ".json":
        yield from _activity_from_json(path, rel)
    else:
        yield from _activity_from_html(path, rel)


def register_parsers(register) -> None:
    register("my_activity", "activity", activity_parser)
