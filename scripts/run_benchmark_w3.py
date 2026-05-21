"""Benchmark esteso settimana 3 — 3 setup × 50 query su `italian_legal_v1_hybrid`.

Due fasi separate (processi distinti per liberare MPS fra encoder e reranker):

    spike/.venv/bin/python scripts/run_benchmark_w3.py --phase=fetch
    spike/.venv/bin/python scripts/run_benchmark_w3.py --phase=rerank

`--phase=fetch` produce `data/benchmark/_w3_phase1.pkl` con dense top-10,
hybrid top-10 e hybrid top-20 (con testo per il rerank) per ciascuna query.

`--phase=rerank` carica il pickle, applica `bge-reranker-v2-m3` sui top-20,
calcola metriche e scrive:
- data/benchmark/results_w3.json (raw per-query + aggregati)
- data/benchmark/BENCHMARK_W3.md (report comparativo)
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
log = logging.getLogger("run_benchmark_w3")

GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated_v2.json"
INTERMEDIATE = ROOT / "data" / "benchmark" / "_w3_phase1.pkl"
RESULTS_JSON = ROOT / "data" / "benchmark" / "results_w3.json"
REPORT_MD = ROOT / "data" / "benchmark" / "BENCHMARK_W3.md"
RESULTS_W2 = ROOT / "data" / "benchmark" / "results.json"

# Rerank config — consistente con spike/smoke_reranker.py
RERANK_MAX_LENGTH = 512
RERANK_BATCH_SIZE = 8
TEXT_CHAR_CAP = 2500
TOP_K_FINAL = 10
RERANK_TOP_K = 20
WARMUP_QUERIES = 3

# Use case mapping
UC_MAP = {
    "UC1": ["Q1", "Q11", "Q12", "Q13", "Q14"],
    "UC2": ["Q2", "Q15", "Q16", "Q17", "Q18"],
    "UC3": ["Q3", "Q6", "Q7", "Q8", "Q19"],
    "UC4": ["Q4", "Q20", "Q21", "Q22"],
    "UC5": ["Q5", "Q9", "Q10", "Q23", "Q24", "Q25"],
}
STRESS_QIDS = [f"Q{i}" for i in range(26, 41)]
EDGE_QIDS = [f"Q{i}" for i in range(41, 51)]
NATURAL_QIDS = [f"Q{i}" for i in range(1, 26)]

# Baseline W2 (per sanity check)
W2_BASELINE_PER_Q = {
    "Q1":  {"r5": 0.75, "r10": 0.75, "mrr": 1.0},
    "Q2":  {"r5": 0.50, "r10": 0.50, "mrr": 1.0},
    "Q3":  {"r5": 0.75, "r10": 0.75, "mrr": 1.0},
    "Q5":  {"r5": 0.00, "r10": 0.00, "mrr": 0.0},
    "Q6":  {"r5": 1.00, "r10": 1.00, "mrr": 1.0},
    "Q7":  {"r5": 0.6667, "r10": 1.00, "mrr": 1.0},
    "Q8":  {"r5": 0.50, "r10": 1.00, "mrr": 0.50},
    "Q9":  {"r5": 0.00, "r10": 0.25, "mrr": 0.125},
    "Q10": {"r5": 0.00, "r10": 0.00, "mrr": 0.0},
}
W2_AGGREGATE = {"r5": 0.463, "r10": 0.5833, "mrr": 0.625}
TARGETS = {"r10": 0.80, "mrr": 0.75}


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def recall_at_k(retrieved: list[str], gold: set[str], k: int) -> float | None:
    if not gold:
        return None
    return len(set(retrieved[:k]) & gold) / len(gold)


def mrr_at_k(retrieved: list[str], gold: set[str], k: int = TOP_K_FINAL) -> float | None:
    if not gold:
        return None
    for i, cid in enumerate(retrieved[:k], start=1):
        if cid in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], gold: set[str], k: int = TOP_K_FINAL) -> float | None:
    if not gold:
        return None
    dcg = sum(
        1.0 / math.log2(i + 2)
        for i, cid in enumerate(retrieved[:k])
        if cid in gold
    )
    idcg = sum(1.0 / math.log2(j + 2) for j in range(min(k, len(gold))))
    return dcg / idcg if idcg > 0 else 0.0


def first_gold_rank(retrieved: list[str], gold: set[str], k: int = TOP_K_FINAL) -> int | None:
    for i, cid in enumerate(retrieved[:k], start=1):
        if cid in gold:
            return i
    return None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


# ---------------------------------------------------------------------------
# Phase 1 — fetch
# ---------------------------------------------------------------------------

def phase_fetch() -> int:
    import torch
    from fastembed import SparseTextEmbedding

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME, get_client

    data = json.loads(GOLD_PATH.read_text())
    queries = data["queries"]
    log.info("Phase 1 FETCH — %d query da %s", len(queries), GOLD_PATH.name)

    encoder = BgeM3Encoder.get()
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    client = get_client()
    if not client.collection_exists(HYBRID_COLLECTION_NAME):
        raise RuntimeError(f"Collection {HYBRID_COLLECTION_NAME} non esiste")

    info = client.get_collection(HYBRID_COLLECTION_NAME)
    log.info("Collection %s: %d points", HYBRID_COLLECTION_NAME, info.points_count)

    retriever = HybridRetriever(client, encoder, bm25, HYBRID_COLLECTION_NAME)

    results: list[dict] = []
    t_start = time.monotonic()
    for i, q in enumerate(queries, start=1):
        qid = q["qid"]
        qtext = q["query"]
        gold_ids = [c["chunk_id"] for c in q["candidates"] if c.get("is_gold")]

        # dense
        t0 = time.perf_counter()
        dense_hits = retriever.retrieve(qtext, top_k=TOP_K_FINAL, mode="dense")
        t_dense = (time.perf_counter() - t0) * 1000

        # hybrid top-10
        t0 = time.perf_counter()
        hybrid_hits = retriever.retrieve(qtext, top_k=TOP_K_FINAL, mode="hybrid")
        t_hybrid = (time.perf_counter() - t0) * 1000

        # hybrid top-20 (per rerank)
        t0 = time.perf_counter()
        hybrid20_hits = retriever.retrieve(qtext, top_k=RERANK_TOP_K, mode="hybrid")
        t_hybrid20 = (time.perf_counter() - t0) * 1000

        results.append({
            "qid": qid,
            "query": qtext,
            "use_case": q["use_case"],
            "expected_kind": q["expected_kind"],
            "gold_chunk_ids": gold_ids,
            "dense_top10": [
                (h.chunk_id, float(h.score)) for h in dense_hits
            ],
            "hybrid_top10": [
                (h.chunk_id, float(h.score)) for h in hybrid_hits
            ],
            "hybrid_top20": [
                (h.chunk_id, float(h.score),
                 (h.payload.get("text") or "")[:TEXT_CHAR_CAP])
                for h in hybrid20_hits
            ],
            "latency": {
                "dense_ms": t_dense,
                "hybrid_ms": t_hybrid,
                "hybrid20_ms": t_hybrid20,
            },
        })

        if i % 10 == 0 or i == len(queries):
            log.info("  fetch %d/%d (last qid=%s, t_dense=%.0fms, t_hybrid=%.0fms, t_hybrid20=%.0fms)",
                     i, len(queries), qid, t_dense, t_hybrid, t_hybrid20)

    elapsed = time.monotonic() - t_start
    log.info("Phase 1 done in %.1fs. Saving intermediate to %s", elapsed, INTERMEDIATE.name)
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
# Phase 2 — rerank + metrics + outputs
# ---------------------------------------------------------------------------

def phase_rerank_and_report() -> int:
    import torch
    from sentence_transformers import CrossEncoder

    if not INTERMEDIATE.exists():
        raise RuntimeError(
            f"Pickle intermedio mancante: {INTERMEDIATE}. "
            "Esegui prima `--phase=fetch` (processo Python separato)."
        )
    results = pickle.loads(INTERMEDIATE.read_bytes())
    log.info("Phase 2 RERANK — %d query caricate", len(results))

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    log.info("Carico reranker bge-reranker-v2-m3 on %s, max_length=%d, batch=%d",
             device, RERANK_MAX_LENGTH, RERANK_BATCH_SIZE)
    reranker = CrossEncoder(
        "BAAI/bge-reranker-v2-m3", device=device, max_length=RERANK_MAX_LENGTH,
    )

    # Warmup
    warmup_pairs = [("Query dummy", "Documento dummy.")] * 10
    for _ in range(3):
        reranker.predict(
            warmup_pairs, batch_size=RERANK_BATCH_SIZE, show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()
    log.info("Warmup reranker completato")

    # Rerank
    for i, r in enumerate(results, start=1):
        if not r["hybrid_top20"]:
            r["hybrid_rrk_top10"] = []
            r["latency"]["rerank_ms"] = 0.0
            continue
        pairs = [(r["query"], item[2]) for item in r["hybrid_top20"]]
        t0 = time.perf_counter()
        scores = reranker.predict(
            pairs, batch_size=RERANK_BATCH_SIZE, show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()
        t_rerank = (time.perf_counter() - t0) * 1000

        scored = sorted(
            zip(r["hybrid_top20"], scores, strict=True),
            key=lambda hs: float(hs[1]),
            reverse=True,
        )
        r["hybrid_rrk_top10"] = [
            (item[0], float(s)) for item, s in scored[:TOP_K_FINAL]
        ]
        r["latency"]["rerank_ms"] = t_rerank

        if i % 10 == 0 or i == len(results):
            log.info("  rerank %d/%d (last qid=%s, t_rerank=%.0fms)",
                     i, len(results), r["qid"], t_rerank)

    # Strip texts dai top-20 prima del serialize (riduce file size, no info loss
    # per le metriche)
    for r in results:
        r["hybrid_top20_ids"] = [it[0] for it in r["hybrid_top20"]]
        r["hybrid_top20_scores"] = [it[1] for it in r["hybrid_top20"]]
        del r["hybrid_top20"]

    # Metrics
    aggregates = compute_aggregates(results)

    # Write JSON
    payload = {
        "config": {
            "collection": "italian_legal_v1_hybrid",
            "gold_file": str(GOLD_PATH.relative_to(ROOT)),
            "top_k_final": TOP_K_FINAL,
            "rerank_top_k": RERANK_TOP_K,
            "rerank_model": "BAAI/bge-reranker-v2-m3",
            "rerank_max_length": RERANK_MAX_LENGTH,
            "rerank_batch_size": RERANK_BATCH_SIZE,
        },
        "per_query": results,
        "aggregates": aggregates,
    }
    RESULTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    log.info("Wrote %s", RESULTS_JSON.relative_to(ROOT))

    # Write report
    write_report(payload)
    log.info("Wrote %s", REPORT_MD.relative_to(ROOT))

    # Stdout final summary
    print_final_summary(aggregates)
    return 0


# ---------------------------------------------------------------------------
# Metrics aggregation
# ---------------------------------------------------------------------------

SETUPS = ["dense_w3", "hybrid", "hybrid_rrk"]


def _retrieved_ids(r: dict, setup: str) -> list[str]:
    key = {"dense_w3": "dense_top10", "hybrid": "hybrid_top10",
           "hybrid_rrk": "hybrid_rrk_top10"}[setup]
    return [it[0] for it in r[key]]


def _per_query_metrics(r: dict, setup: str) -> dict:
    retrieved = _retrieved_ids(r, setup)
    gold = set(r["gold_chunk_ids"])
    return {
        "r5":   recall_at_k(retrieved, gold, 5),
        "r10":  recall_at_k(retrieved, gold, 10),
        "mrr":  mrr_at_k(retrieved, gold),
        "ndcg": ndcg_at_k(retrieved, gold),
        "first_gold_rank": first_gold_rank(retrieved, gold),
    }


def _aggregate(values: list[float | None]) -> float | None:
    """Mean over non-None values."""
    real = [v for v in values if v is not None]
    if not real:
        return None
    return sum(real) / len(real)


def compute_aggregates(results: list[dict]) -> dict:
    by_qid = {r["qid"]: r for r in results}
    positive_qids = [r["qid"] for r in results if r["gold_chunk_ids"]]
    empty_qids = [r["qid"] for r in results if not r["gold_chunk_ids"]]

    out: dict = {
        "n_positive": len(positive_qids),
        "n_empty": len(empty_qids),
        "positive_qids": positive_qids,
        "empty_qids": empty_qids,
        "per_setup": {},
        "per_setup_by_uc": {},
        "per_setup_naturali_vs_stress": {},
        "per_query": {},
        "sanity_w2": {},
        "latency": {},
        "negative_scores": {},
    }

    # Per-query per-setup
    for r in results:
        out["per_query"][r["qid"]] = {
            setup: _per_query_metrics(r, setup) for setup in SETUPS
        }

    # Global aggregate (39 positive)
    for setup in SETUPS:
        pq = [out["per_query"][qid][setup] for qid in positive_qids]
        out["per_setup"][setup] = {
            "r5":   _aggregate([m["r5"] for m in pq]),
            "r10":  _aggregate([m["r10"] for m in pq]),
            "mrr":  _aggregate([m["mrr"] for m in pq]),
            "ndcg": _aggregate([m["ndcg"] for m in pq]),
            "n":    len(pq),
        }

    # Per use case
    for uc, qids in UC_MAP.items():
        positive_uc = [qid for qid in qids if by_qid[qid]["gold_chunk_ids"]]
        if not positive_uc:
            out["per_setup_by_uc"][uc] = {"n": 0}
            continue
        out["per_setup_by_uc"][uc] = {"n": len(positive_uc), "qids": positive_uc}
        for setup in SETUPS:
            pq = [out["per_query"][qid][setup] for qid in positive_uc]
            out["per_setup_by_uc"][uc][setup] = {
                "r5":   _aggregate([m["r5"] for m in pq]),
                "r10":  _aggregate([m["r10"] for m in pq]),
                "mrr":  _aggregate([m["mrr"] for m in pq]),
                "ndcg": _aggregate([m["ndcg"] for m in pq]),
            }

    # Naturali vs stress
    naturali = [qid for qid in NATURAL_QIDS if qid in by_qid and by_qid[qid]["gold_chunk_ids"]]
    stress = [qid for qid in STRESS_QIDS if qid in by_qid and by_qid[qid]["gold_chunk_ids"]]
    for cluster, qids in [("naturali", naturali), ("stress", stress)]:
        out["per_setup_naturali_vs_stress"][cluster] = {"n": len(qids), "qids": qids}
        for setup in SETUPS:
            pq = [out["per_query"][qid][setup] for qid in qids]
            out["per_setup_naturali_vs_stress"][cluster][setup] = {
                "r5":   _aggregate([m["r5"] for m in pq]),
                "r10":  _aggregate([m["r10"] for m in pq]),
                "mrr":  _aggregate([m["mrr"] for m in pq]),
                "ndcg": _aggregate([m["ndcg"] for m in pq]),
            }

    # Sanity W2: dense_w3 vs baseline su Q1, Q2, Q3, Q5-Q10
    common = list(W2_BASELINE_PER_Q.keys())
    deltas_r5, deltas_r10, deltas_mrr = [], [], []
    sanity_rows = []
    for qid in common:
        w2 = W2_BASELINE_PER_Q[qid]
        d = out["per_query"][qid]["dense_w3"]
        dr5 = (d["r5"] or 0) - w2["r5"]
        dr10 = (d["r10"] or 0) - w2["r10"]
        dmrr = (d["mrr"] or 0) - w2["mrr"]
        deltas_r5.append(dr5)
        deltas_r10.append(dr10)
        deltas_mrr.append(dmrr)
        sanity_rows.append({
            "qid": qid,
            "w2": w2,
            "w3_dense": {"r5": d["r5"], "r10": d["r10"], "mrr": d["mrr"]},
            "delta": {"r5": dr5, "r10": dr10, "mrr": dmrr},
        })
    mean_abs_delta = (
        statistics.mean(abs(x) for x in deltas_r5 + deltas_r10 + deltas_mrr)
        if deltas_r5 else 0.0
    )
    out["sanity_w2"] = {
        "rows": sanity_rows,
        "mean_abs_delta": mean_abs_delta,
        "verdict": "PASS" if mean_abs_delta < 0.03 else "FAIL",
    }

    # Latency p50/p95 (skip warmup)
    warmup = WARMUP_QUERIES
    dense_lat = [r["latency"]["dense_ms"] for r in results[warmup:]]
    hyb_lat = [r["latency"]["hybrid_ms"] for r in results[warmup:]]
    hyb20_lat = [r["latency"]["hybrid20_ms"] for r in results[warmup:]]
    rrk_lat = [r["latency"]["rerank_ms"] for r in results[warmup:]
               if r["latency"]["rerank_ms"] > 0]
    e2e_dense = dense_lat
    e2e_hybrid = hyb_lat
    e2e_rrk = [r["latency"]["hybrid20_ms"] + r["latency"]["rerank_ms"]
               for r in results[warmup:]
               if r["latency"]["rerank_ms"] > 0]
    out["latency"] = {
        "warmup_excluded": warmup,
        "retrieval": {
            "dense":      {"p50": percentile(dense_lat, 0.5), "p95": percentile(dense_lat, 0.95)},
            "hybrid":     {"p50": percentile(hyb_lat, 0.5),   "p95": percentile(hyb_lat, 0.95)},
            "hybrid_t20": {"p50": percentile(hyb20_lat, 0.5), "p95": percentile(hyb20_lat, 0.95)},
        },
        "rerank":         {"p50": percentile(rrk_lat, 0.5),   "p95": percentile(rrk_lat, 0.95)},
        "end_to_end": {
            "dense_w3":   {"p50": percentile(e2e_dense, 0.5), "p95": percentile(e2e_dense, 0.95)},
            "hybrid":     {"p50": percentile(e2e_hybrid, 0.5),"p95": percentile(e2e_hybrid, 0.95)},
            "hybrid_rrk": {"p50": percentile(e2e_rrk, 0.5),   "p95": percentile(e2e_rrk, 0.95)},
        },
    }

    # Top-1 score per query con gold vuoto
    for qid in empty_qids:
        r = by_qid[qid]
        out["negative_scores"][qid] = {
            "use_case": r["use_case"],
            "expected_kind": r["expected_kind"],
            "dense_top1":     r["dense_top10"][0][1] if r["dense_top10"] else None,
            "hybrid_top1":    r["hybrid_top10"][0][1] if r["hybrid_top10"] else None,
            "hybrid_rrk_top1": r["hybrid_rrk_top10"][0][1] if r["hybrid_rrk_top10"] else None,
        }
    # Mean/median top-1 negative vs positive (informal sanity)
    for setup in SETUPS:
        key = {"dense_w3": "dense_top10", "hybrid": "hybrid_top10",
               "hybrid_rrk": "hybrid_rrk_top10"}[setup]
        neg_top1 = [by_qid[qid][key][0][1] for qid in empty_qids
                    if by_qid[qid][key]]
        pos_top1 = [r[key][0][1] for r in results
                    if r["gold_chunk_ids"] and r[key]]
        out["negative_scores"][f"_{setup}_neg_top1_mean"] = (
            statistics.mean(neg_top1) if neg_top1 else None
        )
        out["negative_scores"][f"_{setup}_neg_top1_median"] = (
            statistics.median(neg_top1) if neg_top1 else None
        )
        out["negative_scores"][f"_{setup}_pos_top1_mean"] = (
            statistics.mean(pos_top1) if pos_top1 else None
        )

    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _f(v, fmt="{:.3f}") -> str:
    if v is None:
        return "—"
    return fmt.format(v)


def _delta_f(v) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.3f}"


def write_report(payload: dict) -> None:
    agg = payload["aggregates"]
    cfg = payload["config"]
    results = payload["per_query"]

    lines: list[str] = []
    lines.append("# Benchmark esteso settimana 3 — 3 setup × 50 query")
    lines.append("")
    lines.append("**Data:** 2026-05-19")
    lines.append(f"**Collection:** `{cfg['collection']}` (858 chunk, dense+sparse named vectors)")
    lines.append(f"**Gold:** `{cfg['gold_file']}` (50 query, 72 gold, 39 positive)")
    lines.append(f"**Setup:** top_k_final={cfg['top_k_final']}, rerank_top_k={cfg['rerank_top_k']}, "
                 f"reranker `{cfg['rerank_model']}` (MPS float32, batch={cfg['rerank_batch_size']}, "
                 f"max_length={cfg['rerank_max_length']})")
    lines.append("")

    # --- Sanity check vs W2 ---
    lines.append("## Sanity check vs baseline W2")
    lines.append("")
    lines.append("Confronto `dense_w3` (su `italian_legal_v1_hybrid`) vs baseline W2 "
                 "(su `italian_legal_v1`) sulle 9 query positive comuni "
                 "(Q1-Q3, Q5-Q10). Atteso: scarto trascurabile.")
    lines.append("")
    lines.append("| qid | W2 R@5 | W3 R@5 | Δ | W2 R@10 | W3 R@10 | Δ | W2 MRR | W3 MRR | Δ |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in agg["sanity_w2"]["rows"]:
        qid = row["qid"]; w2 = row["w2"]; w3 = row["w3_dense"]; d = row["delta"]
        lines.append(f"| {qid} | {_f(w2['r5'])} | {_f(w3['r5'])} | {_delta_f(d['r5'])} "
                     f"| {_f(w2['r10'])} | {_f(w3['r10'])} | {_delta_f(d['r10'])} "
                     f"| {_f(w2['mrr'])} | {_f(w3['mrr'])} | {_delta_f(d['mrr'])} |")
    lines.append("")
    mean_abs = agg["sanity_w2"]["mean_abs_delta"]
    verdict = agg["sanity_w2"]["verdict"]
    lines.append(f"**Mean |Δ| = {mean_abs:.4f}** → **{verdict}** "
                 f"(soglia: media |Δ| < 0.03 = 3pp).")
    lines.append("")

    # --- Aggregati principali ---
    lines.append("## Metriche aggregate (39 positive)")
    lines.append("")
    lines.append("| Setup | R@5 | R@10 | MRR | NDCG@10 |")
    lines.append("|---|---:|---:|---:|---:|")
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        lines.append(f"| `{setup}` | {_f(a['r5'])} | {_f(a['r10'])} | "
                     f"{_f(a['mrr'])} | {_f(a['ndcg'])} |")
    # Delta rows
    dn = agg["per_setup"]["dense_w3"]
    hy = agg["per_setup"]["hybrid"]
    rk = agg["per_setup"]["hybrid_rrk"]
    lines.append(f"| **Δ hybrid vs dense** | "
                 f"{_delta_f(hy['r5']-dn['r5'])} | {_delta_f(hy['r10']-dn['r10'])} | "
                 f"{_delta_f(hy['mrr']-dn['mrr'])} | {_delta_f(hy['ndcg']-dn['ndcg'])} |")
    lines.append(f"| **Δ hybrid_rrk vs hybrid** | "
                 f"{_delta_f(rk['r5']-hy['r5'])} | {_delta_f(rk['r10']-hy['r10'])} | "
                 f"{_delta_f(rk['mrr']-hy['mrr'])} | {_delta_f(rk['ndcg']-hy['ndcg'])} |")
    lines.append("")
    lines.append(f"**Baseline W2 (riferimento, su 9 positive di Q1-Q10):** "
                 f"R@5={W2_AGGREGATE['r5']:.3f}, R@10={W2_AGGREGATE['r10']:.4f}, "
                 f"MRR={W2_AGGREGATE['mrr']:.3f}")
    lines.append(f"**Target informali SCOPE W3:** R@10 ≥ {TARGETS['r10']}, "
                 f"MRR ≥ {TARGETS['mrr']}")
    lines.append("")

    # --- Per use case ---
    lines.append("## Breakdown per use case")
    lines.append("")
    lines.append("| UC | n_pos | Setup | R@5 | R@10 | MRR | NDCG@10 |")
    lines.append("|---|---:|---|---:|---:|---:|---:|")
    for uc in ["UC1", "UC2", "UC3", "UC4", "UC5"]:
        block = agg["per_setup_by_uc"][uc]
        if block["n"] == 0:
            lines.append(f"| {uc} | 0 | — | — | — | — | — |")
            continue
        for setup in SETUPS:
            a = block[setup]
            lines.append(f"| {uc} | {block['n']} | `{setup}` | "
                         f"{_f(a['r5'])} | {_f(a['r10'])} | "
                         f"{_f(a['mrr'])} | {_f(a['ndcg'])} |")
    lines.append("")
    # Focus Q5 e Q10
    lines.append("**Focus Q5 (multi-normativa 231) e Q10 (NIS2 art definitorio)** "
                 "— i due zero recall@10 della baseline W2:")
    lines.append("")
    lines.append("| qid | Setup | R@5 | R@10 | MRR | first_gold_rank |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for qid in ["Q5", "Q10"]:
        for setup in SETUPS:
            m = agg["per_query"][qid][setup]
            fgr = m["first_gold_rank"]
            lines.append(f"| {qid} | `{setup}` | {_f(m['r5'])} | {_f(m['r10'])} | "
                         f"{_f(m['mrr'])} | {fgr if fgr else '—'} |")
    lines.append("")

    # --- Naturali vs stress ---
    lines.append("## Stress lessicali vs use case naturali")
    lines.append("")
    nat = agg["per_setup_naturali_vs_stress"]["naturali"]
    stress = agg["per_setup_naturali_vs_stress"]["stress"]
    lines.append(f"- **Naturali** ({nat['n']} query positive in Q1-Q25)")
    lines.append(f"- **Stress** ({stress['n']} query positive in Q26-Q40)")
    lines.append("")
    lines.append("| Cluster | Setup | R@10 | MRR | NDCG@10 |")
    lines.append("|---|---|---:|---:|---:|")
    for cluster_name, block in [("Naturali", nat), ("Stress", stress)]:
        for setup in SETUPS:
            a = block[setup]
            lines.append(f"| {cluster_name} | `{setup}` | "
                         f"{_f(a['r10'])} | {_f(a['mrr'])} | {_f(a['ndcg'])} |")
    lines.append("")
    # gap hybrid vs dense per cluster
    gap_nat = nat["hybrid"]["r10"] - nat["dense_w3"]["r10"]
    gap_str = stress["hybrid"]["r10"] - stress["dense_w3"]["r10"]
    lines.append(f"**Gap R@10 (hybrid − dense):** Naturali {_delta_f(gap_nat)}, "
                 f"Stress {_delta_f(gap_str)}. "
                 f"{'Aspettativa BM25 confermata: hybrid migliora più sugli stress.' if gap_str > gap_nat else 'Aspettativa BM25 NON confermata sui dati attuali.'}")
    lines.append("")

    # --- Per-query 39 righe (verticale per leggibilità) ---
    lines.append("## Per-query (39 positive)")
    lines.append("")
    lines.append("| qid | use_case | Setup | R@5 | R@10 | MRR | NDCG@10 |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for r in payload["per_query"]:
        if not r["gold_chunk_ids"]:
            continue
        qid = r["qid"]
        uc = r["use_case"][:42]
        for setup in SETUPS:
            m = agg["per_query"][qid][setup]
            lines.append(f"| {qid} | {uc} | `{setup}` | {_f(m['r5'])} | "
                         f"{_f(m['r10'])} | {_f(m['mrr'])} | {_f(m['ndcg'])} |")
    lines.append("")

    # --- Negative & edge ---
    lines.append("## Negative & edge (11 query, gold vuoto)")
    lines.append("")
    lines.append("| qid | kind | use_case | top1 dense | top1 hybrid | top1 hybrid_rrk |")
    lines.append("|---|---|---|---:|---:|---:|")
    for qid in agg["empty_qids"]:
        n = agg["negative_scores"][qid]
        lines.append(f"| {qid} | {n['expected_kind']} | {n['use_case'][:42]} | "
                     f"{_f(n['dense_top1'], '{:.4f}')} | "
                     f"{_f(n['hybrid_top1'], '{:.4f}')} | "
                     f"{_f(n['hybrid_rrk_top1'], '{:.4f}')} |")
    lines.append("")
    lines.append("**Sanity informale** (mean top-1 score, gold-vuote vs positive):")
    lines.append("")
    lines.append("| Setup | neg mean top-1 | neg median top-1 | pos mean top-1 |")
    lines.append("|---|---:|---:|---:|")
    for setup in SETUPS:
        nm = agg["negative_scores"][f"_{setup}_neg_top1_mean"]
        nmd = agg["negative_scores"][f"_{setup}_neg_top1_median"]
        pm = agg["negative_scores"][f"_{setup}_pos_top1_mean"]
        lines.append(f"| `{setup}` | {_f(nm, '{:.4f}')} | "
                     f"{_f(nmd, '{:.4f}')} | {_f(pm, '{:.4f}')} |")
    lines.append("")
    lines.append("Le scale di score sono **diverse fra setup** (cosine [0..1] per dense, "
                 "BM25 raw per sparse, RRF [0..~0.03] per hybrid, logit del cross-encoder "
                 "per hybrid_rrk). Confronta verticalmente, mai orizzontalmente.")
    lines.append("")

    # --- Latency ---
    lat = agg["latency"]
    lines.append("## Latenza")
    lines.append("")
    lines.append(f"Warmup escluso: prime {lat['warmup_excluded']} query. "
                 "Misure su 47 query effettive (Mac M4 Pro MPS, Qdrant Docker).")
    lines.append("")
    lines.append("| Step | p50 (ms) | p95 (ms) |")
    lines.append("|---|---:|---:|")
    r = lat["retrieval"]
    lines.append(f"| retrieval dense (top-10) | {_f(r['dense']['p50'], '{:.1f}')} | "
                 f"{_f(r['dense']['p95'], '{:.1f}')} |")
    lines.append(f"| retrieval hybrid (top-10) | {_f(r['hybrid']['p50'], '{:.1f}')} | "
                 f"{_f(r['hybrid']['p95'], '{:.1f}')} |")
    lines.append(f"| retrieval hybrid (top-20) | {_f(r['hybrid_t20']['p50'], '{:.1f}')} | "
                 f"{_f(r['hybrid_t20']['p95'], '{:.1f}')} |")
    lines.append(f"| rerank (top-20 → top-10) | {_f(lat['rerank']['p50'], '{:.1f}')} | "
                 f"{_f(lat['rerank']['p95'], '{:.1f}')} |")
    lines.append("")
    lines.append("**End-to-end per setup:**")
    lines.append("")
    lines.append("| Setup | p50 (ms) | p95 (ms) |")
    lines.append("|---|---:|---:|")
    for setup in SETUPS:
        e = lat["end_to_end"][setup]
        lines.append(f"| `{setup}` | {_f(e['p50'], '{:.1f}')} | {_f(e['p95'], '{:.1f}')} |")
    lines.append("")

    # --- Verdetto sintetico ---
    lines.append("## Verdetto sintetico")
    lines.append("")
    dn = agg["per_setup"]["dense_w3"]
    hy = agg["per_setup"]["hybrid"]
    rk = agg["per_setup"]["hybrid_rrk"]
    lines.append(f"- **Hybrid vs dense puro:** R@10 {_delta_f(hy['r10']-dn['r10'])}, "
                 f"MRR {_delta_f(hy['mrr']-dn['mrr'])}, NDCG@10 {_delta_f(hy['ndcg']-dn['ndcg'])}.")
    lines.append(f"- **Reranker vs hybrid:** R@10 {_delta_f(rk['r10']-hy['r10'])}, "
                 f"MRR {_delta_f(rk['mrr']-hy['mrr'])}, NDCG@10 {_delta_f(rk['ndcg']-hy['ndcg'])}.")
    # Targets
    target_hits = []
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        r10_ok = (a['r10'] or 0) >= TARGETS['r10']
        mrr_ok = (a['mrr'] or 0) >= TARGETS['mrr']
        if r10_ok and mrr_ok:
            target_hits.append(setup)
    lines.append(f"- **Target SCOPE (R@10 ≥ {TARGETS['r10']}, MRR ≥ {TARGETS['mrr']}):** "
                 f"{'raggiunti da: ' + ', '.join(f'`{s}`' for s in target_hits) if target_hits else 'NESSUN setup li raggiunge entrambi'}.")
    lat_dn = lat["end_to_end"]["dense_w3"]["p50"]
    lat_hy = lat["end_to_end"]["hybrid"]["p50"]
    lat_rk = lat["end_to_end"]["hybrid_rrk"]["p50"]
    lines.append(f"- **Costo latenza p50 end-to-end:** dense {lat_dn:.0f}ms, "
                 f"hybrid {lat_hy:.0f}ms (+{lat_hy-lat_dn:.0f}ms), "
                 f"hybrid_rrk {lat_rk:.0f}ms (+{lat_rk-lat_hy:.0f}ms vs hybrid).")
    lines.append("")

    REPORT_MD.write_text("\n".join(lines))


def print_final_summary(agg: dict) -> None:
    print("\n" + "=" * 70)
    print(f"BENCHMARK W3 — {agg['n_positive']} positive, {agg['n_empty']} gold-vuote")
    print("=" * 70)
    print(f"\n{'Setup':<14s} | {'R@5':>6s} | {'R@10':>6s} | {'MRR':>6s} | {'NDCG':>6s}")
    print("-" * 60)
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        print(f"{setup:<14s} | {a['r5']:>6.3f} | {a['r10']:>6.3f} | "
              f"{a['mrr']:>6.3f} | {a['ndcg']:>6.3f}")
    print(f"\nSanity W2 (mean |Δ|): {agg['sanity_w2']['mean_abs_delta']:.4f} "
          f"→ {agg['sanity_w2']['verdict']}")
    lat = agg["latency"]["end_to_end"]
    print(f"\nLatency p50 e2e: dense={lat['dense_w3']['p50']:.0f}ms, "
          f"hybrid={lat['hybrid']['p50']:.0f}ms, "
          f"hybrid_rrk={lat['hybrid_rrk']['p50']:.0f}ms")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["fetch", "rerank"], required=True)
    args = parser.parse_args()

    if args.phase == "fetch":
        return phase_fetch()
    return phase_rerank_and_report()


if __name__ == "__main__":
    sys.exit(main())
