"""Vector store: Qdrant client wrapper + chunk ingestion."""

from .ingestion import chunk_id_to_point_id, ingest_chunks, ingest_chunks_hybrid
from .qdrant_client import (
    COLLECTION_NAME,
    DENSE_VECTOR_NAME,
    DISTANCE,
    HYBRID_COLLECTION_NAME,
    SPARSE_VECTOR_NAME,
    VECTOR_SIZE,
    ensure_collection,
    ensure_hybrid_collection,
    get_client,
    reset_collection,
    reset_hybrid_collection,
)

__all__ = [
    "COLLECTION_NAME",
    "HYBRID_COLLECTION_NAME",
    "DENSE_VECTOR_NAME",
    "SPARSE_VECTOR_NAME",
    "VECTOR_SIZE",
    "DISTANCE",
    "get_client",
    "ensure_collection",
    "reset_collection",
    "ensure_hybrid_collection",
    "reset_hybrid_collection",
    "ingest_chunks",
    "ingest_chunks_hybrid",
    "chunk_id_to_point_id",
]
