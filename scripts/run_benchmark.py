"""Retrieval benchmark: dense-only top-10 against the 10 manually-validated queries.

Output: `data/benchmark/results.json` + stdout summary (per-query top-10, metrics).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.embedding import BgeM3Encoder  # noqa: E402
from core.vector_store import COLLECTION_NAME, get_client  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("run_benchmark")

GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated.json"
RESULTS_PATH = ROOT / "data" / "benchmark" / "results.json"
TOP_K = 10


def _recall_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int) -> float:
    if not gold_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = top_k & gold_ids
    return len(hits) / len(gold_ids)


def _mrr(retrieved_ids: list[str], gold_ids: set[str]) -> tuple[float, int | None]:
    """Reciprocal rank of the FIRST gold hit (1-indexed). 0 if none in top-k."""
    for i, cid in enumerate(retrieved_ids, start=1):
        if cid in gold_ids:
            return 1.0 / i, i
    return 0.0, None


def _truncate(s: str, n: int = 50) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> int:
    data = json.loads(GOLD_PATH.read_text())
    queries = data["queries"]

    print("Loading bge-m3 encoder + Qdrant client...", file=sys.stderr)
    encoder = BgeM3Encoder.get()
    client = get_client()

    info = client.get_collection(COLLECTION_NAME)
    n_indexed = info.points_count

    per_query: list[dict] = []
    print(f"\nRunning {len(queries)} queries against `{COLLECTION_NAME}` "
          f"({n_indexed} points)...\n", file=sys.stderr)

    for q in queries:
        query_text = q["query"]
        gold_ids = {c["chunk_id"] for c in q["candidates"] if c.get("is_gold")}

        [vec] = encoder.encode([query_text], batch_size=1)
        hits = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vec,
            limit=TOP_K,
            with_payload=True,
        ).points

        top_list: list[dict] = []
        retrieved_ids: list[str] = []
        for rank, h in enumerate(hits, start=1):
            cid = h.payload.get("chunk_id", "")
            ctype = h.payload.get("chunk_type", "")
            retrieved_ids.append(cid)
            top_list.append({
                "rank": rank,
                "chunk_id": cid,
                "score": round(float(h.score), 4),
                "is_gold": cid in gold_ids,
                "chunk_type": ctype,
            })

        entry: dict = {
            "qid": q["qid"],
            "query": query_text,
            "use_case": q["use_case"],
            "expected_kind": q["expected_kind"],
            "gold_chunk_ids": sorted(gold_ids),
            "top_10": top_list,
        }
        if q["expected_kind"] == "positive":
            entry["recall_at_5"] = round(_recall_at_k(retrieved_ids, gold_ids, 5), 4)
            entry["recall_at_10"] = round(_recall_at_k(retrieved_ids, gold_ids, 10), 4)
            mrr_val, first_rank = _mrr(retrieved_ids, gold_ids)
            entry["mrr"] = round(mrr_val, 4)
            entry["first_gold_rank"] = first_rank
        else:
            entry["recall_at_5"] = None
            entry["recall_at_10"] = None
            entry["mrr"] = None
            entry["first_gold_rank"] = None
        per_query.append(entry)

    # Aggregate metrics across positive queries only.
    positives = [e for e in per_query if e["expected_kind"] == "positive"]
    n_pos = len(positives)
    mean_r5 = sum(e["recall_at_5"] for e in positives) / n_pos
    mean_r10 = sum(e["recall_at_10"] for e in positives) / n_pos
    mean_mrr = sum(e["mrr"] for e in positives) / n_pos
    n_zero_r10 = sum(1 for e in positives if e["recall_at_10"] == 0.0)

    result: dict = {
        "config": {
            "collection": COLLECTION_NAME,
            "embedding_model": BgeM3Encoder.MODEL_NAME,
            "instruction_prefix_used": True,
            "top_k": TOP_K,
            "n_chunks_indexed": n_indexed,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "per_query": per_query,
        "aggregate": {
            "n_positive_queries": n_pos,
            "mean_recall_at_5": round(mean_r5, 4),
            "mean_recall_at_10": round(mean_r10, 4),
            "mean_mrr": round(mean_mrr, 4),
            "n_queries_with_zero_recall_at_10": n_zero_r10,
        },
    }
    RESULTS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    # ---------- stdout: per-query top-10 with GOLD flag ----------
    for e in per_query:
        print(f"{e['qid']} — {_truncate(e['use_case'], 60)}")
        for h in e["top_10"]:
            flag = "  [GOLD]" if h["is_gold"] else ""
            print(f"  rank {h['rank']:2d}: {h['chunk_id']:<70s}  score={h['score']:.3f}{flag}")
        print()

    # ---------- stdout: per-query metrics table ----------
    print("## Per-query metrics\n")
    print("| QID | Query (truncated)                              | Gold | Top-10 gold | R@5  | R@10 | MRR  | First gold rank |")
    print("|-----|------------------------------------------------|-----:|------------:|-----:|-----:|-----:|----------------:|")
    for e in per_query:
        if e["expected_kind"] != "positive":
            continue
        n_gold = len(e["gold_chunk_ids"])
        n_found = sum(1 for h in e["top_10"] if h["is_gold"])
        first = e["first_gold_rank"] if e["first_gold_rank"] is not None else "—"
        q_short = _truncate(e["query"], 46)
        print(f"| {e['qid']:3s} | {q_short:46s} | {n_gold:4d} | "
              f"{n_found:11d} | {e['recall_at_5']:.2f} | {e['recall_at_10']:.2f} | "
              f"{e['mrr']:.2f} | {str(first):>15s} |")

    print(f"\n## Aggregate (positive queries only, N={n_pos})\n")
    print(f"Mean Recall@5:  {mean_r5:.2f}")
    print(f"Mean Recall@10: {mean_r10:.2f}")
    print(f"Mean MRR:       {mean_mrr:.2f}")
    print(f"Queries with zero gold in top-10: {n_zero_r10}")

    # ---------- stdout: negative query ----------
    neg = [e for e in per_query if e["expected_kind"] == "negative"]
    if neg:
        print("\n## Negative query\n")
        for e in neg:
            print(f"{e['qid']} ({_truncate(e['use_case'], 60)}): "
                  f"{len(e['top_10'])}/{TOP_K} chunks retrieved "
                  f"(expected: low semantic match with corpus).")
            first3 = ", ".join(h["chunk_id"] for h in e["top_10"][:3])
            print(f"First 3 top results: {first3}")

    print(f"\nWrote {RESULTS_PATH.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
