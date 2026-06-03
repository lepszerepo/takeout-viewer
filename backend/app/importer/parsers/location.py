"""Location History parser.

Supports the classic Records.json layout (top-level "locations" array).
Lat/lng are stored as integers × 1e7 in Google's export.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent
from .base import from_unix_micros, parse_iso


def _to_deg(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if abs(f) > 360:  # encoded as int 1e7
        return f / 1e7
    return f


def records_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    locations = data.get("locations") if isinstance(data, dict) else None
    if not isinstance(locations, list):
        return
    for rec in locations:
        if not isinstance(rec, dict):
            continue
        lat = _to_deg(rec.get("latitudeE7") or rec.get("latitude"))
        lng = _to_deg(rec.get("longitudeE7") or rec.get("longitude"))
        if lat is None or lng is None:
            continue
        ts = (
            parse_iso(rec.get("timestamp"))
            or from_unix_micros(rec.get("timestampMs"))
        )
        accuracy = rec.get("accuracy")
        url = f"https://www.google.com/maps?q={lat},{lng}"
        yield NormalizedEvent(
            source="location",
            service="Historia lokalizacji",
            category="location",
            type="location_point",
            title=f"{lat:.5f}, {lng:.5f}",
            description=f"Dokładność: ±{accuracy} m" if accuracy is not None else None,
            timestamp=ts,
            url=url,
            location={"lat": lat, "lng": lng, "accuracy": accuracy},
            raw_path=rel,
        )


def register_parsers(register) -> None:
    register("location", "records", records_parser)
    register("location", "history", records_parser)
