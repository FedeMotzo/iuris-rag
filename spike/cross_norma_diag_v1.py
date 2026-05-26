"""Diagnostica retrieval per 7 query problematiche v1.0.

Retrieval-only (no generation, no judge). Riusa build_retriever da
run_pipeline_v2 con config produttiva v1.0:
- hybrid RRF + bge-reranker-v2-m3 su MPS
- top_k=20, rerank_top_k=20

Output: spike/CROSS_NORMA_DIAG_v1.md

    spike/.venv/bin/python spike/cross_norma_diag_v1.py
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("cross_norma_diag")

GOLD_PATH = ROOT / "data/benchmark/gold_answers_v3.json"
REPORT_PATH = ROOT / "spike/CROSS_NORMA_DIAG_v1.md"

TARGET_QIDS = ["Q5", "Q9", "Q25", "Q68", "Q69", "Q70", "Q71"]

NORM_PREFIXES = [
    ("eli/reg/2016/679/oj", "GDPR"),
    ("eli/reg/2024/1689/oj", "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


def short_title(question: str) -> str:
    return question.strip().rstrip("?").rstrip(".")[:80]


def main() -> int:
    from spike.run_pipeline_v2 import build_retriever

    entries = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    by_qid = {e["qid"]: e for e in entries}
    missing = [q for q in TARGET_QIDS if q not in by_qid]
    if missing:
        raise RuntimeError(f"qid mancanti in gold v3: {missing}")

    retriever = build_retriever("mps")

    sections: list[str] = []
    sections.append("# Cross-norma retrieval diagnosis — 7 query problematiche v1.0")
    sections.append("")
    sections.append(
        "Retrieval-only su config produttiva v1.0 "
        "(hybrid RRF + bge-reranker-v2-m3, top_k=20, rerank_top_k=20). "
        "Nessuna generation, nessun judge. Source gold: "
        "`data/benchmark/gold_answers_v3.json`."
    )
    sections.append("")

    for qid in TARGET_QIDS:
        entry = by_qid[qid]
        question = entry["question"]
        qtype = entry.get("query_type", "?")
        gold_ids = [g["chunk_id"] for g in entry.get("gold_chunks", []) if g.get("chunk_id")]
        gold_set = set(gold_ids)

        log.info("[%s] (%s) retrieving top-20…", qid, qtype)
        hits = retriever.retrieve(question, top_k=20, rerank_top_k=20)

        ranked = [(h.rank, h.chunk_id, float(h.score)) for h in hits]

        sec: list[str] = []
        sec.append(f"## {qid} — {short_title(question)}")
        sec.append("")
        sec.append(f"**Tipo query**: `{qtype}`")
        sec.append("")
        sec.append(f"**Query**: {question}")
        sec.append("")
        sec.append(f"**Gold attesi** ({len(gold_ids)} chunk):")
        if gold_ids:
            for cid in gold_ids:
                sec.append(f"- `{cid}`  _({norm_of(cid)})_")
        else:
            sec.append("- (nessuno: query `edge`/`negative`)")
        sec.append("")

        sec.append("**Top-20 retrieval** (config produttiva v1.0):")
        sec.append("")
        sec.append("| rank | chunk_id | score | gold? |")
        sec.append("|---:|---|---:|:---:|")
        for rank, cid, score in ranked:
            mark = "✓" if cid in gold_set else "-"
            sec.append(f"| {rank} | `{cid}` | {score:.4f} | {mark} |")
        sec.append("")

        # Gold position
        ranked_ids = [cid for _, cid, _ in ranked]
        if not gold_ids:
            sec.append("**Gold position**: n/a (gold vuoto)")
        else:
            positions = []
            for cid in gold_ids:
                if cid in ranked_ids:
                    positions.append(f"`{cid}` → rank {ranked_ids.index(cid) + 1}")
                else:
                    positions.append(f"`{cid}` → ASSENTE")
            sec.append("**Gold position**:")
            for line in positions:
                sec.append(f"- {line}")
        sec.append("")

        # Norme rappresentate nei top-20
        norm_counts = Counter(norm_of(cid) for _, cid, _ in ranked)
        sec.append("**Norme rappresentate nei top-20**:")
        for n, c in sorted(norm_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            sec.append(f"- {n}: {c}")
        sec.append("")

        sections.extend(sec)

    sections.append("## Pattern osservati")
    sections.append("")
    sections.append("_(da compilare manualmente dopo lettura dei dati)_")
    sections.append("")

    REPORT_PATH.write_text("\n".join(sections), encoding="utf-8")
    log.info("Report scritto: %s", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
