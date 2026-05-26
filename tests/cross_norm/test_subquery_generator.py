"""Test `generate_subquery` con cassette canoniche (no live LLM calls)."""

from __future__ import annotations

import pytest

from core.cross_norm.subquery_generator import generate_subquery

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)


def _count_present(text: str, candidates: list[str]) -> int:
    low = text.lower()
    return sum(1 for c in candidates if c.lower() in low)


def test_q68_gdpr_subquery_uses_norm_vocabulary(q68_stub_llm) -> None:
    out = generate_subquery(Q68, "gdpr", q68_stub_llm)
    candidates = [
        "categorie particolari",
        "dati sanitari",
        "DPIA",
        "valutazione d'impatto",
        "art. 9",
        "art. 35",
    ]
    n = _count_present(out, candidates)
    assert n >= 2, f"Sub-query GDPR contiene solo {n} marker su {candidates}: {out!r}"


def test_q68_ai_act_subquery_uses_norm_vocabulary(q68_stub_llm) -> None:
    out = generate_subquery(Q68, "ai_act", q68_stub_llm)
    candidates = ["alto rischio", "sanitario", "fornitore", "deployer"]
    n = _count_present(out, candidates)
    assert n >= 2, f"Sub-query AI Act contiene solo {n} marker su {candidates}: {out!r}"


def test_q68_l_132_2025_subquery_uses_norm_vocabulary(q68_stub_llm) -> None:
    out = generate_subquery(Q68, "l_132_2025", q68_stub_llm)
    candidates = [
        "sanitario",
        "decisioni cliniche",
        "supervisione del medico",
        "riservatezza",
    ]
    n = _count_present(out, candidates)
    assert n >= 2, f"Sub-query L.132 contiene solo {n} marker su {candidates}: {out!r}"


def test_unknown_norm_id_raises(q68_stub_llm) -> None:
    with pytest.raises(KeyError, match="not_a_norm"):
        generate_subquery(Q68, "not_a_norm", q68_stub_llm)


def test_prompt_contains_glossary_vocabulary(q68_stub_llm) -> None:
    """Lo stub controlla `Norma target:` nel prompt: se la richiesta avviene,
    il prompt è stato formattato correttamente."""
    _ = generate_subquery(Q68, "gdpr", q68_stub_llm)
    calls = q68_stub_llm.calls
    assert len(calls) == 1
    # Lo stub fa lookup `q68:gdpr` → ha trovato la riga `Norma target: GDPR / ...`
    assert calls[0]["key"] == "q68:gdpr"
    # E il prompt era abbastanza lungo da includere il vocabolario completo
    assert calls[0]["prompt_len"] > 1000


def test_max_tokens_passed_through(q68_stub_llm) -> None:
    """Verifica che `max_tokens` arrivi all'LLM client."""
    captured: dict = {}
    original = q68_stub_llm.generate

    def fake_generate(prompt, system=None, max_tokens=200, temperature=0.0):
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        return original(prompt, system, max_tokens, temperature)

    q68_stub_llm.generate = fake_generate  # type: ignore[assignment]
    generate_subquery(Q68, "gdpr", q68_stub_llm, max_tokens=150)
    assert captured["max_tokens"] == 150
    assert captured["temperature"] == 0.0
