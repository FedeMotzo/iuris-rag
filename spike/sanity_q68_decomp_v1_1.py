"""Sanity manuale Q68 — decomposition + filter per-norma.

4 sub-query scritte a mano, retrieval hybrid filtered per doc_urn,
nessuna LLM, nessuna generation.

    spike/.venv/bin/python spike/sanity_q68_decomp_v1_1.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("sanity_q68")

REPORT_PATH = ROOT / "spike/SANITY_Q68_DECOMP_v1_1.md"
COLLECTION  = "italian_legal_v1_hybrid"

# ---------------------------------------------------------------------------
# Sub-query scritte a mano (NON generate da LLM)
# ---------------------------------------------------------------------------
SUB_QUERIES = [
    {
        "norm_label": "AI Act",
        "doc_urn": "eli/reg/2024/1689/oj",
        "sub_query": (
            "Classificazione sistema IA ad alto rischio in ambito sanitario, "
            "obblighi del fornitore e dell'utilizzatore, valutazione di impatto "
            "sui diritti fondamentali (FRIA), conformità ai requisiti dell'AI Act"
        ),
        "gold_ids": [
            "eli/reg/2024/1689/oj__art_6",
            "eli/reg/2024/1689/oj__art_27",
        ],
        "note": None,
    },
    {
        "norm_label": "GDPR",
        "doc_urn": "eli/reg/2016/679/oj",
        "sub_query": (
            "Trattamento di dati sanitari come categorie particolari di dati "
            "personali, base giuridica art. 9, valutazione d'impatto sulla "
            "protezione dei dati (DPIA) per trattamenti automatizzati su larga scala"
        ),
        "gold_ids": [
            "eli/reg/2016/679/oj__art_9",
            "eli/reg/2016/679/oj__art_35",
        ],
        "note": None,
    },
    {
        "norm_label": "L.132/2025",
        "doc_urn": "akn/it/act/legge/stato/2025-09-23/132",
        "sub_query": (
            "Uso di sistemi di intelligenza artificiale in ambito sanitario, "
            "principi di tutela della persona, supervisione umana nelle "
            "decisioni cliniche"
        ),
        "gold_ids": [
            "akn/it/act/legge/stato/2025-09-23/132__art_7",
        ],
        "note": "art_7 era già rank 2 in globale v1.0. Controllo coerenza.",
    },
]


def query_hybrid_filtered(client, encoder, bm25, reranker,
                           query: str, doc_urn: str, top_k: int = 10) -> list[dict]:
    """Hybrid RRF + reranker con filter doc_urn (full scan, no payload index)."""
    from qdrant_client import models
    from core.vector_store import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
    from core.terminology import expand_query

    query_exp = expand_query(query)

    [dvec_arr] = encoder.encode([query_exp], batch_size=1)
    dvec = dvec_arr.tolist() if hasattr(dvec_arr, "tolist") else list(dvec_arr)

    emb = next(bm25.query_embed(query_exp))
    svec = models.SparseVector(
        indices=emb.indices.tolist(),
        values=emb.values.tolist(),
    )

    filt = models.Filter(must=[
        models.FieldCondition(key="doc_urn", match=models.MatchValue(value=doc_urn))
    ])
    prefetch_limit = max(top_k * 2, 20)

    pts = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            models.Prefetch(query=dvec, using=DENSE_VECTOR_NAME,
                            limit=prefetch_limit, filter=filt),
            models.Prefetch(query=svec, using=SPARSE_VECTOR_NAME,
                            limit=prefetch_limit, filter=filt),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=prefetch_limit,
        with_payload=True,
    ).points

    if not pts:
        return []

    pairs = [(query_exp, (p.payload or {}).get("text", "")) for p in pts]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(pts, scores), key=lambda x: float(x[1]), reverse=True)

    return [
        {
            "rank": rank,
            "chunk_id": (p.payload or {}).get("chunk_id", ""),
            "score": float(sc),
        }
        for rank, (p, sc) in enumerate(ranked[:top_k], start=1)
    ]


def main() -> int:
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from qdrant_client import QdrantClient
    from core.embedding import BgeM3Encoder

    client   = QdrantClient(host="localhost", port=6333)
    encoder  = BgeM3Encoder.get(device="mps")
    bm25     = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)

    sections: list[str] = []
    sections.append("# Sanity Q68 — decomposition + filter per-norma")
    sections.append("")
    sections.append(
        "Branch: `diag/sanity-q68`. "
        "Sub-query scritte a mano. Retrieval hybrid filtered per `doc_urn` (full scan). "
        "Nessuna generation, nessun LLM, nessun judge."
    )
    sections.append("")
    sections.append(
        "**Query originale Q68**: "
        "\"Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare "
        "il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e "
        "L. 132/2025 devono essere previsti prima dell'avvio?\""
    )
    sections.append("")

    rescue_rows: list[dict] = []

    for sq in SUB_QUERIES:
        norm   = sq["norm_label"]
        urn    = sq["doc_urn"]
        query  = sq["sub_query"]
        golds  = sq["gold_ids"]
        note   = sq["note"]

        log.info("[%s] filtered retrieval, doc_urn=%s", norm, urn)
        hits = query_hybrid_filtered(client, encoder, bm25, reranker, query, urn, top_k=10)

        hit_ids = [h["chunk_id"] for h in hits]
        hit_set = set(hit_ids)
        gold_set = set(golds)

        sec: list[str] = []
        sec.append(f"## Sub-query {norm}")
        sec.append("")
        sec.append(f"**Sub-query**: {query}")
        sec.append("")
        if golds:
            sec.append(f"**Gold attesi in questa norma** ({len(golds)}):")
            for cid in golds:
                sec.append(f"- `{cid}`")
        else:
            sec.append("**Gold attesi in questa norma**: nessuno (test bonus context).")
        if note:
            sec.append(f"**Nota**: {note}")
        sec.append("")

        if not hits:
            sec.append("_Nessun hit restituito con questo filtro._")
            sec.append("")
            for cid in golds:
                rescue_rows.append({"norm": norm, "gold": cid, "rank_filtered": "ASSENTE (0 hit)"})
        else:
            sec.append(f"**Top-10 retrieval filtered** `doc_urn={urn}`:")
            sec.append("")
            sec.append("| rank | chunk_id | score | gold? |")
            sec.append("|---:|---|---:|:---:|")
            for h in hits:
                mark = "✓" if h["chunk_id"] in gold_set else "-"
                sec.append(f"| {h['rank']} | `{h['chunk_id']}` | {h['score']:.4f} | {mark} |")
            sec.append("")

            if golds:
                sec.append("**Gold position in filtered**:")
                for cid in golds:
                    if cid in hit_set:
                        r = hit_ids.index(cid) + 1
                        sec.append(f"- `{cid}` → rank {r}")
                        rescue_rows.append({"norm": norm, "gold": cid, "rank_filtered": f"rank {r}"})
                    else:
                        sec.append(f"- `{cid}` → **ASSENTE**")
                        rescue_rows.append({"norm": norm, "gold": cid, "rank_filtered": "ASSENTE"})
            else:
                sec.append("_Nessun gold da verificare per questa norma (NIS2 bonus context)._")
            sec.append("")

        sections.extend(sec)

    # Rescue summary table
    sections.append("## Rescue summary")
    sections.append("")
    sections.append("| Norma | Gold atteso | Stato globale v1.0 | Rank filtered sub-query |")
    sections.append("|---|---|:---:|:---:|")

    # Aggiungo anche L.132 art_7 che era già rank 2 globale
    # e NIS2 che non ha gold
    norm_to_global = {
        "eli/reg/2024/1689/oj__art_6":                                      "ASSENTE",
        "eli/reg/2024/1689/oj__art_27":                                     "ASSENTE",
        "eli/reg/2016/679/oj__art_9":                                       "ASSENTE",
        "eli/reg/2016/679/oj__art_35":                                      "ASSENTE",
        "akn/it/act/legge/stato/2025-09-23/132__art_7":                     "rank 2",
    }

    for r in rescue_rows:
        cid   = r["gold"]
        short = cid.split("__")[-1] if "__" in cid else cid
        glob  = norm_to_global.get(cid, "?")
        sections.append(f"| {r['norm']} | `…{short}` | {glob} | {r['rank_filtered']} |")

    sections.append("")

    rescued = sum(
        1 for r in rescue_rows
        if r["rank_filtered"] not in ("ASSENTE", "ASSENTE (0 hit)")
        and r["gold"] not in ("akn/it/act/legge/stato/2025-09-23/132__art_7",)
    )
    # gold ASSENTI in globale (escluso L.132 art_7 che era già ok)
    absent_global = [r for r in rescue_rows
                     if norm_to_global.get(r["gold"], "?") == "ASSENTE"]
    n_absent = len(absent_global)
    rescued_absent = sum(
        1 for r in absent_global
        if r["rank_filtered"] not in ("ASSENTE", "ASSENTE (0 hit)")
    )
    sections.append(
        f"**Rescue ratio** (gold ASSENTI in globale, trovati in filtered top-10): "
        f"**{rescued_absent}/{n_absent}**"
    )
    sections.append("")

    REPORT_PATH.write_text("\n".join(sections), encoding="utf-8")
    log.info("Report scritto: %s", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
