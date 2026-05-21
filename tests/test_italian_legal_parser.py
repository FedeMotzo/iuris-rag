"""Tests for the AKN XML parser against the spike fixture (Codice Privacy)."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pytest

from core.italian_legal_parser import (
    AKNArticle,
    AKNDocument,
    parse_akn,
)

FIXTURE = Path(__file__).resolve().parents[1] / "spike" / "data" / "codice_privacy_akn.xml"


@pytest.fixture(scope="module")
def codice_privacy() -> AKNDocument:
    return parse_akn(FIXTURE.read_bytes())


def _all_articles(doc: AKNDocument) -> list[AKNArticle]:
    return [art for ch in doc.chapters for art in ch.articles]


def _find_article(doc: AKNDocument, eid: str) -> AKNArticle | None:
    for art in _all_articles(doc):
        if art.eid == eid:
            return art
    return None


def test_total_article_count(codice_privacy: AKNDocument) -> None:
    # SPIKE_RESULTS D6: 221 <article> tags in the body.
    assert len(_all_articles(codice_privacy)) == 221


def test_metadata_urn_and_dates(codice_privacy: AKNDocument) -> None:
    md = codice_privacy.metadata
    assert md.urn == "/akn/it/act/decreto_legislativo/stato/2003-06-30/196"
    assert md.doc_type == "decreto_legislativo"
    assert md.number == "196"
    assert md.date_promulgation == date(2003, 6, 30)
    assert md.date_version == date(2026, 2, 20)
    assert md.title and "Codice in materia di protezione dei dati personali" in md.title


def test_article_2_bis_eid_and_commi(codice_privacy: AKNDocument) -> None:
    art = _find_article(codice_privacy, "art_2-bis")
    assert art is not None, "art_2-bis must be present"
    assert art.eid == "art_2-bis"
    assert art.number == "2-bis"
    # The XML has a single numbered <paragraph eId="art_2-bis__para_1"> (the
    # other two <paragraph> children are the modification markers `((` / `))`
    # which the parser intentionally drops). The spike note that mentioned "5
    # commi" referred to art_2-ter in the MD parser output, not 2-bis.
    assert len(art.commi) >= 1
    assert art.commi[0].eid == "art_2-bis__para_1"
    assert art.commi[0].number == "1"
    assert "Autorita'" in art.commi[0].text or "Garante" in art.commi[0].text


def test_article_2_ter_has_four_commi(codice_privacy: AKNDocument) -> None:
    # Sanity check on a richer article (cf. SPIKE_RESULTS D1 — 5 commi in the
    # MD output, 4 numbered in the XML; the 5th in MD was a `((1-bis. ...))`
    # block embedded in an unnumbered <paragraph>).
    art = _find_article(codice_privacy, "art_2-ter")
    assert art is not None
    assert [c.number for c in art.commi] == ["1", "2", "3", "4"]


def test_article_2_sex_decies_present(codice_privacy: AKNDocument) -> None:
    # Composite suffix — verifies we treat the article number as an opaque
    # string and never try to parse it into integer parts.
    art = _find_article(codice_privacy, "art_2-sex-decies")
    assert art is not None
    assert art.eid == "art_2-sex-decies"
    assert art.number == "2-sex-decies"


def test_art_3_is_abrogated(codice_privacy: AKNDocument) -> None:
    # art_3 has empty <heading/> and a first <paragraph> whose body starts with
    # "((ARTICOLO ABROGATO DAL D.LGS. 10 AGOSTO 2018, N. 101))".
    art = _find_article(codice_privacy, "art_3")
    assert art is not None
    assert art.is_abrogated is True


def test_art_2_bis_is_not_abrogated(codice_privacy: AKNDocument) -> None:
    art = _find_article(codice_privacy, "art_2-bis")
    assert art is not None
    assert art.is_abrogated is False


def test_count_abrogated_in_codice_privacy(
    codice_privacy: AKNDocument, capsys: pytest.CaptureFixture[str]
) -> None:
    articles = _all_articles(codice_privacy)
    abrogated = [a for a in articles if a.is_abrogated]
    count = len(abrogated)
    # Stderr so it always surfaces under `pytest -v -s` for manual inspection.
    print(f"abrogated count on Codice Privacy: {count}/{len(articles)}")
    # Massive post-GDPR repeal (D.Lgs 101/2018) — expect a sizeable share.
    assert count > 50, f"expected > 50 abrogated, got {count}"
    # But never the bulk of the codex (guard against runaway false positives).
    assert count < 200, f"expected < 200 abrogated, got {count}"


def test_inline_soppresso_does_not_mark_article_abrogated() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act>
    <meta>
      <identification>
        <FRBRWork>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRExpression>
      </identification>
    </meta>
    <body>
      <chapter eId="chp_I">
        <num>I</num>
        <heading>Capo</heading>
        <article eId="art_1">
          <num>Art. 1.</num>
          <heading>(Disposizioni generali)</heading>
          <paragraph eId="art_1__para_1">
            <num>1.</num>
            <content><p>Il titolare del trattamento adotta misure adeguate. <ins>((PERIODO SOPPRESSO DAL D.L. 8 OTTOBRE 2021))</ins>. Restano valide le altre previsioni.</p></content>
          </paragraph>
        </article>
      </chapter>
    </body>
  </act>
</akomaNtoso>
"""
    doc = parse_akn(xml)
    art = doc.chapters[0].articles[0]
    assert art.eid == "art_1"
    assert art.is_abrogated is False


def test_heading_with_abrogato_marks_article() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act>
    <meta>
      <identification>
        <FRBRWork>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRExpression>
      </identification>
    </meta>
    <body>
      <chapter eId="chp_I">
        <num>I</num>
        <heading>Capo</heading>
        <article eId="art_99">
          <num>Art. 99.</num>
          <heading>ARTICOLO ABROGATO DAL DECRETO X DEL 2020</heading>
          <paragraph eId="art_99__para_1">
            <num>1.</num>
            <content><p>Testo residuo non rilevante.</p></content>
          </paragraph>
        </article>
      </chapter>
    </body>
  </act>
</akomaNtoso>
"""
    doc = parse_akn(xml)
    art = doc.chapters[0].articles[0]
    assert art.eid == "art_99"
    assert art.is_abrogated is True


def test_chapters_present_and_articles_belong_to_chapters(codice_privacy: AKNDocument) -> None:
    assert len(codice_privacy.chapters) >= 1
    # Codice Privacy uses real <chapter> tags, so no synthetic root chapter.
    assert all(ch.eid for ch in codice_privacy.chapters)


def test_attachments_info_logged_on_codice_privacy(caplog: pytest.LogCaptureFixture) -> None:
    # Codice Privacy ships 106 <attachment> blocks (deontological codes etc.).
    # The parser must announce them at INFO level but not parse them in v1.
    with caplog.at_level(logging.INFO, logger="core.italian_legal_parser.parser"):
        parse_akn(FIXTURE.read_bytes())

    info_messages = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert any(
        "Found 106 attachments, skipped (out of scope v1)" == m for m in info_messages
    ), f"Expected attachment-count INFO log; got: {info_messages}"


def test_no_attachment_log_when_absent(caplog: pytest.LogCaptureFixture) -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act>
    <meta>
      <identification>
        <FRBRWork>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRExpression>
      </identification>
    </meta>
    <body>
      <chapter eId="chp_I">
        <num>I</num>
        <heading>Capo</heading>
        <article eId="art_1">
          <num>Art. 1.</num>
          <heading>(Rubrica)</heading>
          <paragraph eId="art_1__para_1">
            <num>1.</num>
            <content><p>Testo del comma 1.</p></content>
          </paragraph>
        </article>
      </chapter>
    </body>
  </act>
</akomaNtoso>
"""
    with caplog.at_level(logging.INFO, logger="core.italian_legal_parser.parser"):
        parse_akn(xml)

    attachment_logs = [
        r for r in caplog.records if "attachments" in r.getMessage().lower()
    ]
    assert attachment_logs == [], (
        f"Expected no attachment log when none present; got: "
        f"{[r.getMessage() for r in attachment_logs]}"
    )


def test_warns_on_unhandled_structural_tag(caplog: pytest.LogCaptureFixture) -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act>
    <meta>
      <identification>
        <FRBRWork>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRthis value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01/!main"/>
          <FRBRuri value="/akn/it/act/legge/stato/2024-01-01/1/ita@2024-01-01"/>
          <FRBRdate date="2024-01-01" name=""/>
        </FRBRExpression>
      </identification>
    </meta>
    <body>
      <part eId="part_I">
        <num>PARTE I</num>
        <heading>Una parte non gestita</heading>
      </part>
      <chapter eId="chp_I">
        <num>I</num>
        <heading>Capo</heading>
        <article eId="art_1">
          <num>Art. 1.</num>
          <heading>(Rubrica)</heading>
          <paragraph eId="art_1__para_1">
            <num>1.</num>
            <content><p>Testo del comma 1.</p></content>
          </paragraph>
        </article>
      </chapter>
    </body>
  </act>
</akomaNtoso>
"""
    with caplog.at_level(logging.WARNING, logger="core.italian_legal_parser.parser"):
        doc = parse_akn(xml)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("<part>" in r.getMessage() and "part_I" in r.getMessage() for r in warnings), (
        f"Expected a warning mentioning <part> with eId 'part_I'; got: "
        f"{[r.getMessage() for r in warnings]}"
    )

    # Sanity: the rest of the document still parsed.
    assert doc.metadata.urn == "/akn/it/act/legge/stato/2024-01-01/1"
    assert len(doc.chapters) == 1
    assert doc.chapters[0].articles[0].eid == "art_1"
