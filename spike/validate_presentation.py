"""PARTE 6 — validazione presentation sui 12 artefatti (tutto $0, no LLM).

Per ogni artefatto: faith PRIMA (assembled raw), ri-normalizza i body (bracket-fix
+ id pieni), costruisce CrossNormPresentation (grouping per-articolo), verifica
per-sezione, scrive <qid>.presentation.json. Poi stampa le 4 tabelle.

    spike/.venv/bin/python spike/validate_presentation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "spike/runs/paid_subset_v1"
ALL12 = ["Q68", "Q70", "Q76", "Q3", "Q9", "Q23", "Q58", "Q65", "Q67", "Q69", "Q71", "Q72"]


def main() -> int:
    from core.citation_verifier import verify_citations
    from core.cross_norm.map_assemble import (
        load_norm_doc_urns, load_norm_short_names, normalize_mini_text,
    )
    from core.cross_norm.presentation import GroupView, build_presentation

    urns = load_norm_doc_urns()
    shorts = load_norm_short_names()
    rows = {}

    for qid in ALL12:
        art = json.loads((RUNS / f"{qid}.json").read_text(encoding="utf-8"))
        uni = set(art["universe"])

        # faith PRIMA (assembled raw) + conteggio bracket non chiusi
        vr_before = verify_citations(art["assembled_text"], uni)
        unclosed = sum(
            1 for m in vr_before.markers
            if not m.verified and ("\n" in m.chunk_id or len(m.chunk_id) > 120)
        )

        # ri-normalizza i body (bracket-fix + id pieni)
        gvs = []
        for g in art["groups"]:
            body = normalize_mini_text(g["mini"], urns.get(g["source"], ""), uni)
            gvs.append(GroupView(
                source=g["source"], sub_query=g["sub_query"],
                body=body, hit_chunk_ids=g["hit_chunk_ids"],
            ))

        # faith GLOBALE dopo bracket-fix+normalizzazione (universo pieno) →
        # isola l'effetto bracket-fix (niente fabbricazioni → atteso ~0).
        global_after = verify_citations("\n\n".join(g.body for g in gvs), uni)
        global_after_unver = global_after.n_total - global_after.n_verified

        pres = build_presentation(art["detected_norms"], gvs, shorts)

        # scrivi presentation.json
        (RUNS / f"{qid}.presentation.json").write_text(
            json.dumps(pres.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8",
        )

        n_sections = sum(len(n.articles) for n in pres.norms)
        unver = [(n.norm_id, a.article) for n in pres.norms for a in n.articles
                 if not a.verified]
        rows[qid] = {
            "groups_before": len(art["groups"]),
            "sections_after": n_sections,
            "unclosed_before": unclosed,
            "ver_before": (vr_before.n_verified, vr_before.n_total),
            "global_after_unver": global_after_unver,
            "unver_sections": unver,
            "all_verified": pres.all_verified,
            "pres": pres,
        }

    # -------- 1. bracket-fix --------
    print("=" * 72)
    print("1. BRACKET-FIX (universo GLOBALE: isola l'effetto del fix)")
    print("qid  | unclosed_before | faith_before(v/tot) | global_unverified_AFTER")
    for q in ALL12:
        r = rows[q]
        print(f"{q:4} | {r['unclosed_before']:^15} | "
              f"{r['ver_before'][0]}/{r['ver_before'][1]:<6} | {r['global_after_unver']}")
    tot_unclosed = sum(r["unclosed_before"] for r in rows.values())
    tot_global_after = sum(r["global_after_unver"] for r in rows.values())
    print(f"  TOT unclosed_before={tot_unclosed}  → global_unverified_AFTER={tot_global_after}")

    # -------- 2. grouping --------
    print("\n" + "=" * 72)
    print("2. GROUPING: sezioni PRIMA (per-sub-query) → DOPO (per-articolo)")
    print("qid  | before | after | Δ")
    for q in ALL12:
        r = rows[q]
        b, a = r["groups_before"], r["sections_after"]
        print(f"{q:4} | {b:^6} | {a:^5} | -{b - a}")

    # -------- 3. faith per-sezione --------
    print("\n" + "=" * 72)
    print("3. FAITH PER-SEZIONE")
    print("qid  | all_verified | sezioni unverified")
    for q in ALL12:
        r = rows[q]
        print(f"{q:4} | {r['all_verified']} | {r['unver_sections']}")

    # -------- 4. orientamento Q70, Q72 --------
    for q in ("Q70", "Q72"):
        print("\n" + "=" * 72)
        print(f"4. ORIENTAMENTO {q}")
        print(rows[q]["pres"].orientation)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
