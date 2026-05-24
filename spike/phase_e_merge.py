"""Phase E merge — v1 (Q1-Q50) + v2_curated (Q51-Q100) → gold_answers_v2.json.

Step 1: validazione input (count, schema, qid non sovrapposti).
Step 2: lookup Qdrant per popolare hierarchy + text in gold_chunks v2.
Step 3: schema consistency check (10 campi, qid unici, pattern citazione,
        pattern corpus_limit).
Step 4: statistiche aggregate.
Step 5: scrivi `data/benchmark/gold_answers_v2.json` + report.

    spike/.venv/bin/python spike/phase_e_merge.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spike.corpus_limit_regex import CORPUS_LIMIT_RE  # noqa: E402

V1_PATH = ROOT / "data/benchmark/gold_answers_v1.json"
V2_CURATED_PATH = ROOT / "data/benchmark/candidates_v2_curated.json"
OUTPUT_PATH = ROOT / "data/benchmark/gold_answers_v2.json"
REPORT_PATH = ROOT / "spike/PHASE_E_MERGE_REPORT.md"
DEBUG_PATH = ROOT / "spike/_phase_e_merge_debug.json"

COLLECTION = "italian_legal_v1_hybrid"

EXPECTED_FIELDS = {
    "qid", "use_case", "query_type", "question", "gold_chunks",
    "gold_answer", "review_status", "has_corpus_limit_declaration",
    "runtime_corpus_limit_observed", "notes",
}

NORM_PREFIXES = [
    ("eli/reg/2016/679/oj", "GDPR"),
    ("eli/reg/2024/1689/oj", "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]

CITE_RE = re.compile(r"\[cite:([^\]]+)\]")
CITE_ATTACHED_RE = re.compile(r"\[cite:[^\]]+\]\[cite:")


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


def load_inputs() -> tuple[list[dict], list[dict], dict]:
    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))
    v2_wrapper = json.loads(V2_CURATED_PATH.read_text(encoding="utf-8"))
    v2 = v2_wrapper["entries"]
    v2_meta = v2_wrapper["metadata"]
    return v1, v2, v2_meta


def step1_validate(v1: list[dict], v2: list[dict]) -> list[str]:
    errs: list[str] = []
    if len(v1) != 50:
        errs.append(f"v1 ha {len(v1)} entry, atteso 50")
    if len(v2) != 50:
        errs.append(f"v2_curated ha {len(v2)} entry, atteso 50")

    for label, dataset in [("v1", v1), ("v2_curated", v2)]:
        for i, e in enumerate(dataset):
            keys = set(e.keys())
            missing = EXPECTED_FIELDS - keys
            extra = keys - EXPECTED_FIELDS
            if missing:
                errs.append(f"{label}[{i}] qid={e.get('qid')} chiavi mancanti: {sorted(missing)}")
            if extra:
                errs.append(f"{label}[{i}] qid={e.get('qid')} chiavi extra: {sorted(extra)}")

    v1_qids = {e["qid"] for e in v1}
    v2_qids = {e["qid"] for e in v2}
    overlap = v1_qids & v2_qids
    if overlap:
        errs.append(f"qid sovrapposti v1/v2: {sorted(overlap)}")

    expected_v1 = {f"Q{i}" for i in range(1, 51)}
    expected_v2 = {f"Q{i}" for i in range(51, 101)}
    if v1_qids != expected_v1:
        errs.append(f"v1 qid set ≠ atteso Q1-Q50; diff: {sorted((v1_qids ^ expected_v1))[:5]}")
    if v2_qids != expected_v2:
        errs.append(f"v2 qid set ≠ atteso Q51-Q100; diff: {sorted((v2_qids ^ expected_v2))[:5]}")

    return errs


def fetch_qdrant_payloads(chunk_ids: set[str]) -> dict[str, dict]:
    from qdrant_client import QdrantClient
    try:
        client = QdrantClient(host="localhost", port=6333, timeout=10.0)
        if not client.collection_exists(COLLECTION):
            raise RuntimeError(f"Collection {COLLECTION} non esiste")
    except Exception as exc:
        raise RuntimeError(f"Qdrant non raggiungibile: {exc}") from exc

    out: dict[str, dict] = {}
    offset = None
    while True:
        pts, offset = client.scroll(
            COLLECTION, limit=512, offset=offset,
            with_payload=["chunk_id", "hierarchy_path", "text"],
            with_vectors=False,
        )
        for p in pts:
            cid = p.payload.get("chunk_id")
            if cid in chunk_ids:
                hier = " > ".join(p.payload.get("hierarchy_path") or [])
                out[cid] = {
                    "hierarchy": hier,
                    "text": p.payload.get("text") or "",
                }
        if offset is None:
            break
    return out


def step2_populate_v2(v2: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Popola hierarchy + text per ogni chunk_id in gold_chunks v2."""
    required = set()
    for e in v2:
        for g in e["gold_chunks"]:
            required.add(g["chunk_id"])

    print(f"Step 2: chunk_id da popolare: {len(required)}")
    payloads = fetch_qdrant_payloads(required)
    print(f"        chunk_id popolati: {len(payloads)} / {len(required)}")

    missing = sorted(required - set(payloads.keys()))
    if missing:
        print(f"        MISSING: {missing}")

    populated = 0
    for e in v2:
        for g in e["gold_chunks"]:
            p = payloads.get(g["chunk_id"])
            if p:
                g["hierarchy"] = p["hierarchy"]
                g["text"] = p["text"]
                populated += 1

    stats = {
        "required": len(required),
        "populated": len(payloads),
        "missing": len(missing),
        "missing_ids": missing,
        "chunk_dicts_populated": populated,
    }
    return v2, stats


def step3_schema_consistency(all_entries: list[dict]) -> dict:
    """Step 3 checks."""
    results: dict = {
        "checks": [], "errors": [], "warnings": [],
    }

    # 1. schema
    bad_schema = []
    for e in all_entries:
        keys = set(e.keys())
        if keys != EXPECTED_FIELDS:
            bad_schema.append((e.get("qid"), sorted(keys - EXPECTED_FIELDS), sorted(EXPECTED_FIELDS - keys)))
    results["checks"].append(("schema 10 campi", len(all_entries) - len(bad_schema), len(bad_schema)))
    if bad_schema:
        results["errors"].extend([f"schema {q}: extra={ex} missing={ms}" for q, ex, ms in bad_schema])

    # 2. qid uniqueness
    qids = [e["qid"] for e in all_entries]
    dups = [q for q, n in Counter(qids).items() if n > 1]
    results["checks"].append(("qid uniqueness", 100 - len(dups), len(dups)))
    if dups:
        results["errors"].append(f"qid duplicati: {dups}")

    # 3. query_type valido
    bad_type = [(e["qid"], e["query_type"]) for e in all_entries
                if e["query_type"] not in ("positive", "negative", "edge")]
    results["checks"].append(("query_type valido", 100 - len(bad_type), len(bad_type)))
    if bad_type:
        results["errors"].extend([f"{q}: query_type={t!r}" for q, t in bad_type])

    # 4-5. gold_chunks per tipo
    bad_gold = []
    bad_chunk_fields = []
    for e in all_entries:
        qt = e["query_type"]
        gc = e["gold_chunks"]
        if qt == "positive":
            if not gc:
                bad_gold.append(f"{e['qid']} positive senza gold_chunks")
                continue
            for i, g in enumerate(gc):
                if not g.get("chunk_id"):
                    bad_chunk_fields.append(f"{e['qid']} chunk[{i}] senza chunk_id")
                # hierarchy può essere vuota se hierarchy_path è vuoto (es. recital)
                # ma text deve essere popolato
                if not g.get("text"):
                    bad_chunk_fields.append(f"{e['qid']} chunk[{i}] {g.get('chunk_id')} senza text")
        # negative+edge: gold_chunks può essere [] o popolato, tutto ok
    results["checks"].append(("positive con gold_chunks", 100 - len(bad_gold), len(bad_gold)))
    results["checks"].append(("chunk text popolato", 100 - len(bad_chunk_fields), len(bad_chunk_fields)))
    if bad_gold:
        results["errors"].extend(bad_gold)
    if bad_chunk_fields:
        results["errors"].extend(bad_chunk_fields[:10])
        if len(bad_chunk_fields) > 10:
            results["errors"].append(f"(altri {len(bad_chunk_fields)-10} chunk con campi vuoti)")

    # 6. pattern canonico corpus_limit
    bad_pattern = []
    for e in all_entries:
        if e["has_corpus_limit_declaration"]:
            if not CORPUS_LIMIT_RE.search(e["gold_answer"]):
                bad_pattern.append(e["qid"])
    results["checks"].append(("pattern canonico corpus_limit",
                              sum(1 for e in all_entries if e["has_corpus_limit_declaration"]) - len(bad_pattern),
                              len(bad_pattern)))
    if bad_pattern:
        results["warnings"].append(f"has_corpus_limit_declaration=true ma pattern non trovato: {bad_pattern}")

    # 7. pattern citazione
    bad_cite = []
    for e in all_entries:
        qt = e["query_type"]
        gc = e["gold_chunks"]
        ga = e["gold_answer"]
        cites = CITE_RE.findall(ga)
        if qt == "positive" and gc and not cites:
            bad_cite.append(f"{e['qid']} positive con gold_chunks ma 0 citazioni")
        if qt == "negative" and not gc and cites:
            bad_cite.append(f"{e['qid']} negative senza gold_chunks ma {len(cites)} citazioni nella risposta")
        if CITE_ATTACHED_RE.search(ga):
            bad_cite.append(f"{e['qid']}: citazioni attaccate senza spazio [cite:X][cite:Y]")
    results["checks"].append(("pattern citazione", 100 - len(bad_cite), len(bad_cite)))
    if bad_cite:
        results["warnings"].extend(bad_cite)

    return results


def step4_statistics(all_entries: list[dict], v2_meta: dict) -> dict:
    """Statistiche aggregate."""
    v1 = [e for e in all_entries if int(e["qid"][1:]) <= 50]
    v2 = [e for e in all_entries if int(e["qid"][1:]) > 50]

    def block(dataset: list[dict]) -> dict:
        qt = Counter(e["query_type"] for e in dataset)
        hcl = Counter(bool(e["has_corpus_limit_declaration"]) for e in dataset)
        norms: Counter = Counter()
        for e in dataset:
            seen = set()
            for g in e["gold_chunks"]:
                n = norm_of(g.get("chunk_id", ""))
                if n != "?":
                    seen.add(n)
            for n in seen:
                norms[n] += 1
        # query_type × has_corpus_limit_declaration
        cross: Counter = Counter()
        for e in dataset:
            cross[(e["query_type"], bool(e["has_corpus_limit_declaration"]))] += 1
        return {
            "n": len(dataset),
            "query_type": dict(qt),
            "has_corpus_limit": {"true": hcl[True], "false": hcl[False]},
            "norms_touched": dict(norms),
            "cross": {f"{k[0]}_limit={k[1]}": v for k, v in cross.items()},
        }

    return {
        "v1": block(v1),
        "v2": block(v2),
        "cumulato": block(all_entries),
        "paired_queries": v2_meta.get("curation_summary", {}).get("design_intentional_paired_queries", {}),
    }


def write_report(step1_errs: list[str], step2_stats: dict,
                 step3_results: dict, step4_stats: dict) -> None:
    L: list[str] = []
    L.append("# Phase E merge report — gold_answers_v2.json")
    L.append("")
    L.append("Data: 2026-05-20.")
    L.append("Sorgenti: `data/benchmark/gold_answers_v1.json` (Q1-Q50) + `data/benchmark/candidates_v2_curated.json` (Q51-Q100).")
    L.append("Output: `data/benchmark/gold_answers_v2.json` (100 entry).")
    L.append("")

    L.append("## Step 1 — Validazione input")
    if not step1_errs:
        L.append("✅ OK. 50+50 entry, schema identico (10 campi), qid Q1-Q50 + Q51-Q100 non sovrapposti.")
    else:
        L.append("❌ FAIL:")
        for e in step1_errs:
            L.append(f"- {e}")
    L.append("")

    L.append("## Step 2 — Lookup Qdrant (popolamento hierarchy + text v2)")
    L.append(f"- chunk_id unici richiesti: **{step2_stats['required']}**")
    L.append(f"- chunk_id popolati: **{step2_stats['populated']}**")
    L.append(f"- chunk_id missing: **{step2_stats['missing']}**")
    if step2_stats['missing']:
        L.append("\nMissing:")
        for m in step2_stats['missing_ids']:
            L.append(f"  - `{m}`")
    L.append(f"- gold_chunks dict popolati end-to-end: **{step2_stats['chunk_dicts_populated']}**")
    L.append("")

    L.append("## Step 3 — Schema consistency")
    L.append("")
    L.append("| Check | pass | fail |")
    L.append("|---|---:|---:|")
    for name, p, f in step3_results["checks"]:
        L.append(f"| {name} | {p} | {f} |")
    L.append("")
    if step3_results["errors"]:
        L.append("### Errori critici")
        for e in step3_results["errors"]:
            L.append(f"- {e}")
        L.append("")
    if step3_results["warnings"]:
        L.append("### Warning (non bloccanti)")
        for w in step3_results["warnings"]:
            L.append(f"- {w}")
        L.append("")
    if not step3_results["errors"] and not step3_results["warnings"]:
        L.append("Nessun errore o warning.")
        L.append("")

    L.append("## Step 4 — Statistiche aggregate")
    L.append("")
    L.append("### query_type")
    L.append("| dataset | positive | negative | edge | totale |")
    L.append("|---|---:|---:|---:|---:|")
    for k in ("v1", "v2", "cumulato"):
        d = step4_stats[k]
        qt = d["query_type"]
        L.append(f"| {k} | {qt.get('positive',0)} | {qt.get('negative',0)} | {qt.get('edge',0)} | {d['n']} |")
    L.append("")

    L.append("### has_corpus_limit_declaration")
    L.append("| dataset | true | false |")
    L.append("|---|---:|---:|")
    for k in ("v1", "v2", "cumulato"):
        d = step4_stats[k]
        h = d["has_corpus_limit"]
        L.append(f"| {k} | {h['true']} | {h['false']} |")
    L.append("")

    L.append("### query_type × has_corpus_limit_declaration")
    L.append("| dataset | positive_limit=F | positive_limit=T | negative_limit=F | edge_limit=F | edge_limit=T |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for k in ("v1", "v2", "cumulato"):
        d = step4_stats[k]["cross"]
        row = [
            d.get("positive_limit=False", 0),
            d.get("positive_limit=True", 0),
            d.get("negative_limit=False", 0),
            d.get("edge_limit=False", 0),
            d.get("edge_limit=True", 0),
        ]
        L.append(f"| {k} | {' | '.join(str(x) for x in row)} |")
    L.append("")

    L.append("### Norme toccate (count query, cross-norma somma >100%)")
    all_norms = sorted({n for k in ("v1", "v2", "cumulato") for n in step4_stats[k]["norms_touched"]})
    L.append("| Norma | v1 | v2 | cumulato |")
    L.append("|---|---:|---:|---:|")
    for n in all_norms:
        v1n = step4_stats["v1"]["norms_touched"].get(n, 0)
        v2n = step4_stats["v2"]["norms_touched"].get(n, 0)
        cn = step4_stats["cumulato"]["norms_touched"].get(n, 0)
        L.append(f"| {n} | {v1n} | {v2n} | {cn} |")
    L.append("")

    L.append("### Paired queries intenzionali (design v2)")
    paired = step4_stats["paired_queries"]
    if paired:
        L.append("| Tema | qid coppia |")
        L.append("|---|---|")
        for theme, qids in paired.items():
            L.append(f"| {theme} | {', '.join(qids)} |")
    else:
        L.append("Nessuna coppia dichiarata nei metadata di v2_curated.")
    L.append("")

    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Scritto {REPORT_PATH}")


def main() -> int:
    print("=" * 70)
    print("Phase E merge — gold_answers_v2.json")
    print("=" * 70)

    v1, v2, v2_meta = load_inputs()
    print(f"v1: {len(v1)} entry · v2_curated: {len(v2)} entry")

    # Step 1
    print("\n--- Step 1: validazione input ---")
    errs = step1_validate(v1, v2)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
        raise RuntimeError("Step 1 fallito, abort merge.")
    print("  OK.")

    # Step 2
    print("\n--- Step 2: Qdrant lookup ---")
    v2, step2_stats = step2_populate_v2(v2)
    if step2_stats["missing"]:
        raise RuntimeError(
            f"{step2_stats['missing']} chunk_id missing in Qdrant: "
            f"{step2_stats['missing_ids']}. Abort merge."
        )
    # Verifica: v1 deve già avere hierarchy/text popolati
    v1_empty = sum(1 for e in v1 for g in e["gold_chunks"] if not g.get("text"))
    if v1_empty:
        print(f"  WARNING: v1 ha {v1_empty} chunk con text vuoto (atteso 0).")
    else:
        print("  v1 chunk text already populated (atteso).")

    # Merge ordinato per qid
    all_entries = sorted(v1 + v2, key=lambda e: int(e["qid"][1:]))

    # Step 3
    print("\n--- Step 3: schema consistency ---")
    s3 = step3_schema_consistency(all_entries)
    for name, p, f in s3["checks"]:
        mark = "✓" if f == 0 else "⚠"
        print(f"  {mark} {name}: pass={p} fail={f}")
    if s3["errors"]:
        print(f"  ERRORI: {len(s3['errors'])}")
        for e in s3["errors"][:5]:
            print(f"    - {e}")
    if s3["warnings"]:
        print(f"  WARNING: {len(s3['warnings'])}")

    # Step 4
    print("\n--- Step 4: statistiche aggregate ---")
    stats = step4_statistics(all_entries, v2_meta)
    print(f"  cumulato: positive={stats['cumulato']['query_type'].get('positive',0)}, "
          f"negative={stats['cumulato']['query_type'].get('negative',0)}, "
          f"edge={stats['cumulato']['query_type'].get('edge',0)}")
    print(f"  has_corpus_limit_declaration true: {stats['cumulato']['has_corpus_limit']['true']}/{100}")
    print(f"  norme toccate (cumulato): {stats['cumulato']['norms_touched']}")

    # Step 5
    print("\n--- Step 5: write output ---")
    output = {
        "metadata": {
            "schema_version": "2.0",
            "date": "2026-05-20",
            "n_entries": len(all_entries),
            "source_v1": "data/benchmark/gold_answers_v1.json",
            "source_v2_curated": "data/benchmark/candidates_v2_curated.json",
            "merge_phase": "E",
            "schema": "ogni entry ha 10 campi identici a gold_answers_v1.json; wrapper {metadata, entries} aggiunto per tracciabilità",
        },
        "entries": all_entries,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Scritto {OUTPUT_PATH}")

    write_report(errs, step2_stats, s3, stats)

    DEBUG_PATH.write_text(
        json.dumps({
            "step1_errors": errs,
            "step2_stats": step2_stats,
            "step3_results": s3,
            "step4_stats": stats,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Debug → {DEBUG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
