"""Tests for the EUR-Lex HTML parser against three real fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.eur_lex_parser import (
    EurLexDocument,
    parse_articles,
    parse_recitals,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURE_CONS_GDPR = REPO / "data" / "cache" / "eurlex" / "IT" / "02016R0679-20160504.html"
FIXTURE_INIT_GDPR = REPO / "spike" / "data" / "gdpr_eurlex.html"
FIXTURE_INIT_AI_ACT = REPO / "spike" / "data" / "ai_act_eurlex.html"


def _articles(doc: EurLexDocument):
    return [a for ch in doc.chapters for a in ch.articles]


def _find(doc: EurLexDocument, eid: str):
    for a in _articles(doc):
        if a.eid == eid:
            return a
    return None


@pytest.fixture(scope="module")
def cons_gdpr() -> EurLexDocument:
    return parse_articles(FIXTURE_CONS_GDPR.read_bytes(), "consolidated", "02016R0679-20160504")


@pytest.fixture(scope="module")
def init_gdpr() -> EurLexDocument:
    return parse_articles(FIXTURE_INIT_GDPR.read_bytes(), "initial", "32016R0679")


@pytest.fixture(scope="module")
def init_ai_act() -> EurLexDocument:
    return parse_articles(FIXTURE_INIT_AI_ACT.read_bytes(), "initial", "32024R1689")


def test_parse_articles_consolidated_gdpr(cons_gdpr: EurLexDocument) -> None:
    arts = _articles(cons_gdpr)
    assert len(arts) == 99

    art1 = _find(cons_gdpr, "art_1")
    assert art1 is not None
    assert art1.rubrica == "Oggetto e finalità"

    art5 = _find(cons_gdpr, "art_5")
    assert art5 is not None
    assert "Principi" in (art5.rubrica or "")

    # Metadata sanity.
    assert cons_gdpr.metadata.celex == "02016R0679-20160504"
    assert cons_gdpr.metadata.template == "consolidated"
    assert cons_gdpr.metadata.doc_type == "regulation"
    assert cons_gdpr.metadata.title and "REGOLAMENTO" in cons_gdpr.metadata.title


def test_parse_articles_initial_ai_act(init_ai_act: EurLexDocument) -> None:
    arts = _articles(init_ai_act)
    assert len(arts) == 113

    art1 = _find(init_ai_act, "art_1")
    assert art1 is not None

    # The full 1..113 range must be present without holes.
    numbers = sorted(int(a.eid[len("art_"):]) for a in arts if a.eid[len("art_"):].isdigit())
    assert numbers == list(range(1, 114))


def test_parse_articles_initial_gdpr(init_gdpr: EurLexDocument) -> None:
    arts = _articles(init_gdpr)
    assert len(arts) == 99
    # No recital should leak into the article list.
    assert all(a.eid.startswith("art_") for a in arts)
    assert not any(a.eid.startswith("rct_") for a in arts)


def test_parse_recitals_gdpr() -> None:
    recitals = parse_recitals(FIXTURE_INIT_GDPR.read_bytes(), "32016R0679")
    assert len(recitals) == 173
    numbers = sorted(r.number for r in recitals)
    assert numbers == list(range(1, 174))

    rct84 = next(r for r in recitals if r.number == 84)
    # Recital 84 is the impact-assessment / "rischio elevato" recital.
    lower = rct84.text.lower()
    assert "rischio elevato" in lower or "valutazione d'impatto" in lower or "dpia" in lower


def test_parse_recitals_ai_act() -> None:
    recitals = parse_recitals(FIXTURE_INIT_AI_ACT.read_bytes(), "32024R1689")
    assert len(recitals) == 180
    numbers = sorted(r.number for r in recitals)
    assert numbers == list(range(1, 181))
    assert all(r.celex == "32024R1689" for r in recitals)


def test_parse_recitals_on_consolidated_returns_empty() -> None:
    recitals = parse_recitals(FIXTURE_CONS_GDPR.read_bytes(), "02016R0679-20160504")
    assert recitals == []


def test_modref_filtered_from_article_text(cons_gdpr: EurLexDocument) -> None:
    art7 = _find(cons_gdpr, "art_7")
    assert art7 is not None
    assert len(art7.commi) == 4
    for c in art7.commi:
        assert "▼" not in c.text, f"comma {c.number} still contains a modref marker: {c.text[:80]!r}"
        assert "modref" not in c.text.lower()
    # Paragraph numbering survived the modref interleaving.
    assert [c.number for c in art7.commi] == ["1", "2", "3", "4"]


def test_chapters_consolidated(cons_gdpr: EurLexDocument) -> None:
    # GDPR has 11 real Capi; sections (cpt_X.sct_Y) are excluded.
    assert len(cons_gdpr.chapters) == 11
    assert [ch.number for ch in cons_gdpr.chapters] == [
        "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI",
    ]
    cap1 = cons_gdpr.chapters[0]
    assert cap1.eid == "cpt_I"
    assert cap1.number == "I"
    assert cap1.title == "Disposizioni generali"
    assert {a.eid for a in cap1.articles} == {"art_1", "art_2", "art_3", "art_4"}


# ---------------------------------------------------------------------------
# Allegato III (AI Act) — ad-hoc, solo Reg. UE 2024/1689.
# ---------------------------------------------------------------------------

def test_annex_iii_aiact_extracted(init_ai_act: EurLexDocument) -> None:
    """Dopo lo split per punto, Annex III emette 8 EurLexAnnex distinti."""
    assert len(init_ai_act.annexes) == 8
    annex_ids = [a.annex_id for a in init_ai_act.annexes]
    assert annex_ids == [f"III__point_{i}" for i in range(1, 9)]


def test_annex_iii_aiact_contains_hr_systems(init_ai_act: EurLexDocument) -> None:
    """Punto 4 (Occupazione) cita assunzione/selezione del personale —
    è il fondamento dell'use case Q1 (screening CV high-risk)."""
    p4 = next(a for a in init_ai_act.annexes if a.annex_id == "III__point_4")
    text_lower = p4.text.lower()
    assert "selezione" in text_lower or "assunzione" in text_lower


def test_annex_iii_aiact_contains_8_points(init_ai_act: EurLexDocument) -> None:
    """Sanity-check: ciascuno degli 8 chunk inizia con header 'Allegato III, punto N'."""
    for i, annex in enumerate(init_ai_act.annexes, start=1):
        first_line = annex.text.splitlines()[0]
        assert first_line == f"Allegato III, punto {i}: {annex.title}".rstrip(": "), (
            f"point_{i} header mismatch: {first_line!r}"
        )


def test_parse_annex_iii_returns_eight_points(init_ai_act: EurLexDocument) -> None:
    annexes = init_ai_act.annexes
    assert len(annexes) == 8
    assert [a.annex_id for a in annexes] == [f"III__point_{i}" for i in range(1, 9)]

    # Header su ciascun chunk
    for i, a in enumerate(annexes, start=1):
        assert a.text.startswith(f"Allegato III, punto {i}"), (
            f"point_{i} text non inizia col header attesto"
        )

    # Punto 1: Biometria + tutte e 3 le lettere (a/b/c) di copertura semantica
    p1 = annexes[0]
    assert "Biometria" in p1.text
    p1_lower = p1.text.lower()
    assert "identificazione biometrica" in p1_lower
    assert "categorizzazione biometrica" in p1_lower
    assert "riconoscimento delle emozioni" in p1_lower

    # Punto 4: lettere a) e b) — "assunzione"/"selezione" + "condizioni dei rapporti di lavoro"
    p4 = annexes[3]
    p4_lower = p4.text.lower()
    assert "assunzione" in p4_lower
    assert "selezione" in p4_lower
    assert "condizioni dei rapporti di lavoro" in p4_lower

    # Punto 2: NIENTE contaminazione cross-point (no 'Biometria')
    p2 = annexes[1]
    assert "Biometria" not in p2.text


def test_parse_annex_iii_metadata_point_index(init_ai_act: EurLexDocument) -> None:
    annexes = init_ai_act.annexes
    expected_n_letters = {1: 3, 2: 0, 3: 4, 4: 2, 5: 4, 6: 5, 7: 4, 8: 2}
    for i, a in enumerate(annexes, start=1):
        assert a.metadata["point"] == i, f"point {i}: metadata.point={a.metadata['point']!r}"
        assert a.metadata["n_letters"] == expected_n_letters[i], (
            f"point {i}: expected n_letters={expected_n_letters[i]}, "
            f"got {a.metadata['n_letters']}"
        )


# ---------------------------------------------------------------------------
# Articoli senza commi numerati — fallback "__body" su _parse_commi.
# ---------------------------------------------------------------------------

# Replica letterale del blocco art_113 dell'AI Act iniziale (32024R1689.html).
# Mantenuto come fixture sintetica per disaccoppiare il test dal file reale
# (che può cambiare nel tempo o essere assente in ambienti CI).
_AI_ACT_ART113_FIXTURE = b"""<?xml version="1.0" encoding="utf-8"?>
<root xmlns="">
  <div class="eli-subdivision" id="art_113">
    <p id="d1e9295-1-1" class="oj-ti-art">Articolo 113</p>
    <div class="eli-title" id="art_113.tit_1">
      <p class="oj-sti-art">Entrata in vigore e applicazione</p>
    </div>
    <p class="oj-normal">Il presente regolamento entra in vigore il ventesimo giorno successivo alla pubblicazione nella Gazzetta ufficiale dell'Unione europea.</p>
    <p class="oj-normal">Si applica a decorrere dal 2 agosto 2026.</p>
    <p class="oj-normal">Tuttavia:</p>
    <table><tbody><tr><td><p class="oj-normal">a)</p></td><td><p class="oj-normal">I capi I e II si applicano a decorrere dal 2 febbraio 2025;</p></td></tr></tbody></table>
    <table><tbody><tr><td><p class="oj-normal">b)</p></td><td><p class="oj-normal">Il capo III, sezione 4, il capo V, il capo VII, il capo XII e l'articolo 78 si applicano a decorrere dal 2 agosto 2025, ad eccezione dell'articolo 101;</p></td></tr></tbody></table>
    <table><tbody><tr><td><p class="oj-normal">c)</p></td><td><p class="oj-normal">L'articolo 6, paragrafo 1, e i corrispondenti obblighi di cui al presente regolamento si applicano a decorrere dal 2 agosto 2027.</p></td></tr></tbody></table>
  </div>
</root>
"""


def test_parse_commi_fallback_emits_body_for_unnumbered_article() -> None:
    doc = parse_articles(_AI_ACT_ART113_FIXTURE, "initial", "synthetic-art113")
    art = _find(doc, "art_113")
    assert art is not None
    assert art.rubrica == "Entrata in vigore e applicazione"
    assert len(art.commi) == 1
    body = art.commi[0]
    assert body.number is None
    assert body.eid == "art_113__body"
    for needle in ("2 agosto 2026", "2 febbraio 2025", "2 agosto 2025", "2 agosto 2027"):
        assert needle in body.text, f"missing {needle!r} in fallback body"


def test_parse_commi_does_not_trigger_fallback_for_healthy_article(init_ai_act: EurLexDocument) -> None:
    """Articolo sano (art_111 AI Act, commi numerati 1/2/3) NON deve usare il fallback."""
    art = _find(init_ai_act, "art_111")
    assert art is not None
    assert len(art.commi) > 1
    assert all(c.number is not None for c in art.commi)
    assert all(not c.eid.endswith("__body") for c in art.commi)
