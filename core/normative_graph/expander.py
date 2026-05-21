"""Espansione del contesto retrieval tramite graph 1-hop bidirezionale.

API pura: nessun I/O, nessun side effect. Input = top-K + lista di link;
output = lista di `ExpandedChunk` deterministica.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import ExpandedChunk, GraphLink, Relation


@dataclass(frozen=True)
class _Edge:
    """Arco interno per la struttura adjacency: chunk vicino + metadati."""
    neighbor: str
    relation: Relation
    note: str


def _build_adjacency(graph: list[GraphLink]) -> dict[str, list[_Edge]]:
    """Adjacency bidirezionale: per ogni chunk_id, i suoi vicini con la relation
    originale del link e la nota."""
    adj: dict[str, list[_Edge]] = defaultdict(list)
    for link in graph:
        adj[link.from_chunk].append(
            _Edge(neighbor=link.to_chunk, relation=link.relation, note=link.note)
        )
        adj[link.to_chunk].append(
            _Edge(neighbor=link.from_chunk, relation=link.relation, note=link.note)
        )
    return adj


def expand_context(
    retrieved: list[tuple[str, float]],
    graph: list[GraphLink],
    max_expansions: int = 5,
) -> list[ExpandedChunk]:
    """Espande il contesto retrieval con chunk linkati dal graph.

    Politica:
    - Bidirezionale: il link A->B nel graph attiva in entrambe le direzioni.
    - 1 hop hard: non si espande sui chunk espansi.
    - Dedup: i chunk già nel top-K non vengono mai ri-aggiunti come espansione;
      un chunk linkato da più chunk del top-K compare una sola volta, con
      priorità al `source_rank` minore (= chunk sorgente più in alto).
    - Cap: al massimo `max_expansions` chunk espansi totali. Selezione: ordina
      per `source_rank` ascendente, tiebreak `chunk_id` lessicografico, tronca.
    """
    if max_expansions <= 0 or not retrieved or not graph:
        return []

    adj = _build_adjacency(graph)
    retrieved_ids = {cid for cid, _ in retrieved}

    # Mantiene per ciascun chunk candidato il miglior (= minor source_rank)
    # edge che lo raggiunge.
    best: dict[str, ExpandedChunk] = {}
    for rank, (cid, _score) in enumerate(retrieved, start=1):
        for edge in adj.get(cid, []):
            target = edge.neighbor
            if target in retrieved_ids:
                continue  # già nel top-K: dedup hard
            existing = best.get(target)
            if existing is not None and existing.source_rank <= rank:
                continue  # già abbiamo un sorgente con rank migliore o uguale
            best[target] = ExpandedChunk(
                chunk_id=target,
                expanded_from=cid,
                relation=edge.relation,
                note=edge.note,
                source_rank=rank,
            )

    if not best:
        return []

    ordered = sorted(best.values(), key=lambda e: (e.source_rank, e.chunk_id))
    return ordered[:max_expansions]
