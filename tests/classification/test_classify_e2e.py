"""Integration e2e LIVE di classify() su Q102 (Qdrant + LLM) — DoD c.

Richiede: Qdrant su localhost:6333 (collection italian_legal_v1_hybrid),
ANTHROPIC_API_KEY in .env, e le dipendenze pesanti (fastembed,
sentence_transformers). Esegui con spike/.venv:

    spike/.venv/bin/python -m pytest tests/classification/test_classify_e2e.py -q -s

Skippa pulito se l'ambiente non è disponibile. Il test FALLISCE se il modulo
`core.classification` viene rimosso (import + asserzioni sulla card).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Scenario Q102 (Cluster A — comune / edilizia popolare).
Q102 = (
    "Un comune italiano usa un sistema AI per calcolare automaticamente il "
    "punteggio di accesso agli alloggi di edilizia popolare: è classificato ad "
    "alto rischio ai sensi dell'Allegato III?"
)


def _qdrant_up() -> bool:
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:6333/collections", timeout=3)
        return True
    except Exception:  # noqa: BLE001
        return False


def _build_pipeline():
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.serving import build_default_pipeline

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    retriever = HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection="italian_legal_v1_hybrid", reranker=reranker,
    )
    return build_default_pipeline(retriever)


def test_classify_q102_live():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY non impostata")
    if not _qdrant_up():
        pytest.skip("Qdrant non raggiungibile su localhost:6333")
    try:
        import fastembed  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        pytest.skip("dipendenze retrieval assenti (usa spike/.venv)")

    pipeline = _build_pipeline()
    res = pipeline.classify(Q102)

    card = res.card
    # DoD c: il GIUDIZIO deve qualificare il punto 5 come applies=true (cite valido).
    assert res.high_risk_annex is True, res.judgment.to_dict()
    applied_points = {a.point for a in res.judgment.applied_annex()}
    assert 5 in applied_points, res.judgment.to_dict()
    assert card.annex_iii_category is not None
    assert "punto 5" in card.annex_iii_category, card.annex_iii_category
    # La card NON porta più gli adempimenti (operazione separata).
    assert not hasattr(card, "obligations")

    # Adempimenti via get_obligations(role), grounded sul corpus (read-only).
    obs = pipeline.get_obligations("deployer")
    assert len(obs) == 12
    assert all(o.source_text for o in obs), "testo-fonte non risolto via fetch"
    o9 = next(o for o in obs if o.label == "Art. 26(9)")
    assert o9.gdpr_source_text, "puntatore GDPR art. 35 non risolto"
