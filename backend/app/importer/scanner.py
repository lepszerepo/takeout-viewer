"""Filesystem scanner.

Lists datasets in imports/ and classifies files inside a dataset.
The scanner never reads file contents — only paths/sizes/extensions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List

from ..config import settings


@dataclass
class ScannedFile:
    dataset_name: str
    relative_path: str  # relative to dataset root
    size: int
    extension: str
    guessed_service: str | None
    guessed_type: str | None
    parser_available: bool


def list_datasets() -> List[Path]:
    base = settings.imports_dir
    if not base.exists():
        return []
    return sorted(
        [p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")],
        key=lambda p: p.name,
    )


# (service, type) classification by path heuristics.
_HEURISTICS: list[tuple[tuple[str, ...], tuple[str, str]]] = [
    (("YouTube and YouTube Music", "history", "watch-history"), ("youtube", "watch")),
    (("YouTube", "history", "watch-history"), ("youtube", "watch")),
    (("YouTube and YouTube Music", "history", "search-history"), ("youtube", "search")),
    (("YouTube", "history", "search-history"), ("youtube", "search")),
    (("YouTube and YouTube Music", "subscriptions"), ("youtube", "subscriptions")),
    (("YouTube", "subscriptions"), ("youtube", "subscriptions")),
    (("YouTube and YouTube Music", "comments"), ("youtube", "comments")),
    (("YouTube", "comments"), ("youtube", "comments")),

    (("My Activity",), ("my_activity", "activity")),
    (("Moja aktywność",), ("my_activity", "activity")),

    (("Chrome", "BrowserHistory"), ("chrome", "history")),
    (("Chrome", "Bookmarks"), ("chrome", "bookmarks")),
    (("Chrome",), ("chrome", "other")),

    (("Location History", "Records"), ("location", "records")),
    (("Location History",), ("location", "history")),
    (("Historia lokalizacji",), ("location", "history")),
    (("Semantic Location History",), ("location", "semantic")),

    (("Calendar",), ("calendar", "ics")),
    (("Kalendarz",), ("calendar", "ics")),

    (("Contacts",), ("contacts", "vcf")),
    (("Kontakty",), ("contacts", "vcf")),

    (("Tasks",), ("tasks", "task")),
    (("Zadania",), ("tasks", "task")),

    (("Google Meet", "ConferenceHistory"), ("meet", "conference")),

    (("Gemini",), ("gemini", "html")),

    (("Mail", "User Settings"), ("mail", "settings")),
    (("Poczta", "User Settings"), ("mail", "settings")),

    (("Mail",), ("mail", "mbox")),
    (("Poczta",), ("mail", "mbox")),

    (("Drive",), ("drive", "file")),
    (("Maps",), ("maps", "place")),
    (("Google Photos",), ("photos", "media")),
    (("Search",), ("search", "history")),
    (("Assistant",), ("assistant", "activity")),
    (("Fit",), ("fit", "activity")),
    (("Keep",), ("keep", "note")),
    (("Tasks",), ("tasks", "task")),
    (("Ads",), ("ads", "activity")),
    (("Play Store",), ("play", "install")),
]


# Set of (service, type) for which we have a parser
def _parser_available_set() -> set[tuple[str, str]]:
    from .registry import iter_supported_kinds  # local import to avoid cycle
    return set(iter_supported_kinds())


def classify(rel_path: str, ext: str) -> tuple[str | None, str | None]:
    parts_lower = rel_path.replace("\\", "/").split("/")
    haystack = "/".join(parts_lower)
    for keywords, kind in _HEURISTICS:
        if all(kw in haystack for kw in keywords):
            return kind
    return None, None


def scan_dataset(dataset_path: Path) -> Iterable[ScannedFile]:
    supported = _parser_available_set()
    dataset_name = dataset_path.name
    for p in dataset_path.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(dataset_path).as_posix()
        except ValueError:
            continue
        size = p.stat().st_size
        ext = p.suffix.lower().lstrip(".")
        svc, typ = classify(rel, ext)
        parser_ok = bool(svc and typ and (svc, typ) in supported and _file_ext_supported(svc, typ, ext))
        yield ScannedFile(
            dataset_name=dataset_name,
            relative_path=rel,
            size=size,
            extension=ext,
            guessed_service=svc,
            guessed_type=typ,
            parser_available=parser_ok,
        )


# A parser may declare which extensions it accepts; default = json/html/csv/ics/vcf
_DEFAULT_EXT_BY_SERVICE: dict[str, set[str]] = {
    "youtube": {"json", "html"},
    "my_activity": {"json", "html"},
    "chrome": {"json", "html", "csv"},
    "location": {"json"},
    "calendar": {"ics"},
    "contacts": {"vcf", "csv"},
    "mail": {"mbox", "json"},  # json for settings files
    "tasks": {"tasks", "json"},
    "meet": {"csv"},
    "gemini": {"html"},
    "drive": {
        "pdf", "docx", "doc", "xlsx", "xlsm", "pptx", "ppt",
        "txt", "csv", "md", "json", "html", "xml", "tsv", "log", "svg",
        "jpg", "jpeg", "png", "heic", "heif", "tif", "tiff", "bmp", "webp",
    },
}


def _file_ext_supported(svc: str, _typ: str, ext: str) -> bool:
    allowed = _DEFAULT_EXT_BY_SERVICE.get(svc)
    if not allowed:
        return False
    return ext in allowed


def manifest_from(scanned: Iterable[ScannedFile]) -> list[dict]:
    return [asdict(s) for s in scanned]
