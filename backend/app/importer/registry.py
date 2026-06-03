"""Parser registry.

Each parser declares which (service, type) tuples it can handle.
Add a new parser by importing it here and calling `register`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional, Tuple

from .normalizer import NormalizedEvent

ParserFn = Callable[[Path, str], Iterator[NormalizedEvent]]
# parser(path_to_file, relative_path_for_logging) yields NormalizedEvent


_registry: dict[Tuple[str, str], ParserFn] = {}


def register(service: str, type_: str, fn: ParserFn) -> None:
    _registry[(service, type_)] = fn


def find_parser(service: Optional[str], type_: Optional[str]) -> Optional[ParserFn]:
    if not service or not type_:
        return None
    return _registry.get((service, type_))


def iter_supported_kinds() -> Iterable[Tuple[str, str]]:
    return list(_registry.keys())


def _load_parsers() -> None:
    # Local imports to avoid cycles at module import time
    from .parsers import youtube, my_activity, chrome, location, calendar, contacts, mail, tasks, meet, gemini, mail_settings, drive  # noqa: F401

    youtube.register_parsers(register)
    my_activity.register_parsers(register)
    chrome.register_parsers(register)
    location.register_parsers(register)
    calendar.register_parsers(register)
    contacts.register_parsers(register)
    mail.register_parsers(register)
    tasks.register_parsers(register)
    meet.register_parsers(register)
    gemini.register_parsers(register)
    mail_settings.register_parsers(register)
    drive.register_parsers(register)


_load_parsers()
