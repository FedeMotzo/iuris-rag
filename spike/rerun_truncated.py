"""PARTE 2 — re-run chirurgico delle SOLE mini troncate (finish=length) sui 12.

Re-retrieval deterministico (locale, $0) per ricostruire i prompt + score; riusa
dalla cache le mini NON troncate; rigenera solo le troncate col nuovo cap
(1200, retry 2000). Patcha <qid>.json e <qid>.presentation.json, ri-verifica.

    spike/.venv/bin/python spike/rerun_truncated.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spike.validate_map_assemble import _build_cn_result, _build_retriever  # noqa: E402

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
SUBQ = ROOT / "spike/validate_decomposer_v1_2_cache.json"
MAIN_CACHE = ROOT / "spike/map_paid_cache.json"
REGEN_CACHE = ROOT / "spike/map_regen_cache.json"
RUNS = ROOT / "spike/runs/paid_subset_v1"
ALL12 = ["Q68", "Q70", "Q76", "Q3", "Q9", "Q23", "Q58", "Q65", "Q67", "Q69", "Q71", "Q72"]
TOP_K, RERANK_POOL = 5, 20
HAIKU_IN, HAIKU_OUT = 1.0, 5.0
HARD_STOP = float(os.environ.get("RERUN_HARD_STOP", "0.48"))


class _R:
    def __init__(s, c):
        s.text = c["text"]; s.n_input_tokens = c["n_input_tokens"]
        s.n_output_tokens = c["n_output_tokens"]; s.finish_reason = c["finish_reason"]


class RegenHaiku:
    """Rigenera solo i prompt richiesti; cache per (max_tokens, prompt)."""

    provider_name = "anthropic"; model_name = "claude-haiku-4-5"

    def __init__(s, inner, cache):
        s._inner = inner; s._cache = cache
        s.n_api = 0; s.session_cost = 0.0

    def generate(s, prompt, system=None, max_tokens=1200, temperature=0.0):
        key = hashlib.sha1(f"{max_tokens}\n{prompt}".encode()).hexdigest()
        if key in s._cache:
            return _R(s._cache[key])
        if s.session_cost >= HARD_STOP:
            raise RuntimeError(f"HARD STOP ${HARD_STOP}")
        r = s._inner.generate(prompt=prompt, system=system,
                              max_tokens=max_tokens, temperature=temperature)
        c = {"text": r.text, "n_input_tokens": r.n_input_tokens,
             "n_output_tokens": r.n_output_tokens, "finish_reason": r.finish_reason}
        s._cache[key] = c
        s.n_api += 1
        s.session_cost += r.n_input_tokens / 1e6 * HAIKU_IN + r.n_output_tokens / 1e6 * HAIKU_OUT
        REGEN_CACHE.write_text(json.dumps(s._cache, ensure_ascii=False))
        return r


def _haiku():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from core.llm_provider.anthropic_provider import AnthropicProvider
    return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"], model="claude-haiku-4-5")


def main() -> int:
    from core.citation_verifier import verify_citations
    from core.cross_norm.map_assemble import (
        MAP_MAX_TOKENS, MiniResult, _map_one, _parse_article,
        build_run_artifact, collect_universe, load_norm_doc_urns,
        load_norm_short_names, normalize_mini_text, normalize_minis,
    )
    from core.cross_norm.presentation import GroupView, build_presentation

    gold = {it["qid"]: it for it in json.loads(GOLD.read_text())}
    subq = json.loads(SUBQ.read_text())
    regen_cache = json.loads(REGEN_CACHE.read_text()) if REGEN_CACHE.is_file() else {}
    urns = load_norm_doc_urns(); shorts = load_norm_short_names()

    retr = _build_retriever()
    haiku = RegenHaiku(_haiku(), regen_cache)

    report = {}
    for qid in ALL12:
        cn = _build_cn_result(qid, gold[qid]["question"], subq, retr)
        art = json.loads((RUNS / f"{qid}.json").read_text())
        uni_ids = {c for c in art["universe"]}
        # trigger: rigenera SOLO i gruppi la cui mini (normalizzata) resta
        # unverified → sono i frammenti da troncamento (≈28), non tutte le length.
        minis, n_regen = [], 0
        for g, ag in zip(cn.groups, art["groups"]):
            lbl, rub, sk = _parse_article(g.sub_query)
            cur_body = normalize_mini_text(ag["mini"], urns.get(g.source, ""), uni_ids)
            ok = verify_citations(cur_body, uni_ids).all_verified
            if ok:
                minis.append(MiniResult(
                    source=g.source, sub_query=g.sub_query, text=ag["mini"],
                    cited_chunk_ids=[], group_chunk_ids=[h.chunk_id for h in g.hits[:TOP_K]],
                    article_label=lbl, rubric=rub, sort_key=sk,
                    finish_reason="stop", n_input_tokens=0, n_output_tokens=0,
                    truncated=False))
            else:
                minis.append(_map_one(g, haiku, TOP_K, MAP_MAX_TOKENS))
                n_regen += 1

        universe = collect_universe(cn.groups, top_k_hits=TOP_K)
        uni_ids = {h.chunk_id for h in universe}
        minis = normalize_minis(minis, urns, uni_ids)

        # artefatto + presentation patchati
        art = build_run_artifact(qid, cn, minis, "", universe, top_k_hits=TOP_K)
        gvs = [GroupView(source=g.source, sub_query=g.sub_query, body=m.text,
                         hit_chunk_ids=[h.chunk_id for h in g.hits[:TOP_K]],
                         score=float(g.hits[0].score) if g.hits else 0.0,
                         truncated=m.truncated)
               for g, m in zip(cn.groups, minis)]
        pres = build_presentation(cn.detected_norms, gvs, shorts)
        art["assembled_text"] = "\n\n".join(
            f"## {n.short_name}\n\n" + "\n\n".join(
                f"### {a.article} — {a.rubric}\n\n{a.body}" for a in n.articles)
            for n in pres.norms)
        (RUNS / f"{qid}.json").write_text(json.dumps(art, ensure_ascii=False, indent=2))
        (RUNS / f"{qid}.presentation.json").write_text(
            json.dumps(pres.to_dict(), ensure_ascii=False, indent=2))

        # verifica globale post (universo pieno)
        vr = verify_citations("\n\n".join(g.body for g in gvs), uni_ids)
        still_trunc = sum(1 for m in minis if m.truncated)
        unver_sec = [(n.norm_id, a.article) for n in pres.norms for a in n.articles
                     if not a.verified]
        report[qid] = {"regen": n_regen, "still_trunc": still_trunc,
                       "global_unver": vr.n_total - vr.n_verified,
                       "unver_sec": unver_sec, "pres": pres}
        print(f"[{qid}] regen={n_regen} still_trunc={still_trunc} "
              f"global_unver={vr.n_total - vr.n_verified}")

    # -------- OUTPUT --------
    print("\n=== 1. UNVERIFIED full-12 dopo re-run (per-sezione) ===")
    print("qid  | global_unver | sezioni unverified | still_truncated")
    tot_unver = tot_trunc = 0
    for q in ALL12:
        r = report[q]; tot_unver += r["global_unver"]; tot_trunc += r["still_trunc"]
        print(f"{q:4} | {r['global_unver']:^12} | {len(r['unver_sec'])} {r['unver_sec'] or ''} | {r['still_trunc']}")
    print(f"TOT global_unver={tot_unver}  still_truncated={tot_trunc}")

    print("\n=== 2. mini ANCORA truncated dopo retry 2000 ===")
    any_t = False
    for q in ALL12:
        if report[q]["still_trunc"]:
            any_t = True
            print(f"  {q}: {report[q]['still_trunc']}")
    if not any_t:
        print("  nessuna")

    for q in ("Q70", "Q72"):
        print(f"\n=== 3. ORIENTAMENTO COMPATTO {q} ===")
        print(report[q]["pres"].orientation)

    print(f"\nAPI nuove={haiku.n_api}  COSTO sessione=${haiku.session_cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
