"""Tests for `ingest_chunks` (in-memory Qdrant + mocked encoder)."""

from __future__ import annotations

from qdrant_client import QdrantClient

from core.chunking import Chunk
from core.embedding import BgeM3Encoder
from core.vector_store.ingestion import chunk_id_to_point_id, ingest_chunks
from core.vector_store.qdrant_client import COLLECTION_NAME, VECTOR_SIZE, ensure_collection


class _FakeEncoder(BgeM3Encoder):
    """Encoder fake: salta il caricamento del modello, ritorna vettori deterministici."""

    def __init__(self) -> None:
        # Skip parent __init__ — do not touch the singleton or torch device.
        self._model = object()  # sentinel, never used

    def encode(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        out = []
        for t in texts:
            # Vettore unitario costante con un piccolo "fingerprint" dal testo.
            vec = [0.0] * VECTOR_SIZE
            seed = (sum(ord(c) for c in t) % VECTOR_SIZE)
            vec[seed] = 1.0
            out.append(vec)
        return out


def _sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id="urn/test/doc1__art_1",
            text="Articolo 1 - Definizioni. Ai fini della presente legge...",
            source_type="normattiva",
            chunk_type="article",
            doc_urn="urn/test/doc1",
            article_eid="art_1",
            para_eids=[],
            hierarchy_path=["Capo I", "art. 1"],
            metadata={"article_number": "1", "rubrica": "Definizioni", "tokens": 42},
        ),
        Chunk(
            chunk_id="urn/test/doc1__art_2__paras_1_3",
            text="Articolo 2. 1. Comma uno. 2. Comma due. 3. Comma tre.",
            source_type="normattiva",
            chunk_type="article_group",
            doc_urn="urn/test/doc1",
            article_eid="art_2",
            para_eids=["art_2__para_1", "art_2__para_2", "art_2__para_3"],
            hierarchy_path=["Capo I", "art. 2"],
            metadata={"group_index": 0, "group_count": 2, "first_comma": "1", "last_comma": "3"},
        ),
        Chunk(
            chunk_id="urn/test/doc2__recital_42",
            text="Considerando 42 - testo del considerando.",
            source_type="eurlex",
            chunk_type="recital",
            doc_urn="urn/test/doc2",
            article_eid=None,
            para_eids=[],
            hierarchy_path=["Considerando 42"],
            metadata={"recital_number": 42},
        ),
    ]


def test_ingestion_produces_correct_point_count_and_payload():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    chunks = _sample_chunks()

    n = ingest_chunks(chunks, client, _FakeEncoder(), batch_size=2)
    assert n == len(chunks)

    info = client.get_collection(COLLECTION_NAME)
    assert info.points_count == len(chunks)

    # Verifica payload del primo chunk.
    expected_pid = chunk_id_to_point_id(chunks[0].chunk_id)
    retrieved = client.retrieve(
        collection_name=COLLECTION_NAME, ids=[expected_pid], with_payload=True
    )
    assert len(retrieved) == 1
    payload = retrieved[0].payload
    assert payload["chunk_id"] == chunks[0].chunk_id
    assert payload["text"] == chunks[0].text
    assert payload["source_type"] == "normattiva"
    assert payload["chunk_type"] == "article"
    assert payload["doc_urn"] == "urn/test/doc1"
    assert payload["article_eid"] == "art_1"
    assert payload["para_eids"] == []
    assert payload["hierarchy_path"] == ["Capo I", "art. 1"]
    assert payload["metadata"]["rubrica"] == "Definizioni"


def test_ingestion_is_idempotent():
    client = QdrantClient(":memory:")
    ensure_collection(client)
    chunks = _sample_chunks()

    enc = _FakeEncoder()
    ingest_chunks(chunks, client, enc, batch_size=2)
    first_count = client.get_collection(COLLECTION_NAME).points_count

    ingest_chunks(chunks, client, enc, batch_size=2)
    second_count = client.get_collection(COLLECTION_NAME).points_count

    assert first_count == second_count == len(chunks)


def test_chunk_id_to_point_id_is_deterministic():
    cid = "akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_166__paras_1_3"
    p1 = chunk_id_to_point_id(cid)
    p2 = chunk_id_to_point_id(cid)
    assert p1 == p2
    assert len(p1) == 36  # UUID canonico

    different = chunk_id_to_point_id(cid + "_x")
    assert different != p1
