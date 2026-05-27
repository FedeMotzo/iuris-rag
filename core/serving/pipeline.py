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

        # Cross-norma v1.1 (opt-in): wrapper sopra l'HybridRetriever esistente
        # che orchestra trigger + sub-query LLM + RRF fusion.
        self._cross_norm = None
        if enable_cross_norm:
            from core.cross_norm import CrossNormRetriever
            self._cross_norm = CrossNormRetriever(
                hybrid_retriever=retriever,
                llm_client=llm_provider,
                top_k_per_norm=5,
                top_k_global=5,
                top_k_final=max(top_k, rerank_top_k),
                rerank_top_k_per_norm=rerank_top_k,
                rerank_top_k_global=rerank_top_k,
            )

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
        """Esegue retrieval + generate (non-streaming) + verify, ritorna esito."""
        t0 = time.perf_counter()
        retrieval, t_retr = self._do_retrieve(question)
        user_prompt = build_user_prompt(
            question, retrieval, include_expanded=self._use_graph,
        )
        gen, t_gen = self._do_generate(user_prompt)
        verification, t_verify = self._do_verify(gen.text, retrieval)
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
            answer=gen.text,
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
        retrieval, t_retr = self._do_retrieve(question)
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

    # ----------------------------------------------------- internal phases

    def _do_retrieve(self, question: str) -> tuple["RetrievalResult", float]:
        t = time.perf_counter()
        if self._cross_norm is not None:
            # CrossNormRetriever fa fallback automatico su hybrid standard se
            # rileva < 2 norme: zero impatto su query mono-norma. Per query
            # multi-norma, la fusione RRF avviene internamente sui hit
            # per-norma + globale, e ritorna i top `top_k` finali destinati al
            # prompt builder (stessa numerosità del path standard).
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
