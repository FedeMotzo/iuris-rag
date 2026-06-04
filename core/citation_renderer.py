"""Rendering display-only dei marker [cite:CHUNK_ID] in label leggibili.

Nessun I/O a runtime se usato tramite render_cites_default (glossary cachato).
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

import yaml

from core.citation_marker import CITE_PATTERN, has_dangling_cite  # noqa: F401

# Stessa derivazione di path usata in subquery_generator.py — source of truth unica.
_GLOSSARY_PATH = Path(__file__).resolve().parent / "cross_norm" / "norm_glossary.yaml"

# Raccoglie i marker malformati residui dopo CITE_PATTERN.sub (es. [cite:] vuoto,
# [cite: x] con spazio, [cite: troncato senza chiusura).
_MALFORMED_CITE_RE = re.compile(r"\[cite:[^\]]*\]?")

# --- forme articolo/allegato/considerando ----------------------------------
# Cattura: numero articolo + eventuale suffisso (es. 2-ter, 25-undecies),
# poi collassa opzionalmente __paras_X_Y.
_ART_RE = re.compile(r"^art_(\d+(?:-[^_]+)*)(?:__paras_.+)?$")
_ANNEX_POINT_RE = re.compile(r"^annex_(.+?)__point_(\w+)$")
_ANNEX_RE = re.compile(r"^annex_(.+)$")
_RECITAL_RE = re.compile(r"^recital_(\d+)$")


def norm_label(short_name: str) -> str:
    """Restituisce il primo segmento di short_name (prima di ' / ')."""
    return short_name.split(" / ")[0].strip()


def cite_label(chunk_id: str, norm_names: Mapping[str, str]) -> str:
    """Converte un chunk_id in label leggibile.

    Puro, nessun I/O. Se doc_urn ignoto o forma non riconosciuta → chunk_id grezzo.
    """
    if "__" not in chunk_id:
        return chunk_id

    doc_urn, parte = chunk_id.split("__", 1)
    label = norm_names.get(doc_urn)
    if label is None:
        return chunk_id

    m = _ART_RE.match(parte)
    if m:
        return f"art. {m.group(1)} {label}"

    m = _ANNEX_POINT_RE.match(parte)
    if m:
        return f"Allegato {m.group(1)}, punto {m.group(2)} {label}"

    m = _ANNEX_RE.match(parte)
    if m:
        return f"Allegato {m.group(1)} {label}"

    m = _RECITAL_RE.match(parte)
    if m:
        return f"considerando {m.group(1)} {label}"

    return chunk_id


def render_cites(text: str, norm_names: Mapping[str, str]) -> str:
    """Sostituisce ogni [cite:CHUNK_ID] con cite_label(CHUNK_ID, norm_names).

    I marker malformati (vuoti, con spazio iniziale, senza ] di chiusura) che
    CITE_PATTERN non cattura vengono rimossi dal secondo pass.
    """
    text = CITE_PATTERN.sub(lambda m: cite_label(m.group(1), norm_names), text)
    return _MALFORMED_CITE_RE.sub("", text)


@lru_cache(maxsize=None)
def _norm_names() -> dict[str, str]:
    """Mappa {doc_urn: norm_label} costruita dal glossary (cachata).

    Carica norm_glossary.yaml una volta sola; combina {slug→doc_urn} e
    {slug→short_name} — equivalente a load_norm_doc_urns + load_norm_short_names
    di map_assemble.py, ma senza la dipendenza pesante (qdrant) di quel package.
    """
    with _GLOSSARY_PATH.open(encoding="utf-8") as fh:
        glossary: dict = yaml.safe_load(fh) or {}
    return {
        entry["doc_urn"]: norm_label(entry["short_name"])
        for entry in glossary.values()
        if entry and entry.get("doc_urn") and entry.get("short_name")
    }


def render_cites_default(text: str) -> str:
    """render_cites con norm_names dal glossary (lru_cached)."""
    return render_cites(text, _norm_names())
