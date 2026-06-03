"""Application configuration loaded from environment variables.

All paths are inside the container. The host bind mount is ./data → /app/data.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Path(os.environ.get("TAKEOUT_DATA_DIR", "/app/data"))
    imports_dir: Path = Path(os.environ.get("TAKEOUT_IMPORTS_DIR", "/app/data/imports"))
    db_path: Path = Path(os.environ.get("TAKEOUT_DB_PATH", "/app/data/db/takeout_viewer.sqlite"))
    logs_dir: Path = Path(os.environ.get("TAKEOUT_LOGS_DIR", "/app/data/logs"))

    ollama_url: str = os.environ.get("TAKEOUT_OLLAMA_URL", "http://host.docker.internal:11434")
    llm_model: str = os.environ.get("TAKEOUT_LLM_MODEL", "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M")
    embed_model: str = os.environ.get("TAKEOUT_EMBED_MODEL", "bge-m3:latest")

    # Performance / safety limits
    max_raw_json_bytes: int = 32_000  # don't persist huge raw payloads
    page_size_default: int = 50
    page_size_max: int = 500

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.imports_dir, self.db_path.parent, self.logs_dir):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
