"""Analyze benchmark distribution — read-only.

Distribuzione tematica delle 38 query positive di
`data/benchmark/gold_answers_v1.json`. Output: stampe strutturate su
stdout, raccolte poi a mano in `spike/BENCHMARK_DISTRIBUTION_ANALYSIS.md`.

    spike/.venv/bin/python spike/analyze_distribution.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data/benchmark/gold_answers_v1.json"

# Mappa prefisso URN → norma (stessa di audit_corpus.py)
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


def chunk_type(chunk_id: str) -> str:
    if "__art_" in chunk_id and "__paras_" in chunk_id:
        return "article_fragment"
    if "__art_" in chunk_id:
        return "article"
    if "__recital_" in chunk_id:
        return "recital"
    if "__annex_" in chunk_id:
        return "annex"
    return "other"


def map_use_case(q: dict) -> str:
    """Mappa una query positive a uno dei 5 UC SCOPE.

    Logica: keyword match su use_case + question. UC4 (Garante) escluso
    per design v1 (decisione 2026-05-19).
    """
    uc = q["use_case"].lower()
    qt = q["question"].lower()
    text = uc + " " + qt
    # UC3 231 prima per evitare collisione con AI Act (alcune query Q "231 + AI HR")
    if "231" in text or "reato" in uc or "responsabilità degli enti" in qt:
        return "UC3 — 231 responsabilità ente"
    if "nis2" in text or "obblighi notifica" in uc:
        return "UC5 — NIS2 / cybersecurity"
    if "ai act" in text or "fria" in text or "alto rischio" in text or "high-risk" in text or "gpai" in text or "allegato iii" in text or "l. 132/2025" in text or "art 11" in qt:
        return "UC2 — AI Act"
    if "dpia" in text or "dpo" in text or "gdpr" in text or "considerando" in text or "art 22" in text or "art 5" in text or "art 6 gdpr" in text or "art 9" in text or "art 35" in text or "privacy" in text:
        return "UC1 — GDPR compliance"
    return "?"


def classify_type(q: dict) -> tuple[str, str]:
    """(tipologia, dubbio_opzionale).

    Heuristica su question + use_case. Ritorna tupla per tracciare casi
    borderline esplicitamente.
    """
    uc = q["use_case"].lower()
    qt = q["question"].lower()

    # Stress/edge ha priorità: il prefisso lo dichiara esplicitamente
    if uc.startswith("stress") or uc.startswith("edge"):
        return ("Stress/edge", "")

    # Sanzionatorio: query su sanzioni penali/amministrative
    if "sanzione" in qt or "sanzioni" in qt or "pena" in qt or "multa" in qt:
        return ("Sanzionatorio", "")

    # Cross-norma scenario: situazione professionale con più norme
    n_norms = len({norm_of(g["chunk_id"]) for g in q.get("gold_chunks", []) if g.get("chunk_id")})
    if n_norms >= 3 or ("uso" in qt and ("ai" in qt or "screening" in qt or "scoring" in qt)):
        if n_norms >= 2:
            return ("Cross-norma scenario", "")

    # Lookup definitorio: "cos'è X", "definizione", "art N di Z"
    if qt.startswith("cos'è") or qt.startswith("cosa è") or "definizione" in qt or "art " in qt[:20]:
        return ("Lookup definitorio", "")

    # Procedurale: "come si fa", "passi per", "quali sono i compiti"
    if qt.startswith("come ") or "come si" in qt or "quali sono i compiti" in qt or "quali compiti" in qt or "quali sono i passi" in qt:
        return ("Procedurale", "")

    # Condizionale: "in quale caso", "quando è obbligatorio", "ricade tra"
    if "quando" in qt or "in quale caso" in qt or "ricade tra" in qt or "è obbligatoria" in qt or "obbligatorio" in qt or "applica" in qt:
        return ("Condizionale", "")

    return ("Altro", "fallback: non classificata da nessuna euristica")


def main() -> int:
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    positives = [e for e in data if e["query_type"] == "positive"]
    assert len(positives) == 38, f"expected 38 positives, got {len(positives)}"

    # --- Step 1: distribuzione per norma ---
    print("=" * 70)
    print("Step 1 — Distribuzione per norma")
    print("=" * 70)
    norm_query_counts: dict[str, set] = defaultdict(set)
    query_to_norms: dict[str, set] = {}
    for q in positives:
        norms = {norm_of(g["chunk_id"]) for g in q["gold_chunks"] if g.get("chunk_id")}
        norms.discard("?")
        query_to_norms[q["qid"]] = norms
        for n in norms:
            norm_query_counts[n].add(q["qid"])

    print(f"\n{'Norma':<25} {'n_query':>8} {'%':>6}")
    print("-" * 45)
    for _, label in NORM_PREFIXES:
        n = len(norm_query_counts.get(label, set()))
        pct = n / 38 * 100
        print(f"{label:<25} {n:>8} {pct:>5.1f}%")

    # Mono vs cross
    print(f"\n{'Pattern':<35} {'count':>6}  esempi qid")
    print("-" * 80)
    mono_per_norma: dict[str, list[str]] = defaultdict(list)
    cross_2: list[str] = []
    cross_3plus: list[str] = []
    for qid, norms in query_to_norms.items():
        if len(norms) == 1:
            mono_per_norma[next(iter(norms))].append(qid)
        elif len(norms) == 2:
            cross_2.append(qid)
        elif len(norms) >= 3:
            cross_3plus.append(qid)
    for _, label in NORM_PREFIXES:
        qids = mono_per_norma.get(label, [])
        if qids:
            print(f"{'Mono-norma ' + label:<35} {len(qids):>6}  {','.join(sorted(qids, key=lambda s: int(s[1:])))}")
    print(f"{'Cross-norma 2 norme':<35} {len(cross_2):>6}  {','.join(sorted(cross_2, key=lambda s: int(s[1:])))}")
    print(f"{'Cross-norma 3+ norme':<35} {len(cross_3plus):>6}  {','.join(sorted(cross_3plus, key=lambda s: int(s[1:])))}")

    # --- Step 2: distribuzione per tipo di chunk ---
    print("\n" + "=" * 70)
    print("Step 2 — Distribuzione per tipo di chunk")
    print("=" * 70)
    type_total = Counter()
    type_queries: dict[str, set] = defaultdict(set)
    for q in positives:
        seen_in_query = set()
        for g in q["gold_chunks"]:
            cid = g.get("chunk_id")
            if not cid:
                continue
            t = chunk_type(cid)
            type_total[t] += 1
            seen_in_query.add(t)
        for t in seen_in_query:
            type_queries[t].add(q["qid"])
    print(f"\n{'Tipo':<20} {'count tot':>10} {'n_query':>10}")
    print("-" * 45)
    for t in ["article", "article_fragment", "recital", "annex", "other"]:
        print(f"{t:<20} {type_total.get(t, 0):>10} {len(type_queries.get(t, set())):>10}")

    # --- Step 3: distribuzione per use case ---
    print("\n" + "=" * 70)
    print("Step 3 — Distribuzione per use case SCOPE")
    print("=" * 70)
    uc_buckets: dict[str, list[str]] = defaultdict(list)
    for q in positives:
        uc = map_use_case(q)
        uc_buckets[uc].append(q["qid"])
    print(f"\n{'Use case':<35} {'n':>4}  qid")
    print("-" * 80)
    for uc in ["UC1 — GDPR compliance", "UC2 — AI Act", "UC3 — 231 responsabilità ente", "UC5 — NIS2 / cybersecurity", "?"]:
        qids = uc_buckets.get(uc, [])
        if qids:
            print(f"{uc:<35} {len(qids):>4}  {','.join(sorted(qids, key=lambda s: int(s[1:])))}")

    # --- Step 4: tipologia query ---
    print("\n" + "=" * 70)
    print("Step 4 — Distribuzione per tipologia")
    print("=" * 70)
    type_buckets: dict[str, list[str]] = defaultdict(list)
    doubts: list[str] = []
    for q in positives:
        cat, doubt = classify_type(q)
        type_buckets[cat].append(q["qid"])
        if doubt:
            doubts.append(f"{q['qid']}: {doubt}")
    print(f"\n{'Tipologia':<25} {'count':>6} {'%':>6}  qid")
    print("-" * 100)
    for cat in ["Lookup definitorio", "Procedurale", "Condizionale", "Cross-norma scenario", "Sanzionatorio", "Stress/edge", "Altro"]:
        qids = type_buckets.get(cat, [])
        pct = len(qids) / 38 * 100
        if qids:
            qids_sorted = ','.join(sorted(qids, key=lambda s: int(s[1:])))
            print(f"{cat:<25} {len(qids):>6} {pct:>5.1f}%  {qids_sorted}")
    if doubts:
        print("\nDubbi (annotati nel report):")
        for d in doubts:
            print(f"  - {d}")

    # --- Step 5: has_corpus_limit_declaration vs runtime ---
    print("\n" + "=" * 70)
    print("Step 5 — has_corpus_limit_declaration vs runtime")
    print("=" * 70)
    bucket = defaultdict(list)
    for q in positives:
        flag = q.get("has_corpus_limit_declaration", False)
        runtime = q.get("runtime_corpus_limit_observed", False)
        if flag and runtime:
            bucket["flag=true, runtime=true"].append(q["qid"])
        elif flag and not runtime:
            bucket["flag=true, runtime=false"].append(q["qid"])
        elif not flag and runtime:
            bucket["flag=false, runtime=true (FALSO NEGATIVO)"].append(q["qid"])
        else:
            bucket["flag=false, runtime=false (standard)"].append(q["qid"])
    print(f"\n{'Categoria':<55} {'n':>4}  qid")
    print("-" * 100)
    for k in ["flag=true, runtime=true", "flag=true, runtime=false",
              "flag=false, runtime=true (FALSO NEGATIVO)", "flag=false, runtime=false (standard)"]:
        qids = bucket.get(k, [])
        if qids:
            print(f"{k:<55} {len(qids):>4}  {','.join(sorted(qids, key=lambda s: int(s[1:])))}")

    # raw export per il report
    print("\n" + "=" * 70)
    print("Step 6+7 raw — dump per usare nel report")
    print("=" * 70)
    print("\nmono_per_norma:")
    for n, qids in sorted(mono_per_norma.items()):
        print(f"  {n}: {len(qids)} → {sorted(qids, key=lambda s: int(s[1:]))}")
    print(f"\ncross_2: {len(cross_2)} → {sorted(cross_2, key=lambda s: int(s[1:]))}")
    print(f"cross_3plus: {len(cross_3plus)} → {sorted(cross_3plus, key=lambda s: int(s[1:]))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
