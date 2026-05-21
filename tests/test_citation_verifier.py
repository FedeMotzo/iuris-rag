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
