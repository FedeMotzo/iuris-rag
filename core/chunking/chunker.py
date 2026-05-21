"""Public chunking API: turn parsed legal documents into retrieval-ready Chunks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from core.eur_lex_parser import EurLexDocument, EurLexRecital
from core.italian_legal_parser import AKNDocument

from ._tokenizer import count_tokens

logger = logging.getLogger(__name__)

CHUNK_TOKEN_THRESHOLD: int = 2000


SourceType = Literal["normattiva", "eurlex"]
ChunkType = Literal["article", "article_group", "recital", "annex"]


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_type: SourceType
    chunk_type: ChunkType
    doc_urn: str
    article_eid: str | None
    para_eids: list[str] = field(default_factory=list)
    hierarchy_path: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def chunk_document(
    doc: AKNDocument | EurLexDocument,
    *,
    include_recitals: bool = True,  # noqa: ARG001 — recitals live outside the doc model
) -> list[Chunk]:
    """Dispatch on the concrete document type.

    `include_recitals` is accepted for forward-compatibility; recitals are not
    part of `EurLexDocument` and must be chunked separately via `chunk_recitals`.
    """
    if isinstance(doc, AKNDocument):
        from ._normattiva import chunk_akn_document
        return chunk_akn_document(doc)
    if isinstance(doc, EurLexDocument):
        from ._eurlex import chunk_eurlex_document
        return chunk_eurlex_document(doc)
    raise TypeError(f"Unsupported document type: {type(doc).__name__}")


def chunk_recitals(recitals: list[EurLexRecital]) -> list[Chunk]:
    """Sibling helper: recitals come from a separate parser call than articles."""
    from ._eurlex import chunk_eurlex_recitals
    return chunk_eurlex_recitals(recitals)


def greedy_group_by_threshold(
    items: list[tuple[str, int]],
    threshold: int = CHUNK_TOKEN_THRESHOLD,
) -> list[list[int]]:
    """Greedy bin-packing on individual token counts.

    Returns groups of indices. A single item exceeding `threshold` enters its
    own group (caller must accept the over-sized chunk).
    """
    groups: list[list[int]] = []
    current: list[int] = []
    current_sum = 0
    for i, (_, tokens) in enumerate(items):
        if current and current_sum + tokens > threshold:
            groups.append(current)
            current = [i]
            current_sum = tokens
            continue
        current.append(i)
        current_sum += tokens
    if current:
        groups.append(current)
    return groups
