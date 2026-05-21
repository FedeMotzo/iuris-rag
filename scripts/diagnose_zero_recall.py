"""Diagnostica zero-recall — 8 query positive del benchmark W3.

Per ognuna delle 8 query con R@10=0 in tutti i 3 setup:
- Verifica esistenza dei chunk_id gold (STEP 1)
- Stampa testo completo dei gold esistenti (STEP 2)
- Retrieval esteso top-50 in 3 setup (STEP 3)
- Verdetto categoria a/b/c/d (STEP 4)

Due fasi separate (processi distinti per liberare MPS fra encoder e reranker):

    spike/.venv/bin/python scripts/diagnose_zero_recall.py --phase=fetch
    spike/.venv/bin/python scripts/diagnose_zero_recall.py --phase=report

Output: data/benchmark/zero_recall_diagnosis.md
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("diagnose_zero_recall")

GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated_v2.json"
INTERMEDIATE = ROOT / "data" / "benchmark" / "_zero_recall_phase1.pkl"
REPORT_MD = ROOT / "data" / "benchmark" / "zero_recall_diagnosis.md"

ZERO_QIDS = ["Q13", "Q15", "Q19", "Q24", "Q30", "Q34", "Q35", "Q39"]
TOP_K_DIAG = 50
RERANK_BATCH_SIZE = 8
RERANK_MAX_LENGTH = 512
TEXT_CHAR_CAP = 2500


# ---------------------------------------------------------------------------
# Phase 1 — fetch all 858 chunk_ids + payload for gold + retrieval top-50 × 2
# ---------------------------------------------------------------------------

def phase_fetch() -> int:
    import torch
    from fastembed import SparseTextEmbedding
    from qdrant_client import models

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME, get_client

    log.info("Phase 1 FETCH — diagnostica zero-recall su %d query", len(ZERO_QIDS))

    client = get_client()
    info = client.get_collection(HYBRID_COLLECTION_NAME)
    log.info("Collection %s: %d points", HYBRID_COLLECTION_NAME, info.points_count)

    # 1) Scroll full collection: collect chunk_id set + payload by chunk_id
    log.info("Scroll completo collection per indice chunk_id → payload...")
    all_chunks: dict[str, dict] = {}
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=HYBRID_COLLECTION_NAME,
            limit=200,
            offset=offset,
            with_payload=True,
        )
        for p in points:
            cid = p.payload.get("chunk_id", "")
            if cid:
                all_chunks[cid] = p.payload
        if offset is None:
            break
    log.info("Indicizzati %d chunk_id locali", len(all_chunks))

    # 2) Load gold dal JSON
    gold_data = json.loads(GOLD_PATH.read_text())
    qs_by_qid = {q["qid"]: q for q in gold_data["queries"]}

    # 3) Per ciascuna query: lookup gold + retrieval top-50 dense/hybrid
    encoder = BgeM3Encoder.get()
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    retriever = HybridRetriever(client, encoder, bm25, HYBRID_COLLECTION_NAME)

    diagnostics = []
    for qid in ZERO_QIDS:
        q = qs_by_qid[qid]
        gold_ids = [c["chunk_id"] for c in q["candidates"] if c.get("is_gold")]

        # STEP 1 — esistenza + prefix-search
        gold_status: list[dict] = []
        for gid in gold_ids:
            exists = gid in all_chunks
            entry = {"chunk_id": gid, "exists": exists}
            if exists:
                payload = all_chunks[gid]
                entry["payload"] = {
                    "chunk_type": payload.get("chunk_type"),
                    "hierarchy_path": payload.get("hierarchy_path"),
                    "text": payload.get("text", ""),
                }
            else:
                # prefix-search: chunk_id che iniziano con article_eid del gold
                # Costruisco il prefix = gold + "__" per evitare match troppo larghi.
                prefix_candidates = [
                    cid for cid in all_chunks
                    if cid.startswith(gid + "__") or cid == gid
                ]
                # Inoltre, prova un prefix più largo se il gold è del tipo
                # `{urn}__art_N` e magari il chunker ha sub-chunkato:
                # ad es. gold=`...__art_9` → cerca `...__art_9__paras_...`
                entry["prefix_candidates"] = sorted(prefix_candidates)
            gold_status.append(entry)

        # STEP 3 — retrieval top-50 dense + hybrid
        t0 = time.perf_counter()
        dense_hits = retriever.retrieve(q["query"], top_k=TOP_K_DIAG, mode="dense")
        t_dense = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        hybrid_hits = retriever.retrieve(q["query"], top_k=TOP_K_DIAG, mode="hybrid")
        t_hybrid = (time.perf_counter() - t0) * 1000

        diagnostics.append({
            "qid": qid,
            "query": q["query"],
            "use_case": q["use_case"],
            "gold_status": gold_status,
            "dense_top50": [
                {"rank": h.rank, "chunk_id": h.chunk_id, "score": float(h.score),
                 "hierarchy_path": h.payload.get("hierarchy_path")}
                for h in dense_hits
            ],
            "hybrid_top50": [
                {"rank": h.rank, "chunk_id": h.chunk_id, "score": float(h.score),
                 "hierarchy_path": h.payload.get("hierarchy_path"),
                 "text": (h.payload.get("text") or "")[:TEXT_CHAR_CAP]}
                for h in hybrid_hits
            ],
            "latency_ms": {"dense": t_dense, "hybrid": t_hybrid},
        })
        log.info("  %s done (gold=%d, dense top-50 OK, hybrid top-50 OK)",
                 qid, len(gold_ids))

    INTERMEDIATE.write_bytes(pickle.dumps(diagnostics))
    log.info("Phase 1 done. Saved to %s", INTERMEDIATE.name)

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
# Phase 2 — rerank top-50 (hybrid) + write markdown
# ---------------------------------------------------------------------------

def phase_report() -> int:
    import torch
    from sentence_transformers import CrossEncoder

    if not INTERMEDIATE.exists():
        raise RuntimeError(f"Pickle intermedio mancante: {INTERMEDIATE}. "
                           "Esegui prima `--phase=fetch`.")
    diagnostics = pickle.loads(INTERMEDIATE.read_bytes())
    log.info("Phase 2 — caricamento reranker per rerank top-50 hybrid")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    reranker = CrossEncoder(
        "BAAI/bge-reranker-v2-m3", device=device, max_length=RERANK_MAX_LENGTH,
    )
    # Warmup
    for _ in range(3):
        reranker.predict(
            [("warmup", "warmup")] * 10,
            batch_size=RERANK_BATCH_SIZE, show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()

    # Rerank each query's hybrid top-50
    for d in diagnostics:
        candidates = d["hybrid_top50"]
        if not candidates:
            d["rrk_top50"] = []
            continue
        pairs = [(d["query"], c["text"]) for c in candidates]
        scores = reranker.predict(
            pairs, batch_size=RERANK_BATCH_SIZE, show_progress_bar=False,
        )
        if device == "mps":
            torch.mps.synchronize()
        scored = sorted(
            zip(candidates, scores, strict=True),
            key=lambda hs: float(hs[1]),
            reverse=True,
        )
        d["rrk_top50"] = [
            {"rank": i + 1, "chunk_id": c["chunk_id"], "score": float(s),
             "hierarchy_path": c["hierarchy_path"]}
            for i, (c, s) in enumerate(scored)
        ]
        log.info("  %s rerank done", d["qid"])

    # Strip text dai hybrid_top50 prima del report
    for d in diagnostics:
        for c in d["hybrid_top50"]:
            c.pop("text", None)

    write_report(diagnostics)
    log.info("Wrote %s", REPORT_MD.relative_to(ROOT))

    print_summary(diagnostics)
    return 0


# ---------------------------------------------------------------------------
# Verdetto categoria + summary
# ---------------------------------------------------------------------------

def classify(gold_status: list[dict], dense_top50, hybrid_top50, rrk_top50) -> str:
    """Categoria principale per la query.

    Nota sul rrk: nel benchmark W3 `rerank_top_k=20`, qui invece il reranker
    vede top-50 — più candidati significa che il reranker può recuperare gold
    che nel benchmark non avrebbe mai visto. Il verdetto NEAR_MISS si basa
    sulle posizioni in dense/hybrid (le viste senza rerank), allineate al
    benchmark; le posizioni rrk del diagnostico sono informative ma non
    direttamente confrontabili con il benchmark.
    """
    # (a) Almeno un gold non esiste → GOLD_NOT_EXIST
    if any(not g["exists"] for g in gold_status):
        return "(a) GOLD_NOT_EXIST"

    def rank_of(gid, hits):
        for h in hits:
            if h["chunk_id"] == gid:
                return h["rank"]
        return None

    # Rank per gold in dense e hybrid (no rrk, vedi docstring)
    min_rank_no_rrk = None
    for g in gold_status:
        ranks = [rank_of(g["chunk_id"], dense_top50),
                 rank_of(g["chunk_id"], hybrid_top50)]
        ranks = [r for r in ranks if r is not None]
        if ranks:
            r = min(ranks)
            if min_rank_no_rrk is None or r < min_rank_no_rrk:
                min_rank_no_rrk = r

    if min_rank_no_rrk is None:
        return "(b) GOLD_EXIST_BUT_NOT_RETRIEVED"
    if min_rank_no_rrk > 10:
        # Sotto-tag: indica anche se il rrk top-50 lo avrebbe recuperato
        # (= aumentare rerank_top_k chiude il fail).
        rrk_min = None
        for g in gold_status:
            r = rank_of(g["chunk_id"], rrk_top50)
            if r is not None and (rrk_min is None or r < rrk_min):
                rrk_min = r
        suffix = ""
        if rrk_min is not None and rrk_min <= 10:
            suffix = f" — rrk_top50 lo promuove a rank {rrk_min} → fix: rerank_top_k≥{min_rank_no_rrk}"
        return f"(d) GOLD_NEAR_MISS{suffix}"
    # min_rank_no_rrk ≤ 10 — non dovrebbe succedere per zero-recall query
    return "(?) IN_TOP10_BUT_BENCHMARK_R10=0 — riverificare"


def _rank_of(cid: str, hits: list[dict]) -> int | None:
    for h in hits:
        if h["chunk_id"] == cid:
            return h["rank"]
    return None


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(diagnostics: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# Diagnostica zero-recall benchmark W3")
    lines.append("")
    lines.append("**Data:** 2026-05-19")
    lines.append("**Soggetto:** 8 query positive con R@10=0 in tutti e 3 i setup "
                 "(dense, hybrid, hybrid_rrk) — vedi `BENCHMARK_W3.md`.")
    lines.append(f"**Top-K diagnostico:** {TOP_K_DIAG} (esteso rispetto al benchmark "
                 "per misurare 'quanto fuori' è il gold).")
    lines.append("")

    summary_rows = []

    for d in diagnostics:
        qid = d["qid"]
        lines.append(f"## {qid} — {d['use_case']}")
        lines.append("")
        lines.append(f"**Query:** {d['query']!r}")
        lines.append("")

        # STEP 1 + 2
        lines.append("### STEP 1 — Esistenza chunk_id gold")
        lines.append("")
        for g in d["gold_status"]:
            if g["exists"]:
                lines.append(f"- ✓ `{g['chunk_id']}` — esiste")
            else:
                lines.append(f"- ✗ `{g['chunk_id']}` — **NON ESISTE** nella collection")
                if g.get("prefix_candidates"):
                    lines.append(f"  - Candidati con prefix simile: "
                                 f"{', '.join(f'`{c}`' for c in g['prefix_candidates'])}")
                else:
                    lines.append("  - Nessun chunk_id con prefix simile trovato.")
        lines.append("")

        # STEP 2 — text completo dei gold esistenti
        lines.append("### STEP 2 — Testo dei gold esistenti")
        lines.append("")
        any_exists = False
        for g in d["gold_status"]:
            if not g["exists"]:
                continue
            any_exists = True
            p = g["payload"]
            lines.append(f"**`{g['chunk_id']}`** (`{p['chunk_type']}`, hierarchy: "
                         f"{p['hierarchy_path']})")
            lines.append("")
            lines.append("```")
            lines.append(p["text"][:1500])
            if len(p["text"]) > 1500:
                lines.append(f"... [troncato; lunghezza totale {len(p['text'])} char]")
            lines.append("```")
            lines.append("")
        if not any_exists:
            lines.append("_Nessun gold esiste, niente da mostrare._")
            lines.append("")

        # STEP 3 — rank dei gold nei 3 setup + top-5
        lines.append("### STEP 3 — Rank dei gold nei top-50 per setup")
        lines.append("")
        lines.append("| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |")
        lines.append("|---|---:|---:|---:|")
        for g in d["gold_status"]:
            gid = g["chunk_id"]
            r_dense = _rank_of(gid, d["dense_top50"])
            r_hybrid = _rank_of(gid, d["hybrid_top50"])
            r_rrk = _rank_of(gid, d["rrk_top50"])
            f = lambda r: str(r) if r is not None else "fuori top-50"
            lines.append(f"| `{gid}` | {f(r_dense)} | {f(r_hybrid)} | {f(r_rrk)} |")
        lines.append("")

        # Top-5 per setup
        lines.append("**Top-5 effettivi recuperati**")
        lines.append("")
        for setup, hits in [("dense", d["dense_top50"]),
                            ("hybrid", d["hybrid_top50"]),
                            ("hybrid_rrk", d["rrk_top50"])]:
            lines.append(f"_{setup}_:")
            for h in hits[:5]:
                hp = h.get("hierarchy_path") or []
                hp_str = " → ".join(hp[-2:]) if hp else "—"
                lines.append(f"  - rank {h['rank']}: `{h['chunk_id']}` "
                             f"(score {h['score']:.4f}, {hp_str})")
            lines.append("")

        # STEP 4 — verdetto
        verdict = classify(d["gold_status"], d["dense_top50"],
                           d["hybrid_top50"], d["rrk_top50"])
        lines.append(f"### STEP 4 — Verdetto: **{verdict}**")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Per summary
        n_gold = len(d["gold_status"])
        n_exist = sum(1 for g in d["gold_status"] if g["exists"])
        # rank by ANY gold appearing in any setup
        best_dense = min((r for r in [_rank_of(g["chunk_id"], d["dense_top50"])
                                       for g in d["gold_status"]]
                          if r is not None), default=None)
        best_hyb = min((r for r in [_rank_of(g["chunk_id"], d["hybrid_top50"])
                                     for g in d["gold_status"]]
                        if r is not None), default=None)
        best_rrk = min((r for r in [_rank_of(g["chunk_id"], d["rrk_top50"])
                                     for g in d["gold_status"]]
                        if r is not None), default=None)
        summary_rows.append({
            "qid": qid, "n_gold": n_gold, "n_exist": n_exist,
            "rank_dense": best_dense, "rank_hyb": best_hyb,
            "rank_rrk": best_rrk, "verdict": verdict,
            "d": d,
        })

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| qid | gold_count | esistono | rank_dense | rank_hybrid | rank_rrk | verdetto |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for s in summary_rows:
        f = lambda r: str(r) if r is not None else "—"
        lines.append(f"| {s['qid']} | {s['n_gold']} | {s['n_exist']}/{s['n_gold']} "
                     f"| {f(s['rank_dense'])} | {f(s['rank_hyb'])} | "
                     f"{f(s['rank_rrk'])} | {s['verdict']} |")
    lines.append("")

    # Suggested fixes
    fix_rows = [s for s in summary_rows
                if "(a)" in s["verdict"] or "(c)" in s["verdict"]]
    if fix_rows:
        lines.append("## Suggested fixes (verdetti a / c)")
        lines.append("")
        for s in fix_rows:
            d = s["d"]
            lines.append(f"### {s['qid']} — {s['verdict']}")
            lines.append("")
            for g in d["gold_status"]:
                if g["exists"]:
                    continue
                lines.append(f"`{g['chunk_id']}` non esiste.")
                if g.get("prefix_candidates"):
                    lines.append("")
                    lines.append("**Suggested fix in `NEW_GOLD[\"" + s['qid'] + "\"]`:**")
                    lines.append("")
                    lines.append(f"- Rimuovi: `\"{g['chunk_id']}\"`")
                    lines.append("- Aggiungi:")
                    for c in g["prefix_candidates"]:
                        lines.append(f"  - `\"{c}\"`")
                else:
                    lines.append("Nessun chunk_id con prefix simile: probabile typo, "
                                 "ispezione manuale.")
                lines.append("")
            lines.append("")
    else:
        lines.append("## Suggested fixes")
        lines.append("")
        lines.append("_Nessun verdetto (a) o (c): nessun fix automatico da proporre. "
                     "I fail di tipo (b) richiedono indagine separata "
                     "(indicizzazione o pattern semantico)._")
        lines.append("")

    REPORT_MD.write_text("\n".join(lines))


def print_summary(diagnostics: list[dict]) -> None:
    from collections import Counter
    print("\n" + "=" * 70)
    print("DIAGNOSI ZERO-RECALL — 8 query positive del benchmark W3")
    print("=" * 70)
    print(f"\n{'qid':<5s} | {'n_gold':>6s} | {'esiste':>8s} | "
          f"{'rank_d':>7s} | {'rank_h':>7s} | {'rank_r':>7s} | verdetto")
    print("-" * 90)
    verdicts = Counter()
    for d in diagnostics:
        gold_status = d["gold_status"]
        n_gold = len(gold_status)
        n_exist = sum(1 for g in gold_status if g["exists"])
        bd = min((r for r in [_rank_of(g["chunk_id"], d["dense_top50"])
                              for g in gold_status] if r is not None), default=None)
        bh = min((r for r in [_rank_of(g["chunk_id"], d["hybrid_top50"])
                              for g in gold_status] if r is not None), default=None)
        br = min((r for r in [_rank_of(g["chunk_id"], d["rrk_top50"])
                              for g in gold_status] if r is not None), default=None)
        verdict = classify(gold_status, d["dense_top50"], d["hybrid_top50"],
                           d["rrk_top50"])
        verdicts[verdict] += 1
        f = lambda r: str(r) if r is not None else "—"
        print(f"{d['qid']:<5s} | {n_gold:>6d} | {n_exist}/{n_gold:<5d} | "
              f"{f(bd):>7s} | {f(bh):>7s} | {f(br):>7s} | {verdict}")
    print("\nDistribuzione verdetti:")
    for v, n in verdicts.most_common():
        print(f"  {n}× {v}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["fetch", "report"], required=True)
    args = parser.parse_args()
    if args.phase == "fetch":
        return phase_fetch()
    return phase_report()


if __name__ == "__main__":
    sys.exit(main())
