"""Test per `core/hybrid_retriever/`.

I test di integrazione richiedono:
- Qdrant attivo su localhost:6333
- Collection `italian_legal_v1_hybrid` popolata (vedi `scripts/ingest_hybrid.py`)

Vengono skippati automaticamente se le precondizioni non sono soddisfatte.
Il test del reranker è marcato `requires_reranker` perché carica ~2.3 GB di pesi
e non può coabitare con bge-m3 su MPS — eseguibile manualmente con:
    pytest tests/test_hybrid_retriever.py -m requires_reranker
"""

from __future__ import annotations

import os

import pytest
from qdrant_client import QdrantClient

from core.hybrid_retriever import HybridRetriever, RetrievalHit, RetrievalResult
from core.normative_graph import GraphLink
from core.vector_store import HYBRID_COLLECTION_NAME

HYBRID_QUERIES = [
    "diritti dell'interessato GDPR",
    "art 24-bis 231",
    "art 35 GDPR",
]


# ----------------------------------------------------------------------------
# Fixture / helpers
# ----------------------------------------------------------------------------

def _qdrant_with_hybrid_collection() -> QdrantClient | None:
    """Qdrant client se up + collection popolata. Altrimenti None."""
    try:
        client = QdrantClient(host="localhost", port=6333, timeout=2)
        if not client.collection_exists(HYBRID_COLLECTION_NAME):
            return None
        info = client.get_collection(HYBRID_COLLECTION_NAME)
        if info.points_count == 0:
            return None
        return client
    except Exception:
        return None


@pytest.fixture(scope="module")
def qdrant_client() -> QdrantClient:
    client = _qdrant_with_hybrid_collection()
    if client is None:
        pytest.skip(
            f"Qdrant non disponibile o collection `{HYBRID_COLLECTION_NAME}` "
            "vuota: skip dei test di integrazione."
        )
    return client


@pytest.fixture(scope="module")
def bm25():
    from fastembed import SparseTextEmbedding
    return SparseTextEmbedding(model_name="Qdrant/bm25")


@pytest.fixture(scope="module")
def encoder():
    from core.embedding import BgeM3Encoder
    return BgeM3Encoder.get()


@pytest.fixture(scope="module")
def retriever(qdrant_client, encoder, bm25) -> HybridRetriever:
    return HybridRetriever(
        client=qdrant_client,
        encoder=encoder,
        bm25=bm25,
        collection=HYBRID_COLLECTION_NAME,
    )


# ----------------------------------------------------------------------------
# Smoke integrazione: 3 query × 3 modi
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("query", HYBRID_QUERIES)
@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid"])
def test_retrieve_smoke(retriever: HybridRetriever, query: str, mode: str) -> None:
    hits = retriever.retrieve(query, top_k=5, mode=mode)

    assert isinstance(hits, list)
    assert 0 < len(hits) <= 5, f"expected 1..5 hits, got {len(hits)}"

    # Rank consecutivi 1..N
    assert [h.rank for h in hits] == list(range(1, len(hits) + 1))

    # Score discendente
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True), (
        f"scores not monotonically descending: {scores}"
    )

    # Payload contiene chunk_id e text
    for h in hits:
        assert h.chunk_id, "empty chunk_id"
        assert "chunk_id" in h.payload
        assert "text" in h.payload
        assert isinstance(h.payload["text"], str)


# ----------------------------------------------------------------------------
# Conversione: il primo hit ha tutti i campi corretti
# ----------------------------------------------------------------------------

def test_retrieval_hit_fields(retriever: HybridRetriever) -> None:
    hits = retriever.retrieve("diritti dell'interessato GDPR", top_k=3, mode="hybrid")
    assert hits, "expected at least one hit"
    first = hits[0]
    assert isinstance(first, RetrievalHit)
    assert isinstance(first.chunk_id, str) and first.chunk_id
    assert isinstance(first.score, float)
    assert isinstance(first.payload, dict)
    assert first.rank == 1


# ----------------------------------------------------------------------------
# Validazione argomenti (non richiede Qdrant)
# ----------------------------------------------------------------------------

class _StubEncoder:
    def encode(self, texts, batch_size=1):
        return [[0.0] * 1024 for _ in texts]


class _StubBM25:
    def query_embed(self, q):
        yield type("E", (), {
            "indices": type("A", (), {"tolist": lambda self: [0]})(),
            "values": type("A", (), {"tolist": lambda self: [1.0]})(),
        })()


def _stub_retriever(reranker=None) -> HybridRetriever:
    # Il client non viene chiamato perché le validazioni scattano prima.
    return HybridRetriever(
        client=None,  # type: ignore[arg-type]
        encoder=_StubEncoder(),  # type: ignore[arg-type]
        bm25=_StubBM25(),  # type: ignore[arg-type]
        collection="dummy",
        reranker=reranker,
    )


def test_validation_top_k_zero() -> None:
    r = _stub_retriever()
    with pytest.raises(ValueError, match="top_k"):
        r.retrieve("q", top_k=0)


def test_validation_top_k_negative() -> None:
    r = _stub_retriever()
    with pytest.raises(ValueError, match="top_k"):
        r.retrieve("q", top_k=-1)


def test_validation_rerank_smaller_than_top_k() -> None:
    r = _stub_retriever(reranker=object())  # presenza basta, non viene chiamato
    with pytest.raises(ValueError, match="rerank_top_k"):
        r.retrieve("q", top_k=10, rerank_top_k=5)


def test_validation_rerank_without_reranker(retriever: HybridRetriever) -> None:
    # Usa il retriever reale (no reranker iniettato): il fetch da Qdrant avviene,
    # poi al momento di rerank scatta ValueError.
    with pytest.raises(ValueError, match="no reranker provided"):
        retriever.retrieve("q", top_k=5, mode="dense", rerank_top_k=10)


def test_validation_bad_mode() -> None:
    r = _stub_retriever()
    with pytest.raises(ValueError, match="mode"):
        r.retrieve("q", top_k=5, mode="bogus")  # type: ignore[arg-type]


# ----------------------------------------------------------------------------
# Terminology expansion wiring — verifica che expand_query sia applicato
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid"])
def test_retrieve_applies_terminology_expansion(monkeypatch, mode: str) -> None:
    """`expand_query` deve essere applicato prima del fetch in tutti i modi.

    Se la chiamata viene rimossa da `retrieve()`, questo test fallisce perché
    la query passata a `_query_{dense,sparse,hybrid}` non conterrebbe la forma
    estesa dell'alias FRIA. Vedi `core/terminology/aliases.yaml`.
    """
    r = _stub_retriever()
    captured: dict[str, str] = {}

    def fake_query(query: str, fetch_k: int):
        captured["query"] = query
        return []

    monkeypatch.setattr(r, "_query_dense", fake_query)
    monkeypatch.setattr(r, "_query_sparse", fake_query)
    monkeypatch.setattr(r, "_query_hybrid", fake_query)

    r.retrieve("art 27 FRIA", top_k=5, mode=mode)  # type: ignore[arg-type]

    assert "query" in captured, "fake_query non è stata invocata"
    assert "valutazione d'impatto sui diritti fondamentali" in captured["query"], (
        f"expand_query non applicato (alias FRIA mancante): {captured['query']!r}"
    )


# ----------------------------------------------------------------------------
# Graph expansion — integrazione opzionale
# ----------------------------------------------------------------------------

def test_retrieve_without_graph_links_has_empty_expanded(retriever: HybridRetriever) -> None:
    """graph_links=None: comportamento storico invariato + expanded_chunks vuoto."""
    result = retriever.retrieve("art 35 GDPR", top_k=5, mode="hybrid")
    assert isinstance(result, RetrievalResult)
    assert isinstance(result, list)  # backward-compat: subclass di list
    assert result.expanded_chunks == []
    assert 0 < len(result) <= 5
    assert [h.rank for h in result] == list(range(1, len(result) + 1))


def test_retrieve_with_graph_links_populates_expansion(retriever: HybridRetriever) -> None:
    """Un link cucito sui top-K reali deve produrre almeno una espansione."""
    # Query mirata: l'art. 35 GDPR è quasi certamente nei top-5 hybrid.
    base = retriever.retrieve("art 35 GDPR DPIA", top_k=5, mode="hybrid")
    top_ids = [h.chunk_id for h in base]

    # Costruisci on-the-fly un link dal primo chunk recuperato verso un chunk
    # esterno noto (art. 27 AI Act, atteso fuori dal top-5 per questa query).
    source = top_ids[0]
    target = "eli/reg/2024/1689/oj__art_27"
    if target in top_ids:
        target = "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24"
    assert target not in top_ids, (
        f"target {target} già nel top-5: scegliere altro chunk fuori top-K per il test"
    )

    link = GraphLink(
        from_chunk=source,
        to_chunk=target,
        relation="complementare",  # type: ignore[arg-type]
        note="link sintetico per test integrazione",
    )
    result = retriever.retrieve(
        "art 35 GDPR DPIA",
        top_k=5,
        mode="hybrid",
        graph_links=[link],
        graph_max_expansions=5,
    )
    assert len(result.expanded_chunks) == 1
    exp = result.expanded_chunks[0]
    assert exp.chunk_id == target
    assert exp.expanded_from == source
    assert 1 <= exp.source_rank <= 5
    assert exp.relation == "complementare"


# ----------------------------------------------------------------------------
# Reranker — marcato come slow, caricato manualmente
# ----------------------------------------------------------------------------

@pytest.mark.requires_reranker
@pytest.mark.skipif(
    not os.environ.get("RUN_RERANKER_TESTS"),
    reason="Carica ~2.3 GB su MPS; esegui con RUN_RERANKER_TESTS=1 pytest ...",
)
def test_rerank_changes_ordering(qdrant_client, encoder, bm25) -> None:
    """Carica il reranker e verifica che produca un ordinamento valido.

    Non assert che cambi (può capitare che il top-1 sia stabile), ma logga le
    differenze e verifica che la lista resti coerente (rank 1..N, score float).
    """
    from sentence_transformers import CrossEncoder

    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    retriever = HybridRetriever(
        client=qdrant_client,
        encoder=encoder,
        bm25=bm25,
        collection=HYBRID_COLLECTION_NAME,
        reranker=reranker,
    )
    query = "diritti dell'interessato GDPR"

    base = retriever.retrieve(query, top_k=5, mode="hybrid")
    reranked = retriever.retrieve(query, top_k=5, mode="hybrid", rerank_top_k=10)

    assert len(reranked) <= 5
    assert [h.rank for h in reranked] == list(range(1, len(reranked) + 1))
    assert all(isinstance(h.score, float) for h in reranked)

    print("\nBase top-5      :", [h.chunk_id for h in base])
    print("Reranked top-5  :", [h.chunk_id for h in reranked])
