"""Qdrant client wrapper + collection setup."""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

COLLECTION_NAME = "italian_legal_v1"
VECTOR_SIZE = 1024  # bge-m3 dense
DISTANCE = models.Distance.COSINE

HYBRID_COLLECTION_NAME = "italian_legal_v1_hybrid"
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "bm25"


def get_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    return QdrantClient(host=host, port=port)


def ensure_collection(client: QdrantClient) -> None:
    """Crea la collection se non esiste. Idempotente."""
    if client.collection_exists(COLLECTION_NAME):
        logger.info("Collection %s already exists", COLLECTION_NAME)
        return
    logger.info("Creating collection %s (size=%d, distance=%s)", COLLECTION_NAME, VECTOR_SIZE, DISTANCE.value)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
    )


def reset_collection(client: QdrantClient) -> None:
    """Droppa la collection se esiste, poi la ricrea pulita."""
    if client.collection_exists(COLLECTION_NAME):
        logger.warning("Dropping existing collection %s", COLLECTION_NAME)
        client.delete_collection(COLLECTION_NAME)
    ensure_collection(client)


def ensure_hybrid_collection(client: QdrantClient) -> None:
    """Crea la collection ibrida (dense+sparse named vectors) se non esiste. Idempotente."""
    if client.collection_exists(HYBRID_COLLECTION_NAME):
        logger.info("Collection %s already exists", HYBRID_COLLECTION_NAME)
        return
    logger.info("Creating hybrid collection %s (dense=%d/%s, sparse=%s+IDF)",
                HYBRID_COLLECTION_NAME, VECTOR_SIZE, DISTANCE.value, SPARSE_VECTOR_NAME)
    client.create_collection(
        collection_name=HYBRID_COLLECTION_NAME,
        vectors_config={
            DENSE_VECTOR_NAME: models.VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: models.SparseVectorParams(modifier=models.Modifier.IDF),
        },
    )


def reset_hybrid_collection(client: QdrantClient) -> None:
    """Droppa la collection ibrida se esiste, poi la ricrea pulita."""
    if client.collection_exists(HYBRID_COLLECTION_NAME):
        logger.warning("Dropping existing collection %s", HYBRID_COLLECTION_NAME)
        client.delete_collection(HYBRID_COLLECTION_NAME)
    ensure_hybrid_collection(client)
