"""Probe diagnostico: CrossNormRetriever su Q68 con `debug=True`.

Stampa lo stato intermedio della pipeline cross-norma:
- sub-query Sonnet (da cassette tests/cross_norm/cassettes/)
- top-N filtered per-norma PRIMA dell'RRF
- top-N retrieval globale PRIMA dell'RRF
- RRF merge finale top-20 con attribuzione source per ciascun chunk

Niente fix, niente refactor. Solo log.

    spike/.venv/bin/python spike/cross_norm_probe_q68.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASSETTE_PATH = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)

GOLD_Q68 = {
    "eli/reg/2024/1689/oj__art_6":                       "AI Act art_6",
    "eli/reg/2024/1689/oj__art_27":                      "AI Act art_27",
    "eli/reg/2016/679/oj__art_9":                        "GDPR art_9",
    "eli/reg/2016/679/oj__art_35":                       "GDPR art_35",
    "akn/it/act/legge/stato/2025-09-23/132__art_7":      "L.132 art_7",
}


@dataclass
class _StubResult:
    text: str


class CassetteLLM:
    """LLM stub: lookup deterministico via cassette JSON."""

    def __init__(self, cassette_path: Path) -> None:
        self._cassette = json.loads(cassette_path.read_text(encoding="utf-8"))

    def generate(self, prompt: str, system=None, max_tokens=200, temperature=0.0):
        SHORT_TO_ID = {
            "GDPR": "gdpr",
            "AI Act": "ai_act",
            "D.Lgs 231/2001": "dlgs_231",
            "NIS2": "nis2",
            "Codice Privacy": "codice_privacy",
            "L. 132/2025": "l_132_2025",
        }
        norm_id = None
        for line in prompt.splitlines():
            if line.startswith("Norma target:"):
                tail = line[len("Norma target:"):].strip()
                for short, nid in SHORT_TO_ID.items():
                    if tail.startswith(short):
                        norm_id = nid
                        break
                break
        if norm_id is None:
            raise ValueError("Norma non rilevata dal prompt")
        key = f"q68:{norm_id}"
        return _StubResult(text=self._cassette[key])


def main() -> int:
    import logging
    logging.basicConfig(level=logging.WARNING)

    from qdrant_client import QdrantClient
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME
    from core.cross_norm import CrossNormRetriever

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
    llm = CassetteLLM(CASSETTE_PATH)

    cnr = CrossNormRetriever(
        hybrid_retriever=hybrid,
        llm_client=llm,
        top_k_per_norm=5,
        top_k_global=5,
        top_k_final=20,
        rerank_top_k_per_norm=20,
        rerank_top_k_global=20,
        debug=True,
    )

    print("\nRunning cross-norm retrieve on Q68...\n")
    result = cnr.retrieve(Q68, top_k=20)

    print("\n" + "=" * 78)
    print("GOLD POSITION ANALYSIS")
    print("=" * 78)
    fused_ids = [h.chunk_id for h in result]
    for gid, label in GOLD_Q68.items():
        if gid in fused_ids:
            r = fused_ids.index(gid) + 1
            print(f"  {label:<22} → FUSED rank {r}")
        else:
            print(f"  {label:<22} → ASSENTE in fused top-{len(result)}")

    # Per-source rank dei gold (anche se assenti dal fused)
    trace = cnr.last_trace
    print()
    print("=" * 78)
    print("GOLD RANK PER SOURCE (anche fuori fused)")
    print("=" * 78)
    for gid, label in GOLD_Q68.items():
        sources = []
        for norm_id, ranking in trace["per_norm_filtered"].items():
            for rank, cid, _score in ranking:
                if cid == gid:
                    sources.append(f"norm:{norm_id}@{rank}")
        for rank, cid, _score in trace["global"]:
            if cid == gid:
                sources.append(f"global@{rank}")
        if sources:
            print(f"  {label:<22} → {', '.join(sources)}")
        else:
            print(f"  {label:<22} → NON appare in ALCUNA source (filtered + global)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
