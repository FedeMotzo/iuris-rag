"""Probe diagnostico Q69 — sub-query Sonnet LIVE, no cassette.

Query Q69 (multi-norma AI Act+GDPR+NIS2):
  "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale
   NIS2 per il settore sanitario, intende impiegare un sistema di IA per
   supportare le attività di farmacovigilanza con dati provenienti da
   operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai
   sensi di AI Act, GDPR e NIS2?"

Gold ASSENTI in retrieval v1.0 (da PRE_FIX_DIAG_v1_1):
  - AI Act art_6
  - GDPR art_9
  - GDPR art_35
  - NIS2 art_24
  - NIS2 art_25

Flow:
  1. detect_norms(Q69) → atteso ['ai_act','gdpr','nis2']
  2. generate_subquery(Q69, norma) LIVE Sonnet 4.6 per ciascuna
  3. retrieval hybrid filtrato per doc_urn, top-10
  4. rescue ratio = gold trovati in filtered top-10 / 5

Costo atteso: ~$0.012 (3 chiamate Sonnet 4.6, prompt ~600-700 token, output ~80-120 token).

    spike/.venv/bin/python spike/cross_norm_probe_q69.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING)

Q69 = (
    "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale "
    "NIS2 per il settore sanitario, intende impiegare un sistema di IA per "
    "supportare le attività di farmacovigilanza con dati provenienti da "
    "operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai "
    "sensi di AI Act, GDPR e NIS2?"
)

GOLD_Q69_ABSENT = {
    "eli/reg/2024/1689/oj__art_6":                                  "AI Act art_6",
    "eli/reg/2016/679/oj__art_9":                                   "GDPR art_9",
    "eli/reg/2016/679/oj__art_35":                                  "GDPR art_35",
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24":  "NIS2 art_24",
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25":  "NIS2 art_25",
}


def main() -> int:
    from qdrant_client import QdrantClient
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME
    from core.cross_norm import detect_norms, generate_subquery
    from core.llm_provider.config import load_provider_from_env

    print("Loading models (bge-m3 + bm25 + bge-reranker-v2-m3)...")
    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)

    client = QdrantClient(host="localhost", port=6333)
    hybrid = HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=HYBRID_COLLECTION_NAME, reranker=reranker,
    )

    print("Loading LLM provider (Anthropic Sonnet 4.6)...")
    llm = load_provider_from_env()
    print(f"  provider={llm.provider_name} model={llm.model_name}")

    # 1. detect norms
    norms = detect_norms(Q69)
    print(f"\ndetect_norms(Q69) → {norms}")
    expected = {"ai_act", "gdpr", "nis2"}
    if set(norms) != expected:
        print(f"WARNING: atteso {expected}, ottenuto {set(norms)}")

    norm_to_doc_urn = {
        "ai_act":         "eli/reg/2024/1689/oj",
        "gdpr":           "eli/reg/2016/679/oj",
        "nis2":           "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    }

    # 2-3. live sub-query + filtered retrieval
    results: dict[str, dict] = {}
    for nid in norms:
        print(f"\n[{nid}] generating sub-query (live Sonnet)...")
        sub_q = generate_subquery(Q69, nid, llm, max_tokens=200)
        print(f"  → {sub_q}")

        print(f"[{nid}] filtered retrieval top-10...")
        hits = hybrid.retrieve(
            query=sub_q,
            top_k=10,
            mode="hybrid",
            rerank_top_k=20,
            filter_doc_urn=norm_to_doc_urn[nid],
        )
        ranking = [(h.rank, h.chunk_id, float(h.score)) for h in hits]
        results[nid] = {"sub_query": sub_q, "ranking": ranking}

    # 4. report
    print()
    print("=" * 78)
    print("Q69 PROBE — Sub-query Sonnet 4.6 LIVE + filtered retrieval")
    print("=" * 78)
    print(f"Query: {Q69}")
    print(f"Norme rilevate: {norms}")
    print()

    for nid in norms:
        sub_q = results[nid]["sub_query"]
        ranking = results[nid]["ranking"]
        print(f"--- Sub-query [{nid}] ---")
        print(f"  {sub_q}")
        print()
        print(f"--- Filtered top-10 [norm:{nid}] ---")
        gold_in_norm = {cid for cid in GOLD_Q69_ABSENT
                        if cid.startswith(norm_to_doc_urn[nid] + "__")}
        for rank, cid, score in ranking:
            mark = " ✓" if cid in gold_in_norm else ""
            print(f"  {rank:>2}. {cid}  (score={score:.4f}){mark}")
        print()

    # rescue ratio
    print("=" * 78)
    print("RESCUE RATIO Q69 (gold ASSENTI in v1.0)")
    print("=" * 78)
    print()
    print("| Norma  | Gold       | Filtered top-10 rank |")
    print("|--------|------------|----------------------|")
    rescued = 0
    for gid, label in GOLD_Q69_ABSENT.items():
        # individua norma del gold
        target_nid = next((n for n, urn in norm_to_doc_urn.items()
                           if gid.startswith(urn + "__")), None)
        if target_nid is None or target_nid not in results:
            print(f"| ?      | {label:<10} | norma non probata    |")
            continue
        ranking = results[target_nid]["ranking"]
        rank_in_top10 = None
        for r, c, _ in ranking:
            if c == gid:
                rank_in_top10 = r
                break
        if rank_in_top10:
            cell = f"rank {rank_in_top10}"
            rescued += 1
        else:
            cell = "ASSENTE"
        norm_short = {"ai_act": "AI Act", "gdpr": "GDPR ",
                      "nis2": "NIS2 "}[target_nid]
        chunk_short = label.split(" ", 1)[1] if " " in label else label
        print(f"| {norm_short} | {chunk_short:<10} | {cell:<20} |")

    print()
    print(f"**Filtered rescue ratio Q69**: {rescued}/{len(GOLD_Q69_ABSENT)}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
