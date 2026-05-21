"""Benchmark W3 con query expansion (`core.terminology.expand_query`).

3 setup ricalcolati: dense_w3, hybrid, hybrid_rrk (rerank_top_k=20). NO rrk_50.
Confronto contro `results_w3.json` (W3 senza expansion).

Tre fasi (processi distinti per liberare MPS):

    spike/.venv/bin/python scripts/run_benchmark_w3_with_expansion.py --phase=fetch
    spike/.venv/bin/python scripts/run_benchmark_w3_with_expansion.py --phase=report
    spike/.venv/bin/python scripts/run_benchmark_w3_with_expansion.py --phase=verdict

`fetch` e `report` come prima. `verdict` rilegge `results_w3_expansion.json` e
`results_w3.json` e applica la regola boundary-fragile (vedi REGOLA sotto) senza
ricalcolare retrieval/rerank.

REGOLA BOUNDARY-FRAGILE (introdotta 2026-05-19)

Una query è "boundary-fragile" in un setup se almeno uno dei suoi gold in
baseline ha score identico ad almeno un altro chunk fuori dalla top-K usata
per la metrica. In tal caso il rank del gold è instabile fra run distinti per
tie-breaking interno di Qdrant — il chunk al boundary può oscillare tra
"dentro" e "fuori" top-K (verificato empiricamente su Q5 hybrid: 5 run
producono 3 in-top10 / 2 out-of-top10 senza nessuna modifica).

Le regressioni Δ R@K < 0 su query boundary-fragile NON contano come
regressioni significative ai fini del verdetto PASS/FAIL.

Approssimazione operativa: l'esistenza di chunk a score identico è verificata
nel margine top-(K+10) usando `hybrid_top20_*` salvati in results_w3.json
(disponibili per il solo setup hybrid). Per dense_w3 e hybrid_rrk la regola
non si applica: gli score sono granulari (cosine / cross-encoder logits) e
tie-breaking raro.

Nessun tie-breaking deterministico introdotto in core/hybrid_retriever: è
fuori scope di settimana 4 (vedi TODO post-W3).

Output:
- data/benchmark/results_w3_expansion.json
- Report markdown a stdout durante phase=report e phase=verdict
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import math
import pickle
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("benchmark_w3_expansion")

GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated_v2.json"
RESULTS_BASELINE = ROOT / "data" / "benchmark" / "results_w3.json"
RESULTS_OUT = ROOT / "data" / "benchmark" / "results_w3_expansion.json"
INTERMEDIATE = ROOT / "data" / "benchmark" / "_w3_expansion_phase1.pkl"

TOP_K_FINAL = 10
RERANK_TOP_K = 20
RERANK_MAX_LENGTH = 512
RERANK_BATCH_SIZE = 8
TEXT_CHAR_CAP = 2500


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def recall_at_k(retrieved, gold, k):
    if not gold:
        return None
    return len(set(retrieved[:k]) & gold) / len(gold)


def mrr_at_k(retrieved, gold, k=TOP_K_FINAL):
    if not gold:
        return None
    for i, cid in enumerate(retrieved[:k], start=1):
        if cid in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved, gold, k=TOP_K_FINAL):
    if not gold:
        return None
    dcg = sum(1.0 / math.log2(i + 2)
              for i, cid in enumerate(retrieved[:k]) if cid in gold)
    idcg = sum(1.0 / math.log2(j + 2) for j in range(min(k, len(gold))))
    return dcg / idcg if idcg > 0 else 0.0


def _mean(vals):
    real = [v for v in vals if v is not None]
    return sum(real) / len(real) if real else None


# ---------------------------------------------------------------------------
# Phase 1 — fetch (con query expansion)
# ---------------------------------------------------------------------------

def phase_fetch() -> int:
    import torch
    from fastembed import SparseTextEmbedding

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.terminology import expand_query, load_aliases
    from core.vector_store import HYBRID_COLLECTION_NAME, get_client

    aliases = load_aliases()
    log.info("Phase 1 FETCH — query expansion attiva (%d alias)", len(aliases))

    data = json.loads(GOLD_PATH.read_text())
    queries = data["queries"]

    client = get_client()
    info = client.get_collection(HYBRID_COLLECTION_NAME)
    log.info("Collection %s: %d points", HYBRID_COLLECTION_NAME, info.points_count)

    encoder = BgeM3Encoder.get()
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    retriever = HybridRetriever(client, encoder, bm25, HYBRID_COLLECTION_NAME)

    results: list[dict] = []
    t_start = time.monotonic()
    for i, q in enumerate(queries, start=1):
        qid = q["qid"]
        original = q["query"]
        expanded = expand_query(original, aliases=aliases)
        was_expanded = expanded != original

        gold_ids = [c["chunk_id"] for c in q["candidates"] if c.get("is_gold")]

        dense_hits = retriever.retrieve(expanded, top_k=TOP_K_FINAL, mode="dense")
        hybrid_hits = retriever.retrieve(expanded, top_k=TOP_K_FINAL, mode="hybrid")
        hybrid20_hits = retriever.retrieve(expanded, top_k=RERANK_TOP_K, mode="hybrid")

        results.append({
            "qid": qid,
            "query_original": original,
            "query_expanded": expanded,
            "was_expanded": was_expanded,
            "use_case": q["use_case"],
            "expected_kind": q["expected_kind"],
            "gold_chunk_ids": gold_ids,
            "dense_top10": [(h.chunk_id, float(h.score)) for h in dense_hits],
            "hybrid_top10": [(h.chunk_id, float(h.score)) for h in hybrid_hits],
            "hybrid_top20": [
                (h.chunk_id, float(h.score),
                 (h.payload.get("text") or "")[:TEXT_CHAR_CAP])
                for h in hybrid20_hits
            ],
        })

        if i % 10 == 0 or i == len(queries):
            log.info("  fetch %d/%d (last qid=%s, expanded=%s)",
                     i, len(queries), qid, was_expanded)

    log.info("Phase 1 done in %.1fs. Saving %s",
             time.monotonic() - t_start, INTERMEDIATE.name)
    INTERMEDIATE.write_bytes(pickle.dumps(results))

    # Cleanup MPS
    if encoder._model is not None:
        encoder._model.cpu()
        del encoder._model
        encoder._model = None
    BgeM3Encoder._singleton = None
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    return 0


# ---------------------------------------------------------------------------
# Phase 2 — rerank + metrics + stdout report
# ---------------------------------------------------------------------------

def phase_rerank_and_report() -> int:
    import torch
    from sentence_transformers import CrossEncoder

    if not INTERMEDIATE.exists():
        raise RuntimeError(
            f"Pickle mancante: {INTERMEDIATE}. Esegui --phase=fetch."
        )
    results = pickle.loads(INTERMEDIATE.read_bytes())
    log.info("Phase 2 — %d query caricate", len(results))

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3",
                            device=device, max_length=RERANK_MAX_LENGTH)
    for _ in range(3):
        reranker.predict([("warmup", "warmup")] * 10,
                         batch_size=RERANK_BATCH_SIZE, show_progress_bar=False)
        if device == "mps":
            torch.mps.synchronize()
    log.info("Warmup reranker completato")

    for i, r in enumerate(results, start=1):
        if not r["hybrid_top20"]:
            r["hybrid_rrk_top10"] = []
            continue
        pairs = [(r["query_expanded"], item[2]) for item in r["hybrid_top20"]]
        scores = reranker.predict(pairs, batch_size=RERANK_BATCH_SIZE,
                                  show_progress_bar=False)
        if device == "mps":
            torch.mps.synchronize()
        scored = sorted(zip(r["hybrid_top20"], scores, strict=True),
                        key=lambda hs: float(hs[1]), reverse=True)
        r["hybrid_rrk_top10"] = [(item[0], float(s))
                                  for item, s in scored[:TOP_K_FINAL]]
        if i % 10 == 0 or i == len(results):
            log.info("  rerank %d/%d (last qid=%s)", i, len(results), r["qid"])

    # Strip texts dai top-20 prima del serialize
    for r in results:
        r["hybrid_top20_ids"] = [it[0] for it in r["hybrid_top20"]]
        del r["hybrid_top20"]

    # Compute per-query + aggregates
    per_query = {}
    for r in results:
        gold = set(r["gold_chunk_ids"])
        if not gold:
            continue
        per_query[r["qid"]] = {
            setup: {
                "r5":   recall_at_k([t[0] for t in r[key]], gold, 5),
                "r10":  recall_at_k([t[0] for t in r[key]], gold, 10),
                "mrr":  mrr_at_k([t[0] for t in r[key]], gold),
                "ndcg": ndcg_at_k([t[0] for t in r[key]], gold),
            }
            for setup, key in [
                ("dense_w3",    "dense_top10"),
                ("hybrid",      "hybrid_top10"),
                ("hybrid_rrk",  "hybrid_rrk_top10"),
            ]
        }

    positive_qids = list(per_query.keys())
    aggregates = {}
    for setup in ["dense_w3", "hybrid", "hybrid_rrk"]:
        aggregates[setup] = {
            "r5":   _mean([per_query[q][setup]["r5"]   for q in positive_qids]),
            "r10":  _mean([per_query[q][setup]["r10"]  for q in positive_qids]),
            "mrr":  _mean([per_query[q][setup]["mrr"]  for q in positive_qids]),
            "ndcg": _mean([per_query[q][setup]["ndcg"] for q in positive_qids]),
            "n":    len(positive_qids),
        }

    # Save JSON
    payload = {
        "config": {
            "collection": "italian_legal_v1_hybrid",
            "gold_file": str(GOLD_PATH.relative_to(ROOT)),
            "top_k_final": TOP_K_FINAL,
            "rerank_top_k": RERANK_TOP_K,
            "rerank_model": "BAAI/bge-reranker-v2-m3",
            "query_expansion": "core.terminology.expand_query (aliases.yaml)",
        },
        "per_query": results,
        "per_query_metrics": per_query,
        "aggregates": aggregates,
    }
    RESULTS_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    log.info("Wrote %s", RESULTS_OUT.relative_to(ROOT))

    # Load baseline for comparison
    if not RESULTS_BASELINE.exists():
        raise RuntimeError(f"Baseline mancante: {RESULTS_BASELINE}")
    baseline = json.loads(RESULTS_BASELINE.read_text())
    baseline_by_qid = {r["qid"]: r for r in baseline["per_query"]}
    baseline_per_q_metrics = {}
    for r in baseline["per_query"]:
        gold = set(r["gold_chunk_ids"])
        if not gold:
            continue
        baseline_per_q_metrics[r["qid"]] = {
            setup: {
                "r5":   recall_at_k([t[0] for t in r[key]], gold, 5),
                "r10":  recall_at_k([t[0] for t in r[key]], gold, 10),
                "mrr":  mrr_at_k([t[0] for t in r[key]], gold),
                "ndcg": ndcg_at_k([t[0] for t in r[key]], gold),
            }
            for setup, key in [
                ("dense_w3",    "dense_top10"),
                ("hybrid",      "hybrid_top10"),
                ("hybrid_rrk",  "hybrid_rrk_top10"),
            ]
        }
    baseline_agg = {}
    for setup in ["dense_w3", "hybrid", "hybrid_rrk"]:
        baseline_agg[setup] = {
            "r5":   _mean([baseline_per_q_metrics[q][setup]["r5"]   for q in positive_qids]),
            "r10":  _mean([baseline_per_q_metrics[q][setup]["r10"]  for q in positive_qids]),
            "mrr":  _mean([baseline_per_q_metrics[q][setup]["mrr"]  for q in positive_qids]),
            "ndcg": _mean([baseline_per_q_metrics[q][setup]["ndcg"] for q in positive_qids]),
        }

    # Build stdout report
    print_report(payload, baseline_per_q_metrics, baseline_agg, results,
                 baseline_by_qid)
    return 0


def _f(v, fmt="{:.3f}"):
    return "—" if v is None else fmt.format(v)


def _delta_f(v):
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.3f}"


def print_report(payload, baseline_pq, baseline_agg, results, baseline_by_qid):
    agg = payload["aggregates"]
    per_q = payload["per_query_metrics"]
    positive_qids = list(per_q.keys())

    L = []
    L.append("# Benchmark W3 con query expansion — report")
    L.append("")
    L.append(f"**Gold:** `data/benchmark/gold_validated_v2.json` "
             f"({agg['dense_w3']['n']} positive)")
    L.append("**Query expansion:** `core.terminology.expand_query` "
             "(3 alias: FRIA, DPIA, scoring creditizio)")
    L.append("**Setup confrontati:** dense_w3, hybrid, hybrid_rrk (rerank_top_k=20)")
    L.append("")

    # 1. Aggregato pre/post
    L.append("## 1. Aggregato 3 setup × 4 metriche × {baseline W3, expansion, Δ}")
    L.append("")
    L.append("| Setup | Metrica | W3 baseline | + expansion | Δ |")
    L.append("|---|---|---:|---:|---:|")
    for setup in ["dense_w3", "hybrid", "hybrid_rrk"]:
        for metric in ["r5", "r10", "mrr", "ndcg"]:
            b = baseline_agg[setup][metric]
            n = agg[setup][metric]
            d = n - b if (b is not None and n is not None) else None
            L.append(f"| `{setup}` | {metric.upper()} | "
                     f"{_f(b)} | {_f(n)} | {_delta_f(d)} |")
    L.append("")

    # 2. Focus Q19
    L.append("## 2. Focus Q19 — DPIA + FRIA scoring bancario")
    L.append("")
    q19 = next(r for r in results if r["qid"] == "Q19")
    L.append(f"**Query originale:** `{q19['query_original']}`")
    L.append(f"**Query espansa:**   `{q19['query_expanded']}`")
    L.append("")
    gold_q19 = set(q19["gold_chunk_ids"])
    L.append(f"**Gold ({len(gold_q19)}):**")
    for gid in q19["gold_chunk_ids"]:
        L.append(f"- `{gid}`")
    L.append("")
    L.append("**Top-10 hybrid_rrk con expansion:**")
    L.append("")
    L.append("| rank | chunk_id | score | in gold? |")
    L.append("|---:|---|---:|:---:|")
    for i, (cid, sc) in enumerate(q19["hybrid_rrk_top10"], 1):
        mark = "✓" if cid in gold_q19 else ""
        L.append(f"| {i} | `{cid}` | {sc:.4f} | {mark} |")
    L.append("")
    # Pre/post Q19
    L.append("**Pre/post Q19 (3 setup):**")
    L.append("")
    L.append("| Setup | R@5 pre | R@5 post | R@10 pre | R@10 post | MRR pre | MRR post | NDCG pre | NDCG post |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for setup in ["dense_w3", "hybrid", "hybrid_rrk"]:
        b = baseline_pq["Q19"][setup]; n = per_q["Q19"][setup]
        L.append(f"| `{setup}` | {_f(b['r5'])} | {_f(n['r5'])} | "
                 f"{_f(b['r10'])} | {_f(n['r10'])} | "
                 f"{_f(b['mrr'])} | {_f(n['mrr'])} | "
                 f"{_f(b['ndcg'])} | {_f(n['ndcg'])} |")
    L.append("")

    # 3. Regressioni (delta R@10 < 0 per qualunque setup)
    L.append("## 3. Regressioni (Δ R@10 < 0)")
    L.append("")
    regressions = []
    for qid in positive_qids:
        for setup in ["dense_w3", "hybrid", "hybrid_rrk"]:
            b = baseline_pq[qid][setup]["r10"]
            n = per_q[qid][setup]["r10"]
            if b is None or n is None:
                continue
            d = n - b
            if d < 0:
                regressions.append({"qid": qid, "setup": setup, "delta": d,
                                    "pre": b, "post": n})
    if not regressions:
        L.append("_Nessuna regressione._")
    else:
        L.append("| qid | setup | R@10 pre | R@10 post | Δ |")
        L.append("|---|---|---:|---:|---:|")
        regressions.sort(key=lambda x: x["delta"])
        for r in regressions:
            L.append(f"| {r['qid']} | `{r['setup']}` | "
                     f"{_f(r['pre'])} | {_f(r['post'])} | {_delta_f(r['delta'])} |")
    L.append("")

    # 4. Verdetto
    severe = [r for r in regressions if abs(r["delta"]) > 0.25]
    agg_deltas_r10 = [
        agg[s]["r10"] - baseline_agg[s]["r10"]
        for s in ["dense_w3", "hybrid", "hybrid_rrk"]
    ]
    agg_regression = any(d < 0 for d in agg_deltas_r10)

    verdict_pass = (not severe) and (not agg_regression)
    L.append("## 4. Verdetto")
    L.append("")
    L.append(f"- Regressioni totali (Δ R@10 < 0 su qualunque query/setup): "
             f"**{len(regressions)}**")
    L.append(f"- Regressioni severe (|Δ| > 0.25 su singola query): "
             f"**{len(severe)}**")
    L.append(f"- Δ R@10 aggregato per setup: dense_w3 "
             f"{_delta_f(agg_deltas_r10[0])}, hybrid {_delta_f(agg_deltas_r10[1])}, "
             f"hybrid_rrk {_delta_f(agg_deltas_r10[2])}")
    L.append(f"- Aggregato in regressione su qualche setup? **{'SÌ' if agg_regression else 'NO'}**")
    L.append("")
    L.append(f"**VERDETTO: {'PASS ✅' if verdict_pass else 'FAIL ❌'}**")
    L.append("")

    print("\n".join(L))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _is_boundary_fragile_hybrid(qid: str, baseline_by_qid: dict,
                                 top_k: int = TOP_K_FINAL) -> tuple[bool, str]:
    """Boundary-fragile per setup hybrid: esiste un chunk a rank > K (in top-20
    baseline) con score identico al gold dentro top-K?

    Ritorna (is_fragile, reason). `top_k=10`.
    """
    r = baseline_by_qid.get(qid)
    if r is None:
        return False, "no baseline"
    gold = set(r["gold_chunk_ids"])
    top10 = r.get("hybrid_top10", [])
    top20_ids = r.get("hybrid_top20_ids", [])
    top20_scores = r.get("hybrid_top20_scores", [])
    if len(top20_scores) <= top_k:
        return False, "top-20 indisponibile"

    gold_scores_in_top_k = [
        sc for cid, sc in top10[:top_k] if cid in gold
    ]
    if not gold_scores_in_top_k:
        return False, "nessun gold in baseline top-K"

    overflow_scores = top20_scores[top_k:]
    for gs in gold_scores_in_top_k:
        for os_ in overflow_scores:
            if abs(gs - os_) < 1e-9:
                return True, f"gold score {gs:.4f} == overflow score (rank >{top_k})"
    return False, f"no tied overflow (gold scores {gold_scores_in_top_k})"


def phase_verdict() -> int:
    """Applica la regola boundary-fragile e riemette il verdetto.

    Legge baseline (`results_w3.json`) e expansion (`results_w3_expansion.json`),
    rifa il confronto, classifica le regressioni e ignora quelle boundary-fragile.
    Nessun retrieval né rerank: solo aggregazione dei dati salvati.
    """
    if not RESULTS_BASELINE.exists():
        raise RuntimeError(f"Baseline mancante: {RESULTS_BASELINE}")
    if not RESULTS_OUT.exists():
        raise RuntimeError(f"Expansion mancante: {RESULTS_OUT}")
    baseline = json.loads(RESULTS_BASELINE.read_text())
    new = json.loads(RESULTS_OUT.read_text())

    baseline_by_qid = {r["qid"]: r for r in baseline["per_query"]}
    new_by_qid = {r["qid"]: r for r in new["per_query"]}

    positive_qids = sorted([
        r["qid"] for r in new["per_query"] if r["gold_chunk_ids"]
    ])

    def metrics(r, key):
        gold = set(r["gold_chunk_ids"])
        ids = [t[0] for t in r[key]]
        return {
            "r5":   recall_at_k(ids, gold, 5),
            "r10":  recall_at_k(ids, gold, 10),
            "mrr":  mrr_at_k(ids, gold),
            "ndcg": ndcg_at_k(ids, gold),
        }

    setups = [
        ("dense_w3",   "dense_top10"),
        ("hybrid",     "hybrid_top10"),
        ("hybrid_rrk", "hybrid_rrk_top10"),
    ]

    baseline_pq = {qid: {s: metrics(baseline_by_qid[qid], k) for s, k in setups}
                   for qid in positive_qids}
    new_pq = {qid: {s: metrics(new_by_qid[qid], k) for s, k in setups}
              for qid in positive_qids}

    baseline_agg = {
        s: {m: _mean([baseline_pq[q][s][m] for q in positive_qids])
            for m in ["r5", "r10", "mrr", "ndcg"]}
        for s, _ in setups
    }
    new_agg = {
        s: {m: _mean([new_pq[q][s][m] for q in positive_qids])
            for m in ["r5", "r10", "mrr", "ndcg"]}
        for s, _ in setups
    }

    # Regressioni
    raw_regressions = []
    for qid in positive_qids:
        for s, _ in setups:
            b = baseline_pq[qid][s]["r10"]
            n = new_pq[qid][s]["r10"]
            if b is None or n is None:
                continue
            d = n - b
            if d < 0:
                raw_regressions.append({"qid": qid, "setup": s,
                                        "pre": b, "post": n, "delta": d})

    severe_raw = [r for r in raw_regressions if abs(r["delta"]) > 0.25]
    severe_after_rule = []
    fragile_skipped = []
    for r in severe_raw:
        if r["setup"] == "hybrid":
            fragile, reason = _is_boundary_fragile_hybrid(r["qid"], baseline_by_qid)
        else:
            fragile, reason = False, "regola non applicata a non-hybrid"
        if fragile:
            fragile_skipped.append({**r, "reason": reason})
        else:
            severe_after_rule.append({**r, "reason": reason})

    agg_deltas_r10 = [new_agg[s]["r10"] - baseline_agg[s]["r10"]
                      for s, _ in setups]
    agg_regression = any(d < 0 for d in agg_deltas_r10)
    verdict_pass = (not severe_after_rule) and (not agg_regression)

    # ---- stampa report ----
    L = []
    L.append("# Benchmark W3 con query expansion — verdetto (regola boundary-fragile)")
    L.append("")
    L.append(f"**Positive query:** {len(positive_qids)}")
    L.append("")
    L.append("## Aggregato (invariato dal report precedente)")
    L.append("")
    L.append("| Setup | Metrica | W3 baseline | + expansion | Δ |")
    L.append("|---|---|---:|---:|---:|")
    for s, _ in setups:
        for m in ["r5", "r10", "mrr", "ndcg"]:
            b = baseline_agg[s][m]; n = new_agg[s][m]
            d = (n - b) if (b is not None and n is not None) else None
            L.append(f"| `{s}` | {m.upper()} | {_f(b)} | {_f(n)} | {_delta_f(d)} |")
    L.append("")

    L.append("## Regressioni grezze (Δ R@10 < 0)")
    L.append("")
    if not raw_regressions:
        L.append("_Nessuna._")
    else:
        L.append("| qid | setup | R@10 pre | R@10 post | Δ |")
        L.append("|---|---|---:|---:|---:|")
        for r in sorted(raw_regressions, key=lambda x: x["delta"]):
            L.append(f"| {r['qid']} | `{r['setup']}` | {_f(r['pre'])} | "
                     f"{_f(r['post'])} | {_delta_f(r['delta'])} |")
    L.append("")

    L.append("## Regressioni severe (|Δ| > 0.25)")
    L.append("")
    if not severe_raw:
        L.append("_Nessuna._")
    else:
        L.append("| qid | setup | Δ | boundary-fragile? | reason |")
        L.append("|---|---|---:|:---:|---|")
        for r in severe_raw:
            in_fragile = any(x["qid"] == r["qid"] and x["setup"] == r["setup"]
                             for x in fragile_skipped)
            tag = "✓ ignorata" if in_fragile else "✗"
            reason = next(
                (x["reason"] for x in (fragile_skipped + severe_after_rule)
                 if x["qid"] == r["qid"] and x["setup"] == r["setup"]),
                ""
            )
            L.append(f"| {r['qid']} | `{r['setup']}` | {_delta_f(r['delta'])} "
                     f"| {tag} | {reason} |")
    L.append("")

    L.append("## Verdetto con regola boundary-fragile")
    L.append("")
    L.append(f"- Regressioni grezze (Δ R@10 < 0): **{len(raw_regressions)}**")
    L.append(f"- Regressioni severe pre-regola: **{len(severe_raw)}**")
    L.append(f"- Regressioni boundary-fragile ignorate: **{len(fragile_skipped)}**")
    L.append(f"- Regressioni severe rimanenti: **{len(severe_after_rule)}**")
    L.append(f"- Δ R@10 aggregato per setup: dense_w3 "
             f"{_delta_f(agg_deltas_r10[0])}, hybrid "
             f"{_delta_f(agg_deltas_r10[1])}, hybrid_rrk "
             f"{_delta_f(agg_deltas_r10[2])}")
    L.append(f"- Aggregato in regressione: **{'SÌ' if agg_regression else 'NO'}**")
    L.append("")
    L.append(f"**VERDETTO: {'PASS ✅' if verdict_pass else 'FAIL ❌'}**")
    L.append("")

    print("\n".join(L))
    return 0


def phase_graph_rescue(use_graph: bool) -> int:
    """Misura graph-rescued + coverage concettuale sul top-K hybrid_rrk salvato.

    `expand_context` è puro: applicarlo come post-processing su
    `hybrid_rrk_top10` (salvato in `results_w3_expansion.json`) è
    funzionalmente equivalente a propagare `graph_links` dentro
    `retriever.retrieve()`, e molto più veloce. Le metriche R@K/MRR/NDCG
    restano quelle del top-K originale per costruzione (i chunk espansi
    sono "bonus context" non misurato).

    Due metriche distinte:
    - graph-rescued: query con gold mancante dal top-10 ma presente in
      expanded_chunks (misura il graph come strumento di rescue retrieval).
    - coverage concettuale: n. query con almeno 1 chunk espanso e link
      più attivati (misura il graph come bonus context per generation).
    """
    from core.normative_graph import expand_context, load_graph

    if not RESULTS_OUT.exists():
        raise RuntimeError(
            f"Manca {RESULTS_OUT}. Esegui --phase=fetch e --phase=report prima."
        )
    payload = json.loads(RESULTS_OUT.read_text())
    queries = payload["per_query"]

    if use_graph:
        links = load_graph()
        log.info("Graph caricato: %d link", len(links))
    else:
        links = []
        log.info("--use-graph=False: nessun graph caricato (baseline)")

    # Lista query zero-recall calcolata dal payload (no hard-coding).
    zero_recall_qids: list[str] = []
    for r in queries:
        gold = set(r["gold_chunk_ids"])
        if not gold:
            continue
        ids = {t[0] for t in r["hybrid_rrk_top10"]}
        if not (gold & ids):
            zero_recall_qids.append(r["qid"])

    rescued_qids: list[dict] = []
    expansions_per_query: list[int] = []
    queries_with_expansion = 0
    link_activation_count: dict[tuple[str, str, str], int] = {}
    zero_recall_coverage: dict[str, list[dict]] = {}

    for r in queries:
        gold = set(r["gold_chunk_ids"])
        if not gold:
            continue
        top_k_ids = [t[0] for t in r["hybrid_rrk_top10"]]
        gold_in_top = gold & set(top_k_ids)

        if not links:
            continue

        top_for_expand = [(t[0], float(t[1])) for t in r["hybrid_rrk_top10"]]
        expanded = expand_context(top_for_expand, links, max_expansions=5)
        expansions_per_query.append(len(expanded))
        if expanded:
            queries_with_expansion += 1
            for e in expanded:
                key = (e.expanded_from, e.chunk_id, e.relation)
                link_activation_count[key] = link_activation_count.get(key, 0) + 1

        if r["qid"] in zero_recall_qids:
            zero_recall_coverage[r["qid"]] = [
                {
                    "from": e.expanded_from,
                    "to": e.chunk_id,
                    "relation": e.relation,
                    "note": e.note,
                }
                for e in expanded
            ]

        expanded_ids = {e.chunk_id for e in expanded}
        gold_in_expanded = gold & expanded_ids
        gold_new_via_graph = gold_in_expanded - gold_in_top

        if gold_new_via_graph:
            rescued_qids.append({
                "qid": r["qid"],
                "gold_rescued": sorted(gold_new_via_graph),
                "baseline_r10": len(gold_in_top) / len(gold),
                "effective_r10": len(gold_in_top | gold_new_via_graph) / len(gold),
                "links_used": [
                    {
                        "from": e.expanded_from,
                        "to": e.chunk_id,
                        "relation": e.relation,
                        "note": e.note,
                    }
                    for e in expanded
                    if e.chunk_id in gold_new_via_graph
                ],
            })

    # Inventario link mai applicati su query positive (orientamento agnostico).
    applied_undirected: set[frozenset] = set()
    for (src, tgt, _rel) in link_activation_count:
        applied_undirected.add(frozenset((src, tgt)))
    never_applied = [
        l for l in links
        if frozenset((l.from_chunk, l.to_chunk)) not in applied_undirected
    ]

    n_positive = sum(1 for r in queries if r["gold_chunk_ids"])

    # ----------- Report -----------
    L = []
    L.append("# Graph rescue + coverage concettuale (post-hoc su hybrid_rrk_top10)")
    L.append("")
    L.append(f"**--use-graph:** {use_graph}")
    L.append(f"**Link caricati:** {len(links)}")
    L.append(f"**Query positive:** {n_positive}")
    L.append("")

    # ---- A. Graph-rescued ----
    L.append("## A. Graph-rescued (R@10 baseline → R@10 effective)")
    L.append("")
    L.append(f"**Query rescued: {len(rescued_qids)}**")
    L.append("")
    if rescued_qids:
        L.append("| qid | gold rescued | baseline R@10 | effective R@10 |")
        L.append("|---|---|---:|---:|")
        for r in rescued_qids:
            L.append(f"| {r['qid']} | "
                     f"`{', '.join(r['gold_rescued'])}` | "
                     f"{r['baseline_r10']:.2f} | {r['effective_r10']:.2f} |")
        L.append("")
        L.append("**Link attivati per il rescue:**")
        L.append("")
        for r in rescued_qids:
            L.append(f"- **{r['qid']}**")
            for link in r["links_used"]:
                L.append(f"  - `{link['from']}` → `{link['to']}` "
                         f"({link['relation']}): {link['note']}")
    else:
        L.append("_Nessuna query rescued — il graph in v1 non risolve gap retrieval._")
    L.append("")

    # ---- B. Coverage concettuale ----
    L.append("## B. Coverage concettuale (graph come bonus context)")
    L.append("")
    mean_exp = (
        sum(expansions_per_query) / len(expansions_per_query)
        if expansions_per_query else 0.0
    )
    L.append(f"- **n_queries_with_expansion:** {queries_with_expansion} / {n_positive}")
    L.append(f"- **mean_expansions_per_query:** {mean_exp:.2f}")
    L.append(f"- **total expanded chunks attivati (con dedup):** "
             f"{sum(expansions_per_query)}")
    L.append("")
    if link_activation_count:
        L.append("**Top-5 link più attivati:**")
        L.append("")
        L.append("| count | from | to | relation |")
        L.append("|---:|---|---|---|")
        top5 = sorted(link_activation_count.items(), key=lambda kv: -kv[1])[:5]
        for (src, tgt, rel), n in top5:
            L.append(f"| {n} | `{src}` | `{tgt}` | {rel} |")
        L.append("")
    if links:
        L.append(f"**Link mai applicati su query positive:** {len(never_applied)}")
        for l in never_applied:
            L.append(f"  - `{l.from_chunk}` ↔ `{l.to_chunk}` ({l.relation})")
        L.append("")

    # ---- C. Zero-recall queries: coverage del graph ----
    L.append("## C. Query zero-recall (hybrid_rrk) — esito coverage graph")
    L.append("")
    L.append(f"Query zero-recall identificate: **{len(zero_recall_qids)}** "
             f"(`{', '.join(zero_recall_qids)}`)")
    L.append("")
    L.append("| qid | n. chunk espansi | link attivati |")
    L.append("|---|---:|---|")
    for qid in zero_recall_qids:
        exps = zero_recall_coverage.get(qid, [])
        if exps:
            details = "; ".join(
                f"`{e['from']}` → `{e['to']}` ({e['relation']})"
                for e in exps
            )
        else:
            details = "_nessun link attivato (top-10 non contiene anchor del graph)_"
        L.append(f"| {qid} | {len(exps)} | {details} |")
    L.append("")

    L.append("> NOTA: le metriche ufficiali R@K/MRR/NDCG NON sono modificate. "
             "Graph-rescued misura se il graph riempie buchi del retrieval; "
             "coverage concettuale misura quanto il graph aggiunge contesto "
             "utile alla generation a valle.")
    print("\n".join(L))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase",
                        choices=["fetch", "report", "verdict", "graph_rescue"],
                        required=True)
    parser.add_argument("--use-graph", action="store_true",
                        help="Solo per --phase=graph_rescue: applica graph.yaml")
    args = parser.parse_args()
    if args.phase == "fetch":
        return phase_fetch()
    if args.phase == "report":
        return phase_rerank_and_report()
    if args.phase == "verdict":
        return phase_verdict()
    return phase_graph_rescue(use_graph=args.use_graph)


if __name__ == "__main__":
    sys.exit(main())
