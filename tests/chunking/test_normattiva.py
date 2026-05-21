"""AKN-specific assertions."""

from __future__ import annotations

from core.chunking import chunk_document


def test_dlgs_231_capo_sezione_deannidamento(akn_docs):
    """At least one article in D.Lgs 231/2001 must have hierarchy_path containing
    both a Capo and a Sezione label distinctly (validates the regex-based
    flat-to-nested reconstruction).
    """
    chunks = chunk_document(akn_docs["dlgs_231_2001"])
    found = False
    for ch in chunks:
        path = ch.hierarchy_path
        has_capo = any(p.startswith("Capo ") for p in path)
        has_sezione = any(p.startswith("Sezione ") for p in path)
        if has_capo and has_sezione:
            found = True
            break
    assert found, "no 231/2001 chunk has both 'Capo' and 'Sezione' in its hierarchy_path"


def test_dlgs_231_hierarchy_examples(akn_docs):
    """Spot-check: articles in 'SEZIONE II' sibling chapter (Sanzioni in generale)
    inherit Capo I from the preceding chapter — this is the deannidamento that
    can only happen by carrying state across siblings.
    """
    chunks = chunk_document(akn_docs["dlgs_231_2001"])
    sezione_ii_first_capo_i = [
        c for c in chunks
        if "Capo I" in c.hierarchy_path and "Sezione II" in c.hierarchy_path
    ]
    assert sezione_ii_first_capo_i, (
        "expected at least one 231 article with path including both 'Capo I' "
        "and 'Sezione II' (carry-over of Capo across sibling Sezione)"
    )


def test_nis2_capo_only_hierarchy(akn_docs):
    """NIS2 has clean Capo-only structure; no spurious 'Sezione' labels should appear."""
    chunks = chunk_document(akn_docs["dlgs_138_2024_nis2"])
    for ch in chunks:
        assert not any(p.startswith("Sezione ") for p in ch.hierarchy_path), (
            f"unexpected Sezione in NIS2 chunk: {ch.chunk_id} → {ch.hierarchy_path}"
        )
        assert any(p.startswith("Capo ") for p in ch.hierarchy_path)


def test_monoblock_articles_preserved(akn_docs):
    """The known monoblock-oversize articles from Normattiva produce 1 `article` chunk
    each (not article_group)."""
    known = {
        "dlgs_138_2024_nis2": "art_2",  # 3542 tokens, 1 single paragraph that the parser
        "l_132_2025": "art_19",         # 1118 tokens, no commi extracted by the parser
    }
    for doc_key, art_eid in known.items():
        chunks = [c for c in chunk_document(akn_docs[doc_key]) if c.article_eid == art_eid]
        # NIS2 art_2 has exactly 1 comma → it becomes a single `article_group`
        # with that single comma. L.132/2025 art_19 has 0 commi → `article`.
        assert len(chunks) == 1, f"{doc_key}/{art_eid}: expected 1 chunk, got {len(chunks)}"


def test_l132_art19_monoblock(akn_docs):
    """L.132/2025 art_19 has zero structured commi and exceeds 1000 tokens → emitted
    as a single `article` chunk (oversize accepted)."""
    chunks = [c for c in chunk_document(akn_docs["l_132_2025"]) if c.article_eid == "art_19"]
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "article"
    assert chunks[0].para_eids == []


def test_oversize_articles_with_multi_commi_split(akn_docs):
    """Articles whose total tokens exceed the threshold AND that have more than one
    parsed comma must split into ≥2 `article_group` chunks.
    """
    # From corpus_stats_output.json: NIS2 art_38 (16 commi), D.Lgs 231 art_25-undecies (10 commi).
    for doc_key, art_eid in [
        ("dlgs_138_2024_nis2", "art_38"),
        ("dlgs_231_2001", "art_25-undecies"),
    ]:
        chunks = [c for c in chunk_document(akn_docs[doc_key]) if c.article_eid == art_eid]
        assert len(chunks) >= 2, f"{doc_key}/{art_eid}: expected ≥2 chunks, got {len(chunks)}"
        assert all(c.chunk_type == "article_group" for c in chunks)


def test_doc_urn_format(akn_docs):
    """AKN doc_urn must match the parser's URN, stripped of the leading slash."""
    for doc in akn_docs.values():
        chunks = chunk_document(doc)
        expected_urn = doc.metadata.urn.lstrip("/")
        for ch in chunks:
            assert ch.doc_urn == expected_urn
            assert ch.chunk_id.startswith(expected_urn + "__")
