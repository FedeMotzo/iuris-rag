"""Unit test di RAGPipeline.classify() (role-free) + get_obligations() — DoD a/b.

Post-split: classify() NON costruisce più il dossier (niente generate_subquery /
map_and_assemble); ritorna solo classificazione + high_risk. Gli adempimenti
sono in get_obligations(role). Fake retriever/LLM, niente Qdrant/LLM live.
"""

from __future__ import annotations

import json
import types

from core.classification.obligations_data import AI_ACT_URN, GDPR_ART35
from core.hybrid_retriever.types import RetrievalHit, RetrievalResult
from core.serving.pipeline import RAGPipeline

URN = "eli/reg/2024/1689/oj"
P4 = f"{URN}__annex_III__point_4"


def _judgment_json(*, p4=False, practice_f=False, art6_1=False):
    annex = [{"point": n, "applies": False, "reason": "", "cite": None} for n in range(1, 9)]
    if p4:
        annex[3] = {"point": 4, "applies": True, "reason": "occupazione", "cite": P4}
    practices = []
    for k in "abcdefgh":
        if k == "f" and practice_f:
            practices.append({"practice": "f", "applies": True, "reason": "emozioni lavoro",
                              "cite": f"{URN}__art_5__paras_1_3"})
        else:
            practices.append({"practice": k, "applies": False, "reason": "no", "cite": None})
    return json.dumps({
        "annex_iii": annex,
        "prohibited_practices": practices,
        "art6_1_safety_component": {"plausible": art6_1, "reason": "dispositivo medico"},
        "art6_3_exception": {"plausible": False, "reason": ""},
    })


class FakeLLM:
    provider_name = "fake"
    model_name = "fake-sonnet"

    def __init__(self, judgment_json: str) -> None:
        self._judgment_json = judgment_json
        self.n_calls = 0

    def generate(self, prompt, system=None, max_tokens=0, temperature=0.0):
        self.n_calls += 1
        return types.SimpleNamespace(
            text=self._judgment_json, finish_reason="stop",
            n_input_tokens=0, n_output_tokens=0,
        )


class FakeRetriever:
    """fetch_by_chunk_ids → 1 hit per id (per giudizio e per grounding obblighi).
    retrieve() NON deve essere chiamato da classify() dopo lo split."""

    def __init__(self):
        self.retrieve_called = False

    def fetch_by_chunk_ids(self, chunk_ids):
        return RetrievalResult([
            RetrievalHit(chunk_id=c, score=0.0,
                         payload={"text": f"TXT:{c.split('__', 1)[1]}"}, rank=i + 1)
            for i, c in enumerate(chunk_ids)
        ])

    def retrieve(self, *a, **k):
        self.retrieve_called = True
        raise AssertionError("classify() non deve chiamare retrieve() (no dossier)")


def _pipeline(judgment_json):
    return RAGPipeline(
        retriever=FakeRetriever(),
        llm_provider=FakeLLM(judgment_json),
        enable_cross_norm=False,
    )


# --------------------------------------------------------------------------- #
# classify() — solo classificazione, role-free, senza dossier
# --------------------------------------------------------------------------- #

def test_classify_high_risk_no_dossier():
    p = _pipeline(_judgment_json(p4=True))
    res = p.classify("Una banca filtra i CV dei candidati.")

    assert res.high_risk_annex is True
    assert res.judgment.high_risk_annex is True
    assert res.card.annex_iii_category is not None
    assert "punto 4" in res.card.annex_iii_category
    assert res.card.art6_3_exception is not None
    # niente attributi di dossier sul risultato
    assert not hasattr(res, "obligations")
    assert not hasattr(res, "assembled_text")
    assert not hasattr(res, "minis")
    # un solo giudizio LLM, nessuna sub-query
    assert p._llm.n_calls == 1
    assert p._retriever.retrieve_called is False


def test_classify_negative():
    p = _pipeline(_judgment_json(p4=False))
    res = p.classify("Un sistema prevede le scorte di magazzino.")
    assert res.high_risk_annex is False
    assert res.card.annex_iii_category is None
    assert "Non risulta alto rischio" in res.card.verdict
    assert "6(1)" not in res.card.verdict  # nessuna falsa plausibilità
    assert res.card.prohibited_flag is False


def test_classify_art6_1_pathway_limit():
    p = _pipeline(_judgment_json(p4=False, art6_1=True))
    res = p.classify("Sistema AI per analisi di radiografie.")
    assert res.high_risk_annex is False
    # FIX #1: il verdetto riflette il pathway art. 6(1), non solo i limiti
    assert "art. 6(1)" in res.card.verdict
    assert "POSSIBILE alto rischio" in res.card.verdict
    assert any("art. 6(1)" in l for l in res.card.declared_limits)


def test_classify_prohibited_practice():
    """Pratica vietata (f) → prohibited_flag, verdetto apre con vietata,
    obligations NON pertinenti anche se Allegato III scatta."""
    p = _pipeline(_judgment_json(p4=True, practice_f=True))
    res = p.classify("Sistema che inferisce le emozioni dei dipendenti.")
    assert res.card.prohibited_flag is True
    assert res.card.verdict.startswith("PRATICA VIETATA ex art. 5:")
    assert res.high_risk_annex is True            # Allegato III scatta comunque
    assert res.obligations_applicable is False     # ma adempimenti non pertinenti


def test_classify_does_not_enable_cross_norm():
    p = _pipeline(_judgment_json(p4=True))
    assert p._cross_norm is None
    p.classify("scenario")
    assert p._cross_norm is None


def test_classify_serializes():
    d = _pipeline(_judgment_json(p4=True)).classify("scenario").to_dict()
    assert d["high_risk_annex"] is True
    assert d["judgment"]["annex_iii"][3]["applies"] is True
    assert d["card"]["annex_iii_category"] is not None
    assert "obligations" not in d["card"]


# --------------------------------------------------------------------------- #
# get_obligations(role) — operazione separata, grounded
# --------------------------------------------------------------------------- #

def test_get_obligations_deployer_default():
    p = _pipeline(_judgment_json())
    obs = p.get_obligations()  # default deployer
    assert len(obs) == 12
    assert all(o.source_text and o.source_text.startswith("TXT:") for o in obs)
    o9 = next(o for o in obs if o.label == "Art. 26(9)")
    assert o9.gdpr_link == GDPR_ART35
    assert o9.gdpr_source_text == "TXT:art_35"  # puntatore GDPR risolto


def test_get_obligations_provider():
    p = _pipeline(_judgment_json())
    obs = p.get_obligations("provider")
    assert len(obs) == 20
    assert obs[0].source_chunk_id == f"{AI_ACT_URN}__art_9"
    # Art. 10 è obbligo del PROVIDER (non comparirà tra i deployer)
    assert any(o.article == "Art. 10" for o in obs)


def test_provider_and_deployer_disjoint_on_art10():
    p = _pipeline(_judgment_json())
    dep_labels = {o.label for o in p.get_obligations("deployer")}
    assert "Art. 10" not in dep_labels  # Art. 10 è solo provider
