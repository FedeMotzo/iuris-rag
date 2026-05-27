"""Localizza art_9 GDPR nel filtered di Q68 (sub-query V2) — top-15."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from qdrant_client import QdrantClient
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.vector_store import HYBRID_COLLECTION_NAME

    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("a", "b")], show_progress_bar=False)
    r = HybridRetriever(QdrantClient(host="localhost", port=6333), enc, bm,
                        HYBRID_COLLECTION_NAME, reranker=rr)

    subq = (
        "Quali obblighi prevede il GDPR per un trattamento di dati sanitari "
        "(art. 9) tramite sistema automatizzato con profilazione (art. 22) a "
        "larga scala in ambito ospedaliero, con riferimento a DPIA (art. 35), "
        "misure di sicurezza e pseudonimizzazione (art. 32), nomina del "
        "responsabile del trattamento (art. 28) e informativa all'interessato "
        "(artt. 13-14)?"
    )
    hits = r.retrieve(subq, top_k=15, rerank_top_k=20,
                      filter_doc_urn="eli/reg/2016/679/oj")
    print("Q68 GDPR filtered top-15 (sub-query V2):")
    for h in hits:
        g = "  <-- art_9 GOLD" if h.chunk_id == "eli/reg/2016/679/oj__art_9" else ""
        print(f"  {h.rank:>2}. {h.chunk_id}  ({h.score:.4f}){g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
