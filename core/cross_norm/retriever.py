"""`CrossNormRetriever`: orchestratore retrieval cross-norma v1.2 (step 2).

Step 2 cambia SOLO come i risultati sono impacchettati, non cosa viene
recuperato: niente più fusione score-aware (sigmoide / IQR-gating / RRF),
niente source `global`. `retrieve()` ritorna i **gruppi per-sub-query**
(profondità preservata): un gruppo per sub-query, ciascuno con i top-k hit
della propria sub-query. Il retrieval per-sub-query è già filtrato per
`doc_urn` della norma → i gruppi sono norm-puri per costruzione (nessun
filtro sigla≠source necessario).

Contratto di ritorno:
    SubQueryGroup{ sub_query: str, source: str (norm_id), hits: list[RetrievalHit] }
    CrossNormResult{ query: str, detected_norms: list[str],
                     groups: list[SubQueryGroup] }

Pipeline:
1. Trigger lessicale deterministico (`detect_norms`) → lista norme citate.
2. Se < 2 norme: fallback su `HybridRetriever.retrieve(query)` standard
   (retrieval INVARIATO), il cui esito è wrappato in un gruppo singolo per
   uniformità di ritorno (profondità preservata).
3. Per ogni norma N: `generate_subquery(query, N) → list[str]`; per ogni
   sub-query un retrieval hybrid filtrato per `doc_urn=N`, rerank contro la
   sub-query, top-`top_k_per_subquery` hit → un `SubQueryGroup`.

La riduzione dei gruppi (map-reduce) è lo step 3; qui la pipeline li
appiattisce con un adattatore temporaneo.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from core.hybrid_retriever.types import RetrievalHit

from .multi_norm_trigger import detect_norms
from .subquery_generator import DEFAULT_GLOSSARY_PATH, generate_subquery

if TYPE_CHECKING:
    from core.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubQueryGroup:
    """Hit recuperati da UNA sub-query, già filtrati per norma.

    `source` è il norm_id (gdpr/ai_act/...) della sub-query, oppure "global"
    per il gruppo singolo del fallback mono/zero-norma. `hits` è ordinato per
    score reranker discendente.
    """

    sub_query: str
    source: str
    hits: list[RetrievalHit]


@dataclass
class CrossNormResult:
    """Esito cross-norma: gruppi per-sub-query, profondità preservata."""

    query: str
    detected_norms: list[str]
    groups: list[SubQueryGroup] = field(default_factory=list)


class CrossNormRetriever:
    """Cross-norma multi-sub-query → gruppi per-sub-query (v1.2 step 2).

    `top_k_per_subquery` è la leva isolata: quanti hit (rerankati) ogni
    gruppo trattiene. Default 3, fissato empiricamente col check di copertura
    retrieval sulle query cross-norma del benchmark.
    """

    def __init__(
        self,
        hybrid_retriever: "HybridRetriever",
        llm_client: Any,
        glossary_path: Path = DEFAULT_GLOSSARY_PATH,
        top_k_per_subquery: int = 3,
        rerank_pool_per_subquery: int = 20,
        top_k_final: int = 20,
        rerank_top_k_final: int | None = 20,
        debug: bool = False,
    ) -> None:
        if top_k_per_subquery <= 0:
            raise ValueError(
                f"top_k_per_subquery must be > 0 (got {top_k_per_subquery})"
            )
        if rerank_pool_per_subquery < top_k_per_subquery:
            raise ValueError(
                f"rerank_pool_per_subquery ({rerank_pool_per_subquery}) must be "
                f">= top_k_per_subquery ({top_k_per_subquery})"
            )
        if top_k_final <= 0:
            raise ValueError(f"top_k_final must be > 0 (got {top_k_final})")

        self._hybrid = hybrid_retriever
        self._llm = llm_client
        self._glossary_path = glossary_path
        self._top_k_per_subquery = top_k_per_subquery
        self._rerank_pool_per_subquery = rerank_pool_per_subquery
        self._top_k_final = top_k_final
        self._rerank_top_k_final = rerank_top_k_final
        self._debug = debug
        self._norm_to_doc_urn = self._load_norm_to_doc_urn(glossary_path)
        self.last_trace: dict[str, Any] = {}

        logger.info(
            "CrossNormRetriever v1.2 init top_k_per_subquery=%d "
            "rerank_pool_per_subquery=%d top_k_final=%d debug=%s",
            top_k_per_subquery, rerank_pool_per_subquery, top_k_final, debug,
        )

    # ---------------------------------------------------------------- public

    def retrieve(self, query: str, top_k: int | None = None) -> CrossNormResult:
        """Cross-norma retrieval v1.2 → gruppi per-sub-query.

        Se la query cita < 2 norme, fallback su HybridRetriever.retrieve
        standard (retrieval invariato), wrappato in un gruppo singolo.
        """
        norms = detect_norms(query)

        if len(norms) < 2:
            k_final = top_k or self._top_k_final
            logger.info(
                "cross_norm: %d norme rilevate (< 2) → fallback hybrid standard",
                len(norms),
            )
            hits = list(
                self._hybrid.retrieve(
                    query=query,
                    top_k=k_final,
                    mode="hybrid",
                    rerank_top_k=self._rerank_top_k_final,
                )
            )
            source = norms[0] if norms else "global"
            self.last_trace = {
                "query": query,
                "norms_detected": list(norms),
                "fallback": True,
            }
            return CrossNormResult(
                query=query,
                detected_norms=list(norms),
                groups=[SubQueryGroup(sub_query=query, source=source, hits=hits)],
            )

        logger.info(
            "cross_norm v1.2: %d norme rilevate %s → gruppi per-sub-query",
            len(norms), norms,
        )

        trace: dict[str, Any] = {
            "query": query,
            "norms_detected": list(norms),
            "fallback": False,
            "sub_queries": OrderedDict(),  # norm_id -> list[str]
        }
        groups: list[SubQueryGroup] = []

        for norm_id in norms:
            doc_urn = self._norm_to_doc_urn.get(norm_id)
            if doc_urn is None:
                logger.warning(
                    "cross_norm: norm_id=%s manca doc_urn in glossary; skip",
                    norm_id,
                )
                continue
            sub_queries = generate_subquery(
                query, norm_id, self._llm, glossary_path=self._glossary_path,
            )
            trace["sub_queries"][norm_id] = list(sub_queries)
            logger.info(
                "cross_norm [%s]: %d sub-query mono-concetto",
                norm_id, len(sub_queries),
            )

            for sub_q in sub_queries:
                sub_hits = self._hybrid.retrieve(
                    query=sub_q,
                    top_k=self._top_k_per_subquery,
                    mode="hybrid",
                    rerank_top_k=self._rerank_pool_per_subquery,
                    filter_doc_urn=doc_urn,
                )
                groups.append(
                    SubQueryGroup(
                        sub_query=sub_q, source=norm_id, hits=list(sub_hits),
                    )
                )

        self.last_trace = trace
        if self._debug:
            self._print_trace(trace, groups)

        return CrossNormResult(
            query=query, detected_norms=list(norms), groups=groups,
        )

    # --------------------------------------------------------------- private

    @staticmethod
    def _load_norm_to_doc_urn(glossary_path: Path) -> dict[str, str]:
        with glossary_path.open(encoding="utf-8") as fh:
            glossary = yaml.safe_load(fh)
        mapping: dict[str, str] = {}
        for norm_id, entry in (glossary or {}).items():
            urn = (entry or {}).get("doc_urn")
            if urn:
                mapping[norm_id] = urn
        return mapping

    @staticmethod
    def _print_trace(trace: dict[str, Any], groups: list[SubQueryGroup]) -> None:
        lines: list[str] = []
        lines.append("")
        lines.append("=" * 78)
        lines.append("CROSS_NORM v1.2 DIAGNOSTIC TRACE (gruppi per-sub-query)")
        lines.append("=" * 78)
        lines.append(f"Query: {trace['query']}")
        lines.append(f"Norme rilevate: {trace['norms_detected']}")
        lines.append("")
        for norm_id, sub_qs in trace.get("sub_queries", {}).items():
            lines.append(f"--- Sub-query [{norm_id}] (n={len(sub_qs)}) ---")
            for i, sq in enumerate(sub_qs):
                lines.append(f"  [{i}] {sq}")
        lines.append("")
        for gi, g in enumerate(groups):
            lines.append(
                f"--- Gruppo {gi} [source:{g.source}] "
                f"sub_q='{_truncate(g.sub_query, 60)}' ({len(g.hits)} hit) ---"
            )
            for h in g.hits:
                lines.append(f"  {h.rank:>2}. {h.chunk_id}  (score={h.score:.4f})")
        lines.append("=" * 78)
        print("\n".join(lines))


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."
