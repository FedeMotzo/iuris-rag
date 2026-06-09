"""Smoke logico del FE UC1: esercita le funzioni che i bottoni invocano.

NON serve streamlit: costruisce la stessa pipeline leggera di
app.uc1_classification_app.build_uc1_pipeline (retriever id-lookup, no modelli)
e chiama classify() + get_obligations(), come fanno i bottoni.

    spike/.venv/bin/python spike/smoke_uc1_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

Q102 = ("Un comune italiano usa un sistema AI per calcolare automaticamente il "
        "punteggio di accesso agli alloggi di edilizia popolare.")
NEG = ("Un'azienda usa un sistema AI per prevedere il fabbisogno di scorte di "
       "magazzino in base allo storico delle vendite.")


def build_uc1_pipeline():
    from qdrant_client import QdrantClient

    from core.hybrid_retriever import HybridRetriever
    from core.serving import build_default_pipeline

    client = QdrantClient(host="localhost", port=6333)
    retriever = HybridRetriever(
        client=client, encoder=None, bm25=None,
        collection="italian_legal_v1_hybrid", reranker=None,
    )
    return build_default_pipeline(retriever)


def _esito(res):
    if res.high_risk_annex:
        return "alto rischio via Allegato III"
    if res.judgment.art6_1_safety_component.plausible:
        return "possibile alto rischio via art. 6(1)"
    return "non risulta alto rischio"


def main() -> int:
    pipe = build_uc1_pipeline()

    print("=== [bottone Classifica] classify(Q102) ===")
    res = pipe.classify(Q102)
    print(f"  esito: {_esito(res)} | high_risk_annex={res.high_risk_annex}")
    print(f"  categoria: {res.card.annex_iii_category}")
    assert res.high_risk_annex is True
    assert "punto 5" in (res.card.annex_iii_category or "")

    print("=== [bottone Mostra adempimenti → deployer] get_obligations('deployer') ===")
    obs = pipe.get_obligations("deployer")
    print(f"  n voci: {len(obs)}")
    o9 = next(o for o in obs if o.label == "Art. 26(9)")
    print(f"  26(9) gdpr_link={o9.gdpr_link} | gdpr risolto={bool(o9.gdpr_source_text)}")
    assert len(obs) == 12
    assert all(o.source_text for o in obs)
    assert o9.gdpr_source_text

    print("=== [ruolo provider] get_obligations('provider') ===")
    prov = pipe.get_obligations("provider")
    print(f"  n voci: {len(prov)} | Art.10 presente: {any(o.article == 'Art. 10' for o in prov)}")
    assert len(prov) == 20

    print("=== [classify negativo] classify(scorte) ===")
    resn = pipe.classify(NEG)
    print(f"  esito: {_esito(resn)} | high_risk_annex={resn.high_risk_annex} "
          f"| art6_1={resn.judgment.art6_1_safety_component.plausible}")
    assert resn.high_risk_annex is False
    assert "Non risulta alto rischio" in resn.card.verdict

    print("\nSMOKE UC1 FE: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
