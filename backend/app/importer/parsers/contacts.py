"""Contacts vCard (.vcf) / CSV parser.

Contacts are first-class entities in the data model (Contact table), but we
also emit one Event per contact so they appear on the timeline.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent


_VCARD_BLOCK_RE = re.compile(r"BEGIN:VCARD(.*?)END:VCARD", re.DOTALL | re.IGNORECASE)


def _parse_vcard_block(block: str) -> dict:
    out: dict = {"emails": [], "phones": []}
    for line in block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key_main = key.split(";", 1)[0].upper()
        if key_main == "FN":
            out["display_name"] = value.strip()
        elif key_main == "N" and not out.get("display_name"):
            out["display_name"] = value.replace(";", " ").strip()
        elif key_main == "EMAIL":
            out["emails"].append(value.strip())
        elif key_main == "TEL":
            out["phones"].append(value.strip())
    return out


def vcf_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in _VCARD_BLOCK_RE.finditer(text):
        parsed = _parse_vcard_block(m.group(1))
        name = parsed.get("display_name") or "Kontakt"
        yield NormalizedEvent(
            source="contacts",
            service="Kontakty Google",
            category="contact",
            type="contact",
            title=name,
            description=", ".join(parsed.get("emails") or []) or None,
            people=parsed.get("emails") or None,
            metadata={"phones": parsed.get("phones") or []},
            raw_path=rel,
        )


def csv_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (
                row.get("Name")
                or row.get("name")
                or " ".join(filter(None, [row.get("Given Name"), row.get("Family Name")]))
                or row.get("E-mail 1 - Value")
                or "Kontakt"
            )
            emails = [v for k, v in row.items() if k and "mail" in k.lower() and v]
            phones = [v for k, v in row.items() if k and "phone" in k.lower() and v]
            yield NormalizedEvent(
                source="contacts",
                service="Kontakty Google",
                category="contact",
                type="contact",
                title=name.strip() or "Kontakt",
                description=", ".join(emails) or None,
                people=emails or None,
                metadata={"phones": phones},
                raw_path=rel,
            )


def contacts_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    """Dispatch by extension — same (service, type) for vCard and CSV."""
    if path.suffix.lower() == ".csv":
        yield from csv_parser(path, rel)
    else:
        yield from vcf_parser(path, rel)


def register_parsers(register) -> None:
    register("contacts", "vcf", contacts_parser)
