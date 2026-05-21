"""EUR-Lex specific assertions."""

from __future__ import annotations

from core.chunking import chunk_document, chunk_recitals


def test_recital_counts(eurlex_recitals):
    """Spec-defined exact counts (test #8)."""
    gdpr = chunk_recitals(eurlex_recitals["gdpr_initial"])
    ai_act = chunk_recitals(eurlex_recitals["ai_act_initial"])
    assert len(gdpr) == 173, f"GDPR initial recitals: expected 173, got {len(gdpr)}"
    assert len(ai_act) == 180, f"AI Act initial recitals: expected 180, got {len(ai_act)}"


def test_all_recitals_are_recital_type(eurlex_recitals):
    for recitals in eurlex_recitals.values():
        for ch in chunk_recitals(recitals):
            assert ch.chunk_type == "recital"
            assert ch.article_eid is None
            assert ch.para_eids == []
            assert "recital_number" in ch.metadata


def test_recital_chunk_id_format(eurlex_recitals):
    ai_act = chunk_recitals(eurlex_recitals["ai_act_initial"])
    # ELI URN for AI Act regulation 2024/1689.
    by_num = {ch.metadata["recital_number"]: ch for ch in ai_act}
    assert by_num[84].chunk_id == "eli/reg/2024/1689/oj__recital_84"


def test_gdpr_monoblock_article(eurlex_article_docs):
    """GDPR art_4 (Definizioni) is monoblock (~1982 tokens) → 1 `article` chunk."""
    chunks = [
        c for c in chunk_document(eurlex_article_docs["gdpr_consolidated"])
        if c.article_eid == "art_4"
    ]
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "article"
    assert chunks[0].para_eids == []


def test_ai_act_monoblock_articles(eurlex_article_docs):
    """AI Act art_3 (4188t, definitions) and art_66 (1023t) are monoblock per stats."""
    chunks = chunk_document(eurlex_article_docs["ai_act_initial"])
    for art_eid in ("art_3", "art_66"):
        ch = [c for c in chunks if c.article_eid == art_eid]
        assert len(ch) == 1, f"{art_eid}: expected 1 chunk, got {len(ch)}"
        assert ch[0].chunk_type == "article"
        assert ch[0].para_eids == []


def test_ai_act_oversize_with_commi_split(eurlex_article_docs):
    """AI Act art_5 (2553t, 8 commi) and art_57 (2179t, 17 commi) split into ≥2 groups."""
    chunks = chunk_document(eurlex_article_docs["ai_act_initial"])
    for art_eid in ("art_5", "art_57"):
        sub = [c for c in chunks if c.article_eid == art_eid]
        assert len(sub) >= 2, f"{art_eid}: expected ≥2 chunks, got {len(sub)}"
        assert all(c.chunk_type == "article_group" for c in sub)


def test_eurlex_doc_urn(eurlex_article_docs):
    """CELEX-derived ELI URN."""
    expected = {
        "gdpr_consolidated": "eli/reg/2016/679/oj",
        "ai_act_initial": "eli/reg/2024/1689/oj",
    }
    for key, doc in eurlex_article_docs.items():
        chunks = chunk_document(doc)
        for ch in chunks:
            assert ch.doc_urn == expected[key], f"{key}: {ch.doc_urn} != {expected[key]}"


def test_eurlex_hierarchy_has_chapter(eurlex_article_docs):
    """Every EUR-Lex *article* chunk has a Capo prefix in hierarchy_path.
    Annex chunks live outside the chapter tree and are intentionally excluded.
    """
    for doc in eurlex_article_docs.values():
        for ch in chunk_document(doc):
            if ch.chunk_type == "annex":
                continue
            assert ch.hierarchy_path, f"{ch.chunk_id}: empty hierarchy_path"
            assert any(p.startswith("Capo ") for p in ch.hierarchy_path), (
                f"{ch.chunk_id}: no 'Capo' in {ch.hierarchy_path}"
            )


def test_aiact_chunking_includes_annex_iii(eurlex_article_docs):
    """L'AI Act produce 8 chunk di tipo annex, uno per macro-punto di Annex III."""
    chunks = chunk_document(eurlex_article_docs["ai_act_initial"])
    annex_chunks = [c for c in chunks if c.chunk_type == "annex"]
    assert len(annex_chunks) == 8
    annex_ids = sorted(c.metadata["annex_id"] for c in annex_chunks)
    assert annex_ids == [f"III__point_{i}" for i in range(1, 9)]
    for ch in annex_chunks:
        assert ch.article_eid == f"annex_{ch.metadata['annex_id']}"


def test_annex_chunk_id_format(eurlex_article_docs):
    chunks = chunk_document(eurlex_article_docs["ai_act_initial"])
    annex_chunks = sorted(
        (c for c in chunks if c.chunk_type == "annex"),
        key=lambda c: c.metadata["point"],
    )
    assert annex_chunks[0].chunk_id == "eli/reg/2024/1689/oj__annex_III__point_1"
    assert annex_chunks[3].chunk_id == "eli/reg/2024/1689/oj__annex_III__point_4"
    assert annex_chunks[7].chunk_id == "eli/reg/2024/1689/oj__annex_III__point_8"
    # hierarchy_path a 2 livelli: allegato intero + singolo punto
    p4 = annex_chunks[3]
    assert len(p4.hierarchy_path) == 2
    assert p4.hierarchy_path[0].startswith("Allegato III - ")
    assert p4.hierarchy_path[1].startswith("Allegato III, punto 4")


def test_gdpr_chunking_no_annexes(eurlex_article_docs):
    chunks = chunk_document(eurlex_article_docs["gdpr_consolidated"])
    assert not any(c.chunk_type == "annex" for c in chunks)
