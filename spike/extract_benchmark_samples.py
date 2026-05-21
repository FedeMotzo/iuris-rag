"""Extract 8 representative entries from gold_answers_v1.json.

Output: `data/benchmark/gold_answers_v1_sample_for_v2.json` con 8 entry
selezionate per insegnare lo stile target del benchmark a un LLM in
fresh context (generazione query candidate v2).

Le 8 qid sono selezionate per coprire pattern stilistici diversi:
- Q6, Q1   → positive standard, retrieval pulito
- Q9, Q43  → positive con dichiarazione di limite corpus
- Q3, Q19  → cross-norma
- Q47      → negative (articolo inesistente)
- Q45      → edge (query vaga L. 132/2025)

    spike/.venv/bin/python spike/extract_benchmark_samples.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data/benchmark/gold_answers_v1.json"
OUTPUT_PATH = ROOT / "data/benchmark/gold_answers_v1_sample_for_v2.json"

SELECTED_QIDS = ["Q1", "Q3", "Q6", "Q9", "Q19", "Q43", "Q45", "Q47"]


def main() -> int:
    data = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    by_qid = {e["qid"]: e for e in data}

    missing = [qid for qid in SELECTED_QIDS if qid not in by_qid]
    if missing:
        raise RuntimeError(
            f"qid attese non trovate in {SOURCE_PATH}: {missing}"
        )

    samples = [by_qid[qid] for qid in SELECTED_QIDS]
    payload = {
        "metadata": {
            "purpose": "Sample entries per chat fresh-context generazione v2",
            "selected_qids": SELECTED_QIDS,
            "date": "2026-05-20",
        },
        "samples": samples,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Scritto {OUTPUT_PATH} con {len(samples)} entry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
