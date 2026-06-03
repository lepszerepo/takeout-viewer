"""File-based technical logging without persisting sensitive payloads."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import settings

_initialized = False


def setup_logging() -> logging.Logger:
    global _initialized
    settings.ensure_dirs()

    logger = logging.getLogger("takeout")
    if _initialized:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    file_handler = RotatingFileHandler(
        settings.logs_dir / "backend.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    logger.handlers = [file_handler, stream_handler]
    logger.propagate = False
    _initialized = True
    return logger
