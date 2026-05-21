"""Smoke latenza BAAI/bge-reranker-v2-m3 su MPS — settimana 3.

Misura il tempo dello step di reranking su batch realistici (query reali +
top-k chunk recuperati da `italian_legal_v1`) per decidere se il reranker può
stare ON di default e con quale top-k.

Strategia memoria: bge-m3 e il reranker NON convivono in MPS.
1. Pre-fetch dei top-50 per le 5 query con bge-m3.
2. Drop completo di bge-m3 (`del model; torch.mps.empty_cache()`).
3. Salva (query_text, [text...]) su disco temporaneo.
4. Carica il reranker e misura.

Uso:
    spike/.venv/bin/python spike/smoke_reranker.py [--prefetched-only]

Prerequisito: Qdrant up + collection `italian_legal_v1` popolata.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import pickle
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("smoke_reranker")

COLLECTION = "italian_legal_v1"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated.json"
PREFETCH_CACHE = ROOT / "spike" / "_smoke_reranker_prefetch.pkl"

QUERY_IDS_TO_USE = ["Q1", "Q3", "Q5", "Q7", "Q9"]
TOP_KS = [10, 20, 50]
RUNS_PER_TOPK = 5
WARMUP_BATCHES = 3
WARMUP_PAIRS = 10

# Truncazione conservativa lato CPU: il modello tronca a 512 internamente, ma
# passare stringhe da 2000+ token costringe il tokenizer a fare lavoro inutile
# e tiene viva memoria di troppo. Tagliamo a ~2500 caratteri (~600-700 token
# legalese): garantisce che max_length=512 sia il vero collo.
TEXT_CHAR_CAP = 2500
RERANK_BATCH_SIZE = 8
RERANK_MAX_LENGTH = 512


# ---------------------------------------------------------------------------
# Fase 1: prefetch dei candidati con bge-m3 (poi scaricato)
# ---------------------------------------------------------------------------

def prefetch_candidates() -> dict[str, dict]:
    """Recupera top-50 dense per ciascuna query e scarica bge-m3.

    Ritorna {qid: {"query": str, "texts": list[str]}}.
    Salva su disco per poter riusare senza ricaricare bge-m3.
    """
    log.info("[Fase 1] Pre-fetch candidati con bge-m3 (poi scaricato)")
    import torch
    from qdrant_client import QdrantClient
    from core.embedding import BgeM3Encoder

    encoder = BgeM3Encoder.get()
    client = QdrantClient(host="localhost", port=6333)

    data = json.loads(GOLD_PATH.read_text())
    by_id = {q["qid"]: q for q in data["queries"]}

    out: dict[str, dict] = {}
    for qid in QUERY_IDS_TO_USE:
        q = by_id[qid]
        qtext = q["query"]
        [vec] = encoder.encode([qtext], batch_size=1)
        res = client.query_points(
            collection_name=COLLECTION,
            query=vec,
            limit=50,
            with_payload=["text"],
        )
        texts = [(p.payload.get("text") or "")[:TEXT_CHAR_CAP] for p in res.points]
        out[qid] = {"query": qtext, "texts": texts}
        log.info("  %s — %d candidati (text cap=%d char)", qid, len(texts), TEXT_CHAR_CAP)

    # --- scarica bge-m3 dalla memoria ---
    log.info("Drop bge-m3 dalla memoria MPS...")
    if encoder._model is not None:
        encoder._model.cpu()
        del encoder._model
        encoder._model = None
    BgeM3Encoder._singleton = None
    del encoder
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
        try:
            torch.mps.synchronize()
        except Exception:
            pass
    log.info("bge-m3 unloaded.")

    PREFETCH_CACHE.write_bytes(pickle.dumps(out))
    log.info("Prefetch salvato in %s", PREFETCH_CACHE)
    return out


# ---------------------------------------------------------------------------
# Fase 2: misure reranker
# ---------------------------------------------------------------------------

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


def run_reranker_smoke(prefetch: dict[str, dict]) -> int:
    import torch
    from sentence_transformers import CrossEncoder

    print("=" * 60)
    print(f"RERANKER LATENCY SMOKE — {RERANKER_MODEL} on MPS")
    print("=" * 60)

    mps_ok = torch.backends.mps.is_available()
    device = "mps" if mps_ok else "cpu"
    print(f"torch: {torch.__version__}")
    print(f"MPS available: {mps_ok}  →  using device={device}")
    print("Precision: float32  (MPS non supporta bene float16 al 2026)")
    print(f"Batch size predict: {RERANK_BATCH_SIZE}  |  max_length: {RERANK_MAX_LENGTH}")
    print(f"Text cap input: {TEXT_CHAR_CAP} char")

    # ---- carica reranker ----
    t0 = time.perf_counter()
    reranker = CrossEncoder(
        RERANKER_MODEL,
        device=device,
        max_length=RERANK_MAX_LENGTH,
    )
    # First predict piccolo per forzare il warmup interno (load lazy in alcune versioni).
    _ = reranker.predict(
        [("warmup", "warmup")],
        batch_size=RERANK_BATCH_SIZE,
        show_progress_bar=False,
    )
    if device == "mps":
        torch.mps.synchronize()
    load_time = time.perf_counter() - t0
    print(f"Model load + first-predict: {load_time:.2f} s")

    # ---- warmup vero ----
    print(f"\nWarmup: {WARMUP_BATCHES} batch da {WARMUP_PAIRS} pair (scartati)...")
    dummy = (
        "Documento di warmup. Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
        "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. " * 4
    )[:TEXT_CHAR_CAP]
    warmup_pairs = [("Query dummy di warmup", dummy)] * WARMUP_PAIRS
    for i in range(WARMUP_BATCHES):
        t = time.perf_counter()
        _ = reranker.predict(
            warmup_pairs,
            batch_size=RERANK_BATCH_SIZE,
            show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()
        log.info("  warmup batch %d/%d: %.0f ms", i + 1, WARMUP_BATCHES,
                 (time.perf_counter() - t) * 1000)

    # ---- misure ----
    print("\nMisure: 5 query × 3 top-k × 5 run = 75 misurazioni\n")
    results: dict[int, list[float]] = {k: [] for k in TOP_KS}
    per_query: dict[tuple[str, int], list[float]] = {}

    for qid in QUERY_IDS_TO_USE:
        if qid not in prefetch:
            continue
        qtext = prefetch[qid]["query"]
        all_texts = prefetch[qid]["texts"]
        for k in TOP_KS:
            pairs = [(qtext, t) for t in all_texts[:k]]
            samples: list[float] = []
            for run in range(RUNS_PER_TOPK):
                t = time.perf_counter()
                _ = reranker.predict(
                    pairs,
                    batch_size=RERANK_BATCH_SIZE,
                    show_progress_bar=False,
                )
                if device == "mps":
                    torch.mps.synchronize()
                dt_ms = (time.perf_counter() - t) * 1000
                samples.append(dt_ms)
            per_query[(qid, k)] = samples
            results[k].extend(samples)
            log.info("  %s top-%d: %s ms (p50=%.0f)",
                     qid, k,
                     [f"{x:.0f}" for x in samples],
                     percentile(samples, 0.5))
            if device == "mps":
                torch.mps.empty_cache()

    # ---- aggregati ----
    print("\n" + "=" * 60)
    print("Aggregato per top-k (25 misure ciascuno)")
    print("=" * 60)
    print(f"\n| top-k | p50 (ms) | p95 (ms) | p99 (ms) | mean (ms) | std (ms) |")
    print(f"|-------|----------|----------|----------|-----------|----------|")
    for k in TOP_KS:
        vs = results[k]
        p50 = percentile(vs, 0.5)
        p95 = percentile(vs, 0.95)
        p99 = percentile(vs, 0.99)
        mean = statistics.mean(vs)
        std = statistics.stdev(vs) if len(vs) > 1 else 0.0
        print(f"| {k:>5} | {p50:>8.1f} | {p95:>8.1f} | {p99:>8.1f} | "
              f"{mean:>9.1f} | {std:>8.1f} |")

    print("\nPer-query breakdown (top-20, 5 run each):")
    for qid in QUERY_IDS_TO_USE:
        if (qid, 20) not in per_query:
            continue
        samples = per_query[(qid, 20)]
        p50 = percentile(samples, 0.5)
        ms_list = [f"{x:.0f}" for x in samples]
        print(f"  {qid}: [{', '.join(ms_list)}] ms — p50={p50:.0f}")

    p50_20 = percentile(results[20], 0.5)
    print("\n" + "=" * 60)
    print("VERDETTO")
    print("=" * 60)
    print(f"p50 @ top-20: {p50_20:.0f} ms")
    if p50_20 < 500:
        print("→ DEFAULT ON top-20, sostenibile in tutti i deploy.")
    elif p50_20 < 1500:
        print("→ DEFAULT ON top-20 con cloud LLM, OPT-IN con local LLM.")
    else:
        print("→ DEFAULT OPT-IN. Valutare downgrade a bge-reranker-base o limitazione a top-10.")

    print("\nBudget di latenza per top-k (p50):")
    for k in TOP_KS:
        p50_k = percentile(results[k], 0.5)
        print(f"  top-{k:<2}: {p50_k:>6.0f} ms  ({p50_k/1000:.2f} s)")

    return 0


def main() -> int:
    use_cache = "--prefetched-only" in sys.argv
    if use_cache and PREFETCH_CACHE.exists():
        log.info("[Fase 1 saltata] Riuso prefetch da %s", PREFETCH_CACHE)
        prefetch = pickle.loads(PREFETCH_CACHE.read_bytes())
    else:
        prefetch = prefetch_candidates()

    # Garbage-collect aggressivo prima di caricare il reranker
    gc.collect()

    rc = run_reranker_smoke(prefetch)

    # Cleanup file prefetch a fine run
    try:
        os.remove(PREFETCH_CACHE)
    except FileNotFoundError:
        pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
