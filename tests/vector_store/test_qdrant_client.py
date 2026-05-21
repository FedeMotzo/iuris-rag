"""Tests for Qdrant collection setup (in-memory)."""

from __future__ import annotations

from qdrant_client import QdrantClient, models

from core.vector_store.qdrant_client import (
    COLLECTION_NAME,
    DISTANCE,
    VECTOR_SIZE,
    ensure_collection,
)


def test_ensure_collection_creates_with_correct_params():
    client = QdrantClient(":memory:")
    ensure_collection(client)

    assert client.collection_exists(COLLECTION_NAME)
    info = client.get_collection(COLLECTION_NAME)
    vectors_cfg = info.config.params.vectors
    assert isinstance(vectors_cfg, models.VectorParams)
    assert vectors_cfg.size == VECTOR_SIZE == 1024
    assert vectors_cfg.distance == DISTANCE == models.Distance.COSINE


def test_ensure_collection_is_idempotent():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    ensure_collection(client)  # must not raise
    assert client.collection_exists(COLLECTION_NAME)
