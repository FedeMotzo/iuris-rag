"""Candidates v2 audit — verifica esistenza chunk_id in Qdrant.

Audit meccanico read-only: per ogni candidate in
`data/benchmark/candidates_v2.json`, verifica che ogni
`gold_chunks_proposed` esista nella collection Qdrant
`italian_legal_v1_hybrid`. Genera report con classificazione errori e
raccomandazione (riparabile / sostituibile / da scartare).

Output: stampe su stdout, raccolte poi a mano in
`spike/CANDIDATES_V2_QDRANT_AUDIT.md`.

    spike/.venv/bin/python spike/audit_candidates.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data/benchmark/candidates_v2.json"
COLLECTION = "italian_legal_v1_hybrid"

# Stesso mapping di audit_corpus.py
NORM_PREFIXES = [
    ("eli/reg/2016/679/oj", "GDPR"),
    ("eli/reg/2024/1689/oj", "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]

# Pattern prefissi noti errati (per classificazione (c))
WRONG_PREFIX_PATTERNS = {
    "akn/it/act/decreto_legislativo/stato/2024-09-12/138": "NIS2 — data wrong (corretta: 2024-09-04)",
}

# Target per cluster derivati da BENCHMARK_DISTRIBUTION_ANALYSIS.md step 7
# (50 query finali = 39 positive + 8 negative + 3 edge).
# Negative subcluster: distribuzione proporzionale al pool (somma=8).
CLUSTER_TARGETS = {
    "NIS2 mono-norma": 6,
    "NIS2 cross GDPR": 2,
    "Codice Privacy mono-norma": 5,
    "L. 132/2025": 4,
    "Cross-norma 3+ norme": 5,
    "Cross-norma scenario 2 norme": 4,
    "Diritti dell'interessato GDPR": 4,
    "Sanzionatorio puro": 4,
    "231 fattispecie oltre 24-bis": 3,
    "Procedurali 'come si fa X'": 2,
    "Negative: Garante UC4": 1,
    "Negative: art abrogato Codice Privacy": 2,
    "Negative: art inesistente": 2,
    "Negative: corpus mancante": 2,
    "Negative: omonimia numerazione": 1,
    "Edge: vaghe / mix": 3,
}


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


def fetch_qdrant_chunk_ids() -> dict[str, dict]:
    """Scroll completo collection, ritorna {chunk_id: {hierarchy: str}}."""
    from qdrant_client import QdrantClient
    try:
        client = QdrantClient(host="localhost", port=6333, timeout=10.0)
        if not client.collection_exists(COLLECTION):
            raise RuntimeError(
                f"Collection {COLLECTION} non esiste in Qdrant localhost:6333. "
                "Verifica che Docker Qdrant sia up e la collection sia stata ingerita."
            )
    except Exception as exc:
        raise RuntimeError(
            f"Qdrant non raggiungibile su localhost:6333: {exc}"
        ) from exc

    chunks: dict[str, dict] = {}
    offset = None
    while True:
        pts, offset = client.scroll(
            COLLECTION, limit=512, offset=offset,
            with_payload=["chunk_id", "hierarchy_path"], with_vectors=False,
        )
        for p in pts:
            cid = p.payload.get("chunk_id")
            if not cid:
                continue
            hier = " > ".join(p.payload.get("hierarchy_path") or [])
            chunks[cid] = {"hierarchy": hier}
        if offset is None:
            break
    return chunks


def classify_missing(chunk_id: str, qdrant_cids: set[str]) -> tuple[str, str]:
    """Classifica la causa di un chunk_id mancante.

    Ritorna (codice, descrizione). Codici:
      a = articolo inesistente nella norma
      b = articolo abrogato non in Qdrant
      c = prefisso URN errato
      d = suffisso/formato errato
      e = articolo plausibile ma non ingerito (es. annex AI Act ≠ III)
      f = sconosciuto
    """
    # (c) prefisso URN errato (data wrong, ecc.)
    for wrong, note in WRONG_PREFIX_PATTERNS.items():
        if chunk_id.startswith(wrong + "__"):
            return ("c", note)

    norm = norm_of(chunk_id)
    if norm == "?":
        return ("c", "prefisso URN non riconosciuto (norma sconosciuta)")

    # Estrai suffisso
    prefix = next(pre for pre, _ in NORM_PREFIXES if chunk_id.startswith(pre + "__"))
    suffix = chunk_id[len(prefix) + 2:]

    # (d) suffisso atipico (par_N, paragrafo, ecc. che non matcha mai)
    if re.match(r'art_\d+[a-z\-]*_par_\d+', suffix) or "paragrafo" in suffix:
        return ("d", f"suffisso non-canonico '{suffix}' (atteso art_N o art_N__paras_M_K)")

    # (e) annex AI Act non-III non ingerito
    if norm == "AI Act" and suffix.startswith("annex_") and not suffix.startswith("annex_III"):
        return ("e", "annex AI Act ≠ III: parser v1 ingerisce solo Annex III (vedi CORPUS_INGESTION_AUDIT.md)")

    # (b) per Codice Privacy: l'audit corpus ha mostrato 114 articoli abrogati esclusi
    if norm == "Codice Privacy" and suffix.startswith("art_"):
        return ("b", "verosimilmente articolo abrogato del Codice Privacy (114 abrogati esclusi nell'ingestione)")

    # (a) per altre norme: articolo non presente nel sorgente — confronto numerico
    m = re.match(r'art_(\d+)', suffix)
    if m:
        num = int(m.group(1))
        # max article noto per norma (da audit_corpus.py / ingestione)
        max_known = {"GDPR": 99, "AI Act": 113, "D.Lgs 231/2001": 85, "NIS2": 44, "L. 132/2025": 28}
        if norm in max_known and num > max_known[norm]:
            return ("a", f"articolo {num} oltre il range noto della norma (max={max_known[norm]})")

    # (d-bis) articolo presente come article_fragment splittato per oversize
    fragments = [c for c in qdrant_cids if c.startswith(chunk_id + "__paras_")]
    if fragments:
        return ("d", f"articolo presente come fragment splittato per oversize: {fragments}")

    # fallback (f)
    return ("f", f"chunk_id formattato correttamente ma assente da Qdrant; suffix='{suffix}'")


def suggest_replacement(
    qid: str, missing: list[str], qdrant_cids: set[str], candidate: dict
) -> tuple[str, str]:
    """Suggerisce azione e proposta alternativa.

    Ritorna (azione, proposta) dove azione ∈ {RIPARABILE, SOSTITUIBILE, DA SCARTARE}.
    """
    proposals: list[str] = []
    actions: set[str] = set()
    for cid in missing:
        code, _desc = classify_missing(cid, qdrant_cids)
        if code == "c":
            # prefisso wrong → propongo lo stesso chunk_id col prefisso corretto
            for wrong in WRONG_PREFIX_PATTERNS:
                if cid.startswith(wrong + "__"):
                    correct = "akn/it/act/decreto_legislativo/stato/2024-09-04/138" + cid[len(wrong):]
                    if correct in qdrant_cids:
                        proposals.append(f"{cid} → {correct}")
                        actions.add("RIPARABILE")
                    else:
                        actions.add("DA SCARTARE")
                    break
        elif code == "b":
            actions.add("DA SCARTARE")  # abrogato → fuori corpus v1
        elif code == "a":
            actions.add("DA SCARTARE")  # articolo inesistente
        elif code == "e":
            actions.add("DA SCARTARE")  # annex non ingerito, scope v1.1
        elif code == "d":
            # caso 1: articolo presente come fragment splittato per oversize
            fragments = sorted(c for c in qdrant_cids if c.startswith(cid + "__paras_"))
            if fragments:
                proposals.append(f"{cid} → [{', '.join(fragments)}]")
                actions.add("RIPARABILE")
                continue
            # caso 2: suffix non-canonico (par_N, paragrafo): normalizza a art_N
            m = re.match(r'(.*?__art_\d+[a-z\-]*)_par_\d+', cid) or re.match(r'(.*?__art_\d+[a-z\-]*)', cid)
            if m and m.group(1) in qdrant_cids:
                proposals.append(f"{cid} → {m.group(1)}")
                actions.add("RIPARABILE")
            else:
                actions.add("SOSTITUIBILE")
        else:
            actions.add("SOSTITUIBILE")

    # priorità azione: RIPARABILE > SOSTITUIBILE > DA SCARTARE (la migliore vince)
    if "RIPARABILE" in actions and "DA SCARTARE" not in actions:
        return ("RIPARABILE", "; ".join(proposals))
    if "DA SCARTARE" in actions and not {"RIPARABILE", "SOSTITUIBILE"} & actions:
        return ("DA SCARTARE", "tema irrecuperabile col corpus v1")
    if "SOSTITUIBILE" in actions:
        return ("SOSTITUIBILE", "cercare manualmente articolo affine nella stessa norma")
    # mix: riparo parziale + scarto → SOSTITUIBILE (richiede curatela)
    return ("SOSTITUIBILE", "mix di errori: " + "; ".join(proposals) if proposals else "curatela manuale")


def main() -> int:
    data = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    print(f"Caricato {len(candidates)} candidate da {CANDIDATES_PATH.name}")

    # Step 1: inventario chunk_id proposti
    all_proposed: set[str] = set()
    for c in candidates:
        for cid in c.get("gold_chunks_proposed", []):
            all_proposed.add(cid)
    print(f"Step 1: {len(all_proposed)} chunk_id unici nei gold_chunks_proposed")

    # Step 2: fetch Qdrant
    print("Step 2: scroll Qdrant…")
    qdrant_data = fetch_qdrant_chunk_ids()
    qdrant_cids = set(qdrant_data.keys())
    print(f"        {len(qdrant_cids)} chunk in collection {COLLECTION}")

    existence = {cid: (cid in qdrant_cids) for cid in all_proposed}
    n_existing = sum(1 for v in existence.values() if v)
    n_missing_unique = sum(1 for v in existence.values() if not v)
    print(f"        Esistenti: {n_existing} / {len(all_proposed)} (mancanti unici: {n_missing_unique})")

    # Step 3: audit per candidate
    audit_rows: list[dict] = []
    for c in candidates:
        proposed = c.get("gold_chunks_proposed", [])
        # negative/edge senza gold_chunks atteso = audit pass
        if c["query_type"] in ("negative", "edge") and not proposed:
            audit_rows.append({
                **{k: c[k] for k in ("qid", "cluster", "confidence", "query_type")},
                "n_proposed": 0, "n_existing": 0, "gap": 0,
                "missing": [], "note": "atteso per negative/edge",
            })
            continue
        n_prop = len(proposed)
        n_exist = sum(1 for cid in proposed if cid in qdrant_cids)
        missing = [cid for cid in proposed if cid not in qdrant_cids]
        audit_rows.append({
            **{k: c[k] for k in ("qid", "cluster", "confidence", "query_type")},
            "n_proposed": n_prop, "n_existing": n_exist, "gap": n_prop - n_exist,
            "missing": missing, "note": "",
        })

    audit_rows.sort(key=lambda r: (-r["gap"], {"bassa": 0, "media": 1, "alta": 2}.get(r["confidence"], 9), r["qid"]))

    print("\n" + "=" * 80)
    print("Step 3 — Audit per candidate (head 20)")
    print("=" * 80)
    print(f"{'qid':<6} {'cluster':<38} {'conf':<6} {'np':>3} {'ne':>3} {'gap':>3} missing")
    for r in audit_rows[:20]:
        cl = r["cluster"][:36]
        print(f"{r['qid']:<6} {cl:<38} {r['confidence']:<6} {r['n_proposed']:>3} {r['n_existing']:>3} {r['gap']:>3} {','.join(r['missing'])[:80]}")

    # Step 4: aggregati per cluster
    by_cluster = defaultdict(lambda: {"n": 0, "pass": 0, "fail": 0})
    for r in audit_rows:
        by_cluster[r["cluster"]]["n"] += 1
        if r["gap"] == 0:
            by_cluster[r["cluster"]]["pass"] += 1
        else:
            by_cluster[r["cluster"]]["fail"] += 1

    print("\n" + "=" * 80)
    print("Step 4 — Aggregati per cluster")
    print("=" * 80)
    print(f"{'cluster':<42} {'n':>3} {'pass':>5} {'fail':>5} {'%pass':>7}")
    print("-" * 70)
    for cl in sorted(by_cluster.keys()):
        d = by_cluster[cl]
        pct = d["pass"] / d["n"] * 100 if d["n"] else 0
        flag = "  ⚠ <70%" if pct < 70 else ""
        print(f"{cl:<42} {d['n']:>3} {d['pass']:>5} {d['fail']:>5} {pct:>6.1f}%{flag}")

    # Step 5: pattern errori
    print("\n" + "=" * 80)
    print("Step 5 — Pattern errori sui missing chunks")
    print("=" * 80)
    missing_with_code: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in audit_rows:
        for cid in r["missing"]:
            code, desc = classify_missing(cid, qdrant_cids)
            missing_with_code[r["cluster"]].append((code, cid, desc, r["qid"]))

    err_summary = Counter()
    for entries in missing_with_code.values():
        for code, _, _, _ in entries:
            err_summary[code] += 1
    print(f"\nSommario codici: {dict(err_summary)}")
    print("\nLegenda: a=art inesistente · b=abrogato · c=prefix wrong · d=suffix wrong · e=non ingerito · f=sconosciuto\n")
    for cl in sorted(missing_with_code.keys()):
        if not missing_with_code[cl]:
            continue
        print(f"### {cl}")
        for code, cid, desc, qid in sorted(missing_with_code[cl]):
            print(f"  [{code}] {qid:<6} {cid:<70} {desc}")
        print()

    # frequenza chunk_id missing
    miss_freq = Counter()
    for r in audit_rows:
        for cid in r["missing"]:
            miss_freq[cid] += 1
    systemic = [(c, n) for c, n in miss_freq.most_common() if n >= 3]

    # Step 6: raccomandazione per candidate
    print("=" * 80)
    print("Step 6 — Raccomandazione per candidate (con gap > 0)")
    print("=" * 80)
    actions_count: Counter = Counter()
    candidate_actions: dict[str, str] = {}
    candidate_proposals: dict[str, str] = {}
    cand_by_qid = {c["qid"]: c for c in candidates}
    for r in audit_rows:
        if r["gap"] == 0:
            continue
        action, proposal = suggest_replacement(r["qid"], r["missing"], qdrant_cids, cand_by_qid[r["qid"]])
        candidate_actions[r["qid"]] = action
        candidate_proposals[r["qid"]] = proposal
        actions_count[action] += 1
    print(f"\nDistribuzione azioni: {dict(actions_count)}")

    # Step 7: sintesi
    n_pass = sum(1 for r in audit_rows if r["gap"] == 0)
    n_fail = sum(1 for r in audit_rows if r["gap"] > 0)
    n_rip = actions_count.get("RIPARABILE", 0)
    n_sost = actions_count.get("SOSTITUIBILE", 0)
    n_scart = actions_count.get("DA SCARTARE", 0)
    pool_survivor = n_pass + n_rip + n_sost

    print("\n" + "=" * 80)
    print("Step 7 — Sintesi finale")
    print("=" * 80)
    print(f"  Audit pass (gap=0):  {n_pass} / {len(audit_rows)}")
    print(f"  Audit fail (gap>0):  {n_fail}")
    print(f"    riparabili:        {n_rip}")
    print(f"    sostituibili:      {n_sost}")
    print(f"    da scartare:       {n_scart}")
    print(f"  Pool survivor fase B (pass + riparabili + sostituibili): {pool_survivor}")

    print(f"\n{'cluster':<42} {'surv':>5} {'target':>7} {'ratio':>7} {'ALERT'}")
    print("-" * 80)
    cluster_survivors: dict[str, int] = defaultdict(int)
    for r in audit_rows:
        if r["gap"] == 0 or candidate_actions.get(r["qid"]) in ("RIPARABILE", "SOSTITUIBILE"):
            cluster_survivors[r["cluster"]] += 1
    alerts: list[str] = []
    for cl, tgt in CLUSTER_TARGETS.items():
        surv = cluster_survivors.get(cl, 0)
        ratio = surv / tgt if tgt else 0
        alert = ""
        if ratio < 1.0:
            alert = "⚠ ALERT sotto-target"
            alerts.append(f"{cl}: surv={surv} < target={tgt} (ratio={ratio:.2f})")
        elif ratio < 1.5:
            alert = "⚠ a rischio (ratio <1.5×)"
        print(f"{cl:<42} {surv:>5} {tgt:>7} {ratio:>6.2f}× {alert}")

    print("\n" + "=" * 80)
    print("Errori sistemici (chunk_id che compare in 3+ candidate)")
    print("=" * 80)
    if systemic:
        for cid, n in systemic:
            print(f"  {n}× {cid}")
    else:
        print("  nessuno")

    if alerts:
        print("\n" + "=" * 80)
        print("ALERT cluster sotto-target")
        print("=" * 80)
        for a in alerts:
            print("  -", a)

    # Stash dei dati per generare il report a mano: scrivo JSON di servizio
    debug = ROOT / "spike/_audit_candidates_debug.json"
    debug.write_text(json.dumps({
        "audit_rows": [{**r, "missing": list(r["missing"])} for r in audit_rows],
        "actions": candidate_actions,
        "proposals": candidate_proposals,
        "by_cluster": {k: dict(v) for k, v in by_cluster.items()},
        "missing_with_code": {k: [{"code": c, "chunk_id": cid, "desc": d, "qid": q} for c, cid, d, q in v] for k, v in missing_with_code.items()},
        "systemic": [{"chunk_id": c, "count": n} for c, n in systemic],
        "alerts": alerts,
        "summary": {
            "n_pass": n_pass, "n_fail": n_fail,
            "n_rip": n_rip, "n_sost": n_sost, "n_scart": n_scart,
            "pool_survivor": pool_survivor,
        },
        "cluster_survivors": dict(cluster_survivors),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDebug JSON scritto in {debug.name} (uso interno per il report).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
