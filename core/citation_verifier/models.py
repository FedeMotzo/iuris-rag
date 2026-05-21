"""Pydantic models per `core/citation_verifier`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CitationMarker(BaseModel):
    """Una singola occorrenza di [cite:CHUNK_ID] nell'output LLM."""

    chunk_id: str
    span_start: int
    span_end: int
    verified: bool
    reason: Literal["ok", "unknown_chunk_id", "malformed"] | None = None


class VerificationResult(BaseModel):
    """Esito completo della verifica su un output LLM."""

    original_text: str
    annotated_text: str
    markers: list[CitationMarker]
    n_total: int
    n_verified: int
    n_unverified: int
    all_verified: bool
