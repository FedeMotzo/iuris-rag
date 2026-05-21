"""Diagnostica retrieval Q5 — confronto gold attuali vs gold proposti.

Esegue Q5 in 3 modalità (dense / hybrid / hybrid_rrk20) sul retriever
standard. Per ciascuna stampa top-10 con flag GOLD ATTUALE / GOLD
PROPOSTO. Niente modifiche ai dati, sola lettura.

Uso:
    spike/.venv/bin/python scripts/diagnose_q5_retrieval.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("diag_q5")

QUERY_TEXT = (
    "L'uso di sistemi AI per decisioni che riguardano i lavoratori può "
    "attivare responsabilità ai sensi del D.Lgs 231/2001?"
)

GOLD_PROPOSED = {
    "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis",
    "akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167",
    "eli/reg/2016/679/oj__art_22",
}

GOLD_PATH = ROOT / "data/benchmark/gold_validated_v2.json"
REPORT_PATH = ROOT / "spike/Q5_RETRIEVAL_DIAG.md"


def load_q5_current_gold() -> set[str]:
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    q5 = next(q for q in data["queries"] if q["qid"] == "Q5")
    return {c["chunk_id"] for c in q5.get("candidates", []) if c.get("is_gold")}


def build_retriever_with_reranker():
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME, get_client

    log.info("Carico bge-m3 (MPS) + bm25 + reranker (CPU per coabitazione)")
    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="cpu", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = get_client()
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=HYBRID_COLLECTION_NAME, reranker=reranker,
    )


def run_mode(retriever, mode: str, rerank_top_k: int | None):
    if mode in ("dense", "hybrid"):
        return list(retriever.retrieve(
            query=QUERY_TEXT, top_k=10, mode=mode, rerank_top_k=None,
        ))
    # hybrid_rrk
    return list(retriever.retrieve(
        query=QUERY_TEXT, top_k=10, mode="hybrid", rerank_top_k=rerank_top_k,
    ))


def format_table(
    hits, current_gold: set[str], proposed: set[str],
) -> tuple[list[str], dict[str, int | None]]:
    """Ritorna (righe testuali, dict {chunk_id -> rank o None per proposed})."""
    lines: list[str] = []
    lines.append("| rank | score   | chunk_id                                                                  | hierarchy | flag |")
    lines.append("|------|---------|---------------------------------------------------------------------------|-----------|------|")
    proposed_rank: dict[str, int | None] = {cid: None for cid in proposed}
    current_rank: dict[str, int | None] = {cid: None for cid in current_gold}
    for h in hits:
        flag_parts = []
        if h.chunk_id in current_gold:
            flag_parts.append("GOLD ATTUALE")
            current_rank[h.chunk_id] = h.rank
        if h.chunk_id in proposed:
            flag_parts.append("GOLD PROPOSTO")
            proposed_rank[h.chunk_id] = h.rank
        flag = "; ".join(flag_parts) or ""
        hier = " > ".join(h.payload.get("hierarchy_path") or [])
        hier_short = hier if len(hier) <= 60 else hier[:57] + "..."
        cid_short = h.chunk_id if len(h.chunk_id) <= 70 else h.chunk_id[:67] + "..."
        lines.append(
            f"| {h.rank:>4} | {h.score:7.4f} | {cid_short:<73} | {hier_short} | {flag} |"
        )
    return lines, {"current": current_rank, "proposed": proposed_rank}


def main() -> int:
    current_gold = load_q5_current_gold()
    log.info("Gold attuali Q5 (is_gold=true in gold_validated_v2): %s", sorted(current_gold))
    log.info("Gold proposti (da curatela): %s", sorted(GOLD_PROPOSED))

    retriever = build_retriever_with_reranker()

    out: list[str] = []
    out.append("# Diagnostica retrieval Q5")
    out.append("")
    out.append(f"**Query**: `{QUERY_TEXT}`")
    out.append("")
    out.append(f"**Gold attuali** (is_gold=true in `gold_validated_v2.json`):")
    out.append("")
    for cid in sorted(current_gold):
        out.append(f"- `{cid}`")
    out.append("")
    out.append(f"**Gold proposti** (da curatela manuale):")
    out.append("")
    for cid in sorted(GOLD_PROPOSED):
        out.append(f"- `{cid}`")
    out.append("")

    rank_summary: dict[str, dict] = {}
    for mode_label, mode, rerank_top_k in [
        ("dense", "dense", None),
        ("hybrid", "hybrid", None),
        ("hybrid_rrk20", "hybrid_rrk", 20),
    ]:
        log.info("=== %s ===", mode_label)
        hits = run_mode(retriever, mode, rerank_top_k)
        lines, ranks = format_table(hits, current_gold, GOLD_PROPOSED)
        rank_summary[mode_label] = ranks

        out.append(f"## Modalità: `{mode_label}`")
        out.append("")
        out.extend(lines)
        out.append("")
        # summary per modalità
        n_cur_in = sum(1 for r in ranks["current"].values() if r is not None)
        n_pro_in = sum(1 for r in ranks["proposed"].values() if r is not None)
        out.append(
            f"**Summary `{mode_label}`**: gold attuali nei top-10 = "
            f"**{n_cur_in}/{len(current_gold)}** · gold proposti nei top-10 = "
            f"**{n_pro_in}/{len(GOLD_PROPOSED)}**"
        )
        out.append("")
        out.append("Rank per ciascun gold proposto:")
        for cid in sorted(GOLD_PROPOSED):
            r = ranks["proposed"][cid]
            out.append(f"- `{cid}` → {f'rank {r}' if r else 'fuori top-10'}")
        out.append("")

        log.info("  gold attuali in top-10: %d/%d", n_cur_in, len(current_gold))
        log.info("  gold proposti in top-10: %d/%d", n_pro_in, len(GOLD_PROPOSED))

    # verdetto su hybrid_rrk20 (config produttiva default)
    rrk = rank_summary["hybrid_rrk20"]["proposed"]
    n_in = sum(1 for r in rrk.values() if r is not None)

    out.append("## Verdetto preliminare")
    out.append("")
    if n_in >= 2:
        verdict = (
            f"**{n_in}/3 gold proposti nei top-10 di hybrid_rrk20**. "
            "Fix annotazione probabilmente sufficiente: Q5 può uscire da "
            "zero-recall col solo aggiornamento dei flag `is_gold` in "
            "`gold_validated_v2.json`, senza toccare retriever/parser."
        )
    elif n_in == 1:
        out_cid = [cid for cid, r in rrk.items() if r is None]
        verdict = (
            f"**1/3 gold proposti nei top-10 di hybrid_rrk20**. Fix "
            "annotazione parziale: Q5 esce da zero-recall ma con R@10 ≈ 0.33. "
            f"Indagine residua su retrieval o parser per gli altri 2 chunk: "
            f"{', '.join(f'`{c}`' for c in sorted(out_cid))}."
        )
    else:
        verdict = (
            "**0/3 gold proposti nei top-10 di hybrid_rrk20**. Fix "
            "annotazione corregge la pertinenza giuridica ma Q5 resta "
            "zero-recall: il retrieval non vede i chunk proposti. Problema "
            "separato di retrieval / parser / chunking / vocabolario da "
            "diagnosticare prima di ri-annotare il gold."
        )
    out.append(verdict)
    out.append("")

    report = "\n".join(out)
    print(report)
    REPORT_PATH.write_text(report + "\n", encoding="utf-8")
    log.info("Report salvato in %s", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
