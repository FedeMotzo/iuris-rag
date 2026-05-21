"""Cross-document invariants for the chunker."""

from __future__ import annotations

from core.chunking import CHUNK_TOKEN_THRESHOLD, Chunk, chunk_document, chunk_recitals
from core.chunking._tokenizer import count_tokens


def test_sanity_no_exceptions(akn_docs, eurlex_article_docs, eurlex_recitals):
    all_chunks: list[Chunk] = []
    for doc in akn_docs.values():
        all_chunks.extend(chunk_document(doc))
    for doc in eurlex_article_docs.values():
        all_chunks.extend(chunk_document(doc))
    for recitals in eurlex_recitals.values():
        all_chunks.extend(chunk_recitals(recitals))
    assert len(all_chunks) > 0


def test_chunk_count_matches_inputs(akn_docs, eurlex_article_docs, eurlex_recitals):
    """For every input article we emit ≥1 chunk and no article is silently dropped."""
    for key, doc in akn_docs.items():
        chunks = chunk_document(doc)
        active_eids = {
            a.eid
            for c in doc.chapters
            for a in c.articles
            if not a.is_abrogated
        }
        chunk_eids = {c.article_eid for c in chunks if c.article_eid}
        assert chunk_eids == active_eids, f"{key}: missing articles {active_eids - chunk_eids}"

    for key, doc in eurlex_article_docs.items():
        chunks = chunk_document(doc)
        all_eids = {a.eid for c in doc.chapters for a in c.articles}
        # Annex chunks use a synthetic article_eid ("annex_III") and are NOT
        # in the article eid set — exclude them from this article-coverage check.
        chunk_eids = {
            c.article_eid for c in chunks
            if c.article_eid and c.chunk_type != "annex"
        }
        assert chunk_eids == all_eids, f"{key}: missing articles {all_eids - chunk_eids}"


def test_article_group_threshold(akn_docs, eurlex_article_docs):
    """Multi-comma article_group chunks must stay within the token threshold."""
    docs_to_check = list(akn_docs.values()) + list(eurlex_article_docs.values())
    for doc in docs_to_check:
        for ch in chunk_document(doc):
            if ch.chunk_type != "article_group" or len(ch.para_eids) < 2:
                continue
            tokens = count_tokens(ch.text)
            assert tokens <= CHUNK_TOKEN_THRESHOLD, (
                f"{ch.chunk_id} = {tokens} tokens (threshold={CHUNK_TOKEN_THRESHOLD})"
            )


def test_chunk_id_uniqueness(akn_docs, eurlex_article_docs, eurlex_recitals):
    seen: set[str] = set()
    for doc in akn_docs.values():
        for ch in chunk_document(doc):
            assert ch.chunk_id not in seen, f"duplicate chunk_id: {ch.chunk_id}"
            seen.add(ch.chunk_id)
    for doc in eurlex_article_docs.values():
        for ch in chunk_document(doc):
            assert ch.chunk_id not in seen, f"duplicate chunk_id: {ch.chunk_id}"
            seen.add(ch.chunk_id)
    for recitals in eurlex_recitals.values():
        for ch in chunk_recitals(recitals):
            assert ch.chunk_id not in seen, f"duplicate chunk_id: {ch.chunk_id}"
            seen.add(ch.chunk_id)


def test_para_eids_coherence(akn_docs, eurlex_article_docs):
    """For each article that was split, concatenating its sub-chunks' para_eids in
    order must match the original commi sequence (no overlap, no gap, no reorder).
    """
    def expected_para_eids(doc, source_label: str) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for ch in doc.chapters:
            for art in ch.articles:
                if hasattr(art, "is_abrogated") and art.is_abrogated:
                    continue
                if art.commi:
                    out[art.eid] = [c.eid for c in art.commi]
        return out

    def check(doc, label: str) -> None:
        expected = expected_para_eids(doc, label)
        grouped: dict[str, list[str]] = {}
        for ch in chunk_document(doc):
            if ch.chunk_type != "article_group":
                continue
            grouped.setdefault(ch.article_eid, []).extend(ch.para_eids)
        for eid, eids in grouped.items():
            assert eids == expected[eid], (
                f"{label}/{eid}: para_eids order/coverage mismatch\n"
                f"got: {eids}\nexpected: {expected[eid]}"
            )

    for k, d in akn_docs.items():
        check(d, k)
    for k, d in eurlex_article_docs.items():
        check(d, k)


def test_chunk_type_invariants(akn_docs, eurlex_article_docs):
    """`article` ⇒ para_eids empty; `article_group` ⇒ para_eids non-empty."""
    for doc in list(akn_docs.values()) + list(eurlex_article_docs.values()):
        for ch in chunk_document(doc):
            if ch.chunk_type == "article":
                assert ch.para_eids == []
            elif ch.chunk_type == "article_group":
                assert len(ch.para_eids) >= 1
