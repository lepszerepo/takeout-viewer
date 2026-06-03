"""Pytest configuration: set env vars before importing the app."""
import os
import tempfile
from pathlib import Path

tmp_root = Path(tempfile.mkdtemp(prefix="takeout-test-"))
os.environ.setdefault("TAKEOUT_DATA_DIR", str(tmp_root))
os.environ.setdefault("TAKEOUT_IMPORTS_DIR", str(tmp_root / "imports"))
os.environ.setdefault("TAKEOUT_DB_PATH", str(tmp_root / "db" / "test.sqlite"))
os.environ.setdefault("TAKEOUT_LOGS_DIR", str(tmp_root / "logs"))

(tmp_root / "imports").mkdir(parents=True, exist_ok=True)
(tmp_root / "db").mkdir(parents=True, exist_ok=True)
(tmp_root / "logs").mkdir(parents=True, exist_ok=True)
