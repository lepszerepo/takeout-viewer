"""Calendar .ics parser using the `ics` library."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent


def _arrow_to_dt(value):
    if value is None:
        return None
    try:
        return value.datetime.replace(tzinfo=None)
    except AttributeError:
        return None


def ics_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    from ics import Calendar

    with path.open("r", encoding="utf-8", errors="replace") as f:
        try:
            cal = Calendar(f.read())
        except Exception as exc:
            # Bubble up as parser error
            raise ValueError(f"Niepoprawny plik .ics: {exc}") from exc
    for ev in cal.events:
        attendees = []
        try:
            attendees = [a.email for a in ev.attendees if getattr(a, "email", None)]
        except Exception:
            attendees = []
        yield NormalizedEvent(
            source="calendar",
            service="Kalendarz Google",
            category="calendar",
            type="calendar_event",
            title=ev.name or "Wydarzenie",
            description=ev.description,
            timestamp=_arrow_to_dt(ev.begin),
            end_timestamp=_arrow_to_dt(ev.end),
            location={"name": ev.location} if ev.location else None,
            people=attendees or None,
            raw_path=rel,
        )


def register_parsers(register) -> None:
    register("calendar", "ics", ics_parser)
