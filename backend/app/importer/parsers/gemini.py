"""Gemini Apps parser.

Two file types observed:
- gemini_scheduled_actions_data.html / gemini_gems_data.html — top-level Gemini export (often empty for non-users)
- Takeout/My Activity/Gemini Apps/MyActivity.html — actual conversations (handled by my_activity parser already)

This parser focuses on the top-level Gemini export. We extract any
conversation-like blocks. If the file is essentially empty, we silently
emit nothing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import parse_iso


def gemini_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    from bs4 import BeautifulSoup

    with path.open("r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    blocks = soup.select("div.outer-cell") or soup.select("div.content-cell")
    if not blocks:
        return
    for blk in blocks:
        text = blk.get_text("\n", strip=True)
        if not text:
            continue
        lines = [ln for ln in text.split("\n") if ln]
        title = lines[0][:300] if lines else "Gemini activity"
        timestamp = None
        for ln in reversed(lines):
            ts = parse_iso(ln)
            if ts:
                timestamp = ts
                break
        yield NormalizedEvent(
            source="gemini",
            service="Gemini",
            category="ai",
            type="gemini_activity",
            title=title,
            description="\n".join(lines[:8])[:800] if lines else None,
            timestamp=timestamp,
            raw_path=f"{rel}#{hash(text) & 0xffffffff:08x}",
        )


def register_parsers(register) -> None:
    register("gemini", "html", gemini_parser)
