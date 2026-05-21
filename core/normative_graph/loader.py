"""Caricamento del graph YAML in lista di `GraphLink` validati."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import GraphLink

_DEFAULT_GRAPH_PATH = Path(__file__).parent / "graph.yaml"


def load_graph(path: Path | None = None) -> list[GraphLink]:
    """Carica `graph.yaml` (default: accanto al modulo) e ritorna i link validati.

    Solleva `ValueError` se ci sono duplicati esatti (stessa terna
    from+to+relation), `FileNotFoundError` se il file non esiste,
    `pydantic.ValidationError` se uno qualsiasi dei link non rispetta lo schema.
    """
    p = path if path is not None else _DEFAULT_GRAPH_PATH
    if not p.exists():
        raise FileNotFoundError(f"Graph YAML non trovato: {p}")

    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise ValueError(
            f"Graph YAML deve essere una lista di link al top-level (got {type(raw).__name__})"
        )

    links = [GraphLink.model_validate(item) for item in raw]

    seen: set[tuple[str, str, str]] = set()
    for link in links:
        key = (link.from_chunk, link.to_chunk, link.relation)
        if key in seen:
            raise ValueError(
                f"Duplicato esatto nel graph: from={link.from_chunk!r} "
                f"to={link.to_chunk!r} relation={link.relation!r}"
            )
        seen.add(key)

    return links
