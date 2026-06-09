"""Unit test del dato curato adempimenti + get_obligations() (DoD a).

Nessun LLM, nessun Qdrant per i test di dato; il grounding usa un retriever fake.
"""

from __future__ import annotations

import pytest

from core.classification.obligations_data import (
    AI_ACT_URN,
    GDPR_ART35,
    get_obligations,
)
from core.hybrid_retriever.types import RetrievalHit, RetrievalResult


class FakeRetriever:
    """fetch_by_chunk_ids → 1 hit per id richiesto, payload text = suffisso."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def fetch_by_chunk_ids(self, chunk_ids):
        self.calls.append(list(chunk_ids))
        return RetrievalResult([
            RetrievalHit(chunk_id=c, score=0.0,
                         payload={"text": f"TESTO:{c.split('__', 1)[1]}"}, rank=i + 1)
            for i, c in enumerate(chunk_ids)
        ])


# --------------------------------------------------------------------------- #
# Conteggi e shape
# --------------------------------------------------------------------------- #

def test_provider_count_and_chunk_ids():
    obs = get_obligations("provider")
    assert len(obs) == 20
    arts = [o.article for o in obs]
    assert arts[0] == "Art. 9" and arts[-1] == "Art. 73"
    # ogni voce provider cita il proprio __art_<n>
    assert obs[0].source_chunk_id == f"{AI_ACT_URN}__art_9"
    assert all(o.source_chunk_id.startswith(f"{AI_ACT_URN}__art_") for o in obs)
    # nessun paragraph per i provider
    assert all(o.paragraph is None for o in obs)


def test_deployer_count_and_chunk_ids():
    obs = get_obligations("deployer")
    assert len(obs) == 12
    # i 26(x) citano tutti __art_26; la FRIA cita __art_27
    art26 = [o for o in obs if o.article == "Art. 26"]
    fria = [o for o in obs if o.article == "Art. 27"]
    assert len(art26) == 11 and len(fria) == 1
    assert all(o.source_chunk_id == f"{AI_ACT_URN}__art_26" for o in art26)
    assert fria[0].source_chunk_id == f"{AI_ACT_URN}__art_27"
    # label con paragrafo
    labels = {o.label for o in obs}
    assert "Art. 26(9)" in labels and "Art. 27" in labels


def test_default_role_is_deployer():
    assert [o.label for o in get_obligations()] == [o.label for o in get_obligations("deployer")]


def test_invalid_role_raises():
    with pytest.raises(ValueError):
        get_obligations("auditor")


# --------------------------------------------------------------------------- #
# Tag di condizione / note / gdpr_link
# --------------------------------------------------------------------------- #

def test_condition_tags_present():
    prov = {o.label: o for o in get_obligations("provider")}
    assert prov["Art. 9"].condition is None              # sempre
    assert prov["Art. 10"].condition == "solo se usa training con dati"
    assert prov["Art. 17"].note == "PMI: forma semplificata"
    assert prov["Art. 22"].condition == "solo fornitori paesi terzi"
    assert prov["Art. 73"].condition == "al verificarsi di incidente grave"


def test_art11_provider_has_annex_iv_note():
    # FIX A rehome: il limite Allegato IV vive come note su Art. 11 (provider)
    prov = {o.label: o for o in get_obligations("provider")}
    assert "Allegato IV" in (prov["Art. 11"].note or "")
    # e NON compare tra i deployer (Art. 11 è solo provider)
    assert "Art. 11" not in {o.label for o in get_obligations("deployer")}


def test_deployer_gdpr_link_on_26_9():
    dep = {o.label: o for o in get_obligations("deployer")}
    o9 = dep["Art. 26(9)"]
    assert o9.gdpr_link == GDPR_ART35
    assert o9.note and "GDPR" in o9.note
    assert o9.condition and "DPIA" in o9.condition
    # nessun'altra voce ha gdpr_link
    assert sum(1 for o in get_obligations("deployer") if o.gdpr_link) == 1


def test_deployer_26_10_led_note_no_pointer():
    dep = {o.label: o for o in get_obligations("deployer")}
    o10 = dep["Art. 26(10)"]
    assert o10.gdpr_link is None  # LED fuori corpus → nessun puntatore
    assert "2016/680" in o10.note


# --------------------------------------------------------------------------- #
# Grounding via fetch_by_chunk_ids
# --------------------------------------------------------------------------- #

def test_grounding_populates_source_text():
    r = FakeRetriever()
    obs = get_obligations("provider", retriever=r)
    assert all(o.source_text and o.source_text.startswith("TESTO:art_") for o in obs)
    # una sola chiamata batch
    assert len(r.calls) == 1


def test_grounding_populates_gdpr_pointer_for_26_9():
    r = FakeRetriever()
    obs = get_obligations("deployer", retriever=r)
    o9 = next(o for o in obs if o.label == "Art. 26(9)")
    assert o9.source_text == "TESTO:art_26"
    assert o9.gdpr_source_text == "TESTO:art_35"
    # le voci senza gdpr_link non hanno gdpr_source_text
    o1 = next(o for o in obs if o.label == "Art. 26(1)")
    assert o1.gdpr_source_text is None
    # l'id GDPR è stato incluso nel batch di fetch
    assert GDPR_ART35 in r.calls[0]


def test_no_retriever_leaves_source_text_none():
    obs = get_obligations("deployer")
    assert all(o.source_text is None for o in obs)
