"""Google Meet ConferenceHistory parser.

CSV format:
  Owner Gaia Id, Item Id, Conference Id, Item Type, Meeting Code, Event Id,
  Thread Id, Inbox Id, Call Direction, Start Time, End Time, Duration,
  Direct Call Result, Participation State, Call Counterparts, Meeting Media Type
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import parse_iso


def meet_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = parse_iso(row.get("Start Time"))
            end = parse_iso(row.get("End Time"))
            code = row.get("Meeting Code") or ""
            participation = row.get("Participation State") or ""
            duration = row.get("Duration") or ""
            counterparts = row.get("Call Counterparts") or ""
            title = f"Spotkanie Meet ({code or 'brak kodu'})"
            description = f"Status: {participation}; czas trwania: {duration}"
            url = f"https://meet.google.com/{code}" if code else None
            yield NormalizedEvent(
                source="meet",
                service="Google Meet",
                category="meeting",
                type="meet_conference",
                title=title,
                description=description,
                timestamp=start,
                end_timestamp=end,
                url=url,
                people=[c.strip() for c in counterparts.split(",") if c.strip()] or None,
                metadata={
                    "meeting_code": code,
                    "duration": duration,
                    "participation": participation,
                    "media_type": row.get("Meeting Media Type"),
                    "direction": row.get("Call Direction"),
                    "result": row.get("Direct Call Result"),
                },
                raw_path=f"{rel}#{row.get('Item Id') or row.get('Conference Id')}",
            )


def register_parsers(register) -> None:
    register("meet", "conference", meet_parser)
