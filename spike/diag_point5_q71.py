"""Diagnostica retrieval di point_5 (Allegato III AI Act) per Q71.
Locale, $0, niente LLM. Test dense/sparse/hybrid/rerank per ogni sub-query.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUBQ_FILE = ROOT / "spike/data/declarative_subqueries.json"

TARGET_ID = "eli/reg/2024/1689/oj__annex_III__point_5"
TARGET_DOC_URN = "eli/reg/2024/1689/oj"

CONTROL_SUBQUERY = (
    "Sistemi di IA ad alto rischio per l'accesso a servizi pubblici essenziali, "
    "Allegato III punto 5 AI Act."
)

SIGLA_PATTERNS = [
    ("gdpr", re.compile(r"\bGDPR\b", re.IGNORECASE)),
    ("ai_act", re.compile(r"\bAI\s*Act\b", re.IGNORECASE)),
    ("l_132_2025", re.compile(r"\bL\.?\s*132/2025\b", re.IGNORECASE)),
    ("dlgs_231", re.compile(r"\bD\.?\s*Lgs\.?\s*231/2001\b", re.IGNORECASE)),
    ("nis2", re.compile(r"\bNIS2\b|\bD\.?\s*Lgs\.?\s*138/2024\b", re.IGNORECASE)),
]


def _norm_of_subq(text):
    earliest = None
    for nid, pat in SIGLA_PATTERNS:
        m = pat.search(text)
        if m and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), nid)
    return earliest[1] if earliest else None


def main():
    import logging; logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient, models
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.terminology import expand_query
    from core.vector_store import (
        DENSE_VECTOR_NAME, HYBRID_COLLECTION_NAME, SPARSE_VECTOR_NAME,
    )

    cli = QdrantClient(host="localhost", port=6333, timeout=60)

    # === STEP 0: target chunk + tutti gli annex chunks ai_act ===
    print("=" * 90)
    print("STEP 0 — target chunk + chunking allegati AI Act")
    print("=" * 90)

    # Fetch target
    flt_t = models.Filter(must=[models.FieldCondition(
        key="chunk_id", match=models.MatchValue(value=TARGET_ID))])
    pts, _ = cli.scroll(collection_name=HYBRID_COLLECTION_NAME,
                        scroll_filter=flt_t, limit=1, with_payload=True)
    if not pts:
        print(f"TARGET NON TROVATO: {TARGET_ID}")
        return 1
    p = pts[0].payload
    txt = p.get("text", "")
    hp = p.get("hierarchy_path", [])
    print(f"\ntarget chunk_id = {TARGET_ID}")
    print(f"  presente in Qdrant: SI")
    print(f"  text length = {len(txt)} chars")
    print(f"  hierarchy_path = {hp}")
    print(f"\n  text (primi 800 char):")
    print(f"---")
    print(txt[:800])
    print(f"---")

    # Tutti i chunk ai_act con "annex" nel chunk_id
    flt_a = models.Filter(must=[models.FieldCondition(
        key="doc_urn", match=models.MatchValue(value=TARGET_DOC_URN))])
    all_pts, _ = cli.scroll(collection_name=HYBRID_COLLECTION_NAME,
                            scroll_filter=flt_a, limit=2000, with_payload=True)
    annex_chunks = []
    for x in all_pts:
        cid = x.payload.get("chunk_id", "")
        if "annex" in cid.lower():
            annex_chunks.append((cid, len(x.payload.get("text", ""))))
    annex_chunks.sort(key=lambda x: x[0])
    print(f"\nChunks ai_act con 'annex' nel chunk_id: {len(annex_chunks)}")
    for cid, ln in annex_chunks:
        mk = " ← TARGET" if cid == TARGET_ID else ""
        print(f"  {cid:<55} text_len={ln}{mk}")

    # === STEP 1: funnel di retrieval per ciascuna sub-query ===
    print("\n" + "=" * 90)
    print("STEP 1 — funnel di retrieval (dense | sparse | hybrid-prefetch | rerank)")
    print("=" * 90)

    raw = json.loads(SUBQ_FILE.read_text())
    q71_ai = raw["Q71"]["subqueries_by_norm"].get("ai_act", [])
    q71_ai_filtered = [sq for sq in q71_ai if _norm_of_subq(sq) == "ai_act"]

    queries_to_test = [("CONTROL", CONTROL_SUBQUERY)]
    for i, sq in enumerate(q71_ai_filtered):
        queries_to_test.append((f"Q71_ai_act_v3_#{i}", sq))

    print(f"\nSub-query da testare: {len(queries_to_test)}")
    print(f"  (1 controllo + {len(q71_ai_filtered)} V3 declarative ai_act filtrate)\n")

    print("Loading models...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)

    def find_rank(points, cid):
        for i, pp in enumerate(points, 1):
            if pp.payload.get("chunk_id") == cid:
                return i, float(pp.score)
        return None, None

    print(f"\n{'tag':<24}{'sub_query':<70}{'dense':>10}{'sparse':>10}{'hybrid':>10}{'rerank':>12}")
    results = []

    for tag, sub_q in queries_to_test:
        q_exp = expand_query(sub_q)
        dvec = enc.encode([q_exp], batch_size=1)[0]
        emb = next(bm.query_embed(q_exp))
        svec = models.SparseVector(indices=emb.indices.tolist(),
                                   values=emb.values.tolist())

        # dense top-20
        dpts = cli.query_points(
            collection_name=HYBRID_COLLECTION_NAME, query=dvec, using=DENSE_VECTOR_NAME,
            limit=20, with_payload=["chunk_id"], query_filter=flt_a,
        ).points
        d_rank, d_score = find_rank(dpts, TARGET_ID)

        # sparse top-20
        spts = cli.query_points(
            collection_name=HYBRID_COLLECTION_NAME, query=svec, using=SPARSE_VECTOR_NAME,
            limit=20, with_payload=["chunk_id"], query_filter=flt_a,
        ).points
        s_rank, s_score = find_rank(spts, TARGET_ID)

        # hybrid prefetch RRF, top-20 (= pool che il reranker vede)
        hpts = cli.query_points(
            collection_name=HYBRID_COLLECTION_NAME,
            prefetch=[
                models.Prefetch(query=dvec, using=DENSE_VECTOR_NAME,
                                limit=40, filter=flt_a),
                models.Prefetch(query=svec, using=SPARSE_VECTOR_NAME,
                                limit=40, filter=flt_a),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=20, with_payload=True,
        ).points
        h_rank, h_score = find_rank(hpts, TARGET_ID)

        # rerank: solo se nel pool
        if h_rank is not None:
            pairs = [(q_exp, pp.payload.get("text", "")) for pp in hpts]
            scores = rr.predict(pairs, show_progress_bar=False)
            ranked = sorted(zip(hpts, scores), key=lambda x: -float(x[1]))
            ranked_ids = [pp.payload.get("chunk_id") for pp, _ in ranked]
            if TARGET_ID in ranked_ids:
                r_rank = ranked_ids.index(TARGET_ID) + 1
                r_score = float([s for pp, s in ranked
                                 if pp.payload.get("chunk_id") == TARGET_ID][0])
            else:
                r_rank, r_score = None, None
        else:
            r_rank, r_score = None, None

        d_s = f"r{d_rank}" if d_rank else "—"
        s_s = f"r{s_rank}" if s_rank else "—"
        h_s = f"r{h_rank}" if h_rank else "—"
        r_s = (f"r{r_rank}@{r_score:.3f}" if r_rank else "—")
        # sub_q snippet
        snip = sub_q[:65] + "..." if len(sub_q) > 65 else sub_q
        print(f"{tag:<24}{snip:<70}{d_s:>10}{s_s:>10}{h_s:>10}{r_s:>12}")
        results.append({
            "tag": tag, "sub_query": sub_q,
            "dense_rank": d_rank, "sparse_rank": s_rank,
            "hybrid_rank": h_rank, "rerank_rank": r_rank, "rerank_score": r_score,
        })

    # Sintesi: stadi in cui point_5 sparisce
    print("\n" + "=" * 90)
    print("Sintesi: in quali stadi point_5 entra nel pool")
    print("=" * 90)
    for r in results:
        stages_in = []
        if r["dense_rank"]: stages_in.append(f"DENSE@r{r['dense_rank']}")
        if r["sparse_rank"]: stages_in.append(f"SPARSE@r{r['sparse_rank']}")
        if r["hybrid_rank"]: stages_in.append(f"HYBRID@r{r['hybrid_rank']}")
        if r["rerank_rank"]:
            stages_in.append(f"RERANK@r{r['rerank_rank']}({r['rerank_score']:.3f})")
        print(f"  {r['tag']:<24}: {', '.join(stages_in) if stages_in else 'ASSENTE in tutti gli stadi'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
