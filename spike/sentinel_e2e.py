"""PARTE 3 — sentinelle mono end-to-end attraverso la pipeline INTERA (paid).

enable_cross_norm=True → query mono: detect_norms==1 → fallback HybridRetriever
diretto → generazione (Sonnet) → _do_verify. Verifica chiusura path mono.

    spike/.venv/bin/python spike/sentinel_e2e.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spike.validate_decomposer_v1_2 import parse_gold_chunk  # noqa: E402
from spike.validate_map_assemble import _build_retriever  # noqa: E402

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
SENTINELS = {"Q34": "gdpr", "Q11": "ai_act", "Q40": "nis2",
             "Q25": "dlgs_231", "Q62": "codice_privacy"}
SONNET_IN, SONNET_OUT = 3.0, 15.0  # $/M (stima)


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from core.cross_norm.multi_norm_trigger import detect_norms
    from core.llm_provider.config import load_provider_from_env
    from core.serving.pipeline import RAGPipeline

    gold = {it["qid"]: it for it in json.loads(GOLD.read_text())}
    retr = _build_retriever()
    llm = load_provider_from_env()  # Sonnet di default
    pipe = RAGPipeline(retriever=retr, llm_provider=llm, top_k=5, rerank_top_k=20,
                       enable_cross_norm=True)

    rows = {}
    cost = 0.0
    for qid, nid in SENTINELS.items():
        it = gold[qid]
        assert detect_norms(it["question"]) == [nid], f"{qid} non mono {nid}"
        gold_arts = {c["chunk_id"] for c in it["gold_chunks"]
                     if parse_gold_chunk(c["chunk_id"])[1] in ("article", "annex_point")}
        green = True
        try:
            resp = pipe.query(it["question"])
        except Exception as exc:  # noqa: BLE001
            rows[qid] = {"green": False, "err": str(exc)[:80]}
            continue
        retr_ids = {h.chunk_id for h in resp.retrieval_result}
        cited = {m.chunk_id for m in resp.verification.markers}
        g = resp.generation_meta
        cost += g.n_input_tokens / 1e6 * SONNET_IN + g.n_output_tokens / 1e6 * SONNET_OUT
        rows[qid] = {
            "green": green,
            "gold_retrieved": bool(gold_arts & retr_ids),
            "gold_cited": bool(gold_arts & cited),
            "verifier": resp.verification.all_verified,
            "n_cite": resp.verification.n_total,
            "n_unver": resp.verification.n_unverified,
            "answer_chars": len(resp.answer),
        }
        print(f"[{qid}] green ok, cite={resp.verification.n_total} "
              f"unver={resp.verification.n_unverified}")

    print("\n" + "=" * 74)
    print("PARTE 3 — END-TO-END mono (pipeline intera)")
    print("qid  | norm        | green | gold_retr | gold_cited | verifier(v/tot) | chars")
    print("-" * 74)
    regress = False
    for qid, nid in SENTINELS.items():
        r = rows[qid]
        if not r["green"]:
            print(f"{qid:4} | {nid:11} | NO  err={r['err']}")
            regress = True
            continue
        nver = r["n_cite"] - r["n_unver"]
        print(f"{qid:4} | {nid:11} | {'OK':^5} | {str(r['gold_retrieved']):^9} | "
              f"{str(r['gold_cited']):^10} | {nver}/{r['n_cite']} {'✓' if r['verifier'] else '✗'} | {r['answer_chars']}")
        if not (r["gold_retrieved"] and r["gold_cited"] and r["verifier"]):
            regress = True

    print("\nVERDETTO PARTE 3:",
          "zero regressioni mono-norma" if not regress
          else "ATTENZIONE: una sentinella non chiude")
    print(f"COSTO stimato Sonnet (5 query) = ${cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
