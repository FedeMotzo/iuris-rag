"""Paid run: 4 generation con contesto = union_top3 + RAGAS + coverage judge.

Costo atteso ~$2-3. Hard stop a $5 (controllato post-hoc; se va oltre, dichiarare).

    spike/.venv/bin/python spike/ceiling_paid_dispositive.py
"""
from __future__ import annotations

import json
import logging
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UNION_FILE = ROOT / "spike/data/ceiling_union_results.json"
GOLD_FILE = ROOT / "data/benchmark/gold_answers_v3.json"
OUT = ROOT / "spike/data/ceiling_dispositive_paid_results.json"

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

COVERAGE_PROMPT = """Devi valutare se una risposta normativa affronta in modo SOSTANZIALE le previsioni dell'articolo target.

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
- ADDRESSED: la risposta tratta sostanzialmente almeno una delle previsioni specifiche dell'articolo target. Anche senza citarne il numero, ma con un'affermazione che ne riproduce la sostanza dispositiva. (Non basta un richiamo generico.)
- NOT_ADDRESSED: l'articolo è ignorato o solo accennato in modo troppo generico per essere considerato trattato.

Output (TASSATIVO): una sola riga in questo formato:
VEREDICT: ADDRESSED|NOT_ADDRESSED
REASON: <max 200 caratteri di motivazione>
"""


def _ragas_judge(outputs, R, judge, embeddings):
    return R._evaluate_batch(outputs, judge, embeddings)


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("dispositive")
    log.setLevel(logging.INFO)

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)

    from qdrant_client import QdrantClient, models
    from core.citation_verifier import verify_citations
    from core.hybrid_retriever.types import RetrievalHit, RetrievalResult
    from core.llm_provider.config import load_provider_from_env
    from core.rag_prompt import build_user_prompt, load_system_prompt

    cli = QdrantClient(host="localhost", port=6333, timeout=60)

    def fetch_payload(cid: str) -> dict:
        flt = models.Filter(must=[models.FieldCondition(
            key="chunk_id", match=models.MatchValue(value=cid))])
        pts, _ = cli.scroll(collection_name="italian_legal_v1_hybrid",
                            scroll_filter=flt, limit=1, with_payload=True)
        return pts[0].payload if pts else {}

    llm = load_provider_from_env()
    print(f"provider={llm.provider_name} model={llm.model_name}")
    system_prompt = load_system_prompt("it")
    gold_data = {e["qid"]: e for e in json.loads(GOLD_FILE.read_text())}
    union = json.loads(UNION_FILE.read_text())

    # === STEP 1: generation per query ===
    outputs = []
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        ud = union[qid]
        ut3 = ud["union_top3"]  # list[(cid, src, score)]
        chunk_ids = [c[0] for c in ut3]
        log.info("[%s] fetching %d chunks for union_top3...", qid, len(chunk_ids))
        # Build RetrievalHit list to feed build_user_prompt
        hits = []
        for i, (cid, src, score) in enumerate(ut3, 1):
            p = fetch_payload(cid)
            hits.append(RetrievalHit(chunk_id=cid, score=float(score),
                                     payload=p, rank=i))
        ret = RetrievalResult(hits)
        question = gold_data[qid]["question"]
        gold_answer = gold_data[qid].get("gold_answer", "")
        user_prompt = build_user_prompt(question, ret, include_expanded=False)
        # Sanity: prompt length
        prompt_chars = len(user_prompt)
        log.info("[%s] prompt chars=%d (n_chunks=%d)", qid, prompt_chars, len(hits))

        log.info("[%s] generating (max_tokens=4000)...", qid)
        gen = llm.generate(prompt=user_prompt, system=system_prompt,
                           max_tokens=4000, temperature=0.0)
        answer_raw = gen.text
        verif = verify_citations(answer_raw,
                                 retrieval_context={h.chunk_id for h in ret})
        answer = verif.annotated_text

        outputs.append({
            "qid": qid, "question": question,
            "contexts": [(h.payload.get("text") or "").strip() for h in hits],
            "answer": answer, "ground_truth": gold_answer,
            "n_chunk": len(hits), "prompt_chars": prompt_chars,
            "answer_chars": len(answer),
            "union_top3_ids": chunk_ids,
        })
        log.info("[%s] answer_chars=%d", qid, len(answer))

    # save intermediate
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"outputs": outputs}, ensure_ascii=False, indent=2,
                              default=str), encoding="utf-8")
    log.info("Intermediate saved (pre-judge): %s", OUT)

    # === STEP 2: RAGAS faithfulness + answer_relevancy ===
    sys.path.insert(0, str(ROOT / "spike"))
    import run_ragas_eval_v2 as R
    from langchain_huggingface import HuggingFaceEmbeddings

    R._load_env()
    client, tracker = R.build_tracked_client(enable_caching=False)
    judge = R.build_judge(client)
    embeddings = HuggingFaceEmbeddings(model_name=R.EMBEDDINGS_MODEL)

    log.info("RAGAS judge su %d outputs...", len(outputs))
    rows = R._evaluate_batch(outputs, judge, embeddings)
    for o, row in zip(outputs, rows, strict=True):
        o["faithfulness"] = float(row["faithfulness"]) if row.get("faithfulness") is not None else None
        o["answer_relevancy"] = float(row["answer_relevancy"]) if row.get("answer_relevancy") is not None else None
    ragas_cost = R.cost_from_tracker(tracker)
    log.info("RAGAS done. cost≈$%.3f calls=%d", ragas_cost, tracker["n_calls"])

    # === STEP 3: coverage judge per gold ===
    log.info("Coverage judge: %d gold totali...", sum(len(g) for g in GOLDS.values()))
    coverage_calls = 0
    coverage_results = []
    for o in outputs:
        qid = o["qid"]
        in_ctx_ids = set(o["union_top3_ids"])
        gold_list = GOLDS[qid]
        for gold_id, label in gold_list:
            row = {"qid": qid, "gold_id": gold_id, "label": label}
            if gold_id not in in_ctx_ids:
                row["state"] = "NOT_IN_CONTEXT"
                row["judge_reason"] = ""
                coverage_results.append(row)
                continue
            # Fetch gold rubric/text
            payload = fetch_payload(gold_id)
            text = payload.get("text", "")[:1500]  # primo blocco
            hp = payload.get("hierarchy_path", [])
            rubric = " > ".join(hp) if isinstance(hp, list) else str(hp)
            prompt = COVERAGE_PROMPT.format(
                label=label, rubric=rubric, article_text=text, answer=o["answer"])
            cv = llm.generate(prompt=prompt, system=None, max_tokens=200, temperature=0.0)
            coverage_calls += 1
            txt = (cv.text or "").strip()
            verdict = "NOT_ADDRESSED"
            reason = ""
            for line in txt.splitlines():
                if line.upper().startswith("VEREDICT:"):
                    v = line.split(":", 1)[1].strip().upper()
                    if "ADDRESSED" in v and "NOT" not in v:
                        verdict = "ADDRESSED"
                    elif "NOT_ADDRESSED" in v or "NOT ADDRESSED" in v:
                        verdict = "NOT_ADDRESSED"
                if line.upper().startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()
            row["state"] = "ADDRESSED" if verdict == "ADDRESSED" else "DROWNED"
            row["judge_reason"] = reason
            row["judge_raw"] = txt
            coverage_results.append(row)
            log.info("  %s %s → %s", qid, label, row["state"])

    # === OUTPUT ===
    print("\n" + "=" * 80)
    print("TABELLA 1 — per query: faith, ar, n_chunk, answer_chars")
    print("=" * 80)
    print(f'{"qid":<5}{"faith":>10}{"ar":>10}{"n_chunk":>10}{"ans_chars":>12}')
    for o in outputs:
        fa = o.get("faithfulness"); ar = o.get("answer_relevancy")
        fa_s = f'{fa:.3f}' if fa is not None and fa == fa else 'nan'
        ar_s = f'{ar:.3f}' if ar is not None and ar == ar else 'nan'
        print(f'{o["qid"]:<5}{fa_s:>10}{ar_s:>10}{o["n_chunk"]:>10}{o["answer_chars"]:>12}')

    print("\n" + "=" * 80)
    print("TABELLA 2 — per gold: stato")
    print("=" * 80)
    print(f'{"qid":<5}{"gold":<22}{"state":<18}{"reason"}')
    n_addr = n_drown = n_notin = 0
    for r in coverage_results:
        st = r["state"]
        if st == "ADDRESSED": n_addr += 1
        elif st == "DROWNED": n_drown += 1
        elif st == "NOT_IN_CONTEXT": n_notin += 1
        reason = r.get("judge_reason", "")[:80]
        print(f'{r["qid"]:<5}{r["label"]:<22}{st:<18}{reason}')

    print("\n" + "=" * 80)
    print("AGGREGATO (su 9 gold)")
    print("=" * 80)
    faith_vals = [o.get("faithfulness") for o in outputs
                  if o.get("faithfulness") is not None and o.get("faithfulness") == o.get("faithfulness")]
    print(f'  ADDRESSED        : {n_addr}/9')
    print(f'  DROWNED          : {n_drown}/9')
    print(f'  NOT_IN_CONTEXT   : {n_notin}/9')
    if faith_vals:
        print(f'  faithfulness mediana: {statistics.median(faith_vals):.3f}')
    print()
    print(f'Costo RAGAS ≈ ${ragas_cost:.3f}  (n_calls={tracker["n_calls"]})')
    print(f'Coverage judge calls: {coverage_calls}')

    OUT.write_text(json.dumps({
        "outputs": outputs, "coverage": coverage_results,
        "aggregate": {"ADDRESSED": n_addr, "DROWNED": n_drown, "NOT_IN_CONTEXT": n_notin,
                      "faith_median": statistics.median(faith_vals) if faith_vals else None,
                      "ragas_cost_usd": ragas_cost, "ragas_calls": tracker["n_calls"],
                      "coverage_calls": coverage_calls},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
