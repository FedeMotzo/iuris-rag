"""Unit test `CrossNormRetriever` — orchestrazione + RRF fusion.

Niente Qdrant, niente LLM live. Tutti gli I/O sono stub:
- `_StubHybridRetriever` ritorna liste pre-canned di RetrievalHit basate su
  (sub_query, filter_doc_urn) lookup.
- `q68_stub_llm` (fixture) ritorna le sub-query canoniche dalla cassette.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.cross_norm.retriever import CrossNormRetriever
from core.hybrid_retriever.types import RetrievalHit, RetrievalResult

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)

MONO_NORM_Q = "Cos'è una DPIA secondo il GDPR?"


# ---------------------------------------------------------------- stub retriever

@dataclass
class _Call:
    query: str
    top_k: int
    rerank_top_k: int | None
    filter_doc_urn: str | None


class _StubHybridRetriever:
    """Stub di `HybridRetriever`: registra ogni chiamata + ritorna hit pre-canned.

    `responses` è un dict: chiave = `filter_doc_urn` (o "GLOBAL"), valore =
    lista di chunk_id da restituire come hit ordinati. Lo stub crea
    RetrievalHit con score decrescente e rank 1..N.
    """

    def __init__(self, responses: dict[str | None, list[str]]) -> None:
        self.responses = responses
        self.calls: list[_Call] = []

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid",
        rerank_top_k: int | None = None,
        graph_links=None,
        graph_max_expansions: int = 5,
        filter_doc_urn: str | None = None,
    ) -> RetrievalResult:
        self.calls.append(_Call(query, top_k, rerank_top_k, filter_doc_urn))
        key = filter_doc_urn if filter_doc_urn is not None else "GLOBAL"
        chunk_ids = self.responses.get(key, [])
        hits = [
            RetrievalHit(
                chunk_id=cid,
                score=1.0 - i * 0.01,
                payload={"chunk_id": cid, "text": f"text-of-{cid}"},
                rank=i + 1,
            )
            for i, cid in enumerate(chunk_ids[:top_k])
        ]
        return RetrievalResult(hits)


# ----------------------------------------------------------- fixtures & helpers

GOLD_Q68 = [
    "eli/reg/2024/1689/oj__art_6",
    "eli/reg/2024/1689/oj__art_27",
    "eli/reg/2016/679/oj__art_9",
    "eli/reg/2016/679/oj__art_35",
    "akn/it/act/legge/stato/2025-09-23/132__art_7",
]


def _q68_responses() -> dict[str | None, list[str]]:
    """Risposte pre-canned plausibili: ogni sub-query trova il gold della
    sua norma in top-3, retrieval globale trova solo L.132 art_7."""
    return {
        "eli/reg/2024/1689/oj": [
            "eli/reg/2024/1689/oj__recital_96",
            "eli/reg/2024/1689/oj__art_27",       # gold
            "eli/reg/2024/1689/oj__art_16",
            "eli/reg/2024/1689/oj__art_6",        # gold (rank 4)
            "eli/reg/2024/1689/oj__art_25",
        ],
        "eli/reg/2016/679/oj": [
            "eli/reg/2016/679/oj__recital_91",
            "eli/reg/2016/679/oj__art_9",         # gold
            "eli/reg/2016/679/oj__art_35",        # gold
            "eli/reg/2016/679/oj__recital_53",
            "eli/reg/2016/679/oj__recital_84",
        ],
        "akn/it/act/legge/stato/2025-09-23/132": [
            "akn/it/act/legge/stato/2025-09-23/132__art_7",  # gold
            "akn/it/act/legge/stato/2025-09-23/132__art_3",
            "akn/it/act/legge/stato/2025-09-23/132__art_1",
            "akn/it/act/legge/stato/2025-09-23/132__art_8",
            "akn/it/act/legge/stato/2025-09-23/132__art_10",
        ],
        "GLOBAL": [
            "eli/reg/2024/1689/oj__recital_57",
            "akn/it/act/legge/stato/2025-09-23/132__art_7",  # gold
            "akn/it/act/legge/stato/2025-09-23/132__art_11",
            "eli/reg/2024/1689/oj__recital_85",
            "akn/it/act/legge/stato/2025-09-23/132__art_15",
        ],
    }


# ----------------------------------------------------------- mono-norma fallback

def test_mono_norm_falls_back_to_hybrid(q68_stub_llm) -> None:
    """1 norma rilevata → no sub-query, no fusion: chiamata diretta a hybrid."""
    stub = _StubHybridRetriever({"GLOBAL": ["chunk_a", "chunk_b", "chunk_c"]})
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
        top_k_final=10,
    )
    result = cnr.retrieve(MONO_NORM_Q)
    # Una sola chiamata, senza filtro
    assert len(stub.calls) == 1
    assert stub.calls[0].filter_doc_urn is None
    assert [h.chunk_id for h in result] == ["chunk_a", "chunk_b", "chunk_c"]


def test_zero_norm_falls_back_to_hybrid(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({"GLOBAL": ["chunk_x"]})
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
        top_k_final=10,
    )
    result = cnr.retrieve("Quando serve fare una valutazione d'impatto?")
    assert len(stub.calls) == 1
    assert stub.calls[0].filter_doc_urn is None
    assert [h.chunk_id for h in result] == ["chunk_x"]


# ----------------------------------------------------------- multi-norma fusion

def test_q68_calls_one_subquery_per_norm_plus_global(q68_stub_llm) -> None:
    """Q68 → 3 norme + 1 retrieval globale = 4 chiamate a hybrid."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
        top_k_per_norm=5,
        top_k_global=5,
        top_k_final=20,
    )
    cnr.retrieve(Q68)
    assert len(stub.calls) == 4
    # Le 3 chiamate filtrate corrispondono ai 3 doc_urn
    filtered = sorted(c.filter_doc_urn for c in stub.calls if c.filter_doc_urn)
    assert filtered == sorted([
        "eli/reg/2024/1689/oj",
        "eli/reg/2016/679/oj",
        "akn/it/act/legge/stato/2025-09-23/132",
    ])
    # E una chiamata globale (senza filtro)
    assert sum(1 for c in stub.calls if c.filter_doc_urn is None) == 1


def test_q68_rrf_fusion_returns_all_5_golds(q68_stub_llm) -> None:
    """Con le risposte pre-canned, la fusione RRF deve includere tutti i 5 gold
    nei top-20 (in realtà top-N, dove N = unione delle risposte stub)."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
        top_k_per_norm=5,
        top_k_global=5,
        top_k_final=20,
    )
    result = cnr.retrieve(Q68)
    fused_ids = {h.chunk_id for h in result}
    assert set(GOLD_Q68).issubset(fused_ids), (
        f"Mancano gold: {set(GOLD_Q68) - fused_ids}"
    )


def test_q68_rrf_score_monotonic_descending(q68_stub_llm) -> None:
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
        top_k_per_norm=5,
        top_k_global=5,
        top_k_final=20,
    )
    result = cnr.retrieve(Q68)
    scores = [h.score for h in result]
    assert scores == sorted(scores, reverse=True), (
        f"RRF scores non monotoni: {scores}"
    )
    ranks = [h.rank for h in result]
    assert ranks == list(range(1, len(result) + 1))


def test_q68_rrf_chunk_in_multiple_sources_ranks_higher(q68_stub_llm) -> None:
    """L.132 art_7 appare in sub-query L.132 (rank 1) e in retrieval globale
    (rank 2). La sua RRF score deve essere strettamente maggiore di chunk che
    appaiono in una sola source."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
        rrf_k=60,
        top_k_per_norm=5,
        top_k_global=5,
        top_k_final=20,
    )
    result = cnr.retrieve(Q68)
    by_id = {h.chunk_id: h for h in result}

    l132_art7 = by_id["akn/it/act/legge/stato/2025-09-23/132__art_7"]
    # appare in 2 source (rank 1 + rank 2). RRF score = 1/(60+1) + 1/(60+2)
    expected = 1.0 / 61 + 1.0 / 62
    assert l132_art7.score == pytest.approx(expected, rel=1e-6)


def test_validation_top_k_per_norm_zero(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({})
    with pytest.raises(ValueError, match="top_k_per_norm"):
        CrossNormRetriever(
            hybrid_retriever=stub,  # type: ignore[arg-type]
            llm_client=q68_stub_llm,
            top_k_per_norm=0,
        )


def test_validation_rrf_k_zero(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({})
    with pytest.raises(ValueError, match="rrf_k"):
        CrossNormRetriever(
            hybrid_retriever=stub,  # type: ignore[arg-type]
            llm_client=q68_stub_llm,
            rrf_k=0,
        )


def test_norm_to_doc_urn_loaded_from_glossary(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({})
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm,
    )
    m = cnr._norm_to_doc_urn  # noqa: SLF001
    assert m["gdpr"] == "eli/reg/2016/679/oj"
    assert m["ai_act"] == "eli/reg/2024/1689/oj"
    assert m["dlgs_231"] == "akn/it/act/decreto_legislativo/stato/2001-06-08/231"
    assert m["nis2"] == "akn/it/act/decreto_legislativo/stato/2024-09-04/138"
    assert m["codice_privacy"] == "akn/it/act/decreto_legislativo/stato/2003-06-30/196"
    assert m["l_132_2025"] == "akn/it/act/legge/stato/2025-09-23/132"
