"""PARTE 1b/2/3 — completa la baseline full-12 del map→assembly.

- PARTE 1b ($0): ri-normalizza i 3 artefatti già persistiti (Q68/Q70/Q76).
- PARTE 2 (paid): esegue i 9 rimanenti con normalizzazione attiva, persiste.
- PARTE 3 ($0): verifica tutte e 12 dagli artefatti e stampa le 4 tabelle.

    spike/.venv/bin/python spike/run_map_full12.py
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

from spike.validate_decomposer_v1_2 import parse_gold_chunk  # noqa: E402
from spike.validate_map_assemble import _build_cn_result, _build_retriever  # noqa: E402

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
PAID_CACHE = ROOT / "spike/map_paid_cache.json"
RUNS_DIR = ROOT / "spike/runs"
RUN_ID = "paid_subset_v1"
CACHED3 = ["Q68", "Q70", "Q76"]
NINE = ["Q3", "Q9", "Q23", "Q58", "Q65", "Q67", "Q69", "Q71", "Q72"]
ALL12 = CACHED3 + NINE
TOP_K_HITS, CONCURRENCY = 5, 6
HAIKU_IN_PER_M, HAIKU_OUT_PER_M = 1.0, 5.0
HARD_STOP_USD = float(os.environ.get("MAP_HARD_STOP", "2.85"))
PUNT_HINTS = ("non copr", "non sono coperti", "non trattano", "non affronta")


class _R:
    def __init__(s, c):
        s.text = c["text"]; s.n_input_tokens = c["n_input_tokens"]
        s.n_output_tokens = c["n_output_tokens"]; s.finish_reason = c["finish_reason"]


class PaidHaiku:
    def __init__(s, inner, cache):
        s._inner = inner; s._cache = cache
        s.provider_name = inner.provider_name; s.model_name = inner.model_name
        s.n_api = s.n_cache = s.n_err = 0
        s.api_seconds = 0.0; s.session_cost = 0.0

    def generate(s, prompt, system=None, max_tokens=600, temperature=0.0):
        key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()
        if key in s._cache:
            s.n_cache += 1
            return _R(s._cache[key])
        if s.session_cost >= HARD_STOP_USD:
            raise RuntimeError(f"HARD STOP ${HARD_STOP_USD} (sessione)")
        t = time.perf_counter()
        try:
            r = s._inner.generate(prompt=prompt, system=system,
                                  max_tokens=max_tokens, temperature=temperature)
        except Exception:
            s.n_err += 1
            raise
        s.api_seconds += time.perf_counter() - t
        s.n_api += 1
        c = {"text": r.text, "n_input_tokens": r.n_input_tokens,
             "n_output_tokens": r.n_output_tokens, "finish_reason": r.finish_reason}
        s._cache[key] = c
        s.session_cost += (r.n_input_tokens / 1e6 * HAIKU_IN_PER_M
                           + r.n_output_tokens / 1e6 * HAIKU_OUT_PER_M)
        PAID_CACHE.write_text(json.dumps(s._cache, ensure_ascii=False))
        return r


def _haiku():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from core.llm_provider.anthropic_provider import AnthropicProvider
    return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"],
                             model="claude-haiku-4-5")


def _gold_articles(it):
    out = []
    for c in it["gold_chunks"]:
        nid, kind, ref = parse_gold_chunk(c["chunk_id"])
        if kind == "article":
            out.append((nid, f"Art. {ref}", c["chunk_id"]))
        elif kind == "annex_point":
            out.append((nid, f"Allegato {ref[0]} punto {ref[1]}", c["chunk_id"]))
    return out


def renormalize_existing():
    from core.cross_norm.map_assemble import (
        MiniResult, _parse_article, assemble_report, load_norm_doc_urns,
        load_norm_short_names, normalize_minis,
    )
    urns = load_norm_doc_urns(); shorts = load_norm_short_names()
    for qid in CACHED3:
        p = RUNS_DIR / RUN_ID / f"{qid}.json"
        art = json.loads(p.read_text(encoding="utf-8"))
        uni = set(art["universe"])
        minis = []
        for g in art["groups"]:
            lbl, rub, sk = _parse_article(g["sub_query"])
            minis.append(MiniResult(
                source=g["source"], sub_query=g["sub_query"], text=g["mini"],
                cited_chunk_ids=g.get("cited_chunk_ids", []),
                group_chunk_ids=g["hit_chunk_ids"], article_label=lbl, rubric=rub,
                sort_key=sk, finish_reason="stop", n_input_tokens=0, n_output_tokens=0))
        minis = normalize_minis(minis, urns, uni)
        text, _ = assemble_report(minis, shorts)
        for g, m in zip(art["groups"], minis):
            g["mini"] = m.text; g["cited_chunk_ids"] = m.cited_chunk_ids
        art["assembled_text"] = text
        p.write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[renorm] {qid}")


def run_nine():
    from core.cross_norm.map_assemble import map_and_assemble, write_run_artifact
    gold = {it["qid"]: it for it in json.loads(GOLD.read_text(encoding="utf-8"))}
    subq = json.loads((ROOT / "spike/validate_decomposer_v1_2_cache.json").read_text())
    cache = json.loads(PAID_CACHE.read_text()) if PAID_CACHE.is_file() else {}
    retr = _build_retriever()
    haiku = PaidHaiku(_haiku(), cache)
    timings = {}
    for qid in NINE:
        cn = _build_cn_result(qid, gold[qid]["question"], subq, retr)
        t0 = time.perf_counter()
        text, universe, minis, n_sec = map_and_assemble(
            cn, haiku, top_k_hits=TOP_K_HITS, concurrency=CONCURRENCY)
        wall = time.perf_counter() - t0
        write_run_artifact(RUNS_DIR, RUN_ID, qid, cn, minis, text, universe)
        cost = sum(m.n_input_tokens for m in minis) / 1e6 * HAIKU_IN_PER_M \
            + sum(m.n_output_tokens for m in minis) / 1e6 * HAIKU_OUT_PER_M
        timings[qid] = {"wall": wall, "n_groups": len(cn.groups),
                        "n_fail": sum(1 for m in minis if m.finish_reason == "error")}
        print(f"[{qid}] {len(minis)} mini, {n_sec} sez, {len(text)} char, wall {wall:.1f}s")
    return haiku, timings


def verify_all():
    from core.citation_verifier import verify_citations
    from core.citation_verifier.verifier import _split_cite_tokens, _token_verified
    from core.cross_norm.map_assemble import MAP_FAIL_PREFIX, _parse_article
    gold = {it["qid"]: it for it in json.loads(GOLD.read_text(encoding="utf-8"))}
    rows = {}
    for qid in ALL12:
        art = json.loads((RUNS_DIR / RUN_ID / f"{qid}.json").read_text(encoding="utf-8"))
        uni = set(art["universe"]); groups = art["groups"]
        vr = verify_citations(art["assembled_text"], uni)
        abbrev = other = 0
        for m in vr.markers:
            if m.verified:
                continue
            for tok in _split_cite_tokens(m.chunk_id):
                if _token_verified(tok, uni) or " " in tok:
                    continue
                if "/" in tok:
                    other += 1
                else:
                    abbrev += 1
        golds = _gold_articles(gold[qid])
        addr = miss_marker = punt = 0
        miss_list = []
        for nid, label, cid in golds:
            cands = [g for g in groups if g["source"] == nid
                     and (_parse_article(g["sub_query"])[0] == label or cid in g["hit_chunk_ids"])]
            is_addr = any(
                g["cited_chunk_ids"] and not g["mini"].startswith(MAP_FAIL_PREFIX)
                and (cid in g["cited_chunk_ids"] or _parse_article(g["sub_query"])[0] == label)
                for g in cands)
            if is_addr:
                addr += 1
                continue
            miss_list.append((nid, label))
            # substantive ma senza cite → missing-marker; altrimenti punt/assente
            substantive = any(
                not g["mini"].startswith(MAP_FAIL_PREFIX)
                and len(g["mini"].strip()) > 60
                and not any(h in g["mini"][:160].lower() for h in PUNT_HINTS)
                and not g["cited_chunk_ids"]
                for g in cands)
            if substantive:
                miss_marker += 1
            else:
                punt += 1
        # anti-drowning sanity: sezioni-gold punt o vuote
        rows[qid] = {"vr": vr, "abbrev": abbrev, "other": other,
                     "addr": addr, "ngold": len(golds), "miss_marker": miss_marker,
                     "punt": punt, "miss_list": miss_list,
                     "chars": len(art["assembled_text"]),
                     "n_sec": sum(1 for ln in art["assembled_text"].splitlines()
                                  if ln.startswith("### "))}
    return rows


def main() -> int:
    print("== PARTE 1b: re-normalizzazione artefatti cached ==")
    renormalize_existing()
    print("\n== PARTE 2: run dei 9 ==")
    haiku, timings = run_nine()
    print("\n== PARTE 3: verifica full-12 (artefatti) ==")
    rows = verify_all()

    PREV = {"Q68": "5/5", "Q70": "5/5", "Q76": "4/4"}
    print("\n--- 1. FAITH ---")
    print("qid | verified/tot | all | abbrev | other")
    for q in ALL12:
        r = rows[q]; v = r["vr"]
        print(f"{q:4} | {v.n_verified}/{v.n_total} | {v.all_verified} | {r['abbrev']} | {r['other']}")

    print("\n--- 2. COMPLETEZZA (addressed/gold; marker-mancante; punt) ---")
    print("qid | addr/gold | miss-marker | punt | miss")
    tot_mm = 0
    for q in ALL12:
        r = rows[q]; tot_mm += r["miss_marker"]
        prev = f" (prev {PREV[q]})" if q in PREV else ""
        print(f"{q:4} | {r['addr']}/{r['ngold']}{prev} | {r['miss_marker']} | {r['punt']} | {r['miss_list']}")
    print(f"TOTALE casi marker-mancante (full-12): {tot_mm}")

    print("\n--- 3. ANTI-DROWNING (gold dispositivi con punt/sezione vuota) ---")
    for q in ALL12:
        r = rows[q]
        flag = "OK" if r["punt"] == 0 else f"PUNT su {r['miss_list']}"
        print(f"{q:4} | punt={r['punt']} | {flag}")

    print("\n--- 4. COSTO / DIMENSIONI ---")
    print("qid | wall_map | char | n_sez")
    for q in NINE:
        t = timings[q]
        print(f"{q:4} | {t['wall']:.1f}s | {rows[q]['chars']} | {rows[q]['n_sec']}  fail={t['n_fail']}")
    print(f"\nAPI nuove={haiku.n_api} cache_hit={haiku.n_cache} err(tot)={haiku.n_err}")
    print(f"COSTO sessione (9 query) = ${haiku.session_cost:.4f}")
    print(f"wall map 9 = {sum(timings[q]['wall'] for q in NINE):.1f}s  "
          f"vs API cumulato ≈ {haiku.api_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
