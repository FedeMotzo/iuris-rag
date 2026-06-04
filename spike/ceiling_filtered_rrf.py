"""STEP 1+2 free: filtro cross-norm + pipeline v1.1 RRF + recall@5 + diagnostica.

Riusa spike/data/declarative_subqueries.json (STEP 0). Nessuna chiamata LLM.

    spike/.venv/bin/python spike/ceiling_filtered_rrf.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUBQ_FILE = ROOT / "spike/data/declarative_subqueries.json"
OUT = ROOT / "spike/data/ceiling_filtered_rrf_results.json"

# Sigle → norm_id (ordine = priorità di match: pattern più specifici prima)
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
    "codice_privacy": "akn/it/act/decreto_legislativo/stato/2003-06-30/196",
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


def _norm_of_subquery(text: str) -> str | None:
    """Identifica la prima sigla che appare nel testo (priorità in SIGLA_PATTERNS)."""
    # Per ogni sigla cerca la prima posizione di match e tieni la più precoce.
    earliest = None  # (pos, norm_id)
    for nid, pat in SIGLA_PATTERNS:
        m = pat.search(text)
        if m and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), nid)
    return earliest[1] if earliest else None


def filter_subqueries(raw: dict) -> tuple[dict, list[dict]]:
    """Tiene solo sub-query la cui sigla detected coincide con la source norm."""
    filtered: dict[str, dict] = {}
    drops: list[dict] = []
    for qid, qd in raw.items():
        filtered[qid] = {"question": qd["question"], "subqueries_by_norm": {}}
        for source_norm, sqs in qd["subqueries_by_norm"].items():
            kept = []
            for i, sq in enumerate(sqs):
                detected = _norm_of_subquery(sq)
                if detected == source_norm:
                    kept.append(sq)
                else:
                    drops.append({"qid": qid, "source": source_norm,
                                  "idx": i, "detected_norm": detected, "sub_query": sq})
            filtered[qid]["subqueries_by_norm"][source_norm] = kept
    return filtered, drops


def main() -> int:
    import logging; logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    raw = json.loads(SUBQ_FILE.read_text())
    filt, drops = filter_subqueries(raw)

    print("=" * 80)
    print("FILTRO CROSS-NORM")
    print("=" * 80)
    print(f'{"qid":<5}{"source":<14}{"before":>9}{"after":>9}{"dropped":>9}')
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        for src, sqs in raw[qid]["subqueries_by_norm"].items():
            after = len(filt[qid]["subqueries_by_norm"][src])
            print(f'{qid:<5}{src:<14}{len(sqs):>9}{after:>9}{len(sqs)-after:>9}')
    print(f"\nTotale sub-query droppate (cross-norm): {len(drops)}")

    print("\n" + "=" * 80)
    print("Loading models...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    cli = QdrantClient(host="localhost", port=6333, timeout=60)
    hybrid = HybridRetriever(cli, enc, bm, "italian_legal_v1_hybrid", reranker=rr)

    RRF_K = 60
    TOP_K_PER_RANK = 5
    TOP_K_FINAL = 5

    results = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = filt[qid]
        question = qd["question"]
        print(f"\n[{qid}] running...")

        # per_source_rankings: source_norm → [(sq_idx, sq, ranking)]
        per_source: dict[str, list[tuple[int, str, list]]] = defaultdict(list)
        rankings_all: list[tuple[str, str, list]] = []  # (label, sq_text, [(cid,rank,score)...])

        for src_norm, sqs in qd["subqueries_by_norm"].items():
            doc_urn = NORM_TO_DOC_URN[src_norm]
            for sq_idx, sq in enumerate(sqs):
                hits = hybrid.retrieve(query=sq, top_k=TOP_K_PER_RANK,
                                       mode="hybrid", rerank_top_k=20,
                                       filter_doc_urn=doc_urn)
                ranking = [(h.chunk_id, h.rank, float(h.score)) for h in hits]
                per_source[src_norm].append((sq_idx, sq, ranking))
                rankings_all.append((f"filtered:{src_norm}#{sq_idx}", sq, ranking))

        # global
        ghits = hybrid.retrieve(query=question, top_k=TOP_K_PER_RANK,
                                mode="hybrid", rerank_top_k=20, filter_doc_urn=None)
        g_ranking = [(h.chunk_id, h.rank, float(h.score)) for h in ghits]
        rankings_all.append(("global", question, g_ranking))

        # RRF
        rrf = defaultdict(float)
        contribs = defaultdict(list)  # cid -> [(label,rank,score)]
        for label, sq, ranking in rankings_all:
            for cid, rank, score in ranking:
                rrf[cid] += 1.0 / (RRF_K + rank)
                contribs[cid].append((label, rank, score))
        fused = sorted(rrf.items(), key=lambda kv: (-kv[1], kv[0]))
        top5 = fused[:TOP_K_FINAL]
        full_ranked_ids = [c for c, _ in fused]

        # diagnostica per gold
        diag = []
        for gold_id, gold_label, gold_norm in GOLDS[qid]:
            # best within-source: cerca tra le sub-query della source norm di questo gold
            best_within = None  # (rank, score, sq_idx, sq_text)
            for sq_idx, sq, ranking in per_source.get(gold_norm, []):
                for cid, rank, score in ranking:
                    if cid == gold_id:
                        if best_within is None or rank < best_within[0]:
                            best_within = (rank, score, sq_idx, sq)
            fusion_rank = full_ranked_ids.index(gold_id) + 1 if gold_id in full_ranked_ids else None
            in_top5 = fusion_rank is not None and fusion_rank <= 5
            diag.append({
                "gold_id": gold_id, "label": gold_label, "norm": gold_norm,
                "best_within_source": best_within,
                "fusion_rank": fusion_rank, "in_top5": in_top5,
            })

        results[qid] = {
            "n_rankings": len(rankings_all),
            "n_subq_per_source": {k: len(v) for k, v in per_source.items()},
            "top5": [{"chunk_id": c, "rrf": s,
                      "sources": [(lb, r, sc) for lb, r, sc in contribs[c]]}
                     for c, s in top5],
            "gold_diag": diag,
        }

        # print top-5
        print(f"  top-5:")
        for i, (c, s) in enumerate(top5, 1):
            short = c.split("__", 2)[-1]
            srcs = ",".join(lb.split(":")[1] if ":" in lb else lb
                            for lb, _r, _sc in contribs[c])
            ann = " ★ GOLD" if any(g == c for g, _, _ in GOLDS[qid]) else \
                  " (recital)" if "recital" in c else " (articolo)"
            print(f"    {i}. {short:<22} rrf={s:.4f}  src=[{srcs}]{ann}")

    # === TABELLE OUTPUT ===
    print("\n" + "=" * 80)
    print("TABELLA A — recall@5")
    print("=" * 80)
    base_v11 = {"Q68": 0.40, "Q69": 0.40, "Q70": 0.20, "Q71": 0.40}
    base_5e = {"Q68": 0.20, "Q69": 0.20, "Q70": 0.20, "Q71": 0.00}
    print(f'{"qid":<5}{"r@5 nuovo":>11}{"v1.1":>8}{"5e":>6}')
    recalls = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        golds = GOLDS[qid]
        hits = sum(1 for d in results[qid]["gold_diag"] if d["in_top5"])
        recall = hits / len(golds)
        recalls[qid] = recall
        print(f'{qid:<5}{recall:>11.3f}{base_v11[qid]:>8.2f}{base_5e[qid]:>6.2f}')
    print(f'{"MEDIAN":<5}{statistics.median(recalls.values()):>11.3f}'
          f'{statistics.median(base_v11.values()):>8.2f}'
          f'{statistics.median(base_5e.values()):>6.2f}')

    print("\n" + "=" * 80)
    print("TABELLA B — diagnostica per gold")
    print("=" * 80)
    print(f'{"qid":<5}{"gold":<22}{"rec?":>6}{"best within-src":>16}{"score":>9}{"fusion rank":>14}{"top5?":>7}')
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        for d in results[qid]["gold_diag"]:
            bw = d["best_within_source"]
            if bw is None:
                bw_str = "-"; sc_str = "-"
            else:
                bw_str = f"r{bw[0]}/sq#{bw[2]}"
                sc_str = f"{bw[1]:.3f}"
            fr = d["fusion_rank"]
            fr_str = str(fr) if fr is not None else ">pool"
            rec = "YES" if bw is not None else "no"
            t5 = "YES" if d["in_top5"] else "no"
            print(f'{qid:<5}{d["label"]:<22}{rec:>6}{bw_str:>16}{sc_str:>9}{fr_str:>14}{t5:>7}')

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str),
                   encoding="utf-8")
    print(f"\nSaved → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
