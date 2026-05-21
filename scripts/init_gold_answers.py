"""Inizializza `data/benchmark/gold_answers_v1.json` per la curatela W7 (Ragas).

Pre-popola 50 entry — una per ciascuna query del benchmark — con:
- `question`, `qid`, `use_case`, `query_type`
- `gold_chunks` con testo COMPLETO recuperato da Qdrant (no troncamento)
- `gold_answer` vuoto (positive) oppure boilerplate "non contiene
  riferimenti sufficienti" (negative/edge senza gold)
- `review_status` "todo" oppure "reviewed" rispettivamente

NO chiamate LLM. NO retrieval. Solo assembly meccanico da
`gold_validated_v2.json` + retrieval per `point_id` su Qdrant.

Uso:
    spike/.venv/bin/python scripts/init_gold_answers.py
"""

from __future__ import annotations

import json
import logging
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.vector_store import (  # noqa: E402
    HYBRID_COLLECTION_NAME,
    chunk_id_to_point_id,
    get_client,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("init_gold_answers")

SRC = ROOT / "data" / "benchmark" / "gold_validated_v2.json"
OUT = ROOT / "data" / "benchmark" / "gold_answers_v1.json"

BOILERPLATE_NEGATIVE = (
    "Il contesto normativo fornito non contiene riferimenti sufficienti "
    "per rispondere con precisione."
)
NOTES_NEGATIVE = "Boilerplate negative/edge query, pre-compilato"


def main() -> int:
    if not SRC.is_file():
        raise FileNotFoundError(f"Sorgente non trovata: {SRC}")
    queries = json.loads(SRC.read_text(encoding="utf-8"))["queries"]
    log.info("Sorgente: %d query in %s", len(queries), SRC.name)

    # 1. raccogli chunk_id univoci marcati is_gold=True
    all_gold_ids: set[str] = set()
    for q in queries:
        for c in q.get("candidates", []):
            if c.get("is_gold"):
                all_gold_ids.add(c["chunk_id"])
    log.info("Chunk gold univoci da retrieve: %d", len(all_gold_ids))

    # 2. batch retrieve da Qdrant via point_id (uuid5 deterministico)
    client = get_client()
    id_to_chunk = {cid: chunk_id_to_point_id(cid) for cid in all_gold_ids}
    point_ids = list(id_to_chunk.values())
    points = client.retrieve(
        collection_name=HYBRID_COLLECTION_NAME,
        ids=point_ids,
        with_payload=True,
    )
    # mappa point_id (str) -> payload
    payload_by_pid = {str(p.id): p.payload for p in points}
    log.info("Retrieved da Qdrant: %d/%d punti", len(payload_by_pid), len(point_ids))

    # 3. sanity: nessun orfano
    missing = [cid for cid, pid in id_to_chunk.items() if pid not in payload_by_pid]
    if missing:
        raise RuntimeError(
            f"{len(missing)} chunk_id gold NON trovati in Qdrant "
            f"(orfani dal gold_validated_v2):\n  " + "\n  ".join(sorted(missing))
        )

    # 4. costruisci output
    output: list[dict] = []
    n_positive = n_negative = n_edge = 0
    for q in queries:
        gold_chunks_q = [c for c in q.get("candidates", []) if c.get("is_gold")]
        has_gold = bool(gold_chunks_q)
        expected_kind = q.get("expected_kind", "")

        # query_type: positive se ha gold (override expected_kind), altrimenti
        # propaga expected_kind. Edge senza gold → "edge"; negative → "negative".
        if has_gold:
            query_type = "positive"
            n_positive += 1
        elif expected_kind == "edge":
            query_type = "edge"
            n_edge += 1
        else:
            query_type = "negative"
            n_negative += 1

        if query_type == "positive":
            gold_chunks_out = [_build_chunk(c, payload_by_pid, id_to_chunk)
                               for c in gold_chunks_q]
            gold_answer = ""
            review_status = "todo"
            notes = ""
        else:
            gold_chunks_out = []
            gold_answer = BOILERPLATE_NEGATIVE
            review_status = "reviewed"
            notes = NOTES_NEGATIVE

        output.append({
            "qid": q["qid"],
            "use_case": q.get("use_case", ""),
            "query_type": query_type,
            "question": q["query"],
            "gold_chunks": gold_chunks_out,
            "gold_answer": gold_answer,
            "review_status": review_status,
            "notes": notes,
        })

    # 5. scrivi JSON
    OUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log.info("Scritto %s (%d entry)", OUT, len(output))

    # 6. summary + sanity
    _print_summary(output, n_positive, n_negative, n_edge, len(all_gold_ids))
    _validate_sanity(output)
    _print_sample_positive(output)

    return 0


def _build_chunk(
    candidate: dict,
    payload_by_pid: dict[str, dict],
    id_to_chunk: dict[str, str],
) -> dict:
    chunk_id = candidate["chunk_id"]
    pid = id_to_chunk[chunk_id]
    payload = payload_by_pid[pid]
    hierarchy = " > ".join(payload.get("hierarchy_path") or [])
    return {
        "chunk_id": chunk_id,
        "hierarchy": hierarchy,
        "text": payload.get("text") or "",
    }


def _print_summary(
    output: list[dict],
    n_positive: int,
    n_negative: int,
    n_edge: int,
    n_unique_chunks: int,
) -> None:
    text_lens = [
        len(c["text"]) for entry in output for c in entry["gold_chunks"]
    ]
    log.info("--- summary ---")
    log.info("Totale entry: %d", len(output))
    log.info("  positive (todo)    : %d", n_positive)
    log.info("  negative (reviewed): %d", n_negative)
    log.info("  edge (reviewed)    : %d", n_edge)
    log.info("Chunk univoci retrieved da Qdrant: %d", n_unique_chunks)
    if text_lens:
        log.info(
            "Lunghezza testo chunk (char): min=%d median=%d max=%d",
            min(text_lens), int(statistics.median(text_lens)), max(text_lens),
        )


def _validate_sanity(output: list[dict]) -> None:
    n_warn = 0
    for entry in output:
        for c in entry["gold_chunks"]:
            if not c["text"].strip():
                log.warning("text vuoto: %s in %s", c["chunk_id"], entry["qid"])
                n_warn += 1
            if not c["hierarchy"].strip():
                log.warning("hierarchy mancante: %s in %s", c["chunk_id"], entry["qid"])
                n_warn += 1
    if n_warn:
        log.warning("%d warning di sanity (text vuoto / hierarchy mancante)", n_warn)
    else:
        log.info("Sanity: tutti i chunk hanno text + hierarchy non vuoti")


def _print_sample_positive(output: list[dict]) -> None:
    sample = next((e for e in output if e["query_type"] == "positive"), None)
    if sample is None:
        return
    log.info("--- sample entry positive (%s) ---", sample["qid"])
    # tronca solo PER STAMPA (non per file), per leggibilità
    preview = json.loads(json.dumps(sample, ensure_ascii=False))
    for c in preview["gold_chunks"]:
        if len(c["text"]) > 200:
            c["text"] = c["text"][:200] + f"... [TRONCATO STAMPA, full {len(sample['gold_chunks'][0]['text'])} char nel file]"
    log.info("\n%s", json.dumps(preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
