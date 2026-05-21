"""Phase B curation — fix candidate v2 + overlap view vs v1.

Task B1: applica il fix art_38 fragment a C008/C009/C050.
Task B3: calcola overlap Jaccard candidate v2 ↔ query v1 per il review
in fase C.

Output:
- spike/candidates_v2_fixed.json (B1)
- spike/V1_VS_V2_OVERLAP_VIEW.md (B3)

    spike/.venv/bin/python spike/phase_b_curation.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_IN = ROOT / "data/benchmark/candidates_v2.json"
CANDIDATES_OUT = ROOT / "spike/candidates_v2_fixed.json"
GOLD_V1 = ROOT / "data/benchmark/gold_answers_v1.json"
OVERLAP_OUT = ROOT / "spike/V1_VS_V2_OVERLAP_VIEW.md"

NORM_PREFIXES = [
    ("eli/reg/2016/679/oj", "GDPR"),
    ("eli/reg/2024/1689/oj", "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]

# Stop list italiana minima per Jaccard (corte + funzionali, no contenuto)
STOPWORDS = {
    "a", "ai", "al", "alla", "alle", "agli", "allo", "che", "ci", "come", "con", "cui",
    "da", "dai", "dal", "dalla", "dalle", "dello", "degli", "delle", "di", "del", "della",
    "e", "ed", "è", "i", "il", "in", "la", "le", "lo", "ne", "nel", "nella", "nelle",
    "non", "o", "ogni", "per", "più", "quale", "quali", "quando", "quanto", "se", "si",
    "sia", "sono", "su", "sui", "sul", "sulla", "sulle", "tra", "fra", "un", "una", "uno",
    "ad", "anche", "ancora", "ai", "alcuni", "alcune", "altri", "altre", "altro", "altra",
    "essere", "stato", "stata", "stati", "state", "ha", "ho", "hanno", "questo", "questa",
    "questi", "queste", "tutto", "tutta", "tutti", "tutte", "molto", "molti", "molte",
    "loro", "mio", "mia", "miei", "mie", "suo", "sua", "suoi", "sue", "nostro", "nostra",
    "vostro", "vostra", "ai", "co",
}


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


def norms_set(chunks: list) -> frozenset[str]:
    """Set di norme toccate da una lista di chunk_id (o dict con chunk_id)."""
    out = set()
    for c in chunks:
        cid = c if isinstance(c, str) else c.get("chunk_id", "")
        n = norm_of(cid)
        if n != "?":
            out.add(n)
    return frozenset(out)


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[\w'-]+", text.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2 and not t.isdigit()}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0


def task_b1(candidates: list[dict], metadata: dict) -> dict:
    """Applica fix art_38 fragment alle 3 candidate impattate."""
    ART38 = "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38"
    FRAG_1_11 = ART38 + "__paras_1_11"
    FRAG_12_16 = ART38 + "__paras_12_16"

    # Decisioni dal contenuto delle question + gold_answer
    FIXES = {
        "C008": [FRAG_1_11],                        # massimali essenziali → commi 1-11
        "C009": [FRAG_1_11, FRAG_12_16],            # sospensione + altre misure → both
        "C050": [FRAG_1_11],                        # massimali edittali importanti → commi 1-11
    }

    print("=" * 70)
    print("Task B1 — fix NIS2 art_38 fragment")
    print("=" * 70)
    applied = 0
    for c in candidates:
        if c["qid"] not in FIXES:
            continue
        new_chunks = []
        for cid in c["gold_chunks_proposed"]:
            if cid == ART38:
                new_chunks.extend(FIXES[c["qid"]])
            else:
                new_chunks.append(cid)
        c["gold_chunks_proposed"] = new_chunks
        # gold_answer cita ancora `__art_38` come marker [cite:...]: lo lascio,
        # la citazione semantica è coerente; il marker letterale verrà
        # ri-allineato in fase C col chunk_id splittato.
        # Note: append, non overwrite
        addendum = "fixed art_38 fragments in fase B (2026-05-20)"
        if c.get("notes"):
            c["notes"] = (c["notes"] + " | " + addendum).strip()
        else:
            c["notes"] = addendum
        applied += 1
        print(f"  {c['qid']:<6} → fragments: {[x.split('__art_38')[-1] for x in FIXES[c['qid']]]}")

    metadata.setdefault("warnings", []).append(
        "fase B: art_38 NIS2 fragments fixed su C008/C009/C050"
    )
    print(f"  Applicati: {applied} (atteso 3)")
    return {"metadata": metadata, "candidates": candidates}


def task_b3(candidates: list[dict]) -> None:
    """Vista comparativa overlap v2 ↔ v1."""
    print("\n" + "=" * 70)
    print("Task B3 — overlap view candidate v2 vs gold v1")
    print("=" * 70)

    v1_data = json.loads(GOLD_V1.read_text(encoding="utf-8"))
    # filtro v1 alle 50 entry (38 positive + 10 neg + 2 edge), tutte usate per
    # overlap (anche le negative possono produrre pattern duplicati)
    v1_index: list[dict] = []
    for q in v1_data:
        v1_index.append({
            "qid": q["qid"],
            "question": q["question"],
            "tokens": tokenize(q["question"]),
            "norms": norms_set(q.get("gold_chunks", [])),
        })

    rows: list[dict] = []
    for c in candidates:
        c_tokens = tokenize(c["question"])
        c_norms = norms_set(c["gold_chunks_proposed"])

        # priority 1: stesso set di norme; priority 2: overlap norms; priority 3: any
        same = [q for q in v1_index if q["norms"] and q["norms"] == c_norms]
        overlap = [q for q in v1_index if q["norms"] and q["norms"] & c_norms and q["norms"] != c_norms]
        candidates_pool = same if same else (overlap if overlap else v1_index)

        best = None
        best_j = -1.0
        for q in candidates_pool:
            j = jaccard(c_tokens, q["tokens"])
            if j > best_j:
                best_j = j
                best = q

        # nessun pool norme-matching → flag "zona nuova" se Jaccard troppo basso
        if not c_norms or (not same and not overlap):
            flag = "🟢"
            best_qid = "—"
            best_j = 0.0
            note = "zona nuova (norme non coperte da v1 o gold v2 ancora vuoto)"
        elif best_j >= 0.40:
            flag = "🔴"
            best_qid = best["qid"]
            shared = sorted(c_tokens & best["tokens"])[:5]
            note = f"keyword condivisi: {','.join(shared)}"
        elif best_j >= 0.20:
            flag = "🟡"
            best_qid = best["qid"]
            shared = sorted(c_tokens & best["tokens"])[:4]
            note = f"keyword condivisi: {','.join(shared)}"
        else:
            flag = "🟢"
            best_qid = best["qid"] if best else "—"
            note = "tematicamente distinto da v1"

        rows.append({
            "qid_v2": c["qid"], "cluster": c["cluster"],
            "question_v2": c["question"][:78] + ("…" if len(c["question"]) > 78 else ""),
            "norms": "+".join(sorted(c_norms)) if c_norms else "∅",
            "qid_v1": best_qid, "jaccard": best_j, "flag": flag, "note": note[:60],
        })

    rows.sort(key=lambda r: (-r["jaccard"], r["cluster"]))

    n_red = sum(1 for r in rows if r["flag"] == "🔴")
    n_yellow = sum(1 for r in rows if r["flag"] == "🟡")
    n_green = sum(1 for r in rows if r["flag"] == "🟢")

    print(f"\nAggregati flag: 🔴 {n_red} · 🟡 {n_yellow} · 🟢 {n_green}")
    print("\nCandidate 🔴 ALTO (verifica scarto in fase C):")
    for r in rows:
        if r["flag"] == "🔴":
            print(f"  {r['qid_v2']:<6} ↔ v1 {r['qid_v1']:<4} Jaccard={r['jaccard']:.2f}  cluster={r['cluster'][:35]}")

    # markdown
    lines: list[str] = []
    lines.append("# V1 vs V2 overlap view (preparatoria per audit C)")
    lines.append("")
    lines.append("Data: 2026-05-20. Fase B (pre-audit giuridico).")
    lines.append(f"Input: {len(candidates)} candidate v2 (post-fix B1) ↔ {len(v1_index)} query v1.")
    lines.append("")
    lines.append("Metrica overlap: Jaccard similarity sui token della `question` "
                 "(lowercase, stopwords italiane filtrate, len>2, no digits).")
    lines.append("Pool candidate v1 per ciascuna v2: norme matching first, "
                 "norme overlap second, fallback completo.")
    lines.append("")
    lines.append("**Soglie**: 🔴 ALTO ≥0.40 · 🟡 MEDIO 0.20-0.39 · 🟢 BASSO/zona nuova <0.20.")
    lines.append("")
    lines.append("## Tabella comparativa")
    lines.append("")
    lines.append("Ordinata per Jaccard DESC (overlap ALTO prima), poi cluster.")
    lines.append("")
    lines.append("| qid_v2 | cluster | question_v2 | norme | v1 più simile | jaccard | flag | nota |")
    lines.append("|---|---|---|---|---|---:|---|---|")
    for r in rows:
        cl = r["cluster"][:25]
        lines.append(
            f"| {r['qid_v2']} | {cl} | {r['question_v2']} | {r['norms']} | "
            f"{r['qid_v1']} | {r['jaccard']:.2f} | {r['flag']} | {r['note']} |"
        )

    lines.append("")
    lines.append("## Aggregati overlap")
    lines.append("")
    lines.append("| Flag | n candidate |")
    lines.append("|---|---:|")
    lines.append(f"| 🔴 ALTO (Jaccard ≥0.40)        | {n_red} |")
    lines.append(f"| 🟡 MEDIO (Jaccard 0.20-0.39)   | {n_yellow} |")
    lines.append(f"| 🟢 BASSO/zona nuova (<0.20)    | {n_green} |")
    lines.append(f"| **Totale**                     | **{len(rows)}** |")
    lines.append("")
    lines.append("### Per cluster")
    lines.append("")
    by_cluster: dict[str, dict] = defaultdict(lambda: {"🔴": 0, "🟡": 0, "🟢": 0, "tot": 0})
    for r in rows:
        by_cluster[r["cluster"]][r["flag"]] += 1
        by_cluster[r["cluster"]]["tot"] += 1
    lines.append("| Cluster | 🔴 | 🟡 | 🟢 | totale |")
    lines.append("|---|---:|---:|---:|---:|")
    for cl in sorted(by_cluster.keys()):
        d = by_cluster[cl]
        lines.append(f"| {cl} | {d['🔴']} | {d['🟡']} | {d['🟢']} | {d['tot']} |")

    lines.append("")
    lines.append("## Candidate 🔴 ALTO — verifica in fase C")
    lines.append("")
    if n_red == 0:
        lines.append("Nessuna candidate 🔴 ALTO. Tutte le candidate sono tematicamente distinte da v1 o solo parzialmente sovrapposte (🟡/🟢).")
    else:
        lines.append("Lista da verificare: se l'overlap è solo lessicale (stessa norma, "
                     "stesso argomento generico) ma il taglio sostantivo della v2 è "
                     "diverso, va mantenuta. Se è duplicato puro (stesso scenario, "
                     "stesso gold), va scartata.")
        lines.append("")
        lines.append("| qid_v2 | cluster | qid_v1 corrispondente | Jaccard | raccomandazione |")
        lines.append("|---|---|---|---:|---|")
        for r in rows:
            if r["flag"] == "🔴":
                lines.append(
                    f"| {r['qid_v2']} | {r['cluster']} | {r['qid_v1']} | {r['jaccard']:.2f} | "
                    "verificare se è zona nuova realmente, altrimenti scartare in fase C |"
                )

    OVERLAP_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nScritto {OVERLAP_OUT}")


def main() -> int:
    data = json.loads(CANDIDATES_IN.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    metadata = data["metadata"]

    fixed = task_b1(candidates, metadata)

    CANDIDATES_OUT.write_text(
        json.dumps(fixed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Scritto {CANDIDATES_OUT}")

    task_b3(candidates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
