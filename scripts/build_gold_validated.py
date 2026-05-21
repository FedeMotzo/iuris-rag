"""Produce `data/benchmark/gold_validated.json` from `gold_candidates.json`.

Copies the candidate structure and flips `is_gold: true` on chunks in `GOLD`,
`false` on everything else. Fails loudly if any gold id is not a candidate.

Default: input `gold_candidates.json`, output `gold_validated.json` (10 query
baseline).

`--v2`: input `gold_candidates_v2.json`, output `gold_validated_v2.json`
(50 query). Il GOLD effettivo è `GOLD | NEW_GOLD` (merge), dove `NEW_GOLD`
contiene le annotazioni di Q11-Q50 (placeholder da riempire manualmente).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDS = ROOT / "data" / "benchmark" / "gold_candidates.json"
OUT = ROOT / "data" / "benchmark" / "gold_validated.json"
CANDS_V2 = ROOT / "data" / "benchmark" / "gold_candidates_v2.json"
OUT_V2 = ROOT / "data" / "benchmark" / "gold_validated_v2.json"


GOLD: dict[str, list[str]] = {
    "Q1": [
        "eli/reg/2024/1689/oj__annex_III",
        "eli/reg/2024/1689/oj__art_6",
        "eli/reg/2024/1689/oj__art_26",
        "eli/reg/2024/1689/oj__recital_57",
    ],
    "Q2": [
        "eli/reg/2024/1689/oj__art_113",
        "eli/reg/2024/1689/oj__art_111",
    ],
    "Q3": [
        "eli/reg/2016/679/oj__art_35",
        "eli/reg/2024/1689/oj__art_27",
        "eli/reg/2016/679/oj__recital_84",
        "eli/reg/2024/1689/oj__recital_96",
    ],
    "Q4": [],
    "Q5": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8",
        "eli/reg/2016/679/oj__art_22",
    ],
    "Q6": [
        "eli/reg/2016/679/oj__art_39",
        "eli/reg/2016/679/oj__art_38",
        "eli/reg/2016/679/oj__art_37",
    ],
    "Q7": [
        "eli/reg/2016/679/oj__art_35",
        "eli/reg/2016/679/oj__recital_84",
        "eli/reg/2016/679/oj__recital_91",
    ],
    "Q8": [
        "eli/reg/2024/1689/oj__art_27",
        "eli/reg/2024/1689/oj__recital_96",
    ],
    "Q9": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis",
        "akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167",
    ],
    "Q10": [
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_6",
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_3",
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_7",
    ],
}


# Gold Q11-Q50 — estratti da annotazione manuale di gold_candidates_v2.json (2026-05-19).
# Le query negative/edge senza gold sono rappresentate con lista vuota esplicita.
NEW_GOLD: dict[str, list[str]] = {
    # Q11 — AI Act high-risk credit scoring
    "Q11": [
        "eli/reg/2024/1689/oj__annex_III",
        "eli/reg/2024/1689/oj__art_6",
    ],
    # Q12 — AI Act high-risk emotion recognition scuole
    "Q12": [
        "eli/reg/2024/1689/oj__annex_III",
    ],
    # Q13 — AI Act Allegato III biometria
    "Q13": [
        "eli/reg/2024/1689/oj__annex_III",
    ],
    # Q14 — AI Act GPAI vs high-risk obblighi
    "Q14": [
        "eli/reg/2024/1689/oj__art_53",
        "eli/reg/2024/1689/oj__art_55",
        "eli/reg/2024/1689/oj__art_16",
    ],
    # Q15 — AI Act timeline divieti
    "Q15": [
        "eli/reg/2024/1689/oj__art_113",
    ],
    # Q16 — AI Act timeline GPAI già immessi
    "Q16": [
        "eli/reg/2024/1689/oj__art_111",
    ],
    # Q17 — AI Act art 113 stress
    "Q17": [
        "eli/reg/2024/1689/oj__art_113",
    ],
    # Q18 — AI Act timeline sanzioni
    "Q18": [
        "eli/reg/2024/1689/oj__art_113",
        "eli/reg/2024/1689/oj__art_99",
    ],
    # Q19 — DPIA + FRIA scoring bancario
    "Q19": [
        "eli/reg/2016/679/oj__art_35",
        "eli/reg/2024/1689/oj__annex_III",
        "eli/reg/2024/1689/oj__art_27",
    ],
    # Q20 — Garante sanzioni biometria dipendenti  (negative — Garante off-corpus)
    "Q20": [],
    # Q21 — Garante riconoscimento facciale aeroporti  (negative)
    "Q21": [],
    # Q22 — Garante riconoscimento facciale presenze  (negative)
    "Q22": [],
    # Q23 — 231 + GDPR + AI selezione fornitori  (riclassificata negative: nessun
    # ponte normativo cross-norma codificato nel corpus v1)
    "Q23": [],
    # Q24 — 231 modello organizzativo + AI HR
    "Q24": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7",
        "eli/reg/2024/1689/oj__art_26",
    ],
    # Q25 — 231 fattispecie informatica art 24-bis
    "Q25": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5",
    ],
    # Q26 — stress: art 24-bis 231
    "Q26": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis",
    ],
    # Q27 — stress: art 25-undecies
    "Q27": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8",
    ],
    # Q28 — stress: art 5 GDPR
    "Q28": [
        "eli/reg/2016/679/oj__art_5",
    ],
    # Q29 — stress: considerando 84 GDPR
    "Q29": [
        "eli/reg/2016/679/oj__recital_84",
    ],
    # Q30 — stress: Allegato III punto 4 AI Act
    "Q30": [
        "eli/reg/2024/1689/oj__annex_III",
    ],
    # Q31 — stress: art 22 GDPR
    "Q31": [
        "eli/reg/2016/679/oj__art_22",
    ],
    # Q32 — stress: art 6 NIS2
    "Q32": [
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_6",
    ],
    # Q33 — stress: art 35 disambiguation
    "Q33": [
        "eli/reg/2016/679/oj__art_35",
        "eli/reg/2024/1689/oj__art_27",
    ],
    # Q34 — stress: art 9 GDPR
    "Q34": [
        "eli/reg/2016/679/oj__art_9",
    ],
    # Q35 — stress: art 27 AI Act FRIA
    "Q35": [
        "eli/reg/2024/1689/oj__art_27",
    ],
    # Q36 — stress: art 111 AI Act
    "Q36": [
        "eli/reg/2024/1689/oj__art_111",
    ],
    # Q37 — stress: considerando 71 vs art 22 GDPR
    "Q37": [
        "eli/reg/2016/679/oj__art_22",
        "eli/reg/2016/679/oj__recital_71",
    ],
    # Q38 — stress: L. 132/2025 art 11
    "Q38": [
        "akn/it/act/legge/stato/2025-09-23/132__art_11",
    ],
    # Q39 — stress: art 6 GDPR base giuridica
    "Q39": [
        "eli/reg/2016/679/oj__art_6",
    ],
    # Q40 — stress: NIS2 obblighi notifica naturale
    "Q40": [
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25",
    ],
    # Q41 — edge: Data Act off-corpus  (negative)
    "Q41": [],
    # Q42 — edge: ISO 27001 off-scope  (negative)
    "Q42": [],
    # Q43 — edge: query troppo generica
    "Q43": [
        "akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_1",
        "eli/reg/2016/679/oj__art_1",
    ],
    # Q44 — edge: EDPB off-corpus  (negative)
    "Q44": [],
    # Q45 — edge: query vaga multi-doc
    "Q45": [
        "akn/it/act/legge/stato/2025-09-23/132__art_1",
    ],
    # Q46 — edge: operativa ChatGPT  (gold vuoto, principi GDPR/AI Act attesi in top-k)
    "Q46": [],
    # Q47 — edge: art inesistente  (negative)
    "Q47": [],
    # Q48 — edge: ePrivacy off-corpus  (negative)
    "Q48": [],
    # Q49 — edge: mix in/off corpus
    "Q49": [
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6",
        "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7",
    ],
    # Q50 — edge: vaga ma con anchor lessicale
    "Q50": [
        "eli/reg/2024/1689/oj__art_99",
    ],
}


def _build_gold_validated(
    cands_path: Path,
    out_path: Path,
    gold_map: dict[str, list[str]],
) -> tuple[int, list[tuple[str, int]]]:
    """Ritorna (exit_code, per_query). Lista vuota se fail."""
    data = json.loads(cands_path.read_text())

    missing: list[tuple[str, str]] = []
    for q in data["queries"]:
        qid = q["qid"]
        cand_ids = {c["chunk_id"] for c in q["candidates"]}
        for gid in gold_map.get(qid, []):
            if gid not in cand_ids:
                missing.append((qid, gid))

    if missing:
        print(f"STOP — {len(missing)} gold chunk_id NOT in candidates:", file=sys.stderr)
        for qid, gid in missing:
            print(f"  {qid}: {gid}", file=sys.stderr)
        return 1, []

    n_gold_set = 0
    per_query: list[tuple[str, int]] = []
    for q in data["queries"]:
        gold_set = set(gold_map.get(q["qid"], []))
        n_q = 0
        for c in q["candidates"]:
            c["is_gold"] = c["chunk_id"] in gold_set
            if c["is_gold"]:
                n_gold_set += 1
                n_q += 1
        per_query.append((q["qid"], n_q))

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    n_positive = sum(1 for v in gold_map.values() if v)
    print(f"Wrote {out_path.relative_to(ROOT)}: {n_gold_set} gold chunks across "
          f"{n_positive} positive queries")
    return 0, per_query


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--v2", action="store_true",
        help="Usa gold_candidates_v2.json (50 query) → gold_validated_v2.json; "
             "merge GOLD baseline + NEW_GOLD.",
    )
    args = parser.parse_args()

    if args.v2:
        cands_path = CANDS_V2
        out_path = OUT_V2
        overlap = set(GOLD) & set(NEW_GOLD)
        if overlap:
            print(f"STOP — qid in conflitto fra GOLD e NEW_GOLD: {sorted(overlap)}",
                  file=sys.stderr)
            return 1
        gold_map = {**GOLD, **NEW_GOLD}
    else:
        cands_path = CANDS
        out_path = OUT
        gold_map = GOLD

    if not cands_path.exists():
        print(f"STOP — file candidati non trovato: {cands_path}", file=sys.stderr)
        return 1

    rc, per_query = _build_gold_validated(cands_path, out_path, gold_map)
    if rc != 0:
        return rc

    if args.v2:
        print()
        print(f"{'QID':5s} | n_gold")
        print("-" * 30)
        for qid, n in per_query:
            note = ""
            if qid in NEW_GOLD:
                note = "  (NEW_GOLD)"
            elif qid in GOLD and not GOLD[qid]:
                note = "  (negative baseline)"
            elif qid not in GOLD and qid not in NEW_GOLD:
                note = "  (non annotata)"
            print(f"{qid:5s} | {n:>5d}{note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
