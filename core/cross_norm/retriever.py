"""`CrossNormRetriever`: orchestratore retrieval cross-norma v1.1.

Pipeline:
1. Trigger lessicale deterministico (`detect_norms`) → lista norme citate.
2. Se < 2 norme: fallback su `HybridRetriever.retrieve(query)` standard.
3. Per ogni norma: sub-query LLM (Sonnet) + retrieval hybrid filtrato
   per `doc_urn` (rerank top_k_per_norm).
4. Retrieval globale sulla query originale (rerank top_k_global).
5. RRF fusion di tutti i risultati → top_k_final hit.

Tutti i source pesati uguale (no tuning) nel RRF.
"""

from __future__ import annotations

import logging
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from core.hybrid_retriever.types import RetrievalHit, RetrievalResult

from .multi_norm_trigger import detect_norms
from .subquery_generator import DEFAULT_GLOSSARY_PATH, generate_subquery

if TYPE_CHECKING:
    from core.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


class CrossNormRetriever:
    """Cross-norma RRF fusion: sub-query per norma + retrieval globale."""

    def __init__(
        self,
        hybrid_retriever: "HybridRetriever",
        llm_client: Any,
        glossary_path: Path = DEFAULT_GLOSSARY_PATH,
        top_k_per_norm: int = 5,
        top_k_global: int = 5,
        top_k_final: int = 20,
        rrf_k: int = 60,
        rerank_top_k_per_norm: int | None = 20,
        rerank_top_k_global: int | None = 20,
        debug: bool = False,
    ) -> None:
        if top_k_per_norm <= 0:
            raise ValueError(f"top_k_per_norm must be > 0 (got {top_k_per_norm})")
        if top_k_global <= 0:
            raise ValueError(f"top_k_global must be > 0 (got {top_k_global})")
        if top_k_final <= 0:
            raise ValueError(f"top_k_final must be > 0 (got {top_k_final})")
        if rrf_k <= 0:
            raise ValueError(f"rrf_k must be > 0 (got {rrf_k})")

        self._hybrid = hybrid_retriever
        self._llm = llm_client
        self._glossary_path = glossary_path
        self._top_k_per_norm = top_k_per_norm
        self._top_k_global = top_k_global
        self._top_k_final = top_k_final
        self._rrf_k = rrf_k
        self._rerank_top_k_per_norm = rerank_top_k_per_norm
        self._rerank_top_k_global = rerank_top_k_global
        self._debug = debug
        self._norm_to_doc_urn = self._load_norm_to_doc_urn(glossary_path)
        # Ultima esecuzione: stato intermedio per ispezione (popolato sempre,
        # stampato solo se debug=True). Utile per probe diagnostici futuri.
        self.last_trace: dict[str, Any] = {}

        logger.info(
            "CrossNormRetriever init top_k_per_norm=%d top_k_global=%d "
            "top_k_final=%d rrf_k=%d debug=%s",
            top_k_per_norm, top_k_global, top_k_final, rrf_k, debug,
        )

    # ---------------------------------------------------------------- public

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        """Cross-norma retrieval.

        Se la query cita < 2 norme rilevate dal trigger, fallback su
        HybridRetriever.retrieve standard sulla query originale.

        Args:
            query: query utente originale.
            top_k: opzionale, override di `top_k_final` per questa chiamata.

        Returns:
            `RetrievalResult` con max `top_k` (o `top_k_final`) hit.
        """
        norms = detect_norms(query)
        k_final = top_k or self._top_k_final

        if len(norms) < 2:
            logger.info(
                "cross_norm: %d norme rilevate (< 2) → fallback hybrid standard",
                len(norms),
            )
            return self._hybrid.retrieve(
                query=query,
                top_k=k_final,
                mode="hybrid",
                rerank_top_k=self._rerank_top_k_global,
            )

        logger.info("cross_norm: %d norme rilevate %s → fusion", len(norms), norms)

        trace: dict[str, Any] = {
            "query": query,
            "norms_detected": list(norms),
            "sub_queries": {},
            "per_norm_filtered": OrderedDict(),  # norm_id → [(rank, chunk_id, score)]
            "global": [],                         # [(rank, chunk_id, score)]
            "rrf_contributions": OrderedDict(),   # chunk_id → list[(source, rank, partial_rrf)]
            "fused_top": [],                      # [(rank, chunk_id, rrf_score, sources)]
        }

        # 3. sub-query per norma + retrieval filtrato
        per_source_rankings: list[tuple[str, list[RetrievalHit]]] = []
        hits_by_chunk: dict[str, RetrievalHit] = {}

        for norm_id in norms:
            doc_urn = self._norm_to_doc_urn.get(norm_id)
            if doc_urn is None:
                logger.warning("cross_norm: norm_id=%s manca doc_urn in glossary; skip",
                               norm_id)
                continue
            sub_q = generate_subquery(query, norm_id, self._llm,
                                       glossary_path=self._glossary_path)
            trace["sub_queries"][norm_id] = sub_q
            logger.info("cross_norm sub-query [%s]: %s", norm_id, sub_q[:120])
            sub_hits = self._hybrid.retrieve(
                query=sub_q,
                top_k=self._top_k_per_norm,
                mode="hybrid",
                rerank_top_k=self._rerank_top_k_per_norm,
                filter_doc_urn=doc_urn,
            )
            sub_hits_list = list(sub_hits)
            per_source_rankings.append((f"norm:{norm_id}", sub_hits_list))
            trace["per_norm_filtered"][norm_id] = [
                (h.rank, h.chunk_id, float(h.score)) for h in sub_hits_list
            ]
            for h in sub_hits_list:
                hits_by_chunk.setdefault(h.chunk_id, h)

        # 4. retrieval globale sulla query originale
        global_hits = self._hybrid.retrieve(
            query=query,
            top_k=self._top_k_global,
            mode="hybrid",
            rerank_top_k=self._rerank_top_k_global,
        )
        global_hits_list = list(global_hits)
        per_source_rankings.append(("global", global_hits_list))
        trace["global"] = [
            (h.rank, h.chunk_id, float(h.score)) for h in global_hits_list
        ]
        for h in global_hits_list:
            hits_by_chunk.setdefault(h.chunk_id, h)

        # 5. RRF fusion
        rrf_scores: dict[str, float] = defaultdict(float)
        contribs: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
        for src_label, ranked_hits in per_source_rankings:
            for h in ranked_hits:
                partial = 1.0 / (self._rrf_k + h.rank)
                rrf_scores[h.chunk_id] += partial
                contribs[h.chunk_id].append((src_label, h.rank, partial))
        trace["rrf_contributions"] = dict(contribs)

        # ordinamento RRF decrescente, tiebreak deterministico su chunk_id
        ordered = sorted(
            rrf_scores.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        fused: list[RetrievalHit] = []
        for new_rank, (cid, score) in enumerate(ordered[:k_final], start=1):
            src_hit = hits_by_chunk[cid]
            fused.append(
                RetrievalHit(
                    chunk_id=cid,
                    score=float(score),
                    payload=src_hit.payload,
                    rank=new_rank,
                )
            )
            trace["fused_top"].append((
                new_rank, cid, float(score),
                [(s, r) for s, r, _ in contribs[cid]],
            ))
        logger.info(
            "cross_norm fusion: %d source × ~k hit → %d hit finali (top_k=%d)",
            len(per_source_rankings), len(rrf_scores), k_final,
        )

        self.last_trace = trace
        if self._debug:
            self._print_trace(trace, k_final=k_final)

        return RetrievalResult(fused)

    @staticmethod
    def _print_trace(trace: dict[str, Any], k_final: int) -> None:
        """Stampa lo stato intermedio della retrieve (sub-query, ranking,
        contribuzioni RRF) per analisi diagnostica.

        Output formato leggibile a console. Niente parsing strutturato.
        Vedi `last_trace` per la versione dict ispezionabile.
        """
        lines: list[str] = []
        lines.append("")
        lines.append("=" * 78)
        lines.append("CROSS_NORM DIAGNOSTIC TRACE")
        lines.append("=" * 78)
        lines.append(f"Query: {trace['query']}")
        lines.append(f"Norme rilevate: {trace['norms_detected']}")
        lines.append("")
        for norm_id, sub_q in trace["sub_queries"].items():
            lines.append(f"--- Sub-query [{norm_id}] ---")
            lines.append(f"  {sub_q}")
        lines.append("")
        for norm_id, ranking in trace["per_norm_filtered"].items():
            lines.append(f"--- Filtered top-{len(ranking)} [norm:{norm_id}] ---")
            for rank, cid, score in ranking:
                lines.append(f"  {rank:>2}. {cid}  (score={score:.4f})")
        lines.append("")
        lines.append(f"--- Global top-{len(trace['global'])} ---")
        for rank, cid, score in trace["global"]:
            lines.append(f"  {rank:>2}. {cid}  (score={score:.4f})")
        lines.append("")
        lines.append(f"--- RRF fused top-{k_final} ---")
        for rank, cid, rrf_score, sources in trace["fused_top"]:
            src_str = ", ".join(f"{s}@{r}" for s, r in sources)
            lines.append(
                f"  {rank:>2}. {cid}  (rrf={rrf_score:.5f}, sources=[{src_str}])"
            )
        lines.append("=" * 78)
        print("\n".join(lines))

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
