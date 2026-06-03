"""Lightweight NER service using spaCy.

Lazy-loads pl + en models on first use to keep cold-start fast.
Designed to be called in batch over events:
- extract_entities(text) → list of (kind, key, label, span_text)
- normalize_key — collapse whitespace and lower-case for dedup
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, Iterator

logger = logging.getLogger("takeout")

# Labels we keep. Others are discarded.
_KEEP_LABELS = {
    # Polish + English share most labels
    "PERSON": "PERSON",
    "persName": "PERSON",  # Polish model variant
    "ORG": "ORG",
    "orgName": "ORG",
    "GPE": "GPE",
    "placeName": "GPE",
    "LOC": "LOC",
    "geogName": "LOC",
    "MONEY": "MONEY",
    "DATE": "DATE",
    "time": "DATE",
    "PERCENT": "PERCENT",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
    "WORK_OF_ART": "WORK",
    "LAW": "LAW",
}

# Email/URL patterns extracted by regex (faster + more reliable than NER)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


_models: dict[str, object] = {}


def _load(model_name: str):
    if model_name in _models:
        return _models[model_name]
    import spacy
    try:
        nlp = spacy.load(model_name, disable=["lemmatizer", "tagger", "parser", "attribute_ruler"])
    except Exception as exc:
        logger.warning("spaCy model %s unavailable: %s", model_name, exc)
        _models[model_name] = None
        return None
    _models[model_name] = nlp
    return nlp


def detect_lang(text: str) -> str:
    """Cheap heuristic — Polish diacritics? Otherwise English."""
    if any(c in text for c in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"):
        return "pl"
    return "en"


def normalize_key(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def extract_entities(text: str, max_chars: int = 50_000) -> list[tuple[str, str, str, str]]:
    """Return list of (kind, key, label, span_text)."""
    if not text:
        return []
    text = text[:max_chars]
    lang = detect_lang(text)
    model_name = "pl_core_news_lg" if lang == "pl" else "en_core_web_sm"
    nlp = _load(model_name)
    out: list[tuple[str, str, str, str]] = []

    if nlp is not None:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                kind = _KEEP_LABELS.get(ent.label_)
                if not kind:
                    continue
                span = ent.text.strip()
                if not span or len(span) < 2:
                    continue
                key = normalize_key(span)
                if len(key) > 200:
                    continue
                out.append((kind, key, span, span))
        except Exception as exc:
            logger.warning("spaCy NER failed: %s", exc)

    # Regex pickups for emails / URLs (always run)
    for m in _EMAIL_RE.findall(text):
        em = m.lower()
        out.append(("EMAIL", em, em, em))
    for m in _URL_RE.findall(text):
        url = m
        out.append(("URL", url, url, url))

    # Deduplicate within this document
    seen = set()
    unique: list[tuple[str, str, str, str]] = []
    for tup in out:
        k = (tup[0], tup[1])
        if k in seen:
            continue
        seen.add(k)
        unique.append(tup)
    return unique
