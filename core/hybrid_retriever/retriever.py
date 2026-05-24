"""`HybridRetriever`: retrieval dense / sparse / hybrid + reranking opzionale.

Wrapper sopra Qdrant Query API (≥1.10) per `italian_legal_v1_hybrid`. Stateless,
sync, nessun caching, nessuna astrazione VectorStore — il client è una
dipendenza concreta iniettata dal caller.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from qdrant_client import QdrantClient, models

from core.embedding import BgeM3Encoder
from core.terminology import expand_query
from core.vector_store import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME

from .types import RetrievalHit, RetrievalResult

if TYPE_CHECKING:
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder

    from core.normative_graph import GraphLink

logger = logging.getLogger(__name__)

Mode = Literal["dense", "sparse", "hybrid"]
_VALID_MODES = {"dense", "sparse", "hybrid"}


class HybridRetriever:
    """Recupero dense / sparse / hybrid con eventuale rerank post-hoc.

    Tutti i modelli (encoder dense, BM25 sparse, reranker) sono iniettati
    dall'esterno: la classe non ne carica e non ne possiede il ciclo di vita.
    Questo è intenzionale perché bge-m3 e bge-reranker-v2-m3 non coabitano
    in MPS su Mac M4 Pro 24 GB — la gestione di load/unload spetta al caller.
    """

    def __init__(
        self,
        client: QdrantClient,
        encoder: BgeM3Encoder,
        bm25: "SparseTextEmbedding",
        collection: str,
        reranker: "CrossEncoder | None" = None,
    ) -> None:
        self._client = client
        self._encoder = encoder
        self._bm25 = bm25
        self._collection = collection
        self._reranker = reranker

    # ------------------------------------------------------------------ public

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        mode: Mode = "hybrid",
        rerank_top_k: int | None = None,
        graph_links: "list[GraphLink] | None" = None,
        graph_max_expansions: int = 5,
    ) -> RetrievalResult:
        self._validate_args(top_k, mode, rerank_top_k)

        # Query expansion via terminology aliases (FRIA, DPIA, ecc).
        # Vedi core/terminology/aliases.yaml.
        query = expand_query(query)

        # Quanti hit chiedere a Qdrant: se è prevista una rerank, prendiamo
        # rerank_top_k così il reranker ha materiale; altrimenti top_k.
        fetch_k = rerank_top_k if rerank_top_k is not None else top_k

        logger.info("retrieve mode=%s fetch_k=%d top_k=%d rerank=%s graph=%s",
                    mode, fetch_k, top_k, rerank_top_k is not None,
                    graph_links is not None)

        if mode == "dense":
            points = self._query_dense(query, fetch_k)
        elif mode == "sparse":
            points = self._query_sparse(query, fetch_k)
        else:
            points = self._query_hybrid(query, fetch_k)

        hits = [self._point_to_hit(p, rank=i + 1) for i, p in enumerate(points)]

        if rerank_top_k is not None:
            hits = self._rerank(query, hits, top_k=top_k)
        else:
            hits = hits[:top_k]

        if graph_links is None:
            return RetrievalResult(hits)

        from core.normative_graph import expand_context
        expanded = expand_context(
            retrieved=[(h.chunk_id, h.score) for h in hits],
            graph=graph_links,
            max_expansions=graph_max_expansions,
        )
        return RetrievalResult(hits, expanded_chunks=expanded)

    # ----------------------------------------------------------------- private

    @staticmethod
    def _validate_args(top_k: int, mode: str, rerank_top_k: int | None) -> None:
        if top_k <= 0:
            raise ValueError(f"top_k must be > 0 (got {top_k})")
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(_VALID_MODES)} (got {mode!r})")
        if rerank_top_k is not None:
            if rerank_top_k < top_k:
                raise ValueError(
                    f"rerank_top_k ({rerank_top_k}) must be >= top_k ({top_k})"
                )

    def _ensure_reranker_available(self) -> "CrossEncoder":
        if self._reranker is None:
            raise ValueError("rerank_top_k requested but no reranker provided")
        return self._reranker

    def _encode_dense(self, query: str) -> list[float]:
        # BgeM3Encoder.encode() applica internamente l'instruction prefix
        # italiano (vedi core/embedding/bge_m3.py).
        [vec] = self._encoder.encode([query], batch_size=1)
        return vec

    def _encode_sparse(self, query: str) -> models.SparseVector:
        emb = next(self._bm25.query_embed(query))
        return models.SparseVector(
            indices=emb.indices.tolist(),
            values=emb.values.tolist(),
        )

    def _query_dense(self, query: str, limit: int):
        dvec = self._encode_dense(query)
        return self._client.query_points(
            collection_name=self._collection,
            query=dvec,
            using=DENSE_VECTOR_NAME,
            limit=limit,
            with_payload=True,
        ).points

    def _query_sparse(self, query: str, limit: int):
        svec = self._encode_sparse(query)
        return self._client.query_points(
            collection_name=self._collection,
            query=svec,
            using=SPARSE_VECTOR_NAME,
            limit=limit,
            with_payload=True,
        ).points

    def _query_hybrid(self, query: str, limit: int):
        dvec = self._encode_dense(query)
        svec = self._encode_sparse(query)
        # Larghezza del prefetch: 2x del limit richiesto, così RRF ha
        # abbastanza candidati per fondere senza tagliare prima del tempo.
        prefetch_limit = max(limit * 2, 1)
        return self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                models.Prefetch(query=dvec, using=DENSE_VECTOR_NAME, limit=prefetch_limit),
                models.Prefetch(query=svec, using=SPARSE_VECTOR_NAME, limit=prefetch_limit),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        ).points

    @staticmethod
    def _point_to_hit(point, rank: int) -> RetrievalHit:
        payload = dict(point.payload or {})
        chunk_id = payload.get("chunk_id", "")
        return RetrievalHit(
            chunk_id=chunk_id,
            score=float(point.score),
            payload=payload,
            rank=rank,
        )

    def _rerank(
        self,
        query: str,
        hits: list[RetrievalHit],
        top_k: int,
    ) -> list[RetrievalHit]:
        reranker = self._ensure_reranker_available()
        if not hits:
            return []
        pairs = [(query, h.payload.get("text", "")) for h in hits]
        scores = reranker.predict(pairs, show_progress_bar=False)
        scored = sorted(
            zip(hits, scores, strict=True),
            key=lambda hs: float(hs[1]),
            reverse=True,
        )
        out: list[RetrievalHit] = []
        for new_rank, (h, s) in enumerate(scored[:top_k], start=1):
            out.append(
                RetrievalHit(
                    chunk_id=h.chunk_id,
                    score=float(s),
                    payload=h.payload,
                    rank=new_rank,
                )
            )
        return out
