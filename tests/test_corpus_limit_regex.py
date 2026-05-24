"""Test del pattern CORPUS_LIMIT_RE centralizzato in
`spike/corpus_limit_regex.py`. Copertura delle 4 famiglie lessicali
osservate sulle risposte reali F.2 + subset dev (Q9, Q35, Q43, Q49)
e sanity check su un falso positivo plausibile.
"""

from __future__ import annotations

from spike.corpus_limit_regex import CORPUS_LIMIT_RE


# ---------------------------------------------------------------------------
# Famiglia 1 — canonico gold
# ---------------------------------------------------------------------------

def test_canonico_gold() -> None:
    txt = (
        "Le disposizioni della direttiva ePrivacy non sono incluse nel "
        "corpus normativo di riferimento di questo sistema."
    )
    assert CORPUS_LIMIT_RE.search(txt) is not None


# ---------------------------------------------------------------------------
# Famiglia 2 — "contesto (...) non contiene/include/riguarda"
# ---------------------------------------------------------------------------

def test_contesto_non_contiene() -> None:
    txt = (
        "Il contesto normativo fornito non contiene riferimenti sufficienti "
        "per rispondere con precisione."
    )
    assert CORPUS_LIMIT_RE.search(txt) is not None


def test_contesto_non_include() -> None:
    txt = "Il contesto fornito non include le disposizioni del D.Lgs. 231."
    assert CORPUS_LIMIT_RE.search(txt) is not None


def test_contesto_non_riguarda() -> None:
    txt = "Il contesto normativo non riguarda direttamente il caso esposto."
    assert CORPUS_LIMIT_RE.search(txt) is not None


# ---------------------------------------------------------------------------
# Famiglia 3 — "assenti / non presenti nel contesto"
# ---------------------------------------------------------------------------

def test_assenti_nel_contesto() -> None:
    txt = "Le relative norme settoriali risultano assenti nel contesto fornito."
    assert CORPUS_LIMIT_RE.search(txt) is not None


# ---------------------------------------------------------------------------
# Famiglia 4 — meta-richiesta di norme mancanti
# ---------------------------------------------------------------------------

def test_sarebbe_necessario_disporre() -> None:
    txt = (
        "Per rispondere correttamente sarebbe necessario disporre delle "
        "relative norme settoriali."
    )
    assert CORPUS_LIMIT_RE.search(txt) is not None


def test_sarebbe_necessario_fare_riferimento() -> None:
    txt = (
        "Sarebbe necessario fare riferimento all'intero Regolamento UE "
        "2024/1689 per ottenere una risposta completa."
    )
    assert CORPUS_LIMIT_RE.search(txt) is not None


def test_sarebbe_necessario_consultare() -> None:
    txt = "Sarebbe necessario consultare la direttiva ePrivacy per il consenso ai cookie."
    assert CORPUS_LIMIT_RE.search(txt) is not None


# ---------------------------------------------------------------------------
# Negativi
# ---------------------------------------------------------------------------

def test_no_match_positivo() -> None:
    """Risposta groundata non deve matchare nessuna delle 4 famiglie."""
    txt = (
        "L'articolo 27 dell'AI Act prevede che il deployer effettui una "
        "valutazione d'impatto sui diritti fondamentali prima di utilizzare "
        "un sistema di IA ad alto rischio [cite:eli/reg/2024/1689/oj__art_27]."
    )
    assert CORPUS_LIMIT_RE.search(txt) is None


def test_no_match_falso_positivo() -> None:
    """`contesto storico` con `non riguarda` NON deve matchare: il qualificatore
    della famiglia 2 ammette solo "normativo"/"fornito" (o nulla), non parole
    arbitrarie tra "contesto" e "non".
    """
    txt = "Il contesto storico non riguarda questo aspetto del trattamento."
    assert CORPUS_LIMIT_RE.search(txt) is None
