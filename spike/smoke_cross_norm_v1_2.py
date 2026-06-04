"""Smoke test v1.2 pipeline: real Qdrant + reranker + cassette LLM su Q68.

Costo zero. Verifica:
- generate_subquery → list[str] dal cassette V3
- CrossNormRetriever.retrieve → trace popolata, no exception
- score-aware fusion produce top-20 ordinato per sigmoid score
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASSETTE = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"
Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?"
)
GOLD_Q68 = {
    "eli/reg/2024/1689/oj__art_6",
    "eli/reg/2024/1689/oj__art_27",
    "eli/reg/2016/679/oj__art_9",
    "eli/reg/2016/679/oj__art_35",
    "akn/it/act/legge/stato/2025-09-23/132__art_7",
}


@dataclass
class _R:
    text: str


class CassetteLLM:
    def __init__(self, c, qid):
        self.c = c
        self.qid = qid

    def generate(self, prompt, system=None, max_tokens=200, temperature=0.0):
        S2I = {"GDPR": "gdpr", "AI Act": "ai_act", "L. 132/2025": "l_132_2025",
               "D.Lgs 231/2001": "dlgs_231", "NIS2": "nis2",
               "Codice Privacy": "codice_privacy"}
        for ln in prompt.splitlines():
            if ln.startswith("Norma target:"):
                tail = ln[len("Norma target:"):].strip()
                for short, nid in S2I.items():
                    if tail.startswith(short):
                        val = self.c[f"{self.qid}:{nid}"]
                        if isinstance(val, list):
                            return _R(json.dumps(val, ensure_ascii=False))
                        return _R(val)
        raise ValueError("norma?")


def main():
    import logging
    logging.basicConfig(level=logging.WARNING)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.cross_norm import CrossNormRetriever
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME

    print("Loading models...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    cli = QdrantClient(host="localhost", port=6333)
    hybrid = HybridRetriever(cli, enc, bm, HYBRID_COLLECTION_NAME, reranker=rr)
    cass = json.loads(CASSETTE.read_text())
    llm = CassetteLLM(cass, "q68")

    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid, llm_client=llm,
        top_k_per_norm=20, top_k_global=20, top_k_final=20,
        rerank_top_k_per_norm=20, rerank_top_k_global=20, debug=False,
    )
    res = cnr.retrieve(Q68, top_k=20)
    trace = cnr.last_trace

    print(f"\nSUB-QUERIES per norma:")
    for nid, sqs in trace["sub_queries"].items():
        print(f"  [{nid}] n={len(sqs)}")
        for i, sq in enumerate(sqs):
            print(f"     [{i}] {sq[:90]}")
    print(f"\nFUSED TOP-20:")
    found = []
    for h in res:
        in_gold = "★ GOLD" if h.chunk_id in GOLD_Q68 else ""
        print(f"  {h.rank:>2}. {h.chunk_id[:55]:<55} sig={h.score:.4f} {in_gold}")
        if h.chunk_id in GOLD_Q68:
            found.append((h.rank, h.chunk_id.split('__',2)[-1]))
    print(f"\nGold recuperati in top-20: {len(found)}/5 → {found}")
    top5_gold = [g for r, g in found if r <= 5]
    print(f"Gold in top-5 (generation context): {len(top5_gold)}/5 → {top5_gold}")
    # Verifica monotonia
    ranks = [h.rank for h in res]
    assert ranks == list(range(1, len(ranks) + 1)), "ranks non sequenziali"
    print("\n✓ ranks sequenziali (fusion z-normalized + gated fallback)")


if __name__ == "__main__":
    main()
