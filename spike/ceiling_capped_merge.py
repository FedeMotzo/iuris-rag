"""Merge capped-score (free, locale): riusa cassette declarative, ri-esegue
retrieve+rerank per ricostruire gli intermedi, applica il merge.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUBQ_FILE = ROOT / "spike/data/declarative_subqueries.json"
OUT = ROOT / "spike/data/ceiling_capped_results.json"

SIGLA_PATTERNS = [
    ("gdpr",          re.compile(r"\bGDPR\b", re.IGNORECASE)),
    ("ai_act",        re.compile(r"\bAI\s*Act\b", re.IGNORECASE)),
    ("l_132_2025",    re.compile(r"\bL\.?\s*132/2025\b", re.IGNORECASE)),
    ("dlgs_231",      re.compile(r"\bD\.?\s*Lgs\.?\s*231/2001\b", re.IGNORECASE)),
    ("nis2",          re.compile(r"\bNIS2\b|\bD\.?\s*Lgs\.?\s*138/2024\b", re.IGNORECASE)),
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


def _norm_of_subquery(text):
    earliest = None
    for nid, pat in SIGLA_PATTERNS:
        m = pat.search(text)
        if m and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), nid)
    return earliest[1] if earliest else None


def filter_subqueries(raw):
    out = {}
    for qid, qd in raw.items():
        out[qid] = {"question": qd["question"], "subqueries_by_norm": {}}
        for src_norm, sqs in qd["subqueries_by_norm"].items():
            out[qid]["subqueries_by_norm"][src_norm] = [
                sq for sq in sqs if _norm_of_subquery(sq) == src_norm
            ]
    return out


def capped_merge(per_source_dedup, source_caps, top_k=5):
    """
    per_source_dedup: dict source_label -> sorted list[(chunk_id, max_score)]
    source_caps: dict source_label -> int cap
    Returns: list of (chunk_id, score, source_label) in top_k order.
    Same chunk_id can appear in multiple sources; we keep the entry with
    highest score (and that source's cap is the one that counts).
    """
    # Flatten: for each (chunk_id, source), one entry with that source's max
    # Dedup at chunk_id level: keep BEST (score, source).
    best_by_cid = {}
    for src, ranking in per_source_dedup.items():
        for cid, score in ranking:
            if cid not in best_by_cid or score > best_by_cid[cid][0]:
                best_by_cid[cid] = (score, src)
    pool = [(cid, score, src) for cid, (score, src) in best_by_cid.items()]
    pool.sort(key=lambda x: (-x[1], x[0]))

    selected = []
    src_count = defaultdict(int)
    for cid, score, src in pool:
        if len(selected) >= top_k:
            break
        if src_count[src] >= source_caps[src]:
            continue
        selected.append((cid, score, src))
        src_count[src] += 1
    return selected


def main():
    import logging; logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    raw = json.loads(SUBQ_FILE.read_text())
    filt = filter_subqueries(raw)

    print("Loading models (locale, free)...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    cli = QdrantClient(host="localhost", port=6333, timeout=60)
    hybrid = HybridRetriever(cli, enc, bm, "italian_legal_v1_hybrid", reranker=rr)

    TOP_K_PER_RANK = 5

    intermediates = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = filt[qid]
        question = qd["question"]
        print(f"\n[{qid}] retrieve+rerank per ogni (source, sub-query) + global...")

        # raccolgo: per ogni source label (filtered:<norm> or global) →
        # dict[chunk_id → max score within source]
        per_source_max = defaultdict(dict)  # src_label -> {chunk_id: max_score}
        per_source_per_subq = defaultdict(list)  # src_label -> [(sq_idx, sq, ranking)]

        for src_norm, sqs in qd["subqueries_by_norm"].items():
            doc_urn = NORM_TO_DOC_URN[src_norm]
            src_label = f"filtered:{src_norm}"
            for sq_idx, sq in enumerate(sqs):
                hits = hybrid.retrieve(query=sq, top_k=TOP_K_PER_RANK,
                                       mode="hybrid", rerank_top_k=20,
                                       filter_doc_urn=doc_urn)
                ranking = [(h.chunk_id, h.rank, float(h.score)) for h in hits]
                per_source_per_subq[src_label].append((sq_idx, sq, ranking))
                for cid, _r, sc in ranking:
                    if cid not in per_source_max[src_label] or sc > per_source_max[src_label][cid]:
                        per_source_max[src_label][cid] = sc

        # global
        ghits = hybrid.retrieve(query=question, top_k=TOP_K_PER_RANK,
                                mode="hybrid", rerank_top_k=20, filter_doc_urn=None)
        g_ranking = [(h.chunk_id, h.rank, float(h.score)) for h in ghits]
        per_source_per_subq["global"].append((0, question, g_ranking))
        for cid, _r, sc in g_ranking:
            if cid not in per_source_max["global"] or sc > per_source_max["global"][cid]:
                per_source_max["global"][cid] = sc

        intermediates[qid] = {
            "per_source_max": dict(per_source_max),
            "per_source_per_subq": dict(per_source_per_subq),
            "question": question,
        }

    # Capped merge for cap and cap+1
    def compute(cap_adj=0):
        results = {}
        for qid in ["Q68", "Q69", "Q70", "Q71"]:
            inter = intermediates[qid]
            psm = inter["per_source_max"]
            active = {k: v for k, v in psm.items() if v}
            N = len(active)
            cap = math.ceil(5 / N) + cap_adj
            per_src_sorted = {src: sorted(d.items(), key=lambda x: -x[1])
                              for src, d in active.items()}
            source_caps = {src: cap for src in active}
            top5 = capped_merge(per_src_sorted, source_caps, top_k=5)
            results[qid] = {"N": N, "cap": cap, "top5": top5,
                            "per_src_sorted": per_src_sorted}
        return results

    res_cap = compute(0)
    res_cap1 = compute(+1)

    # === TABELLA A ===
    print("\n" + "=" * 80)
    print("TABELLA A — recall@5 con merge capped-score (cap = ceil(5/N))")
    print("=" * 80)
    base_v11 = {"Q68": 0.40, "Q69": 0.40, "Q70": 0.20, "Q71": 0.40}
    base_rrf_new = {"Q68": 0.20, "Q69": 0.00, "Q70": 0.00, "Q71": 0.00}
    print(f'{"qid":<5}{"N":>3}{"cap":>5}{"r@5 cap":>11}{"v1.1":>8}{"RRF-nuovo":>11}')
    cap_recalls = []
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        top5_ids = {c for c, _, _ in res_cap[qid]["top5"]}
        n = len(GOLDS[qid])
        hits = sum(1 for g, _, _ in GOLDS[qid] if g in top5_ids)
        r = hits / n
        cap_recalls.append(r)
        print(f'{qid:<5}{res_cap[qid]["N"]:>3}{res_cap[qid]["cap"]:>5}'
              f'{r:>11.3f}{base_v11[qid]:>8.2f}{base_rrf_new[qid]:>11.2f}')
    print(f'{"MEDIAN":<5}{"":>3}{"":>5}{statistics.median(cap_recalls):>11.3f}'
          f'{statistics.median(base_v11.values()):>8.2f}'
          f'{statistics.median(base_rrf_new.values()):>11.2f}')

    # === TABELLA B ===
    print("\n" + "=" * 80)
    print("TABELLA B — top-5 per query (chunk_id, score, source, GOLD?)")
    print("=" * 80)
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        r = res_cap[qid]
        print(f"\n{qid}  (N={r['N']}, cap={r['cap']})  top-5:")
        gold_ids = {g for g, _, _ in GOLDS[qid]}
        for i, (cid, sc, src) in enumerate(r["top5"], 1):
            short = cid.split("__", 2)[-1]
            mark = " ★ GOLD" if cid in gold_ids else ""
            print(f"  {i}. {short:<22} score={sc:.4f}  {src}{mark}")

    # === TABELLA C ===
    print("\n" + "=" * 80)
    print("TABELLA C — tag motivo per gold NON in top-5 (cap)")
    print("=" * 80)
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        r = res_cap[qid]
        cap = r["cap"]
        top5_ids = {c for c, _, _ in r["top5"]}
        per_src_sorted = r["per_src_sorted"]
        for gold_id, label, gold_norm in GOLDS[qid]:
            if gold_id in top5_ids:
                continue
            src_label = f"filtered:{gold_norm}"
            if src_label not in per_src_sorted:
                tag = "non recuperato (source non attiva)"
                print(f"  {qid} {label:<22} → {tag}")
                continue
            ranking = per_src_sorted[src_label]
            # find gold's rank within source
            within_rank = None
            for i, (cid, sc) in enumerate(ranking, 1):
                if cid == gold_id:
                    within_rank = i
                    gold_score = sc
                    break
            if within_rank is None:
                # check anche global
                if "global" in per_src_sorted:
                    for i, (cid, sc) in enumerate(per_src_sorted["global"], 1):
                        if cid == gold_id:
                            within_rank = i
                            gold_score = sc
                            src_label = "global"
                            break
            if within_rank is None:
                tag = "non recuperato"
                print(f"  {qid} {label:<22} → {tag}")
                continue
            if within_rank > cap:
                # what scored higher within source: top-cap entries
                higher = ranking[:cap]
                higher_str = ", ".join(f"{c.split('__',2)[-1]}@{s:.3f}" for c, s in higher)
                tag = f"rank within-source troppo basso (r{within_rank}); davanti: {higher_str}"
                print(f"  {qid} {label:<22} → {tag}")
            else:
                # within_rank ≤ cap: gold COULD have entered its source slot.
                # Capped-out if other sources took the 5 slots before gold reached.
                # Or sorted by score: gold ranked too low globally.
                # Tag: capped out (other chunks selected) + show top-5 chunks of
                # gold's source that DID make it (if any).
                in_top5_same_src = [c for c, _, s in r["top5"] if s == src_label]
                if in_top5_same_src:
                    # source has chunks in top-5, but gold isn't among them → impossible
                    # se cap permette gold (within_rank<=cap), gold doveva entrare se source
                    # aveva slot. Quindi cap già pieno con score più alti.
                    higher_same_src = [(c, s) for c, s in ranking[:cap]]
                    higher_str = ", ".join(f"{c.split('__',2)[-1]}@{s:.3f}" for c, s in higher_same_src)
                    tag = (f"capped out (source piena, davanti within-source: {higher_str}; "
                           f"gold score={gold_score:.3f})")
                else:
                    # source has 0 chunks in top-5: greedy didn't reach gold globally
                    # find the chunk at top-5 cutoff in global pool
                    all_pool = []
                    for s, rk in per_src_sorted.items():
                        for c, sc in rk:
                            all_pool.append((c, sc, s))
                    all_pool.sort(key=lambda x: (-x[1], x[0]))
                    cutoff = all_pool[4][1] if len(all_pool) >= 5 else None
                    tag = (f"scavalcato globalmente (gold score={gold_score:.3f} < "
                           f"cutoff top-5={cutoff:.3f}); within-source r{within_rank}/cap{cap}")
                print(f"  {qid} {label:<22} → {tag}")

    # === SENSIBILITÀ: cap+1 ===
    print("\n" + "=" * 80)
    print("D — Sensibilità: stesso run con cap+1")
    print("=" * 80)
    print(f'{"qid":<5}{"N":>3}{"cap+1":>7}{"r@5":>10}{"baseline cap":>15}')
    sens = []
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        top5_ids = {c for c, _, _ in res_cap1[qid]["top5"]}
        n = len(GOLDS[qid])
        hits = sum(1 for g, _, _ in GOLDS[qid] if g in top5_ids)
        r = hits / n
        sens.append(r)
        base = sum(1 for g, _, _ in GOLDS[qid] if g in {c for c, _, _ in res_cap[qid]["top5"]}) / n
        print(f'{qid:<5}{res_cap1[qid]["N"]:>3}{res_cap1[qid]["cap"]:>7}{r:>10.3f}{base:>15.2f}')
    print(f'{"MEDIAN":<5}{"":>3}{"":>7}{statistics.median(sens):>10.3f}'
          f'{statistics.median(cap_recalls):>15.2f}')

    print("\n" + "=" * 80)
    print("D — top-5 cap+1 per query")
    print("=" * 80)
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        r = res_cap1[qid]
        gold_ids = {g for g, _, _ in GOLDS[qid]}
        print(f"\n{qid}  (N={r['N']}, cap={r['cap']})  top-5:")
        for i, (cid, sc, src) in enumerate(r["top5"], 1):
            short = cid.split("__", 2)[-1]
            mark = " ★ GOLD" if cid in gold_ids else ""
            print(f"  {i}. {short:<22} score={sc:.4f}  {src}{mark}")

    # save
    OUT.write_text(json.dumps({
        "cap": {qid: {"top5": res_cap[qid]["top5"],
                      "N": res_cap[qid]["N"], "cap": res_cap[qid]["cap"]}
                for qid in ["Q68","Q69","Q70","Q71"]},
        "cap_plus_1": {qid: {"top5": res_cap1[qid]["top5"],
                             "N": res_cap1[qid]["N"], "cap": res_cap1[qid]["cap"]}
                       for qid in ["Q68","Q69","Q70","Q71"]},
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved → {OUT}")


if __name__ == "__main__":
    main()
