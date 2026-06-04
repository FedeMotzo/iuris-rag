"""Check di copertura retrieval per fissare top_k_per_subquery (v1.2 step 2).

NESSUNA chiamata LLM: usa le sub-query già in cache (validate run-4). Per ogni
gold a livello articolo/allegato delle 12 query cross-norma calcola il MIGLIOR
rank con cui compare nel ranking rerankato di UNA sub-query della sua norma
(gold-in-gruppo-source). Poi riporta a quale top_k per-sub-query la copertura
chiude.

    RUN_RERANKER (implicito): carica bge-reranker-v2-m3 (~2.3GB).
    spike/.venv/bin/python spike/coverage_probe_v1_2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spike.validate_decomposer_v1_2 import parse_gold_chunk  # noqa: E402

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
CACHE = ROOT / "spike/validate_decomposer_v1_2_cache.json"
K_MAX = 15
SWEEP = [1, 2, 3, 4, 5, 8, 10, 15]


def _build_retriever():
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME
    from fastembed import SparseTextEmbedding

    client = QdrantClient(host="localhost", port=6333, timeout=5)
    encoder = BgeM3Encoder.get()
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=HYBRID_COLLECTION_NAME, reranker=reranker,
    )


def main() -> int:
    from core.cross_norm.multi_norm_trigger import detect_norms

    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8"))

    # norm_id -> doc_urn
    import yaml
    g = yaml.safe_load((ROOT / "core/cross_norm/norm_glossary.yaml").read_text())
    norm_to_urn = {nid: e["doc_urn"] for nid, e in g.items()}

    cross = [(it["qid"], detect_norms(it["question"]), it) for it in gold
             if len(detect_norms(it["question"])) >= 2]

    retr = _build_retriever()

    # Per ogni gold: best_rank nel miglior gruppo-source. None = mai recuperato.
    rows: list[tuple[str, str, str, int | None]] = []  # (qid, norm, gold_label, best_rank)

    for qid, norms, it in cross:
        # ranking per (norm, sq_idx): chunk_id -> rank(1-based)
        per_norm_rankings: dict[str, list[dict[str, int]]] = {}
        for nid in norms:
            urn = norm_to_urn[nid]
            sub_qs = cache.get(f"{qid}:{nid}", [])
            rankings = []
            for sq in sub_qs:
                hits = retr.retrieve(
                    query=sq, top_k=K_MAX, mode="hybrid",
                    rerank_top_k=K_MAX, filter_doc_urn=urn,
                )
                rankings.append({h.chunk_id: h.rank for h in hits})
            per_norm_rankings[nid] = rankings

        # gold a livello articolo + allegato
        seen = set()
        for c in it["gold_chunks"]:
            nid, kind, ref = parse_gold_chunk(c["chunk_id"])
            if kind not in ("article", "annex_point"):
                continue
            if nid not in norms:
                continue
            cid = c["chunk_id"]
            if cid in seen:
                continue
            seen.add(cid)
            best = None
            for ranking in per_norm_rankings.get(nid, []):
                r = ranking.get(cid)
                if r is not None and (best is None or r < best):
                    best = r
            label = cid.split("__", 1)[1]
            rows.append((qid, nid, label, best))

    # ---- report per-gold ----
    print("=" * 78)
    print("GOLD-IN-GRUPPO-SOURCE: miglior rank nel ranking rerankato della norma")
    print("qid     | norm        | gold              | best_rank")
    print("-" * 78)
    for qid, nid, label, best in rows:
        print(f"{qid:7} | {nid:11} | {label:17} | {best if best is not None else 'MISS (>%d)' % K_MAX}")

    # ---- sweep copertura ----
    total = len(rows)
    print("\n" + "=" * 78)
    print(f"COPERTURA per top_k_per_subquery (su {total} gold articolo+allegato)")
    print("top_k | coperti | %")
    print("-" * 78)
    for k in SWEEP:
        cov = sum(1 for *_, b in rows if b is not None and b <= k)
        print(f"{k:5} | {cov:7} | {100*cov/total:.0f}%")
    miss = [(q, n, l) for q, n, l, b in rows if b is None]
    print(f"\nMAI recuperati (>{K_MAX}): {miss if miss else 'nessuno'}")
    # k minimo che chiude (escludendo i MISS strutturali)
    closable = [b for *_, b in rows if b is not None]
    if closable:
        print(f"top_k che copre tutti i recuperabili: {max(closable)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
