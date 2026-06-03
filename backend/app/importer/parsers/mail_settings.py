"""Gmail settings parser: Signatures, Vacation Responder, Blocked Addresses, Delegates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from ..normalizer import NormalizedEvent


def settings_parser(path: Path, rel: str) -> Iterator[NormalizedEvent]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    name = path.stem.lower()
    if "signature" in name:
        sigs = data.get("signatures") if isinstance(data, dict) else None
        if isinstance(sigs, list):
            for s in sigs:
                if not isinstance(s, dict):
                    continue
                yield NormalizedEvent(
                    source="mail",
                    service="Gmail",
                    category="settings",
                    type="mail_signature",
                    title=f"Sygnatura: {s.get('alias') or s.get('email') or 'domyślna'}",
                    description=s.get("signature"),
                    metadata={"alias": s.get("alias"), "email": s.get("email")},
                    raw_path=f"{rel}#sig-{s.get('email','')}",
                )
        return

    if "vacation" in name:
        if isinstance(data, dict):
            yield NormalizedEvent(
                source="mail",
                service="Gmail",
                category="settings",
                type="mail_vacation",
                title=data.get("subject") or "Vacation Responder",
                description=data.get("body"),
                metadata={
                    "enabled": data.get("enabled"),
                    "start": data.get("startTime"),
                    "end": data.get("endTime"),
                    "restrict_to_contacts": data.get("restrictToContacts"),
                    "restrict_to_domain": data.get("restrictToDomain"),
                },
                raw_path=f"{rel}#vacation",
            )
        return

    if "blocked" in name:
        addrs = data.get("blocked_addresses") if isinstance(data, dict) else None
        if isinstance(addrs, list):
            for a in addrs:
                if isinstance(a, str):
                    yield NormalizedEvent(
                        source="mail",
                        service="Gmail",
                        category="settings",
                        type="mail_blocked_address",
                        title=f"Zablokowany: {a}",
                        people=[a],
                        raw_path=f"{rel}#{a}",
                    )
        return

    if "delegated" in name or "delegate" in name:
        delegs = data.get("delegated_addresses") if isinstance(data, dict) else None
        if isinstance(delegs, list):
            for d in delegs:
                addr = d if isinstance(d, str) else (d.get("address") if isinstance(d, dict) else None)
                if addr:
                    yield NormalizedEvent(
                        source="mail",
                        service="Gmail",
                        category="settings",
                        type="mail_delegate",
                        title=f"Delegat: {addr}",
                        people=[addr],
                        raw_path=f"{rel}#{addr}",
                    )


def register_parsers(register) -> None:
    register("mail", "settings", settings_parser)
