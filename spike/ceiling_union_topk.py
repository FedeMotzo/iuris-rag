"""union_top1 / union_top3 dei ranking per-(source, sub-query) declarative
filtrate cross-norm. Locale, free, no LLM.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUBQ_FILE = ROOT / "spike/data/declarative_subqueries.json"
OUT = ROOT / "spike/data/ceiling_union_results.json"

SIGLA_PATTERNS = [
    ("gdpr", re.compile(r"\bGDPR\b", re.IGNORECASE)),
    ("ai_act", re.compile(r"\bAI\s*Act\b", re.IGNORECASE)),
    ("l_132_2025", re.compile(r"\bL\.?\s*132/2025\b", re.IGNORECASE)),
    ("dlgs_231", re.compile(r"\bD\.?\s*Lgs\.?\s*231/2001\b", re.IGNORECASE)),
    ("nis2", re.compile(r"\bNIS2\b|\bD\.?\s*Lgs\.?\s*138/2024\b", re.IGNORECASE)),
    ("codice_privacy", re.compile(r"\bD\.?\s*Lgs\.?\s*196/2003\b|\bCodice\s+Privacy\b", re.IGNORECASE)),
]
NORM_TO_DOC_URN = {
    "gdpr": "eli/reg/2016/679/oj",
    "ai_act": "eli/reg/2024/1689/oj",
    "dlgs_231": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
    "nis2": "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    "l_132_2025": "akn/it/act/legge/stato/2025-09-23/132",
}
GOLDS = {
    "Q68": [
        ("eli/reg/2024/1689/oj__art_6", "AI Act art_6", "ai_act"),
        ("eli/reg/2016/679/oj__art_9", "GDPR art_9", "gdpr"),
        ("eli/reg/2024/1689/oj__art_27", "AI Act art_27", "ai_act"),
        ("eli/reg/2016/679/oj__art_35", "GDPR art_35", "gdpr"),
        ("akn/it/act/legge/stato/2025-09-23/132__art_7", "L.132 art_7", "l_132_2025"),
    ],
    "Q69": [("eli/reg/2024/1689/oj__art_6", "AI Act art_6", "ai_act")],
    "Q70": [
        ("eli/reg/2016/679/oj__art_44", "GDPR art_44", "gdpr"),
        ("akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies", "231 art_25-octies", "dlgs_231"),
    ],
    "Q71": [("eli/reg/2024/1689/oj__annex_III__point_5", "AnnexIII point_5", "ai_act")],
}


def _norm_of_subq(text):
    earliest = None
    for nid, pat in SIGLA_PATTERNS:
        m = pat.search(text)
        if m and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), nid)
    return earliest[1] if earliest else None


def main():
    import logging; logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    raw = json.loads(SUBQ_FILE.read_text())

    print("Loading models...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    cli = QdrantClient(host="localhost", port=6333, timeout=60)
    hybrid = HybridRetriever(cli, enc, bm, "italian_legal_v1_hybrid", reranker=rr)

    TOP_K = 5  # per (source, sub-query): top-5 reranked

    results = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        question = raw[qid]["question"]
        print(f"\n[{qid}] retrieve+rerank...")

        # per_subq: list[(src_norm, sq_idx, sq, ranking[(cid,rank,score),...])]
        per_subq = []
        for src_norm, sqs in raw[qid]["subqueries_by_norm"].items():
            # filtro cross-norm
            sqs_kept = [(i, sq) for i, sq in enumerate(sqs) if _norm_of_subq(sq) == src_norm]
            doc_urn = NORM_TO_DOC_URN[src_norm]
            for i, sq in sqs_kept:
                hits = hybrid.retrieve(query=sq, top_k=TOP_K, mode="hybrid",
                                       rerank_top_k=20, filter_doc_urn=doc_urn)
                ranking = [(h.chunk_id, h.rank, float(h.score)) for h in hits]
                per_subq.append((f"filtered:{src_norm}", i, sq, ranking))

        # global
        ghits = hybrid.retrieve(query=question, top_k=TOP_K, mode="hybrid",
                                rerank_top_k=20, filter_doc_urn=None)
        per_subq.append(("global", 0, question,
                         [(h.chunk_id, h.rank, float(h.score)) for h in ghits]))

        # union_top1, union_top3 (dedup per chunk_id; tieni il MAX score)
        union_top1 = {}   # cid -> (best_source, best_score)
        union_top3 = {}
        for src, sq_idx, sq, ranking in per_subq:
            for cid, rank, score in ranking:
                if rank == 1:
                    if cid not in union_top1 or score > union_top1[cid][1]:
                        union_top1[cid] = (src, score)
                if rank <= 3:
                    if cid not in union_top3 or score > union_top3[cid][1]:
                        union_top3[cid] = (src, score)

        gold_ids = {g for g, _, _ in GOLDS[qid]}
        n_top1 = len(union_top1); n_top3 = len(union_top3)
        gold_top1 = sum(1 for g in gold_ids if g in union_top1)
        gold_top3 = sum(1 for g in gold_ids if g in union_top3)
        rec_top1 = gold_top1 / len(gold_ids)
        rec_top3 = gold_top3 / len(gold_ids)

        # Per-gold: best rank within its source's sub-queries
        per_gold = []
        for gold_id, label, gold_norm in GOLDS[qid]:
            best = None  # (rank, score, sq_idx, sq_text)
            for src, sq_idx, sq, ranking in per_subq:
                expected = f"filtered:{gold_norm}"
                if src != expected:
                    continue
                for cid, rank, score in ranking:
                    if cid == gold_id:
                        if best is None or rank < best[0] or (rank == best[0] and score > best[1]):
                            best = (rank, score, sq_idx, sq)
            per_gold.append({"gold_id": gold_id, "label": label, "norm": gold_norm, "best": best})

        results[qid] = {
            "n_subq": len(per_subq),
            "n_top1": n_top1, "n_top3": n_top3,
            "recall_top1": rec_top1, "recall_top3": rec_top3,
            "gold_in_top1": [(g, label) for g, label, _ in GOLDS[qid] if g in union_top1],
            "gold_in_top3": [(g, label) for g, label, _ in GOLDS[qid] if g in union_top3],
            "union_top1": [(cid, src, score) for cid, (src, score) in
                           sorted(union_top1.items(), key=lambda x: -x[1][1])],
            "union_top3": [(cid, src, score) for cid, (src, score) in
                           sorted(union_top3.items(), key=lambda x: -x[1][1])],
            "per_gold": per_gold,
        }

    # === A — cardinalities + recall_gold ===
    print("\n" + "=" * 80)
    print("A — cardinalità union + recall_gold")
    print("=" * 80)
    print(f'{"qid":<5}{"#gold":>6}{"|top1|":>8}{"rec_top1":>11}{"|top3|":>8}{"rec_top3":>11}')
    for q in ["Q68", "Q69", "Q70", "Q71"]:
        r = results[q]; n = len(GOLDS[q])
        print(f'{q:<5}{n:>6}{r["n_top1"]:>8}{r["recall_top1"]:>11.3f}'
              f'{r["n_top3"]:>8}{r["recall_top3"]:>11.3f}')

    # === B — composizione union_top1 per query ===
    print("\n" + "=" * 80)
    print("B — composizione union_top1 per query")
    print("=" * 80)
    for q in ["Q68", "Q69", "Q70", "Q71"]:
        r = results[q]
        gold_ids = {g for g, _, _ in GOLDS[q]}
        n_gold = 0; n_articolo = 0; n_recital = 0
        rows = []
        for cid, src, score in r["union_top1"]:
            is_gold = cid in gold_ids
            is_recital = "recital" in cid or "considerando" in cid
            if is_gold: n_gold += 1
            elif is_recital: n_recital += 1
            else: n_articolo += 1
            rows.append((cid, src, is_gold, is_recital, score))
        print(f'\n{q}  |top1|={r["n_top1"]}  #gold={n_gold}  #articolo_non_gold={n_articolo}  #recital={n_recital}')
        for cid, src, gold, recital, sc in rows:
            mark = " ★ GOLD" if gold else (" (recital)" if recital else " (articolo)")
            short = cid.split("__", 2)[-1]
            print(f'  {short:<24} score={sc:.4f}  {src}{mark}')

    # === C — per ogni gold: best rank dentro la sua sub-query mirata ===
    print("\n" + "=" * 80)
    print("C — per gold: miglior rank dentro la sub-query della sua source")
    print("=" * 80)
    print(f'{"qid":<5}{"gold":<22}{"best rank":>10}{"score":>9}  sub-query (snippet)')
    for q in ["Q68", "Q69", "Q70", "Q71"]:
        for g in results[q]["per_gold"]:
            if g["best"] is None:
                print(f'{q:<5}{g["label"]:<22}{"-":>10}{"-":>9}  (mai in top-5 di alcuna sub-query)')
            else:
                rank, score, sq_idx, sq_text = g["best"]
                print(f'{q:<5}{g["label"]:<22}{rank:>10}{score:>9.4f}  '
                      f'[sq#{sq_idx}] "{sq_text[:80]}"')

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str),
                   encoding="utf-8")
    print(f"\nSaved → {OUT}")


if __name__ == "__main__":
    main()
