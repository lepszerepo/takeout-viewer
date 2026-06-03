"""Integration test: full import → re-import → dedup across datasets."""
import shutil
from pathlib import Path

from app.config import settings
from app.database import SessionLocal, init_db
from app.importer.importer import import_dataset
from app.models import Event, EventDatasetLink, Dataset


def _prepare_dataset(name: str) -> Path:
    ds = settings.imports_dir / name
    target = ds / "Takeout" / "YouTube and YouTube Music" / "history"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        Path(__file__).parent / "fixtures" / "watch-history.json",
        target / "watch-history.json",
    )
    return ds


def test_full_import_and_cross_dataset_dedup():
    init_db()
    ds1 = _prepare_dataset("test_imp_ds1")
    ds2 = _prepare_dataset("test_imp_ds2")
    try:
        with SessionLocal() as db:
            run1 = import_dataset(db, "test_imp_ds1")
            assert run1.imported_events_count == 2
            assert run1.duplicate_events_count == 0
            run2 = import_dataset(db, "test_imp_ds2")
            # All events are dupes across datasets
            assert run2.imported_events_count == 0
            assert run2.duplicate_events_count == 2

            evs = db.query(Event).all()
            assert len(evs) == 2
            links = db.query(EventDatasetLink).all()
            # 2 events × 2 datasets = 4 links
            assert len(links) == 4

            ds_rows = db.query(Dataset).filter(Dataset.name.in_(["test_imp_ds1", "test_imp_ds2"])).all()
            assert len(ds_rows) == 2

            # Re-importing the same dataset is idempotent
            run3 = import_dataset(db, "test_imp_ds1")
            assert run3.imported_events_count == 0
            assert run3.duplicate_events_count == 2
            assert db.query(Event).count() == 2
    finally:
        shutil.rmtree(ds1, ignore_errors=True)
        shutil.rmtree(ds2, ignore_errors=True)
