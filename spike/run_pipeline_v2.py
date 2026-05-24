"""Phase F.1 pipeline run su gold_answers_v2.json (100 query).

Per ciascuna delle 100 query:
- retrieval ibrido (BM25 + bge-m3 + RRF + bge-reranker-v2-m3) top-20
- generazione Sonnet 4.6 (top-5 chunk via RAGPipeline serving)
- compute R@5 / R@10 / R@20 / MRR vs gold_chunks
- salvataggio incrementale (rewrite cumulativo ad ogni query) per
  resilienza ai crash

Output:
- data/benchmark/ragas_pipeline_outputs_v2.json (schema compatibile
  con `spike/run_ragas_eval.py --judge`)
- spike/BENCHMARK_W3_v2.md (report W3-style con aggregati)

REQUISITI: dipendenze identiche a smoke_rag_pipeline.py.
LLM_PROVIDER=anthropic obbligatorio. Reranker su MPS (topologia S1).

    spike/.venv/bin/python spike/run_pipeline_v2.py
    spike/.venv/bin/python spike/run_pipeline_v2.py --limit 10   # dry-run
    spike/.venv/bin/python spike/run_pipeline_v2.py --skip-existing

Modalità dev (subset 20 query, output su path *_subset.* per non
sovrascrivere gli artefatti F.2 archived):

    spike/.venv/bin/python spike/run_pipeline_v2.py \
        --subset data/benchmark/subset_dev.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("pipeline_v2")

GOLD_PATH = ROOT / "data/benchmark/gold_answers_v2.json"
OUTPUTS_PATH = ROOT / "data/benchmark/ragas_pipeline_outputs_v2.json"
REPORT_PATH = ROOT / "spike/BENCHMARK_W3_v2.md"

COLLECTION = "italian_legal_v1_hybrid"
BM25_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

NORM_PREFIXES = [
    ("eli/reg/2016/679/oj", "GDPR"),
    ("eli/reg/2024/1689/oj", "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]

CORPUS_LIMIT_RE = re.compile(
    r"non\s+(?:è\s+|sono\s+|sia\s+|siano\s+)?(?:inclus[oaie]|present[eai])"
    r".{0,40}corpus(?:\s+normativo)?(?:\s+di\s+riferimento)?",
    re.IGNORECASE | re.DOTALL,
)


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


def build_retriever(reranker_device: str):
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL)
    log.info("Reranker device=%s", reranker_device)
    reranker = CrossEncoder(RERANKER_MODEL, device=reranker_device, max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=COLLECTION, reranker=reranker,
    )


def compute_recall_mrr(gold_ids: set[str], ranked_ids: list[str]) -> dict:
    """Retrieval metrics per una singola query.

    Per query con gold vuoto (negative), recall e MRR non sono
    applicabili → None.
    """
    if not gold_ids:
        return {"recall_at_5": None, "recall_at_10": None,
                "recall_at_20": None, "mrr": None}
    n_gold = len(gold_ids)
    top5 = set(ranked_ids[:5])
    top10 = set(ranked_ids[:10])
    top20 = set(ranked_ids[:20])
    rec5 = len(gold_ids & top5) / n_gold
    rec10 = len(gold_ids & top10) / n_gold
    rec20 = len(gold_ids & top20) / n_gold
    mrr = 0.0
    for i, cid in enumerate(ranked_ids[:20], start=1):
        if cid in gold_ids:
            mrr = 1.0 / i
            break
    return {"recall_at_5": rec5, "recall_at_10": rec10,
            "recall_at_20": rec20, "mrr": mrr}


def write_outputs_atomic(payload: dict) -> None:
    tmp = OUTPUTS_PATH.with_suffix(".json.partial")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(OUTPUTS_PATH)


def step_run(limit: int | None, skip_existing: bool,
             subset: set[str] | None = None) -> tuple[list[dict], dict]:
    """Esegue retrieval + generation per ciascuna entry, salva incrementale."""
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)

    provider = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider != "anthropic":
        raise RuntimeError(
            f"Pipeline run F.1 cloud-only (provider=anthropic). "
            f"Trovato LLM_PROVIDER={provider!r}."
        )

    entries = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise RuntimeError("gold_answers_v2.json non è una lista pura")
    if subset is None and len(entries) != 100:
        raise RuntimeError(f"atteso 100 entry, trovato {len(entries)}")
    log.info("Caricate %d entry da %s", len(entries), GOLD_PATH.name)

    if subset is not None:
        entries = [e for e in entries if e["qid"] in subset]
        missing = subset - {e["qid"] for e in entries}
        if missing:
            raise RuntimeError(f"qid del subset non presenti in dataset: {sorted(missing)}")
        log.info("SUBSET attivo → %d entry filtrate (%s)",
                 len(entries), ",".join(e["qid"] for e in entries))

    if limit:
        entries = entries[:limit]
        log.info("LIMIT=%d → eseguo solo le prime %d entry", limit, limit)

    # carico outputs esistenti se skip_existing
    existing: dict[str, dict] = {}
    if skip_existing and OUTPUTS_PATH.is_file():
        prev = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
        for o in prev.get("outputs", []):
            existing[o["qid"]] = o
        log.info("Skip-existing: %d output già in cache", len(existing))

    from core.serving import build_default_pipeline

    retriever = build_retriever("mps")
    pipeline = build_default_pipeline(retriever)

    outputs: list[dict] = []
    setup_meta = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "anthropic",
        "model": pipeline._llm.model_name,
        "topology": "S1 reranker MPS",
        "top_k": pipeline._top_k,
        "rerank_top_k": pipeline._rerank_top_k,
        "use_graph": pipeline.use_graph,
        "max_output_tokens": pipeline._max_tokens,
        "collection": COLLECTION,
        "n_queries_input": len(entries),
    }

    for idx, entry in enumerate(entries, start=1):
        qid = entry["qid"]
        if qid in existing:
            outputs.append(existing[qid])
            log.info("[%d/%d] %s skipped (cached)", idx, len(entries), qid)
            continue

        question = entry["question"]
        gold_ids = {g["chunk_id"] for g in entry.get("gold_chunks", []) if g.get("chunk_id")}
        log.info("[%d/%d] %s: %s", idx, len(entries), qid, question[:80])

        # Retrieval top-20 (rerank_top_k=20, top_k=20 → restituisce 20 hit con rank)
        t_ret = time.perf_counter()
        try:
            ret_top20 = retriever.retrieve(question, top_k=20, rerank_top_k=20)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Retrieval fallito su {qid}: {exc}") from exc
        ret_ms = (time.perf_counter() - t_ret) * 1000

        ranked_ids = [h.chunk_id for h in ret_top20]
        retrieved_chunks = [
            {
                "rank": h.rank,
                "chunk_id": h.chunk_id,
                "score": float(h.score),
                "hierarchy": " > ".join(h.payload.get("hierarchy_path") or []),
                "is_gold": h.chunk_id in gold_ids,
            }
            for h in ret_top20
        ]

        # Generation via pipeline (top_k=5 default)
        t_gen = time.perf_counter()
        try:
            resp = pipeline.query(question)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Pipeline fallita su {qid}: {exc}") from exc
        gen_ms = (time.perf_counter() - t_gen) * 1000

        contexts = []
        for h in resp.retrieval_result[: pipeline._top_k]:
            txt = (h.payload.get("text") or "").strip()
            contexts.append(txt)

        metrics = compute_recall_mrr(gold_ids, ranked_ids)

        out = {
            "qid": qid,
            "query_type": entry["query_type"],
            "question": question,
            "gold_chunks": entry.get("gold_chunks", []),
            "retrieved_chunks": retrieved_chunks,
            "contexts": contexts,
            "answer": resp.annotated_answer,
            "ground_truth": entry.get("gold_answer", ""),
            "has_corpus_limit_declaration": entry.get("has_corpus_limit_declaration", False),
            "runtime_corpus_limit_observed": entry.get("runtime_corpus_limit_observed", False),
            "use_case": entry.get("use_case", ""),
            **metrics,
            "timings_ms": {
                "retrieval_ms": ret_ms,
                "generate_ms": gen_ms,
                "n_output_tokens": resp.generation_meta.n_output_tokens,
                "finish_reason": resp.generation_meta.finish_reason,
            },
        }
        outputs.append(out)

        # Save incrementale ad ogni query
        write_outputs_atomic({
            "metadata": setup_meta,
            "outputs": outputs,
        })

        rec10_s = "n/a" if metrics["recall_at_10"] is None else f"{metrics['recall_at_10']:.2f}"
        log.info("[%s] R@10=%s out_tok=%d ret=%.0fms gen=%.0fms",
                 qid, rec10_s, resp.generation_meta.n_output_tokens, ret_ms, gen_ms)

    setup_meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    setup_meta["n_queries_completed"] = len(outputs)
    write_outputs_atomic({"metadata": setup_meta, "outputs": outputs})
    return outputs, setup_meta


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def write_report(outputs: list[dict], meta: dict) -> None:
    """Genera spike/BENCHMARK_W3_v2.md."""
    positives = [o for o in outputs if o["query_type"] == "positive"]
    negatives_edge = [o for o in outputs if o["query_type"] in ("negative", "edge")]

    def stats_block(rows: list[dict]) -> dict:
        rec5 = [r["recall_at_5"] for r in rows if r["recall_at_5"] is not None]
        rec10 = [r["recall_at_10"] for r in rows if r["recall_at_10"] is not None]
        rec20 = [r["recall_at_20"] for r in rows if r["recall_at_20"] is not None]
        mrr = [r["mrr"] for r in rows if r["mrr"] is not None]
        return {
            "n": len(rows),
            "r5_med": _median(rec5),
            "r10_med": _median(rec10),
            "r20_med": _median(rec20),
            "mrr_med": _median(mrr),
            "n_r10_eq_1": sum(1 for r in rec10 if r == 1.0),
            "n_r10_eq_0": sum(1 for r in rec10 if r == 0.0),
        }

    glob = stats_block(outputs)
    pos = stats_block(positives)

    # negative+edge: comportamento dichiarazione di limite
    neg_with_pattern = []
    neg_substantive = []
    for o in negatives_edge:
        ans = o["answer"]
        if CORPUS_LIMIT_RE.search(ans):
            neg_with_pattern.append(o["qid"])
        else:
            # heuristic: risposta > 200 char e senza pattern = sostanziale
            if len(ans.strip()) > 200:
                neg_substantive.append(o["qid"])

    # runtime corpus_limit observed (flag=false ma pattern presente)
    runtime_limit_observed = []
    for o in positives:
        if not o["has_corpus_limit_declaration"]:
            if CORPUS_LIMIT_RE.search(o["answer"]):
                runtime_limit_observed.append(o["qid"])

    # has_corpus_limit_declaration=true ma pattern non presente (drift lessicale)
    drift_lessicale = []
    for o in positives:
        if o["has_corpus_limit_declaration"]:
            if not CORPUS_LIMIT_RE.search(o["answer"]):
                drift_lessicale.append(o["qid"])

    # per norma toccata (sui gold_chunks)
    by_norm: dict[str, list[float]] = defaultdict(list)
    for o in outputs:
        if o["recall_at_10"] is None:
            continue
        norms = {norm_of(g["chunk_id"]) for g in o["gold_chunks"]} - {"?"}
        for n in norms:
            by_norm[n].append(o["recall_at_10"])

    # v1 vs v2 (Q1-50 vs Q51-100)
    v1_pos = [o for o in positives if int(o["qid"][1:]) <= 50]
    v2_pos = [o for o in positives if int(o["qid"][1:]) > 50]
    v1_stats = stats_block(v1_pos) if v1_pos else None
    v2_stats = stats_block(v2_pos) if v2_pos else None

    # paired queries dal design v2 (hardcoded dai metadata fase C)
    paired = {
        "art_38__paras_1_11 NIS2 sanzioni": ("Q55", "Q83"),
        "NIS2 art_25 notifica": ("Q54", "Q57"),
        "L.132 art_9 trattamento dati": ("Q64", "Q67"),
    }

    L: list[str] = []
    L.append("# BENCHMARK W3 v2 — pipeline outputs su gold_answers_v2.json")
    L.append("")
    L.append(f"**Start (UTC):** {meta.get('started_utc','?')}")
    L.append(f"**End (UTC):** {meta.get('finished_utc','?')}")
    L.append(f"**Provider:** {meta.get('provider')} · model: `{meta.get('model')}`")
    L.append(f"**Pipeline params:** top_k={meta.get('top_k')}, "
             f"rerank_top_k={meta.get('rerank_top_k')}, "
             f"use_graph={meta.get('use_graph')}, "
             f"max_output_tokens={meta.get('max_output_tokens')}.")
    L.append(f"**Reranker device:** MPS (topologia S1). Collection: `{meta.get('collection')}`.")
    L.append("")

    L.append("## 1. Sintesi globale (100 query)")
    L.append("")
    L.append("| metrica | mediana |")
    L.append("|---|---:|")
    L.append(f"| R@5 (su query con gold)  | {glob['r5_med']:.3f} |")
    L.append(f"| R@10 (su query con gold) | {glob['r10_med']:.3f} |")
    L.append(f"| R@20 (su query con gold) | {glob['r20_med']:.3f} |")
    L.append(f"| MRR (su query con gold)  | {glob['mrr_med']:.3f} |")
    L.append(f"| n query con R@10=1.0     | {glob['n_r10_eq_1']} |")
    L.append(f"| n query con R@10=0.0     | {glob['n_r10_eq_0']} |")
    L.append("")

    L.append("## 2. Per query_type")
    L.append("")
    L.append("| type | n | R@5 | R@10 | R@20 | MRR | n R@10=1 | n R@10=0 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    L.append(f"| positive | {pos['n']} | {pos['r5_med']:.3f} | {pos['r10_med']:.3f} | {pos['r20_med']:.3f} | {pos['mrr_med']:.3f} | {pos['n_r10_eq_1']} | {pos['n_r10_eq_0']} |")
    L.append(f"| negative+edge | {len(negatives_edge)} | — | — | — | — | — | — |")
    L.append("")
    L.append(f"- Negative+edge con pattern canonico 'corpus_limit' nella answer: **{len(neg_with_pattern)} / {len(negatives_edge)}** → {neg_with_pattern}")
    L.append(f"- Negative+edge con risposta sostantiva (>200 char, no pattern): **{len(neg_substantive)}** → {neg_substantive}")
    L.append("")

    L.append("## 3. Per cluster v2 (Q51-Q100)")
    L.append("")
    by_uc: dict[str, list[float]] = defaultdict(list)
    by_uc_mrr: dict[str, list[float]] = defaultdict(list)
    for o in v2_pos:
        if o["recall_at_10"] is None:
            continue
        by_uc[o["use_case"]].append(o["recall_at_10"])
        if o["mrr"] is not None:
            by_uc_mrr[o["use_case"]].append(o["mrr"])
    L.append("Aggregati per use_case (proxy del cluster). Soglia outlier: R@10 mediana < globale - 0.20.")
    L.append("")
    L.append("| use_case | n | R@10 med | MRR med |")
    L.append("|---|---:|---:|---:|")
    threshold = max(0.0, pos["r10_med"] - 0.20)
    outliers: list[tuple[str, float]] = []
    for uc in sorted(by_uc.keys()):
        rec = by_uc[uc]
        mrr = by_uc_mrr.get(uc, [])
        m_rec = _median(rec)
        m_mrr = _median(mrr)
        flag = " ⚠ outlier" if m_rec < threshold else ""
        L.append(f"| {uc[:50]} | {len(rec)} | {m_rec:.3f} | {m_mrr:.3f} |{flag}")
        if m_rec < threshold:
            outliers.append((uc, m_rec))
    L.append("")
    if outliers:
        L.append(f"**Outlier identificati ({len(outliers)})**: " + ", ".join(f"`{u}` ({r:.2f})" for u, r in outliers))
        L.append("")

    L.append("## 4. Per norma toccata")
    L.append("")
    L.append("| norma | n query | R@10 med |")
    L.append("|---|---:|---:|")
    for n in sorted(by_norm.keys()):
        L.append(f"| {n} | {len(by_norm[n])} | {_median(by_norm[n]):.3f} |")
    L.append("")

    L.append("## 5. Confronto v1 (Q1-Q50) vs v2 (Q51-Q100)")
    L.append("")
    if v1_stats and v2_stats:
        L.append("| metrica | v1 (n positive) | v2 (n positive) | cumulato |")
        L.append("|---|---:|---:|---:|")
        L.append(f"| R@5 med | {v1_stats['r5_med']:.3f} ({v1_stats['n']}) | {v2_stats['r5_med']:.3f} ({v2_stats['n']}) | {pos['r5_med']:.3f} |")
        L.append(f"| R@10 med | {v1_stats['r10_med']:.3f} | {v2_stats['r10_med']:.3f} | {pos['r10_med']:.3f} |")
        L.append(f"| R@20 med | {v1_stats['r20_med']:.3f} | {v2_stats['r20_med']:.3f} | {pos['r20_med']:.3f} |")
        L.append(f"| MRR med | {v1_stats['mrr_med']:.3f} | {v2_stats['mrr_med']:.3f} | {pos['mrr_med']:.3f} |")
        L.append("")
        L.append("Nota drift: confronto vs `BENCHMARK_W3.md` (W7-prep) per pipeline drift. Se R@10 v1 attuale differisce >0.05 da W3-prep → indagare.")
    else:
        L.append("Run parziale: v1 o v2 manca, confronto non producibile.")
    L.append("")

    L.append("## 6. Paired queries intenzionali")
    L.append("")
    L.append("| Tema | qid coppia | R@10 entrambi | answer differente? |")
    L.append("|---|---|---|---|")
    by_qid = {o["qid"]: o for o in outputs}
    for theme, (qa, qb) in paired.items():
        a = by_qid.get(qa)
        b = by_qid.get(qb)
        if not a or not b:
            L.append(f"| {theme} | {qa},{qb} | n/a (qid non in run) | n/a |")
            continue
        r_a = a["recall_at_10"]
        r_b = b["recall_at_10"]
        r_str = f"{r_a:.2f} / {r_b:.2f}"
        diff = "sì" if a["answer"][:200] != b["answer"][:200] else "no (sospetto)"
        L.append(f"| {theme} | {qa},{qb} | {r_str} | {diff} |")
    L.append("")

    L.append("## 7. Runtime corpus_limit observed (post-eval)")
    L.append("")
    L.append(f"Query positive con `has_corpus_limit_declaration=false` ma pattern canonico presente nella answer: **{len(runtime_limit_observed)} / {len(positives)}**")
    L.append("")
    if runtime_limit_observed:
        L.append("Lista qid (candidati v1.1 per flag update):")
        for q in runtime_limit_observed:
            L.append(f"- `{q}` — use_case: {by_qid[q].get('use_case','')[:60]}")
    L.append("")
    L.append(f"Drift lessicale (has_corpus_limit_declaration=true ma pattern canonico non rilevato): **{len(drift_lessicale)}**")
    if drift_lessicale:
        L.append("Lista qid:")
        for q in drift_lessicale:
            L.append(f"- `{q}` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex")
    L.append("")

    L.append("**Decisione**: pattern documentato qui, dataset `gold_answers_v2.json` non aggiornato. Eventuale fix runtime_corpus_limit_observed in v1.1.")
    L.append("")

    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    log.info("Report scritto: %s", REPORT_PATH)

    return {
        "globals": glob,
        "positives": pos,
        "v1_stats": v1_stats,
        "v2_stats": v2_stats,
        "runtime_limit_observed": runtime_limit_observed,
        "drift_lessicale": drift_lessicale,
        "outliers": outliers,
        "neg_with_pattern": neg_with_pattern,
        "neg_substantive": neg_substantive,
    }


def main() -> int:
    global OUTPUTS_PATH, REPORT_PATH
    parser = argparse.ArgumentParser(description="Phase F.1 pipeline run su 100 query v2")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limita alle prime N query (dry-run / smoke). Applicato dopo --subset.")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Salta qid già presenti in outputs_v2.json.")
    parser.add_argument("--subset", type=str, default=None,
                        help="Path YAML con lista qids (chiave 'qids'). "
                             "Filtra il dataset e devia gli output su path *_subset.* "
                             "per non sovrascrivere gli artefatti F.2 archived.")
    args = parser.parse_args()

    subset_qids: set[str] | None = None
    if args.subset:
        import yaml
        subset_path = Path(args.subset)
        if not subset_path.is_absolute():
            subset_path = ROOT / subset_path
        with subset_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        subset_qids = set(data["qids"])
        OUTPUTS_PATH = ROOT / "data/benchmark/ragas_pipeline_outputs_v2_subset.json"
        REPORT_PATH = ROOT / "spike/BENCHMARK_W3_v2_subset.md"
        log.info("Subset mode: %d qid da %s → output %s",
                 len(subset_qids), subset_path.name, OUTPUTS_PATH.name)

    outputs, meta = step_run(limit=args.limit, skip_existing=args.skip_existing,
                             subset=subset_qids)
    log.info("Pipeline run completato: %d output", len(outputs))

    summary = write_report(outputs, meta)
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"n outputs: {len(outputs)}")
    g = summary["globals"]
    print(f"R@5 med={g['r5_med']:.3f}  R@10={g['r10_med']:.3f}  "
          f"R@20={g['r20_med']:.3f}  MRR={g['mrr_med']:.3f}")
    print(f"runtime_corpus_limit_observed: {len(summary['runtime_limit_observed'])} "
          f"({summary['runtime_limit_observed']})")
    print(f"outliers cluster (R@10 < soglia): {len(summary['outliers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
