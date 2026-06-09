"""Harness di scoring UC1: gira classify() sui 50 scenari gold e misura.

- verdetto-level (4 classi): predetto vs verdetto_atteso;
- candidate-level (per alto-rischio/vietati): punto Allegato III / lettera art. 5 /
  flag art. 6(1) attesi individuati?
- metriche SEPARATE per tipo: strict su positive/negative; gli edge NON pass/fail
  (gold-vs-predetto affiancati, divergenze marcate);
- isolamento esplicito degli scenari con esenzione art. 6(3);
- nota multi-categoria.

Output (diagnostico) in spike/UC1_EVAL/: results.md + raw_results.json.
Corpus read-only (classify usa fetch-by-id). Riporta, non decide.

    spike/.venv/bin/python scripts/eval_uc1_classification.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

GOLD = ROOT / "data" / "benchmark" / "gold_uc1_classification.json"
OUT_DIR = ROOT / "spike" / "UC1_EVAL"
COLLECTION = "italian_legal_v1_hybrid"

V_VIETATO = "vietato"
V_HR = "alto rischio (Allegato III)"
V_61 = "possibile alto rischio (art. 6(1))"
V_NO = "non alto rischio"
VERDICTS = [V_VIETATO, V_HR, V_61, V_NO]
_SHORT = {V_VIETATO: "vietato", V_HR: "AIII", V_61: "6(1)", V_NO: "non-HR"}


def build_pipeline():
    from qdrant_client import QdrantClient

    from core.hybrid_retriever import HybridRetriever
    from core.serving import build_default_pipeline

    client = QdrantClient(host="localhost", port=6333)
    retriever = HybridRetriever(
        client=client, encoder=None, bm25=None, collection=COLLECTION, reranker=None,
    )
    return build_default_pipeline(retriever)


def predicted_verdict(res: dict) -> str:
    """Stessa priorità del builder/_esito: vietato > AIII > 6(1) > non-HR."""
    if res["card"]["prohibited_flag"]:
        return V_VIETATO
    if res["high_risk_annex"]:
        return V_HR
    if res["judgment"]["art6_1_safety_component"]["plausible"]:
        return V_61
    return V_NO


def predicted_candidates(res: dict) -> dict:
    j = res["judgment"]
    return {
        "annex_iii_points": sorted(a["point"] for a in j["annex_iii"] if a["applies"]),
        "art5_letters": [p["practice"] for p in j["prohibited_practices"] if p["applies"]],
        "art6_1": bool(j["art6_1_safety_component"]["plausible"]),
    }


def candidate_match(gold_v: str, gold_c: dict, pred_c: dict):
    """Y/N/— a seconda del verdetto gold. Recall dei candidati attesi."""
    if gold_v == V_VIETATO:
        exp = set(gold_c["art5_letters"])
        return ("Y" if exp and exp <= set(pred_c["art5_letters"]) else "N")
    if gold_v == V_HR:
        exp = set(gold_c["annex_iii_points"])
        return ("Y" if exp and exp <= set(pred_c["annex_iii_points"]) else "N")
    if gold_v == V_61:
        return ("Y" if pred_c["art6_1"] else "N")
    return "—"  # non alto rischio: nessun candidato atteso


def _cand_str(c: dict) -> str:
    parts = []
    if c["annex_iii_points"]:
        parts.append("AIII:" + ",".join(map(str, c["annex_iii_points"])))
    if c["art5_letters"]:
        parts.append("art5:" + ",".join(c["art5_letters"]))
    if c["art6_1"]:
        parts.append("6(1)")
    return " ".join(parts) if parts else "—"


def main() -> int:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    scenarios = gold["scenarios"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pipe = build_pipeline()

    rows = []
    raw = []
    for s in scenarios:
        res = pipe.classify(s["descrizione"]).to_dict()
        pv = predicted_verdict(res)
        pc = predicted_candidates(res)
        gv = s["verdetto_atteso"]
        gc = s["gold_candidates"]
        rows.append({
            "id": s["id"], "tipo": s["tipo"], "settore": s["settore"],
            "gold_verdict": gv, "pred_verdict": pv,
            "verdict_match": (pv == gv),
            "gold_cand": _cand_str(gc), "pred_cand": _cand_str(pc),
            "cand_match": candidate_match(gv, gc, pc),
            "art6_3_exemption": s["art6_3_exemption"],
            "multi": s["multi_categoria"],
            "pred_annex_points": pc["annex_iii_points"],
            "pred_art5": pc["art5_letters"],
            "pred_61": pc["art6_1"],
            "art6_3_plausible": res["judgment"]["art6_3_exception"]["plausible"],
        })
        raw.append({"id": s["id"], "gold_verdict": gv, "pred_verdict": pv,
                    "result": res})
        flag = "OK" if pv == gv else "DIFF"
        print(f"[{s['id']:>4}] {s['tipo']:<8} gold={_SHORT[gv]:<7} "
              f"pred={_SHORT[pv]:<7} {flag}")

    (OUT_DIR / "raw_results.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report(gold, rows)
    print(f"\nReport: {(OUT_DIR / 'results.md').relative_to(ROOT)}")
    return 0


def _write_report(gold: dict, rows: list[dict]) -> None:
    L: list[str] = []
    L.append("# UC1 — Eval classificazione AI Act (run diagnostico)")
    L.append("")
    L.append(f"Gold: `data/benchmark/gold_uc1_classification.json` "
             f"({gold['gold_verified_date']}). Modello classify(): vedi .env "
             "(Anthropic Sonnet). Corpus read-only (fetch-by-id sul set fisso).")
    L.append("")
    L.append("**Lettura.** I `positive`/`negative` sono gold netto → strict "
             "pass/fail. Gli `edge` (incl. i 6 ri-tipizzati, ora positive) "
             "dipendono dalla bozza Orientamenti art. 6: per gli edge ANCORA "
             "edge si affianca la lettura difendibile del gold senza pass/fail. "
             "Candidate-match = recall dei candidati attesi (punto Allegato III / "
             "lettera art. 5 / flag 6(1)). Riporta, non decide.")
    L.append("")

    # ---- tabella per-scenario
    L.append("## Tabella per-scenario")
    L.append("")
    L.append("| id | tipo | settore | gold verdict | predicted | gold cand | "
             "pred cand | verdict ✓ | cand ✓ |")
    L.append("|---|---|---|---|---|---|---|:--:|:--:|")
    for r in rows:
        vm = "✅" if r["verdict_match"] else "❌"
        tag = " ⚑6(3)" if r["art6_3_exemption"] else (" ⚑multi" if r["multi"] else "")
        L.append(
            f"| {r['id']}{tag} | {r['tipo']} | {r['settore']} | "
            f"{_SHORT[r['gold_verdict']]} | {_SHORT[r['pred_verdict']]} | "
            f"{r['gold_cand']} | {r['pred_cand']} | {vm} | {r['cand_match']} |"
        )
    L.append("")

    # ---- confusion matrix (4x4) su tutti
    L.append("## Confusion matrix verdetto (righe=gold, colonne=predetto)")
    L.append("")
    cm = {g: Counter() for g in VERDICTS}
    for r in rows:
        cm[r["gold_verdict"]][r["pred_verdict"]] += 1
    L.append("| gold ↓ \\ pred → | " + " | ".join(_SHORT[v] for v in VERDICTS) + " | tot |")
    L.append("|---|" + "|".join(["--:"] * (len(VERDICTS) + 1)) + "|")
    for g in VERDICTS:
        tot = sum(cm[g].values())
        L.append(f"| **{_SHORT[g]}** | " + " | ".join(str(cm[g][p]) for p in VERDICTS)
                 + f" | {tot} |")
    L.append("")

    # ---- accuratezza per tipo (positive/negative strict)
    L.append("## Accuratezza per tipo")
    L.append("")
    L.append("| tipo | n | verdict accuracy | candidate accuracy (su scorabili) |")
    L.append("|---|--:|--:|--:|")
    for tipo in ("positive", "negative", "edge"):
        sub = [r for r in rows if r["tipo"] == tipo]
        if not sub:
            continue
        n = len(sub)
        vacc = sum(r["verdict_match"] for r in sub) / n
        scor = [r for r in sub if r["cand_match"] in ("Y", "N")]
        cacc = (sum(r["cand_match"] == "Y" for r in scor) / len(scor)) if scor else None
        cacc_s = f"{cacc:.2f}" if cacc is not None else "—"
        note = "  *(edge: NON pass/fail — vedi sotto)*" if tipo == "edge" else ""
        L.append(f"| {tipo} | {n} | {vacc:.2f}{note} | {cacc_s} |")
    L.append("")
    pn = [r for r in rows if r["tipo"] in ("positive", "negative")]
    L.append(f"**Strict accuracy positive+negative (gold stabile): "
             f"{sum(r['verdict_match'] for r in pn)}/{len(pn)} = "
             f"{sum(r['verdict_match'] for r in pn)/len(pn):.2f}.**")
    L.append("")

    # ---- edge side-by-side (no pass/fail)
    L.append("## Edge — gold-vs-predetto (NON pass/fail; divergenze marcate)")
    L.append("")
    L.append("Gli `edge` restano edge: si affianca la lettura difendibile del "
             "gold alla risposta del classificatore. ⚠ = divergenza.")
    L.append("")
    L.append("| id | gold (difendibile) | predicted | divergenza |")
    L.append("|---|---|---|:--:|")
    for r in rows:
        if r["tipo"] != "edge":
            continue
        div = "" if r["verdict_match"] else "⚠"
        L.append(f"| {r['id']} | {_SHORT[r['gold_verdict']]} | "
                 f"{_SHORT[r['pred_verdict']]} | {div} |")
    L.append("")

    # ---- isolamento art. 6(3)
    L.append("## Isolamento esenzione art. 6(3) (S10, S13, S22, S24, S37–S40)")
    L.append("")
    L.append("classify() non ha un filtro 6(3) che retroceda un alto-rischio: "
             "predice `non alto rischio` SOLO se il giudice marca tutti i punti "
             "Allegato III `applies=false`. Qui si vede se ci riesce e cosa fa "
             "il flag informativo `art6_3_exception.plausible`.")
    L.append("")
    L.append("| id | gold | predicted | punti AIII predetti | 6(3).plausible | esito |")
    L.append("|---|---|---|---|:--:|---|")
    ex = [r for r in rows if r["art6_3_exemption"]]
    for r in ex:
        pts = ",".join(map(str, r["pred_annex_points"])) or "—"
        esito = "predetto non-HR (atteso)" if r["pred_verdict"] == V_NO \
            else f"predetto {_SHORT[r['pred_verdict']]} (≠ lettura gold)"
        L.append(f"| {r['id']} | {_SHORT[r['gold_verdict']]} | "
                 f"{_SHORT[r['pred_verdict']]} | {pts} | "
                 f"{'sì' if r['art6_3_plausible'] else 'no'} | {esito} |")
    n_ok = sum(r["pred_verdict"] == V_NO for r in ex)
    L.append("")
    L.append(f"**{n_ok}/{len(ex)} scenari 6(3) predetti `non alto rischio` "
             "(allineati alla lettura difendibile del gold).**")
    L.append("")

    # ---- multi-categoria
    L.append("## Multi-categoria (S17, S50)")
    L.append("")
    L.append("Entrambi gli scenari sono 5(a)+5(d): **stesso punto 5**. Il "
             "classificatore opera a granularità di PUNTO (`annex_iii` 1-8, senza "
             "sotto-lettere) → non può rappresentare due sotto-categorie dello "
             "stesso punto. Il check 'entrambi i punti' è N/A a questa "
             "granularità (collassa su punto 5).")
    L.append("")
    L.append("| id | sotto-lettere gold | punti gold | punti predetti |")
    L.append("|---|---|---|---|")
    g_by_id = {s["id"]: s for s in gold["scenarios"]}
    for r in rows:
        if not r["multi"]:
            continue
        gc = g_by_id[r["id"]]["gold_candidates"]
        L.append(f"| {r['id']} | {','.join(gc['annex_iii_subletters'])} | "
                 f"{','.join(map(str, gc['annex_iii_points']))} | "
                 f"{','.join(map(str, r['pred_annex_points'])) or '—'} |")
    L.append("")

    (OUT_DIR / "results.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
