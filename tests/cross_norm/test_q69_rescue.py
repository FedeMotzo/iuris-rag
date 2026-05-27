"""Integration test: rescue ratio Q69 via CrossNormRetriever.

Analogo a `test_q68_replicate_sanity.py`. Q69 è multi-norma AI Act+GDPR+NIS2.

Verifica end-to-end:
- Trigger rileva 3 norme (gdpr, ai_act, nis2).
- 3 sub-query emesse (cassette canoniche Sonnet, prompt template V2).
- Retrieval reale su Qdrant filtrato per `doc_urn` + globale.
- RRF fusion → top-20 con ≥4 dei 5 gold di Q69.

Gold Q69 ASSENTI in retrieval globale v1.0 (da PRE_FIX_DIAG_v1_1):
  AI Act art_6, GDPR art_9, GDPR art_35, NIS2 art_24, NIS2 art_25.

Skip automatico se Qdrant non disponibile. Niente live LLM (cassette).
"""

from __future__ import annotations

import pytest
from qdrant_client import QdrantClient

from core.cross_norm import CrossNormRetriever
from core.hybrid_retriever import HybridRetriever
from core.vector_store import HYBRID_COLLECTION_NAME

Q69 = (
    "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale "
    "NIS2 per il settore sanitario, intende impiegare un sistema di IA per "
    "supportare le attività di farmacovigilanza con dati provenienti da "
    "operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai "
    "sensi di AI Act, GDPR e NIS2?"
)

GOLD_Q69 = {
    "eli/reg/2024/1689/oj__art_6",
    "eli/reg/2016/679/oj__art_9",
    "eli/reg/2016/679/oj__art_35",
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24",
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25",
}

RESCUE_MIN = 4   # soglia rescue: almeno 4/5 gold nei top-20 finali


def _qdrant_with_collection() -> QdrantClient | None:
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
    c = _qdrant_with_collection()
    if c is None:
        pytest.skip(
            f"Qdrant non disponibile o collection `{HYBRID_COLLECTION_NAME}` "
            "vuota: skip integration test."
        )
    return c


@pytest.fixture(scope="module")
def encoder():
    from core.embedding import BgeM3Encoder
    return BgeM3Encoder.get()


@pytest.fixture(scope="module")
def bm25():
    from fastembed import SparseTextEmbedding
    return SparseTextEmbedding(model_name="Qdrant/bm25")


@pytest.fixture(scope="module")
def reranker():
    import os
    if os.environ.get("RUN_RERANKER_TESTS") != "1":
        pytest.skip(
            "Reranker test attivabile con RUN_RERANKER_TESTS=1 (carica ~2.3GB)."
        )
    from sentence_transformers import CrossEncoder
    return CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)


@pytest.fixture(scope="module")
def hybrid_retriever(qdrant_client, encoder, bm25, reranker) -> HybridRetriever:
    return HybridRetriever(
        client=qdrant_client,
        encoder=encoder,
        bm25=bm25,
        collection=HYBRID_COLLECTION_NAME,
        reranker=reranker,
    )


@pytest.mark.requires_reranker
def test_q69_rescue_via_cross_norm(hybrid_retriever, q69_stub_llm) -> None:
    """Rescue ≥4/5 gold Q69 nei top-20 cross-norm (prompt template V2).

    Usa i default produttivi (top_k_per_norm=5). Rescued: GDPR art_9 +
    art_35, NIS2 art_24 + art_25.

    NOTA: art_6 AI Act resta ASSENTE per gap di retrieval strutturale
    (rubrica definitoria, le sub-query orientate-obblighi non lo
    agganciano). Annotato come open question v1.2.
    """
    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid_retriever,
        llm_client=q69_stub_llm,
        top_k_final=20,
        rerank_top_k_per_norm=20,
        rerank_top_k_global=20,
    )
    result = cnr.retrieve(Q69, top_k=20)
    fused_ids = {h.chunk_id for h in result}

    rescued = GOLD_Q69 & fused_ids
    n_rescued = len(rescued)

    diagnostic = (
        f"Q69 cross-norm rescue: {n_rescued}/5 gold trovati nei top-{len(result)}\n"
        f"  Rescued: {sorted(rescued)}\n"
        f"  Missing: {sorted(GOLD_Q69 - fused_ids)}\n"
        f"  Top-20 fusion: {[h.chunk_id for h in result]}"
    )
    assert n_rescued >= RESCUE_MIN, diagnostic


@pytest.mark.requires_reranker
def test_q69_cross_norm_triggers_three_subqueries(hybrid_retriever, q69_stub_llm) -> None:
    """Sanity: il path cross-norma su Q69 emette esattamente 3 sub-query LLM."""
    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid_retriever,
        llm_client=q69_stub_llm,
        top_k_final=20,
    )
    cnr.retrieve(Q69, top_k=20)
    n_llm_calls = len(q69_stub_llm.calls)
    assert n_llm_calls == 3, (
        f"Atteso 3 chiamate LLM (1 per norma rilevata), trovate {n_llm_calls}: "
        f"{[c['key'] for c in q69_stub_llm.calls]}"
    )
