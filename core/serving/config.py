"""Builder pipeline RAG con config da env + defaults sensati.

Decisioni W5 (vedi PROJECT_CONTEXT.md voci 20-23):
- top_k default 5 (post-rerank), rerank_top_k default 20
- use_graph default False (configurabile, vedi MPS smoke ratio costo/benefit)
- topologia MPS condizionale al provider: cloud → reranker MPS, locale → CPU.
  Nota: HybridRetriever non espone device del reranker nel costruttore (il
  reranker è iniettato già configurato), quindi questa pipeline NON forza
  device. Il caller di build_default_pipeline è responsabile di costruire
  HybridRetriever con il reranker sul device corretto in base al provider.

# TODO W5: esporre device reranker in HybridRetriever per topologia
# condizionale automatica (vedi spike/MPS_COABITATION_RESULTS.md).
# Per ora la pipeline accetta un HybridRetriever pre-costruito esternamente
# e legge solo le env var per top_k, rerank_top_k, use_graph, max_tokens.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from core.llm_provider.config import load_provider_from_env
from core.normative_graph import load_graph

from .pipeline import RAGPipeline

if TYPE_CHECKING:
    from core.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} non è un intero valido: {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def build_default_pipeline(
    retriever: "HybridRetriever",
) -> RAGPipeline:
    """Costruisce `RAGPipeline` con LLM provider + parametri letti da env.

    Env vars (vedi `.env.example`):

    - `LLM_PROVIDER`, `ANTHROPIC_*`, `OLLAMA_*` (gestite da
      `core.llm_provider.config.load_provider_from_env()`)
    - `RAG_TOP_K` (default 5)
    - `RAG_RERANK_TOP_K` (default 20)
    - `RAG_USE_GRAPH` (default false)
    - `RAG_MAX_OUTPUT_TOKENS` (default 1000 — alzato da 500 dopo smoke
      cloud 2026-05-19: Sonnet 4.6 troncava 3/3 query a 500 mid-frase;
      vedi PROJECT_CONTEXT.md registro decisioni)

    `retriever` va costruito dal caller (richiede QdrantClient, BgeM3Encoder,
    bm25, reranker — quest'ultimo sul device corretto in base al provider:
    MPS con cloud, CPU con Ollama locale).
    """
    provider = load_provider_from_env()
    top_k = _env_int("RAG_TOP_K", 5)
    rerank_top_k = _env_int("RAG_RERANK_TOP_K", 20)
    use_graph = _env_bool("RAG_USE_GRAPH", False)
    max_output_tokens = _env_int("RAG_MAX_OUTPUT_TOKENS", 1000)
    enable_cross_norm = _env_bool("RAG_ENABLE_CROSS_NORM", False)

    graph_links = load_graph() if use_graph else None

    return RAGPipeline(
        retriever=retriever,
        llm_provider=provider,
        top_k=top_k,
        rerank_top_k=rerank_top_k,
        use_graph=use_graph,
        graph_links=graph_links,
        max_output_tokens=max_output_tokens,
        enable_cross_norm=enable_cross_norm,
    )
