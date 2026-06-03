import shutil
from pathlib import Path

from app.config import settings
from app.importer.scanner import scan_dataset, manifest_from


def test_scanner_classifies_youtube_watch(tmp_path):
    ds = settings.imports_dir / "test_scanner_ds"
    ds.mkdir(parents=True, exist_ok=True)
    try:
        target_dir = ds / "Takeout" / "YouTube and YouTube Music" / "history"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "watch-history.json"
        shutil.copy(
            Path(__file__).parent / "fixtures" / "watch-history.json", target_file
        )

        manifest = manifest_from(scan_dataset(ds))
        watch = next(
            (m for m in manifest if m["relative_path"].endswith("watch-history.json")),
            None,
        )
        assert watch is not None
        assert watch["guessed_service"] == "youtube"
        assert watch["guessed_type"] == "watch"
        assert watch["parser_available"] is True
    finally:
        shutil.rmtree(ds)
