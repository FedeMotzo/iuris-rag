"""Tipi di ritorno di `HybridRetriever`.

Neutrali rispetto al backend (nessun tipo Qdrant qui).

`RetrievalResult` è una `list[RetrievalHit]` arricchita con un attributo
`expanded_chunks` opzionale, popolato quando il caller passa
`graph_links` a `retrieve()`. Subclassing `list` preserva la firma
storica (`isinstance(result, list)`, iterazione, indicizzazione) — i
test esistenti continuano a funzionare senza modifiche.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.normative_graph import ExpandedChunk


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    score: float
    payload: dict[str, Any]
    rank: int  # 1-indexed nell'ordine finale restituito


class RetrievalResult(list["RetrievalHit"]):
    """Lista di `RetrievalHit` + `expanded_chunks` opzionale.

    Subclass di `list` per non rompere la firma storica di `retrieve()`.
    """

    def __init__(
        self,
        hits: Iterable["RetrievalHit"] = (),
        expanded_chunks: "list[ExpandedChunk] | None" = None,
    ) -> None:
        super().__init__(hits)
        self.expanded_chunks: list[ExpandedChunk] = list(expanded_chunks or [])
