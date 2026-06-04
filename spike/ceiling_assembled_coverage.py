"""STEP 1: assemblaggio Python delle mini per query (no LLM).
STEP 2: coverage judge sui report assemblati (~$0.04).
Hard stop $1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MR_FILE = ROOT / "spike/data/ceiling_mapreduce_results.json"
DUMP_FILE = ROOT / "spike/data/ceiling_dispositive_paid_results.json"
OUT = ROOT / "spike/data/ceiling_assembled_coverage.json"

GOLDS = {
    "Q68": [
        ("eli/reg/2024/1689/oj__art_6", "AI Act art_6"),
        ("eli/reg/2016/679/oj__art_9", "GDPR art_9"),
        ("eli/reg/2024/1689/oj__art_27", "AI Act art_27"),
        ("eli/reg/2016/679/oj__art_35", "GDPR art_35"),
        ("akn/it/act/legge/stato/2025-09-23/132__art_7", "L.132 art_7"),
    ],
    "Q69": [("eli/reg/2024/1689/oj__art_6", "AI Act art_6")],
    "Q70": [
        ("eli/reg/2016/679/oj__art_44", "GDPR art_44"),
        ("akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies", "231 art_25-octies"),
    ],
    "Q71": [("eli/reg/2024/1689/oj__annex_III__point_5", "AnnexIII point_5")],
}

COVERAGE_PROMPT = """Stabilisci se la risposta affronta in modo SOSTANZIALE le previsioni dell'articolo target.

Articolo target: {label}
Rubrica/oggetto:
{rubric}

Estratto dell'articolo target (primo blocco):
{article_text}

Risposta da valutare:
---
{answer}
---

Criteri:
- ADDRESSED: la risposta tratta sostanzialmente almeno una previsione specifica dell'articolo target (anche senza citarne il numero), con almeno un'affermazione che ne riproduca la sostanza dispositiva.
- NOT_ADDRESSED: l'articolo è ignorato o solo accennato in modo generico.

Output (TASSATIVO): una sola riga in questo formato:
VEREDICT: ADDRESSED|NOT_ADDRESSED
REASON: <max 200 caratteri>
"""


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from anthropic import Anthropic
    from qdrant_client import QdrantClient, models

    mr = json.loads(MR_FILE.read_text())
    dump = json.loads(DUMP_FILE.read_text())
    dump_states = {(r["qid"], r["gold_id"]): r["state"] for r in dump["coverage"]}
    mr_gen_states = {(r["qid"], r["gold_id"]): r["state"] for r in mr["coverage"]}

    # === STEP 1: assemble ===
    assembled = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = mr["queries"][qid]
        # group items by src
        by_src = {}
        for it in qd["items"]:
            by_src.setdefault(it["src"], []).append(it)
        # build report
        lines = []
        for src, items in by_src.items():
            for it in items:
                lines.append(f"## [{src}] — {it['sub_query']}")
                lines.append(it["mini_answer"])
                lines.append("")
        assembled[qid] = "\n".join(lines)

    # in_ctx
    in_ctx = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        ids = set()
        for it in mr["queries"][qid]["items"]:
            for cid, _ in it["top3"]:
                ids.add(cid)
        in_ctx[qid] = ids

    # === STEP 2: coverage judge ===
    print("Coverage judge sui report assemblati (Sonnet 4.6)...")
    cli_q = QdrantClient(host="localhost", port=6333, timeout=60)
    anthropic = Anthropic()

    def fetch_payload(cid):
        flt = models.Filter(must=[models.FieldCondition(
            key="chunk_id", match=models.MatchValue(value=cid))])
        pts, _ = cli_q.scroll(collection_name="italian_legal_v1_hybrid",
                              scroll_filter=flt, limit=1, with_payload=True)
        return pts[0].payload if pts else {}

    cost_in = cost_out = calls = 0
    PRICE_IN, PRICE_OUT = 3.00, 15.00  # $/1M Sonnet 4.6

    assembled_states = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        for gold_id, label in GOLDS[qid]:
            if gold_id not in in_ctx[qid]:
                assembled_states[(qid, gold_id)] = ("NOT_IN_CONTEXT", "")
                continue
            payload = fetch_payload(gold_id)
            hp = payload.get("hierarchy_path", [])
            rubric = " > ".join(hp) if isinstance(hp, list) else str(hp)
            txt = payload.get("text", "")[:1500]
            prompt = COVERAGE_PROMPT.format(
                label=label, rubric=rubric, article_text=txt, answer=assembled[qid])
            msg = anthropic.messages.create(
                model="claude-sonnet-4-6", max_tokens=200, temperature=0.0,
                messages=[{"role": "user", "content": prompt}])
            raw = msg.content[0].text if msg.content else ""
            cost_in += msg.usage.input_tokens
            cost_out += msg.usage.output_tokens
            calls += 1
            verdict = "NOT_ADDRESSED"
            reason = ""
            for line in raw.splitlines():
                if line.upper().startswith("VEREDICT:"):
                    v = line.split(":", 1)[1].strip().upper()
                    if "ADDRESSED" in v and "NOT" not in v:
                        verdict = "ADDRESSED"
                if line.upper().startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()
            state = "ADDRESSED" if verdict == "ADDRESSED" else "DROWNED"
            assembled_states[(qid, gold_id)] = (state, reason)
            running_cost = (cost_in / 1_000_000) * PRICE_IN + \
                           (cost_out / 1_000_000) * PRICE_OUT
            print(f"  {qid} {label:<22} → {state}   (cum cost ${running_cost:.4f})")
            if running_cost > 1.0:
                print("WARN: cost > $1 hard stop, aborting.")
                break

    final_cost = (cost_in / 1_000_000) * PRICE_IN + (cost_out / 1_000_000) * PRICE_OUT

    # === OUTPUT 1: tabella 3 colonne ===
    print("\n" + "=" * 95)
    print("Tabella coverage — ASSEMBLATO vs MAP-REDUCE GEN vs DUMP SEMPLICE")
    print("=" * 95)
    print(f'{"qid":<5}{"gold":<22}{"assemblato":<16}{"mapreduce gen":<16}{"dump semplice":<16}')
    n_addr = n_drown = n_notin = 0
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        for gold_id, label in GOLDS[qid]:
            asm = assembled_states[(qid, gold_id)][0]
            mr_g = mr_gen_states.get((qid, gold_id), "?")
            dmp = dump_states.get((qid, gold_id), "?")
            print(f'{qid:<5}{label:<22}{asm:<16}{mr_g:<16}{dmp:<16}')
            if asm == "ADDRESSED": n_addr += 1
            elif asm == "DROWNED": n_drown += 1
            elif asm == "NOT_IN_CONTEXT": n_notin += 1

    # === OUTPUT 2: aggregato ===
    print("\n" + "=" * 95)
    print("Aggregato (su 9 gold) — confronto")
    print("=" * 95)
    n_a_mr = sum(1 for v in mr_gen_states.values() if v == "ADDRESSED")
    n_d_mr = sum(1 for v in mr_gen_states.values() if v == "DROWNED")
    n_n_mr = sum(1 for v in mr_gen_states.values() if v == "NOT_IN_CONTEXT")
    n_a_d = sum(1 for v in dump_states.values() if v == "ADDRESSED")
    n_d_d = sum(1 for v in dump_states.values() if v == "DROWNED")
    n_n_d = sum(1 for v in dump_states.values() if v == "NOT_IN_CONTEXT")
    print(f'{"metrica":<24}{"assemblato":>14}{"mapreduce gen":>16}{"dump semplice":>16}')
    print(f'{"ADDRESSED / 9":<24}{n_addr:>14}{n_a_mr:>16}{n_a_d:>16}')
    print(f'{"DROWNED / 9":<24}{n_drown:>14}{n_d_mr:>16}{n_d_d:>16}')
    print(f'{"NOT_IN_CONTEXT / 9":<24}{n_notin:>14}{n_n_mr:>16}{n_n_d:>16}')

    # === OUTPUT 3: diagnostico art_25-octies ===
    print("\n" + "=" * 95)
    print("DIAGNOSTICO — mini-risposta per art_25-octies (Q70 dlgs_231)")
    print("=" * 95)
    for it in mr["queries"]["Q70"]["items"]:
        if "25-octies" in it["sub_query"]:
            print(f"sub-query #{it['sq_idx']} src={it['src']}:")
            print(f"  '{it['sub_query']}'")
            print(f"top-3 chunks: {[c for c,_ in it['top3']]}")
            print(f"mini_answer:")
            print("---")
            print(it["mini_answer"])
            print("---")

    # === OUTPUT 4: lunghezze ===
    print("\n" + "=" * 95)
    print("Lunghezze report (caratteri)")
    print("=" * 95)
    print(f'{"qid":<5}{"assemblato":>14}{"finale gen":>14}{"ratio":>10}')
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        a_len = len(assembled[qid])
        f_len = len(mr["queries"][qid].get("final_answer", ""))
        ratio = a_len / f_len if f_len else float("nan")
        print(f'{qid:<5}{a_len:>14}{f_len:>14}{ratio:>10.2f}')

    print(f"\nCosto effettivo Sonnet (coverage judge): ${final_cost:.4f} ({calls} calls)")

    OUT.write_text(json.dumps({
        "assembled_reports": assembled,
        "assembled_states": {f"{k[0]}|{k[1]}": v for k, v in assembled_states.items()},
        "cost_usd": final_cost, "n_calls": calls,
        "agg_assembled": {"ADDRESSED": n_addr, "DROWNED": n_drown, "NOT_IN_CONTEXT": n_notin},
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
