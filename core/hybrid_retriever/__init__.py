"""Hybrid retriever: dense (bge-m3) + sparse (BM25) + RRF + reranker opzionale."""

from .retriever import HybridRetriever
from .types import RetrievalHit, RetrievalResult

__all__ = ["HybridRetriever", "RetrievalHit", "RetrievalResult"]
