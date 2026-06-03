import os
import pytest
from app.importer.paths import resolve_dataset_path, UnsafeDatasetName
from app.config import settings


def test_rejects_path_traversal():
    with pytest.raises(UnsafeDatasetName):
        resolve_dataset_path("../escape")


def test_rejects_slashes():
    with pytest.raises(UnsafeDatasetName):
        resolve_dataset_path("nested/path")


def test_rejects_unknown_dataset():
    with pytest.raises(UnsafeDatasetName):
        resolve_dataset_path("nonexistent_dataset_xyz")


def test_accepts_valid_name(tmp_path, monkeypatch):
    target = settings.imports_dir / "valid_dataset"
    target.mkdir(exist_ok=True)
    try:
        out = resolve_dataset_path("valid_dataset")
        assert out == target.resolve()
    finally:
        target.rmdir()
