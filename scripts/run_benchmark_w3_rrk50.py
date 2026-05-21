"""Estensione benchmark W3 — 4° setup `hybrid_rrk_50` (rerank_top_k=50).

Riusa la stessa pipeline di `run_benchmark_w3.py`, calcola un solo nuovo setup
e poi rigenera `BENCHMARK_W3.md` con 4 setup affiancati. I 3 setup esistenti
(dense_w3, hybrid, hybrid_rrk con rerank_top_k=20) sono **letti verbatim da
`results_w3.json`** — nessuna ricomputazione, nessun drift.

Due fasi (processi distinti per liberare MPS fra encoder e reranker):

    spike/.venv/bin/python scripts/run_benchmark_w3_rrk50.py --phase=fetch
    spike/.venv/bin/python scripts/run_benchmark_w3_rrk50.py --phase=report

Output:
- data/benchmark/results_w3_extended.json (4 setup, raw per-query + aggregati)
- data/benchmark/BENCHMARK_W3.md (rigenerato con la 4° colonna + nuova sezione
  "Trade-off rerank_top_k: 20 vs 50")
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
log = logging.getLogger("run_benchmark_w3_rrk50")

GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated_v2.json"
RESULTS_JSON_W3 = ROOT / "data" / "benchmark" / "results_w3.json"
RESULTS_JSON_EXT = ROOT / "data" / "benchmark" / "results_w3_extended.json"
REPORT_MD = ROOT / "data" / "benchmark" / "BENCHMARK_W3.md"
INTERMEDIATE = ROOT / "data" / "benchmark" / "_w3_rrk50_phase1.pkl"

RERANK_TOP_K = 50
TOP_K_FINAL = 10
RERANK_MAX_LENGTH = 512
RERANK_BATCH_SIZE = 8
TEXT_CHAR_CAP = 2500
WARMUP_QUERIES = 3

SETUPS = ["dense_w3", "hybrid", "hybrid_rrk", "hybrid_rrk_50"]
RRK20_KEY = "hybrid_rrk"
RRK50_KEY = "hybrid_rrk_50"

UC_MAP = {
    "UC1": ["Q1", "Q11", "Q12", "Q13", "Q14"],
    "UC2": ["Q2", "Q15", "Q16", "Q17", "Q18"],
    "UC3": ["Q3", "Q6", "Q7", "Q8", "Q19"],
    "UC4": ["Q4", "Q20", "Q21", "Q22"],
    "UC5": ["Q5", "Q9", "Q10", "Q23", "Q24", "Q25"],
}
STRESS_QIDS = [f"Q{i}" for i in range(26, 41)]
NATURAL_QIDS = [f"Q{i}" for i in range(1, 26)]

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


def first_gold_rank(retrieved, gold, k=TOP_K_FINAL):
    for i, cid in enumerate(retrieved[:k], start=1):
        if cid in gold:
            return i
    return None


def percentile(values, p):
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
# Phase 1 — fetch hybrid top-50 with text
# ---------------------------------------------------------------------------

def phase_fetch() -> int:
    import torch
    from fastembed import SparseTextEmbedding

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME, get_client

    log.info("Phase 1 FETCH — hybrid top-50 + text per rerank_top_k=50")
    gold = json.loads(GOLD_PATH.read_text())
    queries = gold["queries"]
    log.info("%d query da %s", len(queries), GOLD_PATH.name)

    encoder = BgeM3Encoder.get()
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    client = get_client()
    if not client.collection_exists(HYBRID_COLLECTION_NAME):
        raise RuntimeError(f"Collection {HYBRID_COLLECTION_NAME} non esiste")
    retriever = HybridRetriever(client, encoder, bm25, HYBRID_COLLECTION_NAME)

    out: list[dict] = []
    t_start = time.monotonic()
    for i, q in enumerate(queries, start=1):
        t0 = time.perf_counter()
        hits = retriever.retrieve(q["query"], top_k=RERANK_TOP_K, mode="hybrid")
        t_hyb50 = (time.perf_counter() - t0) * 1000
        out.append({
            "qid": q["qid"],
            "query": q["query"],
            "hybrid_top50": [
                (h.chunk_id, float(h.score),
                 (h.payload.get("text") or "")[:TEXT_CHAR_CAP])
                for h in hits
            ],
            "latency_hybrid50_ms": t_hyb50,
        })
        if i % 10 == 0 or i == len(queries):
            log.info("  fetch %d/%d (last qid=%s, t_hyb50=%.0fms)",
                     i, len(queries), q["qid"], t_hyb50)

    log.info("Phase 1 done in %.1fs. Saving to %s",
             time.monotonic() - t_start, INTERMEDIATE.name)
    INTERMEDIATE.write_bytes(pickle.dumps(out))

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
# Phase 2 — rerank top-50 + integrate with results_w3.json + write report
# ---------------------------------------------------------------------------

def phase_rerank_and_report() -> int:
    import torch
    from sentence_transformers import CrossEncoder

    if not INTERMEDIATE.exists():
        raise RuntimeError(f"Pickle mancante: {INTERMEDIATE}. Esegui --phase=fetch.")
    fetched = pickle.loads(INTERMEDIATE.read_bytes())
    log.info("Phase 2 — caricamento reranker (rerank_top_k=%d)", RERANK_TOP_K)

    # Load existing results_w3
    if not RESULTS_JSON_W3.exists():
        raise RuntimeError(f"results_w3.json mancante: {RESULTS_JSON_W3}.")
    base = json.loads(RESULTS_JSON_W3.read_text())
    base_by_qid = {r["qid"]: r for r in base["per_query"]}

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    reranker = CrossEncoder(
        "BAAI/bge-reranker-v2-m3", device=device, max_length=RERANK_MAX_LENGTH,
    )
    for _ in range(3):
        reranker.predict(
            [("warmup", "warmup")] * 10,
            batch_size=RERANK_BATCH_SIZE, show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()
    log.info("Warmup reranker completato")

    # Rerank ciascuna query: top-50 hybrid → top-10 dopo rerank
    for i, f in enumerate(fetched, start=1):
        candidates = f["hybrid_top50"]
        if not candidates:
            f["hybrid_rrk_50_top10"] = []
            f["latency_rerank50_ms"] = 0.0
            continue
        pairs = [(f["query"], c[2]) for c in candidates]
        t0 = time.perf_counter()
        scores = reranker.predict(
            pairs, batch_size=RERANK_BATCH_SIZE, show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()
        t_rerank = (time.perf_counter() - t0) * 1000
        scored = sorted(
            zip(candidates, scores, strict=True),
            key=lambda hs: float(hs[1]), reverse=True,
        )
        f["hybrid_rrk_50_top10"] = [
            (item[0], float(s)) for item, s in scored[:TOP_K_FINAL]
        ]
        f["latency_rerank50_ms"] = t_rerank
        if i % 10 == 0 or i == len(fetched):
            log.info("  rerank %d/%d (last qid=%s, t=%.0fms)",
                     i, len(fetched), f["qid"], t_rerank)

    # Merge into per_query: aggiungi hybrid_rrk_50_top10 + latency
    for f in fetched:
        qid = f["qid"]
        if qid not in base_by_qid:
            log.warning("qid %s in pickle ma non in results_w3.json", qid)
            continue
        base_by_qid[qid]["hybrid_rrk_50_top10"] = f["hybrid_rrk_50_top10"]
        base_by_qid[qid]["latency"]["hybrid50_ms"] = f["latency_hybrid50_ms"]
        base_by_qid[qid]["latency"]["rerank50_ms"] = f["latency_rerank50_ms"]

    # Compute aggregates per i 4 setup
    aggregates = compute_aggregates(base["per_query"])

    # Extended payload
    extended = {
        "config": {
            **base.get("config", {}),
            "extended_with": "hybrid_rrk_50",
            "rerank_top_k_extended": RERANK_TOP_K,
        },
        "per_query": base["per_query"],
        "aggregates": aggregates,
    }
    RESULTS_JSON_EXT.write_text(json.dumps(extended, ensure_ascii=False, indent=2))
    log.info("Wrote %s", RESULTS_JSON_EXT.relative_to(ROOT))

    write_report(extended)
    log.info("Wrote %s (regenerated with 4 setup)", REPORT_MD.relative_to(ROOT))

    print_summary(aggregates)
    return 0


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

def _retrieved_ids(r: dict, setup: str) -> list[str]:
    key = {"dense_w3": "dense_top10", "hybrid": "hybrid_top10",
           "hybrid_rrk": "hybrid_rrk_top10",
           "hybrid_rrk_50": "hybrid_rrk_50_top10"}[setup]
    return [it[0] for it in r.get(key, [])]


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


def _agg(values):
    real = [v for v in values if v is not None]
    if not real:
        return None
    return sum(real) / len(real)


def compute_aggregates(results: list[dict]) -> dict:
    by_qid = {r["qid"]: r for r in results}
    positive = [r["qid"] for r in results if r["gold_chunk_ids"]]
    empty = [r["qid"] for r in results if not r["gold_chunk_ids"]]

    out = {
        "n_positive": len(positive),
        "n_empty": len(empty),
        "positive_qids": positive,
        "empty_qids": empty,
        "per_setup": {},
        "per_setup_by_uc": {},
        "per_setup_naturali_vs_stress": {},
        "per_query": {},
        "sanity_w2": {},
        "latency": {},
        "negative_scores": {},
        "trade_off_20_vs_50": {},
    }

    for r in results:
        out["per_query"][r["qid"]] = {s: _per_query_metrics(r, s) for s in SETUPS}

    for setup in SETUPS:
        pq = [out["per_query"][qid][setup] for qid in positive]
        out["per_setup"][setup] = {
            "r5":   _agg([m["r5"] for m in pq]),
            "r10":  _agg([m["r10"] for m in pq]),
            "mrr":  _agg([m["mrr"] for m in pq]),
            "ndcg": _agg([m["ndcg"] for m in pq]),
            "n":    len(pq),
        }

    for uc, qids in UC_MAP.items():
        positive_uc = [qid for qid in qids if by_qid[qid]["gold_chunk_ids"]]
        if not positive_uc:
            out["per_setup_by_uc"][uc] = {"n": 0}
            continue
        out["per_setup_by_uc"][uc] = {"n": len(positive_uc), "qids": positive_uc}
        for setup in SETUPS:
            pq = [out["per_query"][qid][setup] for qid in positive_uc]
            out["per_setup_by_uc"][uc][setup] = {
                "r5":   _agg([m["r5"] for m in pq]),
                "r10":  _agg([m["r10"] for m in pq]),
                "mrr":  _agg([m["mrr"] for m in pq]),
                "ndcg": _agg([m["ndcg"] for m in pq]),
            }

    naturali = [qid for qid in NATURAL_QIDS
                if qid in by_qid and by_qid[qid]["gold_chunk_ids"]]
    stress = [qid for qid in STRESS_QIDS
              if qid in by_qid and by_qid[qid]["gold_chunk_ids"]]
    for cluster, qids in [("naturali", naturali), ("stress", stress)]:
        out["per_setup_naturali_vs_stress"][cluster] = {"n": len(qids), "qids": qids}
        for setup in SETUPS:
            pq = [out["per_query"][qid][setup] for qid in qids]
            out["per_setup_naturali_vs_stress"][cluster][setup] = {
                "r5":   _agg([m["r5"] for m in pq]),
                "r10":  _agg([m["r10"] for m in pq]),
                "mrr":  _agg([m["mrr"] for m in pq]),
                "ndcg": _agg([m["ndcg"] for m in pq]),
            }

    # Sanity W2
    deltas_r5, deltas_r10, deltas_mrr = [], [], []
    rows = []
    for qid, w2 in W2_BASELINE_PER_Q.items():
        d = out["per_query"][qid]["dense_w3"]
        dr5 = (d["r5"] or 0) - w2["r5"]
        dr10 = (d["r10"] or 0) - w2["r10"]
        dmrr = (d["mrr"] or 0) - w2["mrr"]
        deltas_r5.append(dr5); deltas_r10.append(dr10); deltas_mrr.append(dmrr)
        rows.append({
            "qid": qid, "w2": w2,
            "w3_dense": {"r5": d["r5"], "r10": d["r10"], "mrr": d["mrr"]},
            "delta": {"r5": dr5, "r10": dr10, "mrr": dmrr},
        })
    mean_abs = statistics.mean(abs(x) for x in deltas_r5 + deltas_r10 + deltas_mrr)
    out["sanity_w2"] = {
        "rows": rows, "mean_abs_delta": mean_abs,
        "verdict": "PASS" if mean_abs < 0.03 else "FAIL",
    }

    # Latency
    warmup = WARMUP_QUERIES
    dense_lat = [r["latency"]["dense_ms"] for r in results[warmup:]]
    hyb_lat = [r["latency"]["hybrid_ms"] for r in results[warmup:]]
    hyb20_lat = [r["latency"]["hybrid20_ms"] for r in results[warmup:]]
    hyb50_lat = [r["latency"]["hybrid50_ms"] for r in results[warmup:]
                 if "hybrid50_ms" in r["latency"]]
    rrk20_lat = [r["latency"]["rerank_ms"] for r in results[warmup:]
                 if r["latency"]["rerank_ms"] > 0]
    rrk50_lat = [r["latency"]["rerank50_ms"] for r in results[warmup:]
                 if r["latency"].get("rerank50_ms", 0) > 0]
    e2e_dense = dense_lat
    e2e_hybrid = hyb_lat
    e2e_rrk20 = [r["latency"]["hybrid20_ms"] + r["latency"]["rerank_ms"]
                 for r in results[warmup:] if r["latency"]["rerank_ms"] > 0]
    e2e_rrk50 = [r["latency"]["hybrid50_ms"] + r["latency"]["rerank50_ms"]
                 for r in results[warmup:]
                 if r["latency"].get("rerank50_ms", 0) > 0]
    out["latency"] = {
        "warmup_excluded": warmup,
        "retrieval": {
            "dense":      {"p50": percentile(dense_lat, 0.5), "p95": percentile(dense_lat, 0.95)},
            "hybrid":     {"p50": percentile(hyb_lat, 0.5),   "p95": percentile(hyb_lat, 0.95)},
            "hybrid_t20": {"p50": percentile(hyb20_lat, 0.5), "p95": percentile(hyb20_lat, 0.95)},
            "hybrid_t50": {"p50": percentile(hyb50_lat, 0.5), "p95": percentile(hyb50_lat, 0.95)},
        },
        "rerank_top20": {"p50": percentile(rrk20_lat, 0.5), "p95": percentile(rrk20_lat, 0.95)},
        "rerank_top50": {"p50": percentile(rrk50_lat, 0.5), "p95": percentile(rrk50_lat, 0.95)},
        "end_to_end": {
            "dense_w3":      {"p50": percentile(e2e_dense, 0.5),  "p95": percentile(e2e_dense, 0.95)},
            "hybrid":        {"p50": percentile(e2e_hybrid, 0.5), "p95": percentile(e2e_hybrid, 0.95)},
            "hybrid_rrk":    {"p50": percentile(e2e_rrk20, 0.5),  "p95": percentile(e2e_rrk20, 0.95)},
            "hybrid_rrk_50": {"p50": percentile(e2e_rrk50, 0.5),  "p95": percentile(e2e_rrk50, 0.95)},
        },
    }

    # Negative top-1 scores
    for setup in SETUPS:
        key = {"dense_w3": "dense_top10", "hybrid": "hybrid_top10",
               "hybrid_rrk": "hybrid_rrk_top10",
               "hybrid_rrk_50": "hybrid_rrk_50_top10"}[setup]
        neg = [by_qid[qid][key][0][1] for qid in empty if by_qid[qid].get(key)]
        pos = [r[key][0][1] for r in results
               if r["gold_chunk_ids"] and r.get(key)]
        out["negative_scores"][f"_{setup}_neg_top1_mean"] = (
            statistics.mean(neg) if neg else None)
        out["negative_scores"][f"_{setup}_neg_top1_median"] = (
            statistics.median(neg) if neg else None)
        out["negative_scores"][f"_{setup}_pos_top1_mean"] = (
            statistics.mean(pos) if pos else None)

    for qid in empty:
        r = by_qid[qid]
        out["negative_scores"][qid] = {
            "use_case": r["use_case"],
            "expected_kind": r["expected_kind"],
            "dense_top1":         r["dense_top10"][0][1] if r["dense_top10"] else None,
            "hybrid_top1":        r["hybrid_top10"][0][1] if r["hybrid_top10"] else None,
            "hybrid_rrk_top1":    r["hybrid_rrk_top10"][0][1] if r["hybrid_rrk_top10"] else None,
            "hybrid_rrk_50_top1": r["hybrid_rrk_50_top10"][0][1] if r.get("hybrid_rrk_50_top10") else None,
        }

    # Trade-off: query che si chiudono passando da rrk_20 a rrk_50
    closed = []
    still_zero = []
    for qid in positive:
        r20 = out["per_query"][qid]["hybrid_rrk"]["r10"]
        r50 = out["per_query"][qid]["hybrid_rrk_50"]["r10"]
        if (r20 or 0) == 0 and (r50 or 0) > 0:
            closed.append({"qid": qid, "r10_20": r20, "r10_50": r50})
        elif (r20 or 0) == 0 and (r50 or 0) == 0:
            still_zero.append(qid)
    out["trade_off_20_vs_50"] = {
        "closed_by_50": closed,
        "still_zero_50": still_zero,
    }

    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _f(v, fmt="{:.3f}"):
    return "—" if v is None else fmt.format(v)


def _delta_f(v):
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.3f}"


def write_report(payload: dict) -> None:
    agg = payload["aggregates"]
    cfg = payload["config"]

    L: list[str] = []
    L.append("# Benchmark esteso settimana 3 — 4 setup × 50 query")
    L.append("")
    L.append("**Data:** 2026-05-19")
    L.append("**Collection:** `italian_legal_v1_hybrid` (858 chunk, dense+sparse named vectors)")
    L.append("**Gold:** `data/benchmark/gold_validated_v2.json` (50 query, 72 gold, 39 positive)")
    L.append("**Setup confrontati:** `dense_w3`, `hybrid`, `hybrid_rrk` (rerank_top_k=20), "
             "`hybrid_rrk_50` (rerank_top_k=50)")
    L.append(f"**Reranker:** `BAAI/bge-reranker-v2-m3` (MPS float32, batch="
             f"{RERANK_BATCH_SIZE}, max_length={RERANK_MAX_LENGTH})")
    L.append("")
    L.append("Aggiornamento 2026-05-19: aggiunto il 4° setup `hybrid_rrk_50` dopo la "
             "diagnosi zero-recall che ha mostrato 4 query (Q13, Q34, Q35, Q39) con "
             "gold in hybrid top-50 ma fuori top-20 (vedi `zero_recall_diagnosis.md`).")
    L.append("")

    # Sanity vs W2
    L.append("## Sanity check vs baseline W2")
    L.append("")
    L.append("Confronto `dense_w3` (su `italian_legal_v1_hybrid`) vs baseline W2 "
             "(su `italian_legal_v1`) sulle 9 query positive comuni "
             "(Q1-Q3, Q5-Q10). Atteso: scarto trascurabile.")
    L.append("")
    L.append("| qid | W2 R@5 | W3 R@5 | Δ | W2 R@10 | W3 R@10 | Δ | W2 MRR | W3 MRR | Δ |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in agg["sanity_w2"]["rows"]:
        qid = row["qid"]; w2 = row["w2"]; w3 = row["w3_dense"]; d = row["delta"]
        L.append(f"| {qid} | {_f(w2['r5'])} | {_f(w3['r5'])} | {_delta_f(d['r5'])} "
                 f"| {_f(w2['r10'])} | {_f(w3['r10'])} | {_delta_f(d['r10'])} "
                 f"| {_f(w2['mrr'])} | {_f(w3['mrr'])} | {_delta_f(d['mrr'])} |")
    L.append("")
    L.append(f"**Mean |Δ| = {agg['sanity_w2']['mean_abs_delta']:.4f}** → "
             f"**{agg['sanity_w2']['verdict']}** (soglia: media |Δ| < 0.03 = 3pp).")
    L.append("")

    # Aggregati con 4° setup
    L.append("## Metriche aggregate (39 positive)")
    L.append("")
    L.append("| Setup | R@5 | R@10 | MRR | NDCG@10 |")
    L.append("|---|---:|---:|---:|---:|")
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        L.append(f"| `{setup}` | {_f(a['r5'])} | {_f(a['r10'])} | "
                 f"{_f(a['mrr'])} | {_f(a['ndcg'])} |")
    # Delta rows
    dn = agg["per_setup"]["dense_w3"]
    hy = agg["per_setup"]["hybrid"]
    rk20 = agg["per_setup"]["hybrid_rrk"]
    rk50 = agg["per_setup"]["hybrid_rrk_50"]
    L.append(f"| **Δ hybrid vs dense** | {_delta_f(hy['r5']-dn['r5'])} | "
             f"{_delta_f(hy['r10']-dn['r10'])} | {_delta_f(hy['mrr']-dn['mrr'])} | "
             f"{_delta_f(hy['ndcg']-dn['ndcg'])} |")
    L.append(f"| **Δ rrk_20 vs hybrid** | {_delta_f(rk20['r5']-hy['r5'])} | "
             f"{_delta_f(rk20['r10']-hy['r10'])} | {_delta_f(rk20['mrr']-hy['mrr'])} | "
             f"{_delta_f(rk20['ndcg']-hy['ndcg'])} |")
    L.append(f"| **Δ rrk_50 vs rrk_20** | {_delta_f(rk50['r5']-rk20['r5'])} | "
             f"{_delta_f(rk50['r10']-rk20['r10'])} | {_delta_f(rk50['mrr']-rk20['mrr'])} | "
             f"{_delta_f(rk50['ndcg']-rk20['ndcg'])} |")
    L.append("")
    L.append(f"**Baseline W2 (riferimento, 9 positive di Q1-Q10):** "
             f"R@5={W2_AGGREGATE['r5']:.3f}, R@10={W2_AGGREGATE['r10']:.4f}, "
             f"MRR={W2_AGGREGATE['mrr']:.3f}")
    L.append(f"**Target SCOPE W3:** R@10 ≥ {TARGETS['r10']}, MRR ≥ {TARGETS['mrr']}")
    L.append("")

    # Per use case
    L.append("## Breakdown per use case")
    L.append("")
    L.append("| UC | n_pos | Setup | R@5 | R@10 | MRR | NDCG@10 |")
    L.append("|---|---:|---|---:|---:|---:|---:|")
    for uc in ["UC1", "UC2", "UC3", "UC4", "UC5"]:
        block = agg["per_setup_by_uc"][uc]
        if block["n"] == 0:
            L.append(f"| {uc} | 0 | — | — | — | — | — |")
            continue
        for setup in SETUPS:
            a = block[setup]
            L.append(f"| {uc} | {block['n']} | `{setup}` | "
                     f"{_f(a['r5'])} | {_f(a['r10'])} | "
                     f"{_f(a['mrr'])} | {_f(a['ndcg'])} |")
    L.append("")
    L.append("**Focus Q5 e Q10** (zero-recall baseline W2):")
    L.append("")
    L.append("| qid | Setup | R@5 | R@10 | MRR | first_gold_rank |")
    L.append("|---|---|---:|---:|---:|---:|")
    for qid in ["Q5", "Q10"]:
        for setup in SETUPS:
            m = agg["per_query"][qid][setup]
            fgr = m["first_gold_rank"]
            L.append(f"| {qid} | `{setup}` | {_f(m['r5'])} | {_f(m['r10'])} | "
                     f"{_f(m['mrr'])} | {fgr if fgr else '—'} |")
    L.append("")

    # Naturali vs stress
    L.append("## Stress lessicali vs use case naturali")
    L.append("")
    nat = agg["per_setup_naturali_vs_stress"]["naturali"]
    stress = agg["per_setup_naturali_vs_stress"]["stress"]
    L.append(f"- **Naturali** ({nat['n']} query positive in Q1-Q25)")
    L.append(f"- **Stress** ({stress['n']} query positive in Q26-Q40)")
    L.append("")
    L.append("| Cluster | Setup | R@10 | MRR | NDCG@10 |")
    L.append("|---|---|---:|---:|---:|")
    for cluster_name, block in [("Naturali", nat), ("Stress", stress)]:
        for setup in SETUPS:
            a = block[setup]
            L.append(f"| {cluster_name} | `{setup}` | "
                     f"{_f(a['r10'])} | {_f(a['mrr'])} | {_f(a['ndcg'])} |")
    L.append("")

    # Per-query 39 righe (con 4 setup → 156 righe)
    L.append("## Per-query (39 positive × 4 setup)")
    L.append("")
    L.append("| qid | use_case | Setup | R@5 | R@10 | MRR | NDCG@10 |")
    L.append("|---|---|---|---:|---:|---:|---:|")
    for r in payload["per_query"]:
        if not r["gold_chunk_ids"]:
            continue
        qid = r["qid"]
        uc = r["use_case"][:42]
        for setup in SETUPS:
            m = agg["per_query"][qid][setup]
            L.append(f"| {qid} | {uc} | `{setup}` | {_f(m['r5'])} | "
                     f"{_f(m['r10'])} | {_f(m['mrr'])} | {_f(m['ndcg'])} |")
    L.append("")

    # Negative & edge
    L.append("## Negative & edge (11 query, gold vuoto)")
    L.append("")
    L.append("| qid | kind | use_case | top1 dense | top1 hybrid | top1 rrk_20 | top1 rrk_50 |")
    L.append("|---|---|---|---:|---:|---:|---:|")
    for qid in agg["empty_qids"]:
        n = agg["negative_scores"][qid]
        L.append(f"| {qid} | {n['expected_kind']} | {n['use_case'][:42]} | "
                 f"{_f(n['dense_top1'], '{:.4f}')} | "
                 f"{_f(n['hybrid_top1'], '{:.4f}')} | "
                 f"{_f(n['hybrid_rrk_top1'], '{:.4f}')} | "
                 f"{_f(n['hybrid_rrk_50_top1'], '{:.4f}')} |")
    L.append("")
    L.append("**Sanity informale** (mean top-1 score, gold-vuote vs positive):")
    L.append("")
    L.append("| Setup | neg mean | neg median | pos mean |")
    L.append("|---|---:|---:|---:|")
    for setup in SETUPS:
        nm = agg["negative_scores"][f"_{setup}_neg_top1_mean"]
        nmd = agg["negative_scores"][f"_{setup}_neg_top1_median"]
        pm = agg["negative_scores"][f"_{setup}_pos_top1_mean"]
        L.append(f"| `{setup}` | {_f(nm, '{:.4f}')} | "
                 f"{_f(nmd, '{:.4f}')} | {_f(pm, '{:.4f}')} |")
    L.append("")

    # Latency
    lat = agg["latency"]
    L.append("## Latenza")
    L.append("")
    L.append(f"Warmup escluso: prime {lat['warmup_excluded']} query. "
             "Misure su 47 query effettive (Mac M4 Pro MPS, Qdrant Docker).")
    L.append("")
    L.append("| Step | p50 (ms) | p95 (ms) |")
    L.append("|---|---:|---:|")
    r = lat["retrieval"]
    L.append(f"| retrieval dense (top-10) | {_f(r['dense']['p50'], '{:.1f}')} | "
             f"{_f(r['dense']['p95'], '{:.1f}')} |")
    L.append(f"| retrieval hybrid (top-10) | {_f(r['hybrid']['p50'], '{:.1f}')} | "
             f"{_f(r['hybrid']['p95'], '{:.1f}')} |")
    L.append(f"| retrieval hybrid (top-20) | {_f(r['hybrid_t20']['p50'], '{:.1f}')} | "
             f"{_f(r['hybrid_t20']['p95'], '{:.1f}')} |")
    L.append(f"| retrieval hybrid (top-50) | {_f(r['hybrid_t50']['p50'], '{:.1f}')} | "
             f"{_f(r['hybrid_t50']['p95'], '{:.1f}')} |")
    L.append(f"| rerank top-20 → top-10 | {_f(lat['rerank_top20']['p50'], '{:.1f}')} | "
             f"{_f(lat['rerank_top20']['p95'], '{:.1f}')} |")
    L.append(f"| rerank top-50 → top-10 | {_f(lat['rerank_top50']['p50'], '{:.1f}')} | "
             f"{_f(lat['rerank_top50']['p95'], '{:.1f}')} |")
    L.append("")
    L.append("**End-to-end per setup:**")
    L.append("")
    L.append("| Setup | p50 (ms) | p95 (ms) |")
    L.append("|---|---:|---:|")
    for setup in SETUPS:
        e = lat["end_to_end"][setup]
        L.append(f"| `{setup}` | {_f(e['p50'], '{:.1f}')} | {_f(e['p95'], '{:.1f}')} |")
    L.append("")

    # ----- Sezione nuova: trade-off rerank_top_k 20 vs 50 -----
    closed = agg["trade_off_20_vs_50"]["closed_by_50"]
    still_zero = agg["trade_off_20_vs_50"]["still_zero_50"]
    L.append("## Trade-off rerank_top_k: 20 vs 50")
    L.append("")
    L.append("Confronto sintetico fra i 4 setup:")
    L.append("")
    L.append("| Setup | R@5 | R@10 | MRR | NDCG@10 | e2e p50 (ms) |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        e = lat["end_to_end"][setup]
        L.append(f"| `{setup}` | {_f(a['r5'])} | {_f(a['r10'])} | "
                 f"{_f(a['mrr'])} | {_f(a['ndcg'])} | "
                 f"{_f(e['p50'], '{:.1f}')} |")
    L.append("")
    L.append(f"**Query che si chiudono passando rerank_top_k 20 → 50** "
             f"(R@10: 0 → >0): {len(closed)} su {agg['n_positive']}")
    L.append("")
    if closed:
        L.append("| qid | R@10 rrk_20 | R@10 rrk_50 |")
        L.append("|---|---:|---:|")
        for c in closed:
            L.append(f"| {c['qid']} | {_f(c['r10_20'])} | {_f(c['r10_50'])} |")
        L.append("")
    L.append(f"**Query positive che restano R@10=0 anche con rrk_50:** "
             f"{', '.join(still_zero) if still_zero else '—'}.")
    L.append("")
    L.append("Riferimento `zero_recall_diagnosis.md`: 4 query (Q13, Q34, Q35, Q39) "
             "avevano gold in hybrid top-50 ma fuori top-20 — atteso che rrk_50 le "
             "chiuda. Le restanti (Q15, Q19, Q24, Q30) hanno bug isolati (parser "
             "art_113, chunk annex_III monoblocco, vocabolario FRIA/scoring) o "
             "mismatch semantico cross-norma (Q24).")
    L.append("")

    # Verdetto finale aggiornato
    L.append("## Verdetto sintetico (aggiornato con rrk_50)")
    L.append("")
    L.append(f"- **Hybrid vs dense:** R@10 {_delta_f(hy['r10']-dn['r10'])}, "
             f"MRR {_delta_f(hy['mrr']-dn['mrr'])}, NDCG@10 {_delta_f(hy['ndcg']-dn['ndcg'])}.")
    L.append(f"- **rrk_20 vs hybrid:** R@10 {_delta_f(rk20['r10']-hy['r10'])}, "
             f"MRR {_delta_f(rk20['mrr']-hy['mrr'])}, NDCG@10 {_delta_f(rk20['ndcg']-hy['ndcg'])}.")
    L.append(f"- **rrk_50 vs rrk_20:** R@10 {_delta_f(rk50['r10']-rk20['r10'])}, "
             f"MRR {_delta_f(rk50['mrr']-rk20['mrr'])}, NDCG@10 {_delta_f(rk50['ndcg']-rk20['ndcg'])}.")
    target_hits = []
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        if (a['r10'] or 0) >= TARGETS['r10'] and (a['mrr'] or 0) >= TARGETS['mrr']:
            target_hits.append(setup)
    L.append(f"- **Target SCOPE (R@10 ≥ {TARGETS['r10']}, MRR ≥ {TARGETS['mrr']}):** "
             f"{'raggiunti da: ' + ', '.join(f'`{s}`' for s in target_hits) if target_hits else 'NESSUN setup li raggiunge entrambi'}.")
    lat_rk20 = lat["end_to_end"]["hybrid_rrk"]["p50"]
    lat_rk50 = lat["end_to_end"]["hybrid_rrk_50"]["p50"]
    L.append(f"- **Costo latenza p50 rrk_50:** {lat_rk50:.0f}ms (vs rrk_20 {lat_rk20:.0f}ms, "
             f"+{lat_rk50-lat_rk20:.0f}ms).")
    L.append("")
    L.append("**Default produttivo proposto:**")
    L.append("")
    L.append(f"- **LLM cloud (budget <3s totali, di SCOPE):** rrk_50 con p50 "
             f"{lat_rk50:.0f}ms{' lascia margine ~' + str(int(3000-lat_rk50)) + 'ms per la generazione cloud' if lat_rk50 < 3000 else ' SFORA il budget — usare rrk_20'}.")
    L.append(f"- **LLM locale (budget <5s totali):** rrk_50 lascia ~"
             f"{int(5000-lat_rk50)}ms al modello locale; con Qwen2.5-14B Q4_K_M su "
             "Mac M4 Pro la latenza di generazione è ~1.5-2.5s, quindi rientra. "
             "rrk_20 resta fallback se serve margine.")
    L.append("- Decisione definitiva al disegno serving runtime — `core/hybrid_retriever` "
             "espone già `rerank_top_k` come parametro dinamico.")
    L.append("")

    REPORT_MD.write_text("\n".join(L))


def print_summary(agg: dict) -> None:
    print("\n" + "=" * 70)
    print(f"BENCHMARK W3 ESTESO — 4 setup × {agg['n_positive']} positive")
    print("=" * 70)
    print(f"\n{'Setup':<16s} | {'R@5':>6s} | {'R@10':>6s} | {'MRR':>6s} | {'NDCG':>6s}")
    print("-" * 70)
    for setup in SETUPS:
        a = agg["per_setup"][setup]
        print(f"{setup:<16s} | {a['r5']:>6.3f} | {a['r10']:>6.3f} | "
              f"{a['mrr']:>6.3f} | {a['ndcg']:>6.3f}")
    print(f"\nLatency p50 reranker:")
    print(f"  rerank top-20 → top-10: {agg['latency']['rerank_top20']['p50']:.0f} ms")
    print(f"  rerank top-50 → top-10: {agg['latency']['rerank_top50']['p50']:.0f} ms")
    print(f"\nQuery chiuse da rrk_50 (R@10: 0 → >0): "
          f"{[c['qid'] for c in agg['trade_off_20_vs_50']['closed_by_50']]}")
    print(f"Query ancora a R@10=0: {agg['trade_off_20_vs_50']['still_zero_50']}")
    rk20 = agg["per_setup"]["hybrid_rrk"]
    rk50 = agg["per_setup"]["hybrid_rrk_50"]
    print(f"\nΔ R@10 aggregato rrk_50 vs rrk_20: +{(rk50['r10']-rk20['r10'])*100:.1f} pp")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["fetch", "report"], required=True)
    args = parser.parse_args()
    if args.phase == "fetch":
        return phase_fetch()
    return phase_rerank_and_report()


if __name__ == "__main__":
    sys.exit(main())
