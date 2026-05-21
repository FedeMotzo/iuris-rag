"""Smoke RAG end-to-end (W5).

Esegue le stesse 3 query dello smoke MPS (Q6, Q7, Q1), 1 run per query,
stampa timings + annotated_answer + verdetto verifica.

Legge `.env` in repo root per scegliere il provider:
- LLM_PROVIDER=anthropic → reranker su MPS (topologia S1)
- LLM_PROVIDER=ollama   → reranker su CPU (topologia S2)

Default (nessun .env, nessuna env var) = ollama, S2.

    spike/.venv/bin/python spike/smoke_rag_pipeline.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("smoke_rag")

COLLECTION = "italian_legal_v1_hybrid"
BM25_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
TARGET_QIDS = ["Q6", "Q7", "Q1"]
GOLD_PATH = ROOT / "data/benchmark/gold_validated_v2.json"
RESULTS_PATH = ROOT / "spike/SMOKE_RAG_PIPELINE_RESULTS.md"


def load_queries() -> list[dict]:
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    by_qid = {q["qid"]: q for q in data["queries"]}
    return [{"qid": qid, "query": by_qid[qid]["query"]} for qid in TARGET_QIDS]


def build_retriever(reranker_device: str):
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL)
    log.info("Reranker device=%s", reranker_device)
    reranker = CrossEncoder(RERANKER_MODEL, device=reranker_device, max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=COLLECTION, reranker=reranker,
    )


def main() -> int:
    # Carica .env PRIMA di decidere la topologia. load_dotenv usa override=False,
    # quindi env vars già esportate dalla shell vincono sulla .env.
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        log.info("Caricato .env da %s", env_path)

    provider_choice = (os.environ.get("LLM_PROVIDER") or "ollama").strip().lower()
    reranker_device = "mps" if provider_choice == "anthropic" else "cpu"
    log.info("Smoke RAG pipeline — provider=%s (topologia: reranker %s)",
             provider_choice, reranker_device.upper())

    from core.serving import build_default_pipeline

    retriever = build_retriever(reranker_device)
    pipeline = build_default_pipeline(retriever)

    out_lines: list[str] = []
    out_lines.append("# Smoke RAG pipeline — risultati")
    out_lines.append("")
    out_lines.append(
        f"Provider: **{pipeline._llm.provider_name}** "
        f"({pipeline._llm.model_name}), top_k=5, rerank_top_k=20, "
        f"use_graph={pipeline.use_graph}. 1 run/query (no warmup interno)."
    )
    out_lines.append("")

    for q in load_queries():
        log.info("=== %s: %s", q["qid"], q["query"])
        t0 = time.perf_counter()
        resp = pipeline.query(q["query"])
        wall = (time.perf_counter() - t0) * 1000

        log.info(
            "[%s] retrieval=%.0fms gen=%.0fms verify=%.0fms total=%.0fms "
            "n_cite=%d all_verified=%s",
            q["qid"], resp.timings_ms["retrieval_ms"],
            resp.timings_ms["generate_ms"], resp.timings_ms["verify_ms"],
            resp.timings_ms["total_ms"], resp.verification.n_total,
            resp.verification.all_verified,
        )

        out_lines.append(f"## {q['qid']}")
        out_lines.append("")
        out_lines.append(f"**Query**: {q['query']}")
        out_lines.append("")
        out_lines.append(
            f"**Timings (ms)**: retrieval={resp.timings_ms['retrieval_ms']:.0f}, "
            f"gen={resp.timings_ms['generate_ms']:.0f} "
            f"(TTFT={resp.generation_meta.ttft_ms:.0f}, "
            f"{resp.generation_meta.n_output_tokens} tok @ "
            f"{resp.generation_meta.n_output_tokens / max(resp.generation_meta.total_ms / 1000, 1e-3):.1f} tok/s), "
            f"verify={resp.timings_ms['verify_ms']:.0f}, "
            f"total={resp.timings_ms['total_ms']:.0f} "
            f"(wall {wall:.0f})"
        )
        out_lines.append("")
        out_lines.append(
            f"**Citazioni**: n_total={resp.verification.n_total}, "
            f"n_verified={resp.verification.n_verified}, "
            f"all_verified={resp.verification.all_verified}, "
            f"finish_reason={resp.generation_meta.finish_reason}"
        )
        out_lines.append("")
        out_lines.append("**Chunk recuperati (top-5 post-rerank)**:")
        out_lines.append("")
        for h in resp.retrieval_result:
            hier = " > ".join(h.payload.get("hierarchy_path") or [])
            out_lines.append(f"- `{h.chunk_id}` ({hier})")
        out_lines.append("")
        out_lines.append("**Annotated answer**:")
        out_lines.append("")
        out_lines.append("```")
        out_lines.append(resp.annotated_answer.strip())
        out_lines.append("```")
        out_lines.append("")

    RESULTS_PATH.write_text("\n".join(out_lines), encoding="utf-8")
    log.info("Risultati scritti su %s", RESULTS_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
