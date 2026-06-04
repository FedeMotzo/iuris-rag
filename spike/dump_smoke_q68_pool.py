"""Dump del pool fuso completo per Q68 con il pipeline v1.2 (cassette + reale).

Riproduce lo smoke test, ma esporta in JSON tutti i candidati del pool
fuso (deduplicato per chunk_id, attribuzione max-score) prima del cutoff
top-20, con tutte le sub-query che hanno prodotto ogni chunk e i loro
score logit pre-max.

Costo zero. Output: spike/data/smoke_q68_fused_pool.json
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASSETTE = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"
OUT = ROOT / "spike/data/smoke_q68_fused_pool.json"

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?"
)
GOLD_Q68 = {
    "eli/reg/2024/1689/oj__art_6",
    "eli/reg/2024/1689/oj__art_27",
    "eli/reg/2016/679/oj__art_9",
    "eli/reg/2016/679/oj__art_35",
    "akn/it/act/legge/stato/2025-09-23/132__art_7",
}


@dataclass
class _R:
    text: str


class CassetteLLM:
    def __init__(self, c, qid):
        self.c = c
        self.qid = qid

    def generate(self, prompt, system=None, max_tokens=200, temperature=0.0):
        S2I = {"GDPR": "gdpr", "AI Act": "ai_act", "L. 132/2025": "l_132_2025"}
        for ln in prompt.splitlines():
            if ln.startswith("Norma target:"):
                tail = ln[len("Norma target:"):].strip()
                for s, n in S2I.items():
                    if tail.startswith(s):
                        v = self.c[f"{self.qid}:{n}"]
                        return _R(json.dumps(v, ensure_ascii=False)
                                  if isinstance(v, list) else v)
        raise ValueError("norma?")


def main() -> int:
    import logging
    logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.cross_norm import CrossNormRetriever
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    print("Loading models...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    cli = QdrantClient(host="localhost", port=6333)
    hybrid = HybridRetriever(cli, enc, bm, "italian_legal_v1_hybrid", reranker=rr)

    cass = json.loads(CASSETTE.read_text())
    llm = CassetteLLM(cass, "q68")
    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid, llm_client=llm,
        top_k_per_norm=20, top_k_global=20, top_k_final=20,
        rerank_top_k_per_norm=20, rerank_top_k_global=20, debug=False,
    )
    print("Running retrieve(Q68)...")
    cnr.retrieve(Q68, top_k=20)
    tr = cnr.last_trace

    # candidate aggregation: chunk_id -> list[(source_label, sub_query, logit)]
    candidates: dict[str, list[tuple[str, str, float]]] = {}
    for (nid, sq_idx), hits in tr["per_subquery_hits"].items():
        sub_q_text = tr["sub_queries"][nid][sq_idx]
        src = f"filtered:{nid}"
        for _rank, cid, logit in hits:
            candidates.setdefault(cid, []).append((src, sub_q_text, float(logit)))
    for _rank, cid, logit in tr["global"]:
        candidates.setdefault(cid, []).append(("global", Q68, float(logit)))

    pool = []
    for cid, attribs in candidates.items():
        max_logit = max(a[2] for a in attribs)
        sigmoid = 1.0 / (1.0 + math.exp(-max_logit))
        doc_urn = cid.split("__", 1)[0]
        # source primaria = quella con il logit massimo (decide il max)
        primary = max(attribs, key=lambda a: a[2])
        pool.append({
            "chunk_id": cid,
            "score_sigmoid": round(sigmoid, 6),
            "max_logit": round(max_logit, 6),
            "primary_source": primary[0],
            "primary_sub_query": primary[1],
            "all_attributions": [
                {"source": a[0], "sub_query": a[1], "logit": round(a[2], 6)}
                for a in attribs
            ],
            "n_attributions": len(attribs),
            "is_gold": cid in GOLD_Q68,
            "doc_urn": doc_urn,
        })
    pool.sort(key=lambda x: -x["score_sigmoid"])
    # rank per chunk
    for i, c in enumerate(pool, 1):
        c["fused_rank"] = i

    # stats per source
    by_source: dict[str, list[float]] = {}
    for c in pool:
        by_source.setdefault(c["primary_source"], []).append(c["score_sigmoid"])
    sub_query_counts = {f"filtered:{nid}": len(sqs)
                        for nid, sqs in tr["sub_queries"].items()}
    sub_query_counts["global"] = 1
    stats: dict[str, dict] = {}
    for src, scores in by_source.items():
        scores_sorted = sorted(scores)
        n = len(scores_sorted)
        median = statistics.median(scores_sorted)
        q1 = scores_sorted[n // 4] if n >= 4 else scores_sorted[0]
        q3 = scores_sorted[(3 * n) // 4] if n >= 4 else scores_sorted[-1]
        stats[src] = {
            "count_candidati": n,
            "score_sigmoid_min": round(min(scores_sorted), 6),
            "score_sigmoid_median": round(median, 6),
            "score_sigmoid_q1": round(q1, 6),
            "score_sigmoid_q3": round(q3, 6),
            "score_sigmoid_iqr": round(q3 - q1, 6),
            "score_sigmoid_max": round(max(scores_sorted), 6),
            "num_sub_query_mono_concetto": sub_query_counts.get(src, 0),
        }

    out = {
        "_meta": {
            "qid": "Q68",
            "query": Q68,
            "norms_detected": tr["norms_detected"],
            "pipeline": "v1.2 mono-concept + score-aware fusion (sigmoid max)",
            "total_unique_candidates": len(pool),
            "top_k_final": 20,
        },
        "fused_pool": pool,
        "stats_per_source": stats,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(pool)} candidates → {OUT}")
    print("\nStats per source:")
    for src, s in stats.items():
        print(f"  {src:<22} n={s['count_candidati']:>3}  median={s['score_sigmoid_median']:.4f}  "
              f"iqr={s['score_sigmoid_iqr']:.4f}  max={s['score_sigmoid_max']:.4f}  "
              f"n_sub_q={s['num_sub_query_mono_concetto']}")
    print(f"\nGold positions (Q68):")
    for c in pool:
        if c["is_gold"]:
            print(f"  rank {c['fused_rank']:>3}  {c['chunk_id'].split('__',2)[-1]:<14} "
                  f"sig={c['score_sigmoid']:.4f}  logit={c['max_logit']:.4f}  "
                  f"src={c['primary_source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
