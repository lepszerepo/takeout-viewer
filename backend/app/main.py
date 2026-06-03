"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_datasets, routes_entities, routes_events, routes_graph, routes_imports, routes_llm, routes_mail, routes_person, routes_search, routes_sources
from .config import settings
from .database import init_db
from .logging_setup import setup_logging

logger = setup_logging()


def create_app() -> FastAPI:
    settings.ensure_dirs()
    init_db()

    app = FastAPI(
        title="Takeout Viewer",
        description=(
            "Lokalna przeglądarka archiwów Google Takeout. "
            "Wszystkie dane pozostają na komputerze użytkownika."
        ),
        version="0.1.0",
    )

    # CORS: only the local Vite dev server / docker-compose frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_datasets.router)
    app.include_router(routes_imports.router)
    app.include_router(routes_events.router)
    app.include_router(routes_sources.router)
    app.include_router(routes_search.router)
    app.include_router(routes_mail.router)
    app.include_router(routes_llm.router)
    app.include_router(routes_entities.router)
    app.include_router(routes_graph.router)
    app.include_router(routes_person.router)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": app.version,
            "imports_dir": str(settings.imports_dir),
            "db_path": str(settings.db_path),
        }

    @app.get("/")
    def root() -> dict:
        return {
            "name": "Takeout Viewer API",
            "ui": "http://localhost:5173",
            "docs": "/docs",
        }

    return app


app = create_app()
