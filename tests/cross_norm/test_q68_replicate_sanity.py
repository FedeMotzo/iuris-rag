"""Integration test: replica sanity manuale Q68 via CrossNormRetriever.

Verifica end-to-end che:
- Il trigger rilevi 3 norme su Q68.
- 3 sub-query siano emesse (lookup cassette canoniche Sonnet, prompt V2).
- Retrieval reale su Qdrant filtrato per `doc_urn` + globale.
- RRF fusion produca un top-20 finale con ≥3 dei 5 gold di Q68.

Skip automatico se Qdrant non disponibile o collection non popolata.
Niente live LLM call (cassette deterministiche).

Soglia: rescue ≥ 3/5. Rescue effettivo: art_27 (AI Act, recuperato dalla
direttiva FRIA del prompt V2), art_35 (GDPR), art_7 (L.132). I due gold
mancanti hanno cause distinte, entrambe OPEN QUESTION v1.2:
- `art_9` GDPR: sub-query rubrica-mismatch. La rubrica ufficiale è
  "Trattamento di categorie particolari di dati personali"; quando la
  sub-query Sonnet usa la perifrasi "dati sanitari" senza nominare
  l'istituto, il reranker colloca art_9 ~rank 14 (vs rank 5 su Q69, dove
  la sub-query nomina "categorie particolari di dati personali").
- `art_6` AI Act: retrieval gap strutturale. Rubrica definitoria
  ("Regole di classificazione dei sistemi ad alto rischio"); le sub-query
  orientate-obblighi non lo agganciano lessicalmente, ASSENTE anche in
  filtered top-15.
"""

from __future__ import annotations

import pytest
from qdrant_client import QdrantClient

from core.cross_norm import CrossNormRetriever
from core.hybrid_retriever import HybridRetriever
from core.vector_store import HYBRID_COLLECTION_NAME

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)

GOLD_Q68 = {
    "eli/reg/2024/1689/oj__art_6",
    "eli/reg/2024/1689/oj__art_27",
    "eli/reg/2016/679/oj__art_9",
    "eli/reg/2016/679/oj__art_35",
    "akn/it/act/legge/stato/2025-09-23/132__art_7",
}

RESCUE_MIN = 3   # soglia rescue Q68: ≥3/5 (vedi docstring per i 2 gold mancanti)


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
    """Reranker bge-reranker-v2-m3; skip se non attivato via env var.

    Coerente con `tests/test_hybrid_retriever.py::requires_reranker`:
    ~2.3 GB di pesi, non coabita con bge-m3 su MPS.
    """
    import os
    if os.environ.get("RUN_RERANKER_TESTS") != "1":
        pytest.skip(
            "Reranker test attivabile con RUN_RERANKER_TESTS=1 "
            "(carica ~2.3GB)."
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
def test_q68_replicate_sanity_via_cross_norm(hybrid_retriever, q68_stub_llm) -> None:
    """Replica sanity manuale Q68: rescue ≥3/5 gold nei top-20 cross-norm.

    Usa i default produttivi (top_k_per_norm=5). I 2 gold mancanti (art_9
    GDPR rubrica-mismatch, art_6 AI Act retrieval gap definitorio) sono
    open question v1.2 — vedi docstring di modulo.
    """
    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid_retriever,
        llm_client=q68_stub_llm,
        top_k_final=20,
        rerank_top_k_per_norm=20,
        rerank_top_k_global=20,
    )
    result = cnr.retrieve(Q68, top_k=20)
    fused_ids = {h.chunk_id for h in result}

    rescued = GOLD_Q68 & fused_ids
    n_rescued = len(rescued)

    diagnostic = (
        f"Q68 cross-norm rescue: {n_rescued}/5 gold trovati nei top-{len(result)}\n"
        f"  Rescued: {sorted(rescued)}\n"
        f"  Missing: {sorted(GOLD_Q68 - fused_ids)}\n"
        f"  Top-20 fusion: {[h.chunk_id for h in result]}"
    )
    assert n_rescued >= RESCUE_MIN, diagnostic


@pytest.mark.requires_reranker
def test_q68_cross_norm_triggers_three_subqueries(hybrid_retriever, q68_stub_llm) -> None:
    """Sanity: il path cross-norma su Q68 emette esattamente 3 sub-query LLM."""
    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid_retriever,
        llm_client=q68_stub_llm,
        top_k_final=20,
    )
    cnr.retrieve(Q68, top_k=20)
    n_llm_calls = len(q68_stub_llm.calls)
    assert n_llm_calls == 3, (
        f"Atteso 3 chiamate LLM (1 per norma rilevata), trovate {n_llm_calls}: "
        f"{[c['key'] for c in q68_stub_llm.calls]}"
    )
