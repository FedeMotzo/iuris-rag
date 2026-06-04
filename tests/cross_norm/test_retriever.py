"""Unit test `CrossNormRetriever` v1.2 step 2 — gruppi per-sub-query.

Niente Qdrant, niente LLM live. Tutti gli I/O sono stub:
- `_StubHybridRetriever` ritorna liste pre-canned di RetrievalHit basate su
  `filter_doc_urn` lookup (ignora il testo della sub-query, mappa solo per
  norma).
- `q68_stub_llm` (fixture) ritorna sub-query canoniche dalla cassette.

Contratto verificato: `retrieve()` ritorna sempre un `CrossNormResult` con
`groups` per-sub-query; gli hit di ogni gruppo provengono dalla source
(norma) corretta; il fallback < 2 norme è un gruppo singolo.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.cross_norm.retriever import CrossNormResult, CrossNormRetriever
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
    """Stub: registra ogni chiamata + ritorna hit pre-canned per `doc_urn`.

    Ignora il testo della sub-query (multi-subquery → stessa risposta per norma).
    Score = 1.0 - i*0.01 → simula logit ad alta confidenza decrescente.
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

# norm_id -> doc_urn (allineato a norm_glossary.yaml)
_URN = {
    "ai_act": "eli/reg/2024/1689/oj",
    "gdpr": "eli/reg/2016/679/oj",
    "l_132_2025": "akn/it/act/legge/stato/2025-09-23/132",
}


def _q68_responses() -> dict[str | None, list[str]]:
    return {
        "eli/reg/2024/1689/oj": [
            "eli/reg/2024/1689/oj__recital_96",
            "eli/reg/2024/1689/oj__art_27",
            "eli/reg/2024/1689/oj__art_16",
            "eli/reg/2024/1689/oj__art_6",
            "eli/reg/2024/1689/oj__art_25",
        ],
        "eli/reg/2016/679/oj": [
            "eli/reg/2016/679/oj__recital_91",
            "eli/reg/2016/679/oj__art_9",
            "eli/reg/2016/679/oj__art_35",
            "eli/reg/2016/679/oj__recital_53",
            "eli/reg/2016/679/oj__recital_84",
        ],
        "akn/it/act/legge/stato/2025-09-23/132": [
            "akn/it/act/legge/stato/2025-09-23/132__art_7",
            "akn/it/act/legge/stato/2025-09-23/132__art_3",
            "akn/it/act/legge/stato/2025-09-23/132__art_1",
            "akn/it/act/legge/stato/2025-09-23/132__art_8",
            "akn/it/act/legge/stato/2025-09-23/132__art_10",
        ],
        # NB: source `global` rimossa in v1.2 step 2 → la chiave GLOBAL non
        # viene mai consultata per le query multi-norma.
    }


# ----------------------------------------------------------- mono-norma fallback

def test_mono_norm_falls_back_to_single_group(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({"GLOBAL": ["chunk_a", "chunk_b", "chunk_c"]})
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_final=10,
    )
    result = cnr.retrieve(MONO_NORM_Q)
    assert isinstance(result, CrossNormResult)
    assert result.detected_norms == ["gdpr"]
    assert len(stub.calls) == 1
    assert stub.calls[0].filter_doc_urn is None
    # fallback = gruppo singolo, profondità preservata
    assert len(result.groups) == 1
    g = result.groups[0]
    assert g.source == "gdpr"
    assert [h.chunk_id for h in g.hits] == ["chunk_a", "chunk_b", "chunk_c"]


def test_zero_norm_falls_back_to_single_group(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({"GLOBAL": ["chunk_x"]})
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_final=10,
    )
    result = cnr.retrieve("Quando serve fare una valutazione d'impatto?")
    assert isinstance(result, CrossNormResult)
    assert result.detected_norms == []
    assert len(stub.calls) == 1
    assert stub.calls[0].filter_doc_urn is None
    assert len(result.groups) == 1
    assert result.groups[0].source == "global"
    assert [h.chunk_id for h in result.groups[0].hits] == ["chunk_x"]


# --------------------------------------------- multi-norma: gruppi per-sub-query

def test_q68_calls_match_total_subqueries_no_global(q68_stub_llm) -> None:
    """v1.2 step 2: una chiamata hybrid per OGNI sub-query, NESSUNA global.

    Numero totale = Σ_norm |sub_queries(norm)| (niente +1 global).
    """
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_per_subquery=5,
    )
    cnr.retrieve(Q68)
    total_subq = sum(len(sq) for sq in cnr.last_trace["sub_queries"].values())
    assert len(stub.calls) == total_subq, (
        f"Atteso {total_subq} call (niente global), ottenuto {len(stub.calls)}"
    )
    # Tutte le call sono filtrate per norma: nessuna call senza filtro.
    assert all(c.filter_doc_urn is not None for c in stub.calls)
    filtered_urns = {c.filter_doc_urn for c in stub.calls}
    assert filtered_urns == set(_URN.values())


def test_q68_groups_contain_all_5_golds(q68_stub_llm) -> None:
    """Formalizza il check di copertura: ogni gold compare nel top-k del suo
    gruppo-source (un gruppo la cui `source` è la norma del gold)."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_per_subquery=5,
    )
    result = cnr.retrieve(Q68)
    gold_norm = {
        "eli/reg/2024/1689/oj__art_6": "ai_act",
        "eli/reg/2024/1689/oj__art_27": "ai_act",
        "eli/reg/2016/679/oj__art_9": "gdpr",
        "eli/reg/2016/679/oj__art_35": "gdpr",
        "akn/it/act/legge/stato/2025-09-23/132__art_7": "l_132_2025",
    }
    for gold, norm in gold_norm.items():
        covered = any(
            g.source == norm and gold in {h.chunk_id for h in g.hits}
            for g in result.groups
        )
        assert covered, f"Gold {gold} non nel top-k di alcun gruppo source={norm}"


def test_q68_group_hits_come_from_correct_source(q68_stub_llm) -> None:
    """Gli hit di ogni gruppo provengono dalla source (norma) dichiarata."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_per_subquery=5,
    )
    result = cnr.retrieve(Q68)
    assert result.groups, "attesi gruppi per-sub-query"
    for g in result.groups:
        allowed = set(_q68_responses()[_URN[g.source]])
        got = {h.chunk_id for h in g.hits}
        assert got <= allowed, (
            f"Gruppo source={g.source}: hit fuori source {got - allowed}"
        )


def test_q68_top_k_per_subquery_caps_group_size(q68_stub_llm) -> None:
    """top_k_per_subquery è il cap sugli hit per gruppo (leva isolata)."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_per_subquery=3,
    )
    result = cnr.retrieve(Q68)
    assert all(len(g.hits) <= 3 for g in result.groups)
    # e lo stub riceve top_k=3
    assert all(c.top_k == 3 for c in stub.calls)


def test_q68_trace_contains_sub_queries_as_lists(q68_stub_llm) -> None:
    """trace['sub_queries'][norm_id] è list[str]."""
    stub = _StubHybridRetriever(_q68_responses())
    cnr = CrossNormRetriever(
        hybrid_retriever=stub,  # type: ignore[arg-type]
        llm_client=q68_stub_llm, top_k_per_subquery=5,
    )
    cnr.retrieve(Q68)
    sq_dict = cnr.last_trace["sub_queries"]
    assert set(sq_dict.keys()) == {"gdpr", "ai_act", "l_132_2025"}
    for nid, sub_qs in sq_dict.items():
        assert isinstance(sub_qs, list), f"{nid}: atteso list, ottenuto {type(sub_qs)}"
        assert all(isinstance(s, str) for s in sub_qs)
        assert len(sub_qs) >= 1


# --------------------------------------------- validation / config

def test_validation_top_k_per_subquery_zero(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({})
    with pytest.raises(ValueError, match="top_k_per_subquery"):
        CrossNormRetriever(
            hybrid_retriever=stub,  # type: ignore[arg-type]
            llm_client=q68_stub_llm, top_k_per_subquery=0,
        )


def test_validation_rerank_pool_below_top_k(q68_stub_llm) -> None:
    stub = _StubHybridRetriever({})
    with pytest.raises(ValueError, match="rerank_pool_per_subquery"):
        CrossNormRetriever(
            hybrid_retriever=stub,  # type: ignore[arg-type]
            llm_client=q68_stub_llm,
            top_k_per_subquery=5, rerank_pool_per_subquery=3,
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
