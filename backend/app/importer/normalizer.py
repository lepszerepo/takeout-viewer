"""Normalized event dataclass + helpers used by parsers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .dedupe import stable_hash


@dataclass
class NormalizedEvent:
    source: str
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    url: Optional[str] = None
    service: Optional[str] = None
    category: Optional[str] = None
    people: Optional[Any] = None
    location: Optional[Any] = None
    metadata: Optional[dict] = None
    raw_path: Optional[str] = None
    raw: Optional[Any] = None  # may be discarded if too large

    extra: dict = field(default_factory=dict)

    def compute_hash(self) -> str:
        return stable_hash(
            source=self.source,
            type_=self.type,
            timestamp=self.timestamp,
            title=self.title,
            url=self.url,
            raw_path=self.raw_path,
        )

    def people_json(self) -> Optional[str]:
        return json.dumps(self.people, ensure_ascii=False) if self.people else None

    def location_json(self) -> Optional[str]:
        return json.dumps(self.location, ensure_ascii=False) if self.location else None

    def metadata_json(self) -> Optional[str]:
        return json.dumps(self.metadata, ensure_ascii=False) if self.metadata else None

    def raw_json(self, max_bytes: int) -> Optional[str]:
        if self.raw is None:
            return None
        try:
            encoded = json.dumps(self.raw, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return None
        if len(encoded.encode("utf-8")) > max_bytes:
            return None
        return encoded
