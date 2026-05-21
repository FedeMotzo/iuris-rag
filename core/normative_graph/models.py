"""Modelli Pydantic per il graph multi-normativa.

`GraphLink` rappresenta un singolo arco curato a mano tra due chunk_id della
collection `italian_legal_v1_hybrid`. `ExpandedChunk` rappresenta un chunk
aggiunto al contesto retrieval tramite espansione 1-hop bidirezionale.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Relation = Literal[
    "complementare",
    "presupposto_di",
    "rinvia_a",
    "attua",
    "deroga",
]


class GraphLink(BaseModel):
    """Arco curato tra due chunk_id della collection.

    Il YAML usa le chiavi `from` e `to` (parole riservate Python), mappate qui
    via Pydantic Field alias.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_chunk: str = Field(alias="from")
    to_chunk: str = Field(alias="to")
    relation: Relation
    note: str
    source: Literal["curated", "auto"] = "curated"
    validated_by: str | None = None
    validated_at: str | None = None


class ExpandedChunk(BaseModel):
    """Chunk aggiunto al contesto retrieval tramite il graph.

    `source_rank` è il rank (1-indexed) del chunk sorgente nel top-K originale
    da cui è partita l'espansione.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    expanded_from: str
    relation: Relation
    note: str
    source_rank: int
