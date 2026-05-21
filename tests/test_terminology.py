"""Test per `core/terminology/expander.py`."""

from __future__ import annotations

from core.terminology import expand_query, load_aliases


# Aliases fissi per non dipendere da edit futuri di aliases.yaml.
TEST_ALIASES = {
    "FRIA": ["valutazione d'impatto sui diritti fondamentali"],
    "DPIA": ["valutazione d'impatto sulla protezione dei dati"],
    "scoring creditizio": ["merito di credito"],
}


def test_no_match_returns_identical() -> None:
    q = "Quali sono i compiti del responsabile della protezione dei dati?"
    assert expand_query(q, aliases=TEST_ALIASES) == q


def test_fria_expansion_appends_form() -> None:
    q = "Cos'è la FRIA?"
    out = expand_query(q, aliases=TEST_ALIASES)
    assert out.startswith(q)
    assert "valutazione d'impatto sui diritti fondamentali" in out


def test_fria_and_dpia_in_order() -> None:
    # Aliases iterate in YAML order: FRIA first, DPIA second.
    q = "Devo fare FRIA e DPIA?"
    out = expand_query(q, aliases=TEST_ALIASES)
    fria_form = "valutazione d'impatto sui diritti fondamentali"
    dpia_form = "valutazione d'impatto sulla protezione dei dati"
    assert fria_form in out
    assert dpia_form in out
    assert out.index(fria_form) < out.index(dpia_form)


def test_case_insensitive_match() -> None:
    fria_form = "valutazione d'impatto sui diritti fondamentali"
    out_upper = expand_query("Cos'è la FRIA?", aliases=TEST_ALIASES)
    out_lower = expand_query("Cos'è la fria?", aliases=TEST_ALIASES)
    # Le forme estese sono identiche; la query originale resta com'era
    # (preserviamo case), quindi gli output completi differiscono solo per
    # la parte iniziale ma l'espansione è identica.
    assert fria_form in out_upper
    assert fria_form in out_lower


def test_multi_token_key_scoring_creditizio() -> None:
    q = "Una banca che fa scoring creditizio deve gestire il rischio?"
    out = expand_query(q, aliases=TEST_ALIASES)
    assert "merito di credito" in out


def test_idempotent() -> None:
    q = "FRIA oltre alla DPIA?"
    once = expand_query(q, aliases=TEST_ALIASES)
    twice = expand_query(once, aliases=TEST_ALIASES)
    assert once == twice


def test_word_boundary_no_substring_match() -> None:
    # "frialdo" contiene "fria" come substring ma NON come parola separata.
    q = "Il frialdo non c'entra niente."
    out = expand_query(q, aliases=TEST_ALIASES)
    assert out == q, f"Atteso identico, ottenuto {out!r}"


def test_load_aliases_default_path() -> None:
    """Smoke: il file YAML reale carica e contiene le 3 voci minime."""
    aliases = load_aliases()
    assert "FRIA" in aliases
    assert "DPIA" in aliases
    assert "scoring creditizio" in aliases
    assert aliases["FRIA"] == ["valutazione d'impatto sui diritti fondamentali"]
