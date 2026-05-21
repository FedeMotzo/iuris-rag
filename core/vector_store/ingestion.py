"""Chunk → Qdrant points."""

from __future__ import annotations

import logging
import uuid

from qdrant_client import QdrantClient, models

from core.chunking import Chunk
from core.embedding import BgeM3Encoder

from .qdrant_client import (
    COLLECTION_NAME,
    DENSE_VECTOR_NAME,
    HYBRID_COLLECTION_NAME,
    SPARSE_VECTOR_NAME,
)

logger = logging.getLogger(__name__)

# Namespace stabile per derivare UUID deterministici dai chunk_id.
# Riutilizzo NAMESPACE_OID standard come da spec.
CHUNK_ID_NAMESPACE = uuid.NAMESPACE_OID


def chunk_id_to_point_id(chunk_id: str) -> str:
    """Mappa stabile e deterministica da chunk_id stringa a UUID v5."""
    return str(uuid.uuid5(CHUNK_ID_NAMESPACE, chunk_id))


def _chunk_to_payload(chunk: Chunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "source_type": chunk.source_type,
        "chunk_type": chunk.chunk_type,
        "doc_urn": chunk.doc_urn,
        "article_eid": chunk.article_eid,
        "para_eids": chunk.para_eids,
        "hierarchy_path": chunk.hierarchy_path,
        "metadata": chunk.metadata,
    }


def ingest_chunks(
    chunks: list[Chunk],
    client: QdrantClient,
    encoder: BgeM3Encoder,
    *,
    batch_size: int = 32,
) -> int:
    """Encoda e upserta i chunk in Qdrant. Idempotente.

    L'upsert sovrascrive sempre i point con lo stesso id, quindi rieseguire
    `ingest_chunks` sugli stessi chunk produce lo stesso stato finale.
    """
    if not chunks:
        logger.info("No chunks to ingest")
        return 0

    total = len(chunks)
    n_batches = (total + batch_size - 1) // batch_size
    upserted = 0

    for bi in range(n_batches):
        start = bi * batch_size
        end = min(start + batch_size, total)
        batch = chunks[start:end]
        texts = [c.text for c in batch]
        vectors = encoder.encode(texts, batch_size=batch_size)

        points = [
            models.PointStruct(
                id=chunk_id_to_point_id(c.chunk_id),
                vector=vec,
                payload=_chunk_to_payload(c),
            )
            for c, vec in zip(batch, vectors, strict=True)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        upserted += len(points)
        logger.info("Ingested batch %d/%d (%d points, total %d/%d)",
                    bi + 1, n_batches, len(points), upserted, total)

    logger.info("Ingestion complete: %d points upserted into %s", upserted, COLLECTION_NAME)
    return upserted


def ingest_chunks_hybrid(
    chunks: list[Chunk],
    client: QdrantClient,
    encoder: BgeM3Encoder,
    bm25,  # fastembed.SparseTextEmbedding — non importato qui per non aggiungere dipendenza al modulo core
    *,
    batch_size: int = 8,
) -> int:
    """Encoda dense (bge-m3) + sparse (FastEmbed BM25) e upserta come singolo point
    su `italian_legal_v1_hybrid` (named vectors). Idempotente per UUID v5 da chunk_id.
    """
    if not chunks:
        logger.info("No chunks to ingest")
        return 0

    total = len(chunks)
    n_batches = (total + batch_size - 1) // batch_size
    upserted = 0

    for bi in range(n_batches):
        start = bi * batch_size
        end = min(start + batch_size, total)
        batch = chunks[start:end]
        texts = [c.text for c in batch]

        dense_vectors = encoder.encode(texts, batch_size=batch_size)
        sparse_embeddings = list(bm25.passage_embed(texts))

        points = []
        for c, dvec, sparse in zip(batch, dense_vectors, sparse_embeddings, strict=True):
            sparse_vec = models.SparseVector(
                indices=sparse.indices.tolist(),
                values=sparse.values.tolist(),
            )
            points.append(
                models.PointStruct(
                    id=chunk_id_to_point_id(c.chunk_id),
                    vector={
                        DENSE_VECTOR_NAME: dvec,
                        SPARSE_VECTOR_NAME: sparse_vec,
                    },
                    payload=_chunk_to_payload(c),
                )
            )
        client.upsert(collection_name=HYBRID_COLLECTION_NAME, points=points, wait=True)
        upserted += len(points)
        logger.info("Ingested batch %d/%d (%d points, total %d/%d)",
                    bi + 1, n_batches, len(points), upserted, total)

    logger.info("Hybrid ingestion complete: %d points upserted into %s",
                upserted, HYBRID_COLLECTION_NAME)
    return upserted
