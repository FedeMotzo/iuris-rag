"""Unit test del builder della card di CLASSIFICAZIONE (DoD a, post-split).

Sez. 1-3 dal ClassificationJudgment; sez. 6 limiti. Niente sez. 4 (gli
adempimenti sono separati: get_obligations). Nessun LLM, nessun Qdrant.
"""

from __future__ import annotations

from core.classification.builder import build_classification_card
from core.classification.judge import PROHIBITED_PRACTICES
from core.classification.models import (
    AnnexJudgment,
    ClassificationJudgment,
    PlausibilityJudgment,
    ProhibitedPracticeJudgment,
)

URN = "eli/reg/2024/1689/oj"
ART5 = f"{URN}__art_5__paras_1_3"


def _judgment(*, annex_applies=None, practice=None, art6_1=False, art6_3=False):
    """practice: lettera 'a'..'h' della pratica vietata da marcare applies=true."""
    annex_applies = annex_applies or {}
    annex = []
    for n in range(1, 9):
        if n in annex_applies:
            reason, cite = annex_applies[n]
            annex.append(AnnexJudgment(point=n, applies=True, reason=reason, cite=cite))
        else:
            annex.append(AnnexJudgment(point=n, applies=False, reason="", cite=None))
    practices = []
    for k, label in PROHIBITED_PRACTICES:
        if k == practice:
            practices.append(ProhibitedPracticeJudgment(
                practice=k, label=label, applies=True,
                reason="inferenza emozioni sul lavoro", cite=ART5))
        else:
            practices.append(ProhibitedPracticeJudgment(
                practice=k, label=label, applies=False, reason="", cite=None))
    return ClassificationJudgment(
        annex_iii=annex,
        prohibited_practices=practices,
        art6_1_safety_component=PlausibilityJudgment(plausible=art6_1, reason="dispositivo medico"),
        art6_3_exception=PlausibilityJudgment(plausible=art6_3, reason="compito ristretto"),
    )


def test_card_has_no_obligations_attr():
    card = build_classification_card(_judgment())
    assert not hasattr(card, "obligations")


def test_annex_category_from_judgment():
    j = _judgment(annex_applies={4: ("occupazione e selezione", f"{URN}__annex_III__point_4")},
                  art6_3=True)
    card = build_classification_card(j)
    assert card.annex_iii_category is not None
    assert "punto 4" in card.annex_iii_category
    assert "occupazione e selezione" in card.annex_iii_category
    assert "Allegato III, punto 4" in card.verdict
    # sez. 3 dal reason del giudice (plausible=True)
    assert card.art6_3_exception.startswith("Possibile deroga ex art. 6(3):")
    assert "compito ristretto" in card.art6_3_exception
    assert card.prohibited_flag is False


# --- FIX #1: verdetto a 3 stati ------------------------------------------- #

def test_verdict_state3_true_negative():
    """Niente annex, art6_1 NON plausibile → 'non risulta alto rischio', SENZA
    menzione di art. 6(1)."""
    card = build_classification_card(_judgment())
    assert card.annex_iii_category is None
    assert "Non risulta alto rischio" in card.verdict
    assert "6(1)" not in card.verdict
    assert card.art6_3_exception is None


def test_verdict_state2_art6_1_pathway():
    """Niente annex ma art6_1 plausibile → verdetto cita art. 6(1) e 'POSSIBILE
    alto rischio'; high_risk_annex resta False (nessun obbligo)."""
    card = build_classification_card(_judgment(art6_1=True))
    assert card.annex_iii_category is None
    assert "art. 6(1)" in card.verdict
    assert "POSSIBILE alto rischio" in card.verdict
    assert "dispositivo medico" in card.verdict  # reason del giudice
    assert card.art6_3_exception is None  # non high_risk_annex


# --- FIX #2: sez. 3 dal reason del giudice -------------------------------- #

def test_sez3_not_applicable_shows_reason():
    """high_risk_annex True ma 6(3) NON plausibile → 'non applicabile: <reason>'."""
    j = _judgment(annex_applies={4: ("occupazione", f"{URN}__annex_III__point_4")},
                  art6_3=False)
    card = build_classification_card(j)
    assert card.art6_3_exception.startswith("Eccezione art. 6(3) non applicabile:")
    assert "compito ristretto" in card.art6_3_exception  # reason del giudice


# --- FIX #3: niente doppio punto ------------------------------------------ #

def test_no_double_period_in_verdict():
    j = _judgment(annex_applies={4: ("occupazione e selezione del personale.",
                                     f"{URN}__annex_III__point_4")})
    card = build_classification_card(j)
    assert ".. " not in card.verdict
    assert "personale. Verificare" in card.verdict


# --- FIX art. 5: decomposizione + priorità verdetto -------------------- #

def test_prohibited_flag_from_practice():
    card = build_classification_card(_judgment(practice="f"))
    assert card.prohibited_flag is True
    # FIX #3: il verdetto APRE con la pratica vietata
    assert card.verdict.startswith("PRATICA VIETATA ex art. 5:")
    assert "emozioni" in card.verdict.lower()
    assert "non può essere immesso sul mercato" in card.verdict


def test_prohibited_overrides_annex_with_secondary_line():
    """Vietata + Allegato III → verdetto apre con vietata, annex come secondaria."""
    j = _judgment(annex_applies={4: ("occupazione", f"{URN}__annex_III__point_4")},
                  practice="f")
    card = build_classification_card(j)
    assert card.verdict.startswith("PRATICA VIETATA ex art. 5:")
    assert "rientrerebbe anche in Allegato III punto 4" in card.verdict
    assert card.prohibited_flag is True


def test_no_practice_no_prohibited():
    card = build_classification_card(_judgment())
    assert card.prohibited_flag is False
    assert "PRATICA VIETATA" not in card.verdict


def test_mdr_limit_only_when_art6_1_plausible():
    # FIX A: MDR mostrato SOLO se art6_1.plausible
    card = build_classification_card(_judgment(art6_1=True))
    assert any("art. 6(1)" in l for l in card.declared_limits)
    assert any("dispositivo medico" in l for l in card.declared_limits)
    # mai il limite Allegato IV nella card
    assert not any("Allegato IV" in l for l in card.declared_limits)


def test_no_limits_when_not_art6_1():
    # q101/q102/negativi/vietata → sez. 6 vuota
    card = build_classification_card(_judgment())
    assert card.declared_limits == []
    card_annex = build_classification_card(
        _judgment(annex_applies={4: ("occupazione", f"{URN}__annex_III__point_4")}))
    assert card_annex.declared_limits == []


def test_multiple_annex_points():
    j = _judgment(annex_applies={
        4: ("occupazione", f"{URN}__annex_III__point_4"),
        5: ("servizi essenziali", f"{URN}__annex_III__point_5"),
    })
    card = build_classification_card(j)
    assert "punto 4" in card.annex_iii_category
    assert "punto 5" in card.annex_iii_category


def test_disclaimer_present():
    card = build_classification_card(_judgment())
    assert "DPO" in card.disclaimer


def test_prohibited_verdict_no_nested_parens():
    # FIX B: reason concatenato con ' — ', niente '(... (reason))'
    card = build_classification_card(_judgment(practice="f"))
    assert card.verdict.startswith("PRATICA VIETATA ex art. 5:")
    assert " — inferenza emozioni sul lavoro" in card.verdict
    # nessuna parentesi annidata: dopo '(salvo motivi…/sicurezza)' non si apre '(' col reason
    assert "sicurezza) (" not in card.verdict
