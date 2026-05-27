"""Probe trace V2 (cassette) per Q68 + Q69 — filtered top-10 per norma + fusion.

Usa la cassette V2 (no live LLM) via StubLLMClient, debug=True.
Serve a diagnosticare il rescue 3/5 di Q68 (perché art_9 esce dai top-20).

    spike/.venv/bin/python spike/probe_v2_traces.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)
Q69 = (
    "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale "
    "NIS2 per il settore sanitario, intende impiegare un sistema di IA per "
    "supportare le attività di farmacovigilanza con dati provenienti da "
    "operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai "
    "sensi di AI Act, GDPR e NIS2?"
)

GOLD = {
    "q68": {
        "eli/reg/2024/1689/oj__art_6", "eli/reg/2024/1689/oj__art_27",
        "eli/reg/2016/679/oj__art_9", "eli/reg/2016/679/oj__art_35",
        "akn/it/act/legge/stato/2025-09-23/132__art_7",
    },
    "q69": {
        "eli/reg/2024/1689/oj__art_6",
        "eli/reg/2016/679/oj__art_9", "eli/reg/2016/679/oj__art_35",
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24",
        "akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25",
    },
}


def main() -> int:
    from qdrant_client import QdrantClient
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME
    from core.cross_norm import CrossNormRetriever

    import json as _json

    CASSETTES_DIR = ROOT / "tests/cross_norm/cassettes"
    _SHORT_TO_ID = {
        "GDPR": "gdpr", "AI Act": "ai_act", "D.Lgs 231/2001": "dlgs_231",
        "NIS2": "nis2", "Codice Privacy": "codice_privacy", "L. 132/2025": "l_132_2025",
    }

    class _Res:
        def __init__(self, text): self.text = text

    class StubLLMClient:
        def __init__(self, cassette_path, query_label):
            self._c = _json.loads(Path(cassette_path).read_text(encoding="utf-8"))
            self._label = query_label
        def generate(self, prompt, system=None, max_tokens=200, temperature=0.0):
            nid = None
            for line in prompt.splitlines():
                if line.startswith("Norma target:"):
                    tail = line[len("Norma target:"):].strip()
                    for short, _id in _SHORT_TO_ID.items():
                        if tail.startswith(short):
                            nid = _id
                            break
                    break
            return _Res(self._c[f"{self._label}:{nid}"])

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    hybrid = HybridRetriever(client, encoder, bm25, HYBRID_COLLECTION_NAME,
                             reranker=reranker)

    cassette = CASSETTES_DIR / "subquery_responses.json"

    for label, query in [("q68", Q68), ("q69", Q69)]:
        stub = StubLLMClient(cassette, query_label=label)
        cnr = CrossNormRetriever(
            hybrid_retriever=hybrid, llm_client=stub,
            top_k_per_norm=5, top_k_global=5, top_k_final=20,
            rerank_top_k_per_norm=20, rerank_top_k_global=20,
            debug=False,
        )
        result = cnr.retrieve(query, top_k=20)
        tr = cnr.last_trace
        gold = GOLD[label]

        print("\n" + "#" * 80)
        print(f"# {label.upper()}  norme={tr['norms_detected']}")
        print("#" * 80)

        for nid, ranking in tr["per_norm_filtered"].items():
            print(f"\n--- filtered top-{len(ranking)} [norm:{nid}] ---")
            for rank, cid, score in ranking:
                mark = " ◀ GOLD" if cid in gold else ""
                print(f"  {rank:>2}. {cid}  ({score:.4f}){mark}")

        print(f"\n--- global top-{len(tr['global'])} ---")
        for rank, cid, score in tr["global"]:
            mark = " ◀ GOLD" if cid in gold else ""
            print(f"  {rank:>2}. {cid}  ({score:.4f}){mark}")

        print(f"\n--- RRF fused top-20 ---")
        fused_ids = set()
        for rank, cid, rrf, sources in tr["fused_top"]:
            fused_ids.add(cid)
            mark = " ◀ GOLD" if cid in gold else ""
            src = ",".join(f"{s}@{r}" for s, r in sources)
            print(f"  {rank:>2}. {cid}  (rrf={rrf:.5f}) [{src}]{mark}")

        rescued = gold & fused_ids
        print(f"\n  RESCUE {label}: {len(rescued)}/5")
        print(f"    rescued: {sorted(rescued)}")
        print(f"    missing: {sorted(gold - fused_ids)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
