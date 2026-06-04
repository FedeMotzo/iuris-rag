"""PARTE 2+3 — giro a pagamento subset {Q68,Q70,Q76}: Haiku vero, concurrency=6,
artefatti persistiti, poi verifica sugli artefatti (esatta, niente re-run).

Sub-query da cache run-4 (decomposer congelato). Cache mini su disco → re-run
gratis. Costo atteso ~$0.80, hard stop locale a $1.15 (sotto il $1.20 utente).

    spike/.venv/bin/python spike/run_map_paid_subset.py
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
SUBSET = ["Q68", "Q70", "Q76"]
TOP_K_HITS = 5
CONCURRENCY = 6
HAIKU_IN_PER_M, HAIKU_OUT_PER_M = 1.0, 5.0
HARD_STOP_USD = 1.15
PREV = {"Q68": (5, 5), "Q70": (5, 5), "Q76": (4, 4)}


class _R:
    def __init__(self, c):
        self.text = c["text"]; self.n_input_tokens = c["n_input_tokens"]
        self.n_output_tokens = c["n_output_tokens"]; self.finish_reason = c["finish_reason"]


class PaidHaiku:
    """Haiku reale + cache su disco + contatori (cost, concorrenza, errori)."""

    def __init__(self, inner, cache):
        self._inner = inner; self._cache = cache
        self.provider_name = inner.provider_name; self.model_name = inner.model_name
        self.n_api = 0; self.n_cache = 0; self.n_err = 0; self.api_seconds = 0.0

    def generate(self, prompt, system=None, max_tokens=600, temperature=0.0):
        key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()
        if key in self._cache:
            self.n_cache += 1
            return _R(self._cache[key])
        # hard-stop budget prima di pagare un'altra chiamata
        cost = self._cache.get("__cost__", 0.0)
        if cost >= HARD_STOP_USD:
            raise RuntimeError(f"HARD STOP budget ${HARD_STOP_USD} raggiunto")
        t = time.perf_counter()
        try:
            r = self._inner.generate(prompt=prompt, system=system,
                                     max_tokens=max_tokens, temperature=temperature)
        except Exception:
            self.n_err += 1
            raise
        self.api_seconds += time.perf_counter() - t
        self.n_api += 1
        c = {"text": r.text, "n_input_tokens": r.n_input_tokens,
             "n_output_tokens": r.n_output_tokens, "finish_reason": r.finish_reason}
        self._cache[key] = c
        self._cache["__cost__"] = cost + (
            r.n_input_tokens / 1e6 * HAIKU_IN_PER_M
            + r.n_output_tokens / 1e6 * HAIKU_OUT_PER_M
        )
        PAID_CACHE.write_text(json.dumps(self._cache, ensure_ascii=False))
        return r


def _haiku():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from core.llm_provider.anthropic_provider import AnthropicProvider
    return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"],
                             model="claude-haiku-4-5")


def main() -> int:
    from core.citation_verifier import verify_citations
    from core.citation_verifier.verifier import _split_cite_tokens, _token_verified
    from core.cross_norm.map_assemble import (
        MAP_FAIL_PREFIX, _parse_article, map_and_assemble, write_run_artifact,
    )

    gold = {it["qid"]: it for it in json.loads(GOLD.read_text(encoding="utf-8"))}
    subq = json.loads((ROOT / "spike/validate_decomposer_v1_2_cache.json").read_text())
    cache = json.loads(PAID_CACHE.read_text()) if PAID_CACHE.is_file() else {}

    retr = _build_retriever()
    haiku = PaidHaiku(_haiku(), cache)

    per_q = {}
    for qid in SUBSET:
        it = gold[qid]
        cn = _build_cn_result(qid, it["question"], subq, retr)
        t0 = time.perf_counter()
        text, universe, minis, n_sec = map_and_assemble(
            cn, haiku, top_k_hits=TOP_K_HITS, concurrency=CONCURRENCY,
        )
        wall = time.perf_counter() - t0
        path = write_run_artifact(RUNS_DIR, RUN_ID, qid, cn, minis, text, universe)
        n_in = sum(m.n_input_tokens for m in minis)
        n_out = sum(m.n_output_tokens for m in minis)
        cost = n_in / 1e6 * HAIKU_IN_PER_M + n_out / 1e6 * HAIKU_OUT_PER_M
        n_fail = sum(1 for m in minis if m.finish_reason == "error")
        per_q[qid] = {"wall": wall, "path": path, "minis": minis, "n_sec": n_sec,
                      "chars": len(text), "cost": cost, "n_fail": n_fail,
                      "n_groups": len(cn.groups)}
        print(f"[{qid}] {len(minis)} mini, {n_sec} sez, {len(text)} char, "
              f"fail={n_fail}, wall={wall:.1f}s → {path.name}")

    # -------- PARTE 3: verifica sugli ARTEFATTI persistiti (esatto) --------
    print("\n" + "=" * 70)
    print("PARTE 3 — gate (su artefatti persistiti)")
    for qid in SUBSET:
        art = json.loads((RUNS_DIR / RUN_ID / f"{qid}.json").read_text(encoding="utf-8"))
        groups = art["groups"]
        uni = set(art["universe"])

        # FAITH
        vr = verify_citations(art["assembled_text"], uni)
        abbrev = other = 0
        for m in vr.markers:
            if m.verified:
                continue
            for tok in _split_cite_tokens(m.chunk_id):
                if _token_verified(tok, uni) or " " in tok:
                    continue
                other += 1 if "/" in tok else 0
                abbrev += 0 if "/" in tok else 1

        # COMPLETEZZA
        golds = []
        for c in it_chunks(gold[qid]):
            golds.append(c)
        addressed = 0
        miss = []
        for nid, label, cid in golds:
            ok = any(
                g["source"] == nid
                and g["cited_chunk_ids"]
                and not g["mini"].startswith(MAP_FAIL_PREFIX)
                and (cid in g["cited_chunk_ids"] or _parse_article(g["sub_query"])[0] == label)
                for g in groups
            )
            addressed += 1 if ok else 0
            if not ok:
                miss.append((nid, label))
        per_q[qid].update(vr=vr, abbrev=abbrev, other=other,
                          addr=addressed, ngold=len(golds), miss=miss)

    # -------- OUTPUT --------
    print("\n1. ANTI-DROWNING Q70 art_25-octies:")
    a70 = json.loads((RUNS_DIR / RUN_ID / "Q70.json").read_text(encoding="utf-8"))
    oct_g = [g for g in a70["groups"]
             if g["source"] == "dlgs_231" and "25-octies" in g["sub_query"]]
    if not oct_g:
        print("   !!! ASSENTE — drowned !!!")
    for g in oct_g:
        print(f"   [sub_query] {g['sub_query'][:80]}")
        print(f"   [cited] {g['cited_chunk_ids']}")
        print("   " + g["mini"].replace("\n", "\n   "))

    print("\n2. COMPLETEZZA addressed/totale (prev → ora):")
    for qid in SUBSET:
        s = per_q[qid]; pv = PREV[qid]
        print(f"   {qid}: {pv[0]}/{pv[1]} → {s['addr']}/{s['ngold']}"
              + (f"  MISS={s['miss']}" if s["miss"] else ""))

    print("\n3. FAITH (artefatti persistiti):")
    for qid in SUBSET:
        s = per_q[qid]; vr = s["vr"]
        print(f"   {qid}: verified {vr.n_verified}/{vr.n_total} all={vr.all_verified} "
              f"residuo abbrev={s['abbrev']} other={s['other']}")

    print("\n4. CONCORRENZA:")
    for qid in SUBSET:
        s = per_q[qid]
        print(f"   {qid}: wall_map={s['wall']:.1f}s  n_groups={s['n_groups']}  fail={s['n_fail']}")
    print(f"   API: chiamate={haiku.n_api} cache_hit={haiku.n_cache} errori(tot)={haiku.n_err}")
    print(f"   tempo API cumulato (≈sequenziale)={haiku.api_seconds:.1f}s vs "
          f"wall map totale={sum(s['wall'] for s in per_q.values()):.1f}s")

    print("\n5. COSTO / DIMENSIONI:")
    tot = 0.0
    for qid in SUBSET:
        s = per_q[qid]; tot += s["cost"]
        print(f"   {qid}: ${s['cost']:.4f}  char={s['chars']}  sez={s['n_sec']}")
    print(f"   TOTALE ${tot:.4f} (Haiku ${HAIKU_IN_PER_M}/{HAIKU_OUT_PER_M} per M; "
          f"nuove chiamate API={haiku.n_api})")
    return 0


def it_chunks(it):
    out = []
    for c in it["gold_chunks"]:
        nid, kind, ref = parse_gold_chunk(c["chunk_id"])
        if kind == "article":
            out.append((nid, f"Art. {ref}", c["chunk_id"]))
        elif kind == "annex_point":
            out.append((nid, f"Allegato {ref[0]} punto {ref[1]}", c["chunk_id"]))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
