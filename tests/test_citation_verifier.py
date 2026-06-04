"""Test per `core/citation_verifier`."""

from __future__ import annotations

from core.citation_verifier import verify_citations


def test_empty_output() -> None:
    r = verify_citations("", retrieval_context=set())
    assert r.markers == []
    assert r.n_total == 0
    assert r.all_verified is True
    assert r.annotated_text == ""


def test_no_markers() -> None:
    text = "Risposta narrativa senza citazioni."
    r = verify_citations(text, retrieval_context={"some/chunk"})
    assert r.markers == []
    assert r.n_total == 0
    assert r.all_verified is True
    assert r.annotated_text == text


def test_single_verified_marker() -> None:
    text = "Vedi [cite:gdpr/art_35] per la DPIA."
    r = verify_citations(text, retrieval_context={"gdpr/art_35"})
    assert r.n_total == 1
    assert r.n_verified == 1
    assert r.all_verified is True
    assert r.annotated_text == text
    assert r.markers[0].chunk_id == "gdpr/art_35"
    assert r.markers[0].verified is True
    assert r.markers[0].reason == "ok"


def test_single_unknown_marker() -> None:
    text = "Vedi [cite:bogus/chunk] per la DPIA."
    r = verify_citations(text, retrieval_context={"gdpr/art_35"})
    assert r.n_total == 1
    assert r.n_verified == 0
    assert r.n_unverified == 1
    assert r.all_verified is False
    assert "[cite:bogus/chunk NON VERIFICATA]" in r.annotated_text
    assert r.markers[0].verified is False
    assert r.markers[0].reason == "unknown_chunk_id"


def test_mixed_verified_and_unknown_preserves_order() -> None:
    text = "Prima [cite:gdpr/art_35], poi [cite:foo/bar], infine [cite:aiact/art_27]."
    ctx = {"gdpr/art_35", "aiact/art_27"}
    r = verify_citations(text, retrieval_context=ctx)
    assert r.n_total == 3
    assert r.n_verified == 2
    assert r.n_unverified == 1
    assert [m.chunk_id for m in r.markers] == [
        "gdpr/art_35", "foo/bar", "aiact/art_27",
    ]
    assert "[cite:gdpr/art_35]" in r.annotated_text
    assert "[cite:foo/bar NON VERIFICATA]" in r.annotated_text
    assert "[cite:aiact/art_27]" in r.annotated_text


def test_duplicate_marker_both_present() -> None:
    text = "Primo [cite:gdpr/art_35], poi di nuovo [cite:gdpr/art_35]."
    r = verify_citations(text, retrieval_context={"gdpr/art_35"})
    assert r.n_total == 2
    assert r.n_verified == 2
    assert all(m.verified for m in r.markers)
    assert r.markers[0].span_start < r.markers[1].span_start


def test_complex_chunk_id_eli_uri() -> None:
    cid = "eli/reg/2016/679/oj__art_35"
    text = f"Riferimento: [cite:{cid}]."
    r = verify_citations(text, retrieval_context={cid})
    assert r.n_total == 1
    assert r.markers[0].chunk_id == cid
    assert r.markers[0].verified is True


def test_chunk_id_with_dashes_and_split() -> None:
    cid = "akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-sex-decies"
    text = f"Vedi [cite:{cid}] sui dati."
    r = verify_citations(text, retrieval_context={cid})
    assert r.n_total == 1
    assert r.markers[0].chunk_id == cid


def test_malformed_marker_ignored() -> None:
    text = "Marker vuoto [cite:] e con spazio [cite: foo] da ignorare."
    r = verify_citations(text, retrieval_context={"foo"})
    assert r.n_total == 0
    assert r.annotated_text == text


def test_retrieval_context_as_list() -> None:
    text = "Vedi [cite:gdpr/art_35]."
    r = verify_citations(text, retrieval_context=["gdpr/art_35", "other"])
    assert r.n_total == 1
    assert r.markers[0].verified is True


def test_deterministic_repeated_call() -> None:
    text = "Mix [cite:ok], [cite:nope], [cite:ok]."
    ctx = ["ok"]
    r1 = verify_citations(text, retrieval_context=ctx)
    r2 = verify_citations(text, retrieval_context=ctx)
    assert r1.model_dump() == r2.model_dump()
    assert r1.model_dump_json() == r2.model_dump_json()


# ----------------------------------------------------- normalizzazioni additive
# Marker malformati osservati nel run map→assembly (Q68/Q70/Q76).

_AI = "eli/reg/2024/1689/oj"
_D231 = "akn/it/act/decreto_legislativo/stato/2001-06-08/231"


def test_paragraph_suffix_tolerated() -> None:
    """[cite:ID, paragrafo 1] → verificato (prefisso ID al confine)."""
    cid = f"{_AI}__art_12"
    text = f"Logging [cite:{cid}, paragrafo 1] e tracciabilità."
    r = verify_citations(text, retrieval_context={cid})
    assert r.n_total == 1
    assert r.all_verified is True


def test_paragraph_suffix_abbreviato_punto() -> None:
    cid = f"{_AI}__art_26"
    text = f"Obblighi [cite:{cid}, par. 2] del deployer."
    r = verify_citations(text, retrieval_context={cid})
    assert r.all_verified is True


def test_multi_cite_semicolon() -> None:
    a, b = f"{_AI}__art_12", f"{_AI}__art_19"
    text = f"Vedi [cite:{a}; cite:{b}]."
    r = verify_citations(text, retrieval_context={a, b})
    assert r.all_verified is True


def test_multi_cite_comma_internal() -> None:
    a, b = f"{_D231}__art_1", f"{_D231}__art_5"
    text = f"Imputazione [cite:{a}, cite:{b}]."
    r = verify_citations(text, retrieval_context={a, b})
    assert r.all_verified is True


def test_abbreviated_id_residuo_unverified() -> None:
    """Id abbreviato senza doc_urn → resta unverified (no match per suffisso)."""
    text = "Notifica [cite:art_7] e [cite:art_42]."
    r = verify_citations(text, retrieval_context={"akn/it/act/x/138__art_7"})
    assert r.n_total == 2
    assert r.n_verified == 0
    assert r.all_verified is False


def test_prefix_no_false_positive_art3_vs_art35() -> None:
    """art_3 noto NON deve verificare un cite ad art_35 (confine separatore)."""
    known = f"{_AI}__art_3"
    text = f"Vedi [cite:{_AI}__art_35]."
    r = verify_citations(text, retrieval_context={known})
    assert r.all_verified is False
