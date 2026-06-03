"""Lightweight Ollama client wrapper.

Talks to a host Ollama daemon (default http://host.docker.internal:11434).
All requests are streamed but accumulated server-side; for short outputs
this is fine. Embeddings use /api/embeddings.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable, Optional

import httpx

from ..config import settings

logger = logging.getLogger("takeout")


class OllamaError(RuntimeError):
    pass


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.ollama_url, timeout=httpx.Timeout(300.0))


def list_models() -> list[dict]:
    try:
        with _client() as c:
            r = c.get("/api/tags")
            r.raise_for_status()
            return r.json().get("models", [])
    except httpx.HTTPError as exc:
        raise OllamaError(f"Brak połączenia z Ollama: {exc}") from exc


def chat(prompt: str, *, model: Optional[str] = None, system: Optional[str] = None) -> str:
    model = model or settings.llm_model
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        with _client() as c:
            r = c.post(
                "/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_ctx": 8192},
                },
            )
            r.raise_for_status()
            data = r.json()
            return (data.get("message") or {}).get("content", "")
    except httpx.HTTPError as exc:
        raise OllamaError(f"Błąd LLM: {exc}") from exc


def embed(text: str, *, model: Optional[str] = None) -> list[float]:
    model = model or settings.embed_model
    text = text.strip()
    if not text:
        return []
    try:
        with _client() as c:
            r = c.post("/api/embeddings", json={"model": model, "prompt": text})
            r.raise_for_status()
            data = r.json()
            vec = data.get("embedding") or []
            return [float(x) for x in vec]
    except httpx.HTTPError as exc:
        raise OllamaError(f"Błąd embeddings: {exc}") from exc


def embed_many(texts: Iterable[str], *, model: Optional[str] = None) -> list[list[float]]:
    """Sequential embedding — Ollama doesn't support true batching, but the
    daemon keeps the model warm so this is still fast."""
    out: list[list[float]] = []
    for t in texts:
        try:
            out.append(embed(t, model=model))
        except OllamaError as exc:
            logger.warning("embed failed: %s", exc)
            out.append([])
    return out


# Prompts ----------------------------------------------------------------

SYSTEM_PL = (
    "Jesteś analitykiem korpracyjnej korespondencji e-mail. Odpowiadasz "
    "zwięźle po polsku, w punktach. Bazujesz wyłącznie na podanym tekście "
    "i nie zmyślasz."
)


def summarize_mail(subject: str, body: str, from_: str = "", to_: str = "") -> str:
    body = (body or "").strip()
    if not body:
        return "Brak treści do streszczenia."
    body = body[:8000]
    prompt = (
        f"Temat: {subject}\nOd: {from_}\nDo: {to_}\n\n"
        f"Treść:\n{body}\n\n"
        "Zadanie: w 2–4 zdaniach po polsku streść kluczowy przekaz, decyzje, "
        "terminy, kwoty i osoby. Pomijaj stopki i ogólne uprzejmości."
    )
    return chat(prompt, system=SYSTEM_PL)


def classify_mail(subject: str, body: str) -> str:
    body = (body or "").strip()[:4000]
    prompt = (
        f"Temat: {subject}\n\nTreść:\n{body}\n\n"
        "Przypisz JEDNĄ kategorię (HR, Prawne, Finanse, Operacje, Sprzedaż, "
        "Compliance, Spam/Marketing, Personalne, Inne). Odpowiedz wyłącznie "
        "nazwą kategorii."
    )
    return chat(prompt, system=SYSTEM_PL).strip().splitlines()[0][:50]


def extract_entities(text: str) -> str:
    text = (text or "").strip()[:6000]
    prompt = (
        f"Tekst:\n{text}\n\n"
        "Wyekstrahuj jako JSON tylko te klucze, które wystąpiły: "
        "{persons: [], organizations: [], money: [], dates: [], emails: []}. "
        "Nazwiska po polsku w mianowniku. Bez komentarza."
    )
    return chat(prompt, system=SYSTEM_PL)
