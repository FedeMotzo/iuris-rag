"""Chunking module: turn parsed legal documents into retrieval-ready Chunks."""

from .chunker import (
    CHUNK_TOKEN_THRESHOLD,
    Chunk,
    chunk_document,
    chunk_recitals,
)

__all__ = [
    "Chunk",
    "CHUNK_TOKEN_THRESHOLD",
    "chunk_document",
    "chunk_recitals",
]
