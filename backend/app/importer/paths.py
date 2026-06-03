"""Path safety helpers."""
from __future__ import annotations

import re
from pathlib import Path

from ..config import settings


SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")


class UnsafeDatasetName(ValueError):
    pass


def resolve_dataset_path(dataset_name: str) -> Path:
    """Map dataset_name to an absolute path inside imports_dir, rejecting traversal."""
    if not dataset_name or dataset_name in {".", ".."}:
        raise UnsafeDatasetName("Pusta lub niedozwolona nazwa zrzutu.")
    if "/" in dataset_name or "\\" in dataset_name or ".." in dataset_name:
        raise UnsafeDatasetName("Nazwa zrzutu nie może zawierać znaków ścieżki.")
    if not SAFE_NAME_RE.match(dataset_name):
        raise UnsafeDatasetName("Nazwa zrzutu zawiera niedozwolone znaki.")

    base = settings.imports_dir.resolve()
    candidate = (base / dataset_name).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise UnsafeDatasetName("Nazwa zrzutu wskazuje poza katalog importów.") from exc
    if not candidate.exists() or not candidate.is_dir():
        raise UnsafeDatasetName(f"Katalog zrzutu nie istnieje: {dataset_name}")
    return candidate
