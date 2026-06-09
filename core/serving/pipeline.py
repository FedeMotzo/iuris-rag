"""Pipeline RAG serving — orchestra retrieval → generate → verify.

Streaming primo-classe via `query_stream`. Citation verify gira solo a
stream completato (deterministico, lavora su testo completo). Niente
caching, niente conversation history, niente async (W6+ se serviranno).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.citation_verifier import VerificationResult, verify_citations
from core.llm_provider import GenerationChunk, GenerationResult, LLMProvider
from core.rag_prompt import build_user_prompt, load_system_prompt

if TYPE_CHECKING:
    from core.classification import ClassificationResult, ObligationItem
    from core.hybrid_retriever import HybridRetriever
    from core.hybrid_retriever.types import RetrievalResult
    from core.normative_graph import GraphLink

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAGResponse:
    """Esito completo di una query RAG (non-streaming)."""

    answer: str
    annotated_answer: str
    retrieval_result: "RetrievalResult"
    verification: VerificationResult
    timings_ms: dict[str, float]
    generation_meta: GenerationResult


class RAGPipeline:
    """Pipeline RAG: hybrid retrieval + optional graph + LLM + citation verify.

    `use_graph` può essere `True` solo se in init è stato passato `graph_links`
    non vuoto (caricato dall'esterno, p.es. `core.normative_graph.load_graph()`).
    """

    def __init__(
        self,
        retriever: "HybridRetriever",
        llm_provider: LLMProvider,
        top_k: int = 5,
        rerank_top_k: int = 20,
        use_graph: bool = False,
        graph_links: "list[GraphLink] | None" = None,
        max_output_tokens: int = 4000,
        system_prompt_lang: str = "it",
        enable_cross_norm: bool = False,
        map_llm_provider: LLMProvider | None = None,
        cross_norm_map_top_k: int = 5,
    ) -> None:
        if use_graph and not graph_links:
            raise ValueError(
                "use_graph=True ma graph_links non fornito o vuoto. "
                "Carica il graph con core.normative_graph.load_graph() "
                "e passalo a RAGPipeline(graph_links=...)."
            )
        if enable_cross_norm and use_graph:
            raise ValueError(
                "enable_cross_norm=True non è compatibile con use_graph=True in v1.1. "
                "Disabilita una delle due (cross-norma e graph-expansion sono path "
                "indipendenti di retrieval avanzato)."
            )
        self._retriever = retriever
        self._llm = llm_provider
        self._top_k = top_k
        self._rerank_top_k = rerank_top_k
        self._use_graph = use_graph
        self._graph_links = graph_links
        self._max_tokens = max_output_tokens
        self._system_prompt = load_system_prompt(system_prompt_lang)

        # Cross-norma v1.2 (opt-in): trigger + sub-query LLM → gruppi
        # per-sub-query → map (mini Haiku) → assembly strutturato.
        self._cross_norm = None
        self._map_llm: LLMProvider | None = None
        self._cross_norm_map_top_k = cross_norm_map_top_k
        if enable_cross_norm:
            from core.cross_norm import CrossNormRetriever
            self._cross_norm = CrossNormRetriever(
                hybrid_retriever=retriever,
                llm_client=llm_provider,
                top_k_per_subquery=cross_norm_map_top_k,
                rerank_pool_per_subquery=rerank_top_k,
                top_k_final=max(top_k, rerank_top_k),
                rerank_top_k_final=rerank_top_k,
            )
            # Map model: Haiku 4.5 di default (configurabile via map_llm_provider).
            self._map_llm = map_llm_provider or self._default_map_provider(llm_provider)

        logger.info(
            "RAGPipeline init provider=%s model=%s top_k=%d rerank_top_k=%d "
            "use_graph=%s max_tokens=%d enable_cross_norm=%s",
            llm_provider.provider_name, llm_provider.model_name,
            top_k, rerank_top_k, use_graph, max_output_tokens, enable_cross_norm,
        )

    # ----------------------------------------------------- public API

    @property
    def use_graph(self) -> bool:
        return self._use_graph

    def query(self, question: str) -> RAGResponse:
        """Esegue retrieval + generate (non-streaming) + verify, ritorna esito.

        Cross-norma multi-norma (≥2 norme): map (mini Haiku per gruppo) +
        assembly strutturato sostituiscono il generate monolitico. Path
        mono-norma e non-cross invariati.
        """
        t0 = time.perf_counter()
        retrieved, t_retr = self._retrieve(question)

        if self._is_cross_norm_multi(retrieved):
            answer, retrieval, gen, t_gen = self._map_assemble_answer(retrieved)
        else:
            retrieval = self._as_retrieval_result(retrieved)
            user_prompt = build_user_prompt(
                question, retrieval, include_expanded=self._use_graph,
            )
            gen, t_gen = self._do_generate(user_prompt)
            answer = gen.text

        verification, t_verify = self._do_verify(answer, retrieval)
        t_total = (time.perf_counter() - t0) * 1000.0

        timings = {
            "retrieval_ms": t_retr,
            "generate_ms": t_gen,
            "verify_ms": t_verify,
            "total_ms": t_total,
        }
        logger.info(
            "query done retrieval=%.0fms gen=%.0fms verify=%.0fms total=%.0fms "
            "all_verified=%s n_cite=%d",
            t_retr, t_gen, t_verify, t_total,
            verification.all_verified, verification.n_total,
        )
        return RAGResponse(
            answer=answer,
            annotated_answer=verification.annotated_text,
            retrieval_result=retrieval,
            verification=verification,
            timings_ms=timings,
            generation_meta=gen,
        )

    def query_stream(
        self, question: str,
    ) -> Iterator[tuple[str, GenerationChunk | RAGResponse]]:
        """Streaming generation. Yield:

        - `("chunk", GenerationChunk)` per ogni delta dell'LLM (anche il
          marker finale con `text=""` e `is_final=True`),
        - `("final", RAGResponse)` una sola volta al termine, con tutto.

        Il citation verify gira dopo lo stream sull'output completo.
        """
        t0 = time.perf_counter()
        retrieved, t_retr = self._retrieve(question)

        # Cross-norma multi: map+assembly non è streaming → emette il report
        # assemblato come un unico chunk, poi il final.
        if self._is_cross_norm_multi(retrieved):
            answer, retrieval, gen, t_gen = self._map_assemble_answer(retrieved)
            yield ("chunk", GenerationChunk(text=answer, is_final=False))
            yield ("chunk", GenerationChunk(text="", is_final=True))
            verification, t_verify = self._do_verify(answer, retrieval)
            t_total = (time.perf_counter() - t0) * 1000.0
            timings = {
                "retrieval_ms": t_retr,
                "generate_ms": t_gen,
                "verify_ms": t_verify,
                "total_ms": t_total,
            }
            yield (
                "final",
                RAGResponse(
                    answer=answer,
                    annotated_answer=verification.annotated_text,
                    retrieval_result=retrieval,
                    verification=verification,
                    timings_ms=timings,
                    generation_meta=gen,
                ),
            )
            return

        retrieval = self._as_retrieval_result(retrieved)
        user_prompt = build_user_prompt(
            question, retrieval, include_expanded=self._use_graph,
        )

        t_gen_start = time.perf_counter()
        t_first: float | None = None
        chunks: list[str] = []
        for ch in self._llm.generate_stream(
            prompt=user_prompt,
            system=self._system_prompt,
            max_tokens=self._max_tokens,
            temperature=0.0,
        ):
            if ch.text and t_first is None:
                t_first = time.perf_counter()
            chunks.append(ch.text)
            yield ("chunk", ch)
        t_gen_end = time.perf_counter()
        if t_first is None:
            t_first = t_gen_end

        # Costruisce il GenerationResult ex-post (consumo manuale dello stream).
        meta = self._llm._last_stream_meta()
        gen = GenerationResult(
            text="".join(chunks),
            n_input_tokens=meta["n_input_tokens"],
            n_output_tokens=meta["n_output_tokens"],
            ttft_ms=(t_first - t_gen_start) * 1000.0,
            total_ms=(t_gen_end - t_gen_start) * 1000.0,
            finish_reason=meta["finish_reason"],
            provider=self._llm.provider_name,
            model=self._llm.model_name,
        )

        verification, t_verify = self._do_verify(gen.text, retrieval)
        t_total = (time.perf_counter() - t0) * 1000.0
        timings = {
            "retrieval_ms": t_retr,
            "generate_ms": (t_gen_end - t_gen_start) * 1000.0,
            "verify_ms": t_verify,
            "total_ms": t_total,
        }
        logger.info(
            "query_stream done retrieval=%.0fms gen=%.0fms verify=%.0fms "
            "total=%.0fms ttft=%.0fms all_verified=%s n_cite=%d",
            t_retr, timings["generate_ms"], t_verify, t_total, gen.ttft_ms,
            verification.all_verified, verification.n_total,
        )
        yield (
            "final",
            RAGResponse(
                answer=gen.text,
                annotated_answer=verification.annotated_text,
                retrieval_result=retrieval,
                verification=verification,
                timings_ms=timings,
                generation_meta=gen,
            ),
        )

    def classify(self, system_description: str) -> "ClassificationResult":
        """CLASSIFICAZIONE UC1 (single-norm AI Act), parallela a query(). SOLO
        classificazione, role-free e senza adempimenti.

        Insieme CHIUSO: set fisso di norme di classificazione caricato per
        chunk_id (no retrieval semantico) → giudizio per-candidato (self._llm)
        → card sez. 1-3 + limiti. Gli adempimenti (sez. 4) sono separati:
        `get_obligations(role)`.

        Non tocca `query()`/`query_stream()`/`enable_cross_norm`/`_is_cross_norm_multi`.
        """
        from core.classification import (
            FIXED_SET_CHUNK_IDS,
            ClassificationResult,
            build_classification_card,
            judge_classification,
        )

        t0 = time.perf_counter()
        fixed_chunks = self._retriever.fetch_by_chunk_ids(FIXED_SET_CHUNK_IDS)
        judgment = judge_classification(system_description, fixed_chunks, self._llm)
        high_risk_annex = judgment.high_risk_annex
        card = build_classification_card(judgment)

        t_total = (time.perf_counter() - t0) * 1000.0
        logger.info(
            "classify done high_risk_annex=%s art6_1=%s vietata=%s total=%.0fms",
            high_risk_annex, judgment.art6_1_safety_component.plausible,
            card.prohibited_flag, t_total,
        )
        return ClassificationResult(
            system_description=system_description,
            judgment=judgment,
            card=card,
            high_risk_annex=high_risk_annex,
        )

    def get_obligations(self, role: str = "deployer") -> "list[ObligationItem]":
        """Adempimenti AI Act per ruolo (DATO STATICO CURATO), grounded sul corpus.

        Operazione separata da `classify()`. `role`: "provider" o "deployer"
        (default). Ritorna tutte le voci del ruolo con i tag di condizione; il
        testo-fonte di ogni articolo (e l'eventuale puntatore GDPR) è popolato
        via `fetch_by_chunk_ids`.
        """
        from core.classification import get_obligations as _get_obligations

        return _get_obligations(role, retriever=self._retriever)

    # ----------------------------------------------------- internal phases

    def _retrieve(self, question: str):
        """Retrieval. Ritorna `CrossNormResult` (path cross-norma) o
        `RetrievalResult` (path standard / mono-norma) + tempo in ms."""
        t = time.perf_counter()
        if self._cross_norm is not None:
            result = self._cross_norm.retrieve(question, top_k=self._top_k)
        else:
            result = self._retriever.retrieve(
                query=question,
                top_k=self._top_k,
                mode="hybrid",
                rerank_top_k=self._rerank_top_k,
                graph_links=self._graph_links if self._use_graph else None,
            )
        return result, (time.perf_counter() - t) * 1000.0

    @staticmethod
    def _is_cross_norm_multi(retrieved) -> bool:
        from core.cross_norm import CrossNormResult
        return (
            isinstance(retrieved, CrossNormResult)
            and len(retrieved.detected_norms) >= 2
        )

    def _as_retrieval_result(self, retrieved) -> "RetrievalResult":
        """Path standard: `RetrievalResult` così com'è; fallback cross-norma
        (< 2 norme, gruppo singolo) appiattito a `RetrievalResult`."""
        from core.cross_norm import CrossNormResult
        from core.cross_norm.map_assemble import collect_universe

        if isinstance(retrieved, CrossNormResult):
            return collect_universe(retrieved.groups, self._cross_norm_map_top_k)
        return retrieved

    def _map_assemble_answer(self, cn_result):
        """Map (mini Haiku per gruppo) + assembly strutturato. Ritorna
        (testo_assemblato, universo_chunk, GenerationResult, t_map_ms)."""
        from core.cross_norm.map_assemble import map_and_assemble

        t = time.perf_counter()
        text, universe, minis, n_sections = map_and_assemble(
            cn_result, self._map_llm, top_k_hits=self._cross_norm_map_top_k,
        )
        t_map = (time.perf_counter() - t) * 1000.0
        self.last_cross_norm_minis = minis
        gen = GenerationResult(
            text=text,
            n_input_tokens=sum(m.n_input_tokens for m in minis),
            n_output_tokens=sum(m.n_output_tokens for m in minis),
            ttft_ms=0.0,
            total_ms=t_map,
            finish_reason="stop",
            provider=self._map_llm.provider_name,
            model=self._map_llm.model_name,
        )
        logger.info(
            "cross_norm map+assembly: %d mini, %d sezioni, %d char",
            len(minis), n_sections, len(text),
        )
        return text, universe, gen, t_map

    @staticmethod
    def _default_map_provider(fallback: LLMProvider) -> LLMProvider:
        """Provider di default per il map: Haiku 4.5 via .env, con fallback al
        provider principale se la chiave Anthropic non è disponibile."""
        import os

        from core.cross_norm.map_assemble import MAP_MODEL_DEFAULT

        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return fallback
        try:
            from core.llm_provider.anthropic_provider import AnthropicProvider
            return AnthropicProvider(api_key=key, model=MAP_MODEL_DEFAULT)
        except Exception:  # noqa: BLE001
            return fallback

    def _do_generate(self, user_prompt: str) -> tuple[GenerationResult, float]:
        t = time.perf_counter()
        gen = self._llm.generate(
            prompt=user_prompt,
            system=self._system_prompt,
            max_tokens=self._max_tokens,
            temperature=0.0,
        )
        return gen, (time.perf_counter() - t) * 1000.0

    def _do_verify(
        self, llm_text: str, retrieval: "RetrievalResult",
    ) -> tuple[VerificationResult, float]:
        t = time.perf_counter()
        chunk_ids = {h.chunk_id for h in retrieval}
        if self._use_graph:
            chunk_ids.update(
                e.chunk_id for e in getattr(retrieval, "expanded_chunks", None) or []
            )
        verification = verify_citations(llm_text, retrieval_context=chunk_ids)
        return verification, (time.perf_counter() - t) * 1000.0
