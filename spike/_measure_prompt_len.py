"""One-shot: per Q6/Q7/Q1 calcola lunghezza prompt RAG (char + token approx).

Riusa retriever + reranker reali e fa misure deterministiche. Lo scopo è
chiarire se Q1 ha un prompt anomalo che spiega il TTFT 21s.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spike"))

from smoke_mps_coabitation import (  # type: ignore
    BM25_MODEL, COLLECTION, RAG_TOP_K, RERANK_TOP_K, RERANKER_MODEL,
    build_rag_prompt,
)


def main() -> int:
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    queries = []
    data = json.loads((ROOT / "data/benchmark/gold_validated_v2.json").read_text())
    by_qid = {q["qid"]: q for q in data["queries"]}
    for qid in ["Q6", "Q7", "Q1"]:
        queries.append({"qid": qid, "query": by_qid[qid]["query"]})

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL)
    client = QdrantClient(host="localhost", port=6333)
    reranker = CrossEncoder(RERANKER_MODEL, device="cpu", max_length=512)
    retriever = HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=COLLECTION, reranker=reranker,
    )

    print(f"{'qid':4} {'n_chunks':>8} {'prompt_char':>11} {'prompt_word':>11} {'~tokens':>8}")
    print("-" * 50)
    for q in queries:
        # stesso pattern del run_one_query
        raw = list(retriever.retrieve(
            query=q["query"], top_k=RERANK_TOP_K, mode="hybrid", rerank_top_k=None,
        ))
        reranked = retriever._rerank(q["query"], raw, top_k=RAG_TOP_K)
        prompt = build_rag_prompt(q["query"], reranked)
        n_char = len(prompt)
        n_word = len(prompt.split())
        # stima token: legalese italiano ≈ 1.4 token / parola con tokenizer SentencePiece BPE
        n_tok = int(n_word * 1.4)
        print(f"{q['qid']:4} {len(reranked):8d} {n_char:11d} {n_word:11d} {n_tok:8d}")
        # dump per debug
        (ROOT / f"spike/_prompt_{q['qid']}.txt").write_text(prompt, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
