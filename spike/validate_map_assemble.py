"""PARTE D — validazione map→assembly su {Q68, Q70, Q76}.

Riusa le sub-query CACHED del run-4 (decomposer congelato → niente
ri-decomposizione). Retrieval reale (Qdrant+reranker, no costo API), map mini
via Haiku 4.5. Cache delle mini per non ripagare sui re-run.

    spike/.venv/bin/python spike/validate_map_assemble.py
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

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
SUBQ_CACHE = ROOT / "spike/validate_decomposer_v1_2_cache.json"
MINI_CACHE = ROOT / "spike/map_validation_cache.json"
SUBSET = ["Q68", "Q70", "Q76"]
TOP_K_HITS = 5
RERANK_POOL = 20
# Tariffa Haiku 4.5 (stima, $/M token) — token misurati, costo a questo rate.
HAIKU_IN_PER_M = 1.0
HAIKU_OUT_PER_M = 5.0


def _build_retriever():
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME
    from fastembed import SparseTextEmbedding

    client = QdrantClient(host="localhost", port=6333, timeout=5)
    encoder = BgeM3Encoder.get()
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=HYBRID_COLLECTION_NAME, reranker=reranker,
    )


def _haiku():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from core.llm_provider.anthropic_provider import AnthropicProvider
    return AnthropicProvider(
        api_key=os.environ["ANTHROPIC_API_KEY"], model="claude-haiku-4-5",
    )


class _Empty:
    text = ""
    n_input_tokens = 0
    n_output_tokens = 0
    finish_reason = "skip"


class _CachingHaiku:
    """Wrappa Haiku con cache su disco keyed sul prompt. Misura i token.

    `frozen=True` (ri-check gratuito): se un prompt non è in cache SOLLEVA,
    invece di pagare un re-run. Garantisce costo $0.
    """

    def __init__(self, inner, cache: dict, frozen: bool = False):
        self._inner = inner
        self._cache = cache
        self._frozen = frozen
        self.n_calls = 0
        self.n_miss = 0
        self.provider_name = inner.provider_name if inner else "anthropic"
        self.model_name = inner.model_name if inner else "claude-haiku-4-5"

    def generate(self, prompt, system=None, max_tokens=600, temperature=0.0):
        key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()
        if key in self._cache:
            c = self._cache[key]
        elif self._frozen:
            # Retrieval non riproducibile per questo gruppo (tie reranker →
            # top-5 riordinato → prompt diverso). NON paghiamo: skip con mini
            # vuota e conteggio. Segnalato in output.
            self.n_miss += 1
            return _Empty()
        else:
            r = self._inner.generate(
                prompt=prompt, system=system, max_tokens=max_tokens,
                temperature=temperature,
            )
            c = {
                "text": r.text, "n_input_tokens": r.n_input_tokens,
                "n_output_tokens": r.n_output_tokens,
                "finish_reason": r.finish_reason,
            }
            self._cache[key] = c
            self.n_calls += 1
            MINI_CACHE.write_text(json.dumps(self._cache, ensure_ascii=False))

        class _R:
            text = c["text"]
            n_input_tokens = c["n_input_tokens"]
            n_output_tokens = c["n_output_tokens"]
            finish_reason = c["finish_reason"]
        return _R()


def _build_cn_result(qid, question, subq_cache, retr):
    from core.cross_norm.multi_norm_trigger import detect_norms
    from core.cross_norm.retriever import CrossNormResult, SubQueryGroup
    import yaml
    g = yaml.safe_load((ROOT / "core/cross_norm/norm_glossary.yaml").read_text())
    urn = {nid: e["doc_urn"] for nid, e in g.items()}

    norms = detect_norms(question)
    groups = []
    for nid in norms:
        for sq in subq_cache.get(f"{qid}:{nid}", []):
            hits = retr.retrieve(
                query=sq, top_k=TOP_K_HITS, mode="hybrid",
                rerank_top_k=RERANK_POOL, filter_doc_urn=urn[nid],
            )
            groups.append(SubQueryGroup(sub_query=sq, source=nid, hits=list(hits)))
    return CrossNormResult(query=question, detected_norms=list(norms), groups=groups)


def _residual_breakdown(markers, universe_ids):
    """Residuo unverified spaccato: id abbreviati (no doc_urn) vs altro."""
    from core.citation_verifier.verifier import _split_cite_tokens, _token_verified
    ctx = set(universe_ids)
    abbrev, other = 0, 0
    for m in markers:
        if m.verified:
            continue
        for tok in _split_cite_tokens(m.chunk_id):
            if _token_verified(tok, ctx) or " " in tok:
                continue
            if "/" in tok:
                other += 1
            else:
                abbrev += 1
    return abbrev, other


def main() -> int:
    from core.citation_verifier import verify_citations
    from core.cross_norm.map_assemble import map_and_assemble

    frozen = os.environ.get("MAPVAL_FROZEN", "1") == "1"
    gold = {it["qid"]: it for it in json.loads(GOLD.read_text(encoding="utf-8"))}
    subq_cache = json.loads(SUBQ_CACHE.read_text(encoding="utf-8"))
    mini_cache = json.loads(MINI_CACHE.read_text()) if MINI_CACHE.is_file() else {}

    retr = _build_retriever()
    inner = None if frozen else _haiku()
    haiku = _CachingHaiku(inner, mini_cache, frozen=frozen)
    print(f"frozen={frozen} (ri-check su mini in cache, zero LLM)")

    summary = {}
    for qid in SUBSET:
        it = gold[qid]
        cn = _build_cn_result(qid, it["question"], subq_cache, retr)

        t0 = time.perf_counter()
        text, universe, minis, n_sections = map_and_assemble(
            cn, haiku, top_k_hits=TOP_K_HITS,
        )
        wall = time.perf_counter() - t0

        # gold articolo+allegato della query
        golds = []
        for c in it["gold_chunks"]:
            nid, kind, ref = parse_gold_chunk(c["chunk_id"])
            if kind == "article":
                golds.append((nid, f"Art. {ref}", c["chunk_id"]))
            elif kind == "annex_point":
                golds.append((nid, f"Allegato {ref[0]} punto {ref[1]}", c["chunk_id"]))

        # 1. Completezza: gold indirizzato da una mini (label match + cita, o cita il gold)
        addressed = []
        for nid, label, cid in golds:
            ok = any(
                m.source == nid
                and ((m.article_label == label and m.cited_chunk_ids)
                     or cid in m.cited_chunk_ids)
                for m in minis
            )
            addressed.append((nid, label, cid, ok))
        n_addr = sum(1 for *_, ok in addressed if ok)

        # 2. Faith
        universe_ids = {h.chunk_id for h in universe}
        vr = verify_citations(text, universe_ids)
        # mini che citano fuori dal proprio gruppo
        out_of_group = [
            (m.source, m.article_label,
             [c for c in m.cited_chunk_ids if c not in m.group_chunk_ids])
            for m in minis
            if any(c not in m.group_chunk_ids for c in m.cited_chunk_ids)
        ]

        # 4. costo / dimensioni
        n_in = sum(m.n_input_tokens for m in minis)
        n_out = sum(m.n_output_tokens for m in minis)
        cost = n_in / 1e6 * HAIKU_IN_PER_M + n_out / 1e6 * HAIKU_OUT_PER_M

        abbrev, other = _residual_breakdown(vr.markers, {h.chunk_id for h in universe})
        summary[qid] = {
            "minis": minis, "text": text, "n_sections": n_sections,
            "addressed": addressed, "n_addr": n_addr, "n_gold": len(golds),
            "vr": vr, "out_of_group": out_of_group,
            "resid_abbrev": abbrev, "resid_other": other,
            "n_in": n_in, "n_out": n_out, "cost": cost, "wall": wall,
            "chars": len(text),
        }
        print(f"[{qid}] done: {len(minis)} mini, {n_sections} sez, "
              f"{len(text)} char, addr {n_addr}/{len(golds)}, wall {wall:.1f}s")

    # ---------------- OUTPUT ----------------
    # "before" = numeri verifier pre-fix (osservati nel run precedente)
    BEFORE = {"Q68": (259, 259), "Q70": (362, 387), "Q76": (248, 251)}

    print("\n" + "=" * 78)
    print("RI-CHECK VERIFIER — verified PRIMA → DOPO + residuo")
    print("qid | before(v/tot) | after(v/tot) | all_verified | residuo(abbrev/other)")
    print("-" * 78)
    for qid in SUBSET:
        s = summary[qid]
        vr = s["vr"]
        bv, bt = BEFORE[qid]
        print(f"{qid} | {bv}/{bt} | {vr.n_verified}/{vr.n_total} | "
              f"{vr.all_verified} | {s['resid_abbrev']}/{s['resid_other']}")

    print("\n" + "=" * 78)
    print("TABELLA METRICHE")
    print("qid | compl(addr/tot) | faith all_verified (cite v/tot) | "
          "cost$ | wall_s | char | n_sez")
    print("-" * 78)
    for qid in SUBSET:
        s = summary[qid]
        vr = s["vr"]
        print(f"{qid} | {s['n_addr']}/{s['n_gold']} | "
              f"{vr.all_verified} ({vr.n_verified}/{vr.n_total}) | "
              f"${s['cost']:.4f} | {s['wall']:.1f} | "
              f"{s['chars']} | {s['n_sections']}")

    print("\n" + "=" * 78)
    print("Q70 — header 'Artt. N-M' (PARTE 3) — sezioni GDPR con range")
    for line in summary["Q70"]["text"].splitlines():
        if line.startswith("### ") and ("Artt." in line or "44" in line):
            print("  " + line)

    print("\n" + "=" * 78)
    print("Q70 — LISTA SEZIONI (## norma / ### articolo)")
    print("-" * 78)
    for line in summary["Q70"]["text"].splitlines():
        if line.startswith("## ") or line.startswith("### "):
            print(line)

    print("\n" + "=" * 78)
    print("Q70 — MINI dlgs art_25-octies (test anti-drowning)")
    print("-" * 78)
    found = [m for m in summary["Q70"]["minis"]
             if m.source == "dlgs_231" and "25-octies" in m.article_label]
    if not found:
        print("!!! NESSUNA mini art_25-octies — COMPRESSA VIA (drowning) !!!")
    for m in found:
        print(f"[article_label={m.article_label}] cites={m.cited_chunk_ids}")
        print(m.text)
        print()

    print("=" * 78)
    print("CITATION VERIFIER (per query)")
    for qid in SUBSET:
        s = summary[qid]
        vr = s["vr"]
        print(f"{qid}: all_verified={vr.all_verified} "
              f"verified={vr.n_verified}/{vr.n_total} "
              f"out_of_group_minis={len(s['out_of_group'])}")
        for src, lbl, bad in s["out_of_group"]:
            print(f"    OUT {src} {lbl}: {bad}")

    tot_cost = sum(s["cost"] for s in summary.values())
    print(f"\nCOSTO TOTALE stimato (Haiku ${HAIKU_IN_PER_M}/{HAIKU_OUT_PER_M} per M): "
          f"${tot_cost:.4f}  (nuove chiamate Haiku: {haiku.n_calls}, "
          f"gruppi skippati per retrieval non-riprodotto: {haiku.n_miss})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
