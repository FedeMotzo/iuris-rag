"""Test unitari per `core/normative_graph/`.

Nessuna dipendenza da Qdrant: tutti i test usano fixture in-memory o file
temporanei. Il graph reale di produzione non viene mai caricato qui.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.normative_graph import (
    ExpandedChunk,
    GraphLink,
    expand_context,
    load_graph,
)


# ----------------------------------------------------------------------------
# Helpers / fixture
# ----------------------------------------------------------------------------

def _mk_link(a: str, b: str, rel: str = "complementare", note: str = "n") -> GraphLink:
    return GraphLink(
        from_chunk=a,
        to_chunk=b,
        relation=rel,  # type: ignore[arg-type]
        note=note,
    )


@pytest.fixture
def mini_graph() -> list[GraphLink]:
    """Mini graph in-memory: 4 link sintatticamente validi, contenuto inventato."""
    return [
        _mk_link("test_chunk_a", "test_chunk_b", "complementare", "a<->b"),
        _mk_link("test_chunk_c", "test_chunk_d", "presupposto_di", "c<->d"),
        _mk_link("test_chunk_a", "test_chunk_e", "rinvia_a", "a<->e"),
        _mk_link("test_chunk_b", "test_chunk_e", "attua", "b<->e"),
    ]


# ----------------------------------------------------------------------------
# Loader
# ----------------------------------------------------------------------------

def test_load_graph_valid(tmp_path: Path) -> None:
    p = tmp_path / "g.yaml"
    p.write_text(
        "- from: a\n  to: b\n  relation: complementare\n  note: n\n"
        "- from: c\n  to: d\n  relation: deroga\n  note: n2\n",
        encoding="utf-8",
    )
    links = load_graph(p)
    assert len(links) == 2
    assert all(isinstance(l, GraphLink) for l in links)
    assert links[0].from_chunk == "a"
    assert links[0].to_chunk == "b"
    assert links[1].relation == "deroga"


def test_load_graph_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_graph(tmp_path / "does_not_exist.yaml")


def test_load_graph_exact_duplicate(tmp_path: Path) -> None:
    p = tmp_path / "g.yaml"
    p.write_text(
        "- from: a\n  to: b\n  relation: complementare\n  note: n1\n"
        "- from: a\n  to: b\n  relation: complementare\n  note: n2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicato"):
        load_graph(p)


def test_load_graph_invalid_relation(tmp_path: Path) -> None:
    p = tmp_path / "g.yaml"
    p.write_text(
        "- from: a\n  to: b\n  relation: BOGUS_RELATION\n  note: n\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_graph(p)


# ----------------------------------------------------------------------------
# Expander
# ----------------------------------------------------------------------------

def test_expand_no_applicable_links(mini_graph: list[GraphLink]) -> None:
    retrieved = [("unrelated_x", 0.9), ("unrelated_y", 0.8)]
    out = expand_context(retrieved, mini_graph, max_expansions=5)
    assert out == []


def test_expand_forward_direction(mini_graph: list[GraphLink]) -> None:
    retrieved = [("test_chunk_c", 0.9)]
    out = expand_context(retrieved, mini_graph, max_expansions=5)
    assert len(out) == 1
    assert out[0].chunk_id == "test_chunk_d"
    assert out[0].expanded_from == "test_chunk_c"
    assert out[0].relation == "presupposto_di"
    assert out[0].note == "c<->d"
    assert out[0].source_rank == 1


def test_expand_reverse_direction(mini_graph: list[GraphLink]) -> None:
    # Link nel graph: c -> d. Retrieved contiene d, deve espandere a c.
    retrieved = [("test_chunk_d", 0.9)]
    out = expand_context(retrieved, mini_graph, max_expansions=5)
    assert len(out) == 1
    assert out[0].chunk_id == "test_chunk_c"
    assert out[0].expanded_from == "test_chunk_d"
    assert out[0].relation == "presupposto_di"


def test_expand_skips_chunks_already_in_top_k(mini_graph: list[GraphLink]) -> None:
    # a linkato a b; entrambi nel top-K -> nessuna espansione fra loro.
    # In più, a è linkato a e e b è linkato a e -> e va espanso una volta.
    retrieved = [("test_chunk_a", 0.9), ("test_chunk_b", 0.8)]
    out = expand_context(retrieved, mini_graph, max_expansions=5)
    chunk_ids = {e.chunk_id for e in out}
    assert "test_chunk_a" not in chunk_ids
    assert "test_chunk_b" not in chunk_ids
    assert "test_chunk_e" in chunk_ids
    # e deve comparire una sola volta
    e_entries = [x for x in out if x.chunk_id == "test_chunk_e"]
    assert len(e_entries) == 1


def test_expand_dedup_keeps_lowest_source_rank(mini_graph: list[GraphLink]) -> None:
    # a (rank 1) e b (rank 2) entrambi linkati a e: source_rank deve essere 1.
    retrieved = [("test_chunk_a", 0.9), ("test_chunk_b", 0.8)]
    out = expand_context(retrieved, mini_graph, max_expansions=5)
    e_entries = [x for x in out if x.chunk_id == "test_chunk_e"]
    assert len(e_entries) == 1
    assert e_entries[0].source_rank == 1
    assert e_entries[0].expanded_from == "test_chunk_a"


def test_expand_respects_max_expansions_cap() -> None:
    # 5 chunk sorgente, ciascuno linkato a un chunk distinto: cap a 2 deve
    # tenere solo i 2 con source_rank più basso.
    graph = [
        _mk_link("src1", "tgt_z", note="1"),  # rank 1 -> tgt_z
        _mk_link("src2", "tgt_y", note="2"),  # rank 2 -> tgt_y
        _mk_link("src3", "tgt_x", note="3"),  # rank 3 -> tgt_x
        _mk_link("src4", "tgt_w", note="4"),  # rank 4 -> tgt_w
        _mk_link("src5", "tgt_v", note="5"),  # rank 5 -> tgt_v
    ]
    retrieved = [(f"src{i}", 1.0 - i * 0.1) for i in range(1, 6)]
    out = expand_context(retrieved, graph, max_expansions=2)
    assert len(out) == 2
    assert [e.source_rank for e in out] == [1, 2]
    assert {e.chunk_id for e in out} == {"tgt_z", "tgt_y"}


def test_expand_determinism(mini_graph: list[GraphLink]) -> None:
    retrieved = [
        ("test_chunk_a", 0.9),
        ("test_chunk_b", 0.85),
        ("test_chunk_c", 0.8),
    ]
    out1 = expand_context(retrieved, mini_graph, max_expansions=5)
    out2 = expand_context(retrieved, mini_graph, max_expansions=5)
    assert out1 == out2
    # E ordine completo identico
    assert [e.chunk_id for e in out1] == [e.chunk_id for e in out2]


def test_expand_tiebreak_lexicographic() -> None:
    # Due candidati con stesso source_rank (entrambi linkati a src1 al rank 1)
    # devono uscire in ordine lessicografico per chunk_id.
    graph = [
        _mk_link("src1", "tgt_zebra", note="z"),
        _mk_link("src1", "tgt_alpha", note="a"),
        _mk_link("src1", "tgt_mango", note="m"),
    ]
    retrieved = [("src1", 0.9)]
    out = expand_context(retrieved, graph, max_expansions=5)
    assert [e.chunk_id for e in out] == ["tgt_alpha", "tgt_mango", "tgt_zebra"]
    assert all(e.source_rank == 1 for e in out)


# ----------------------------------------------------------------------------
# Extra: copertura comportamenti di bordo
# ----------------------------------------------------------------------------

def test_expand_empty_inputs(mini_graph: list[GraphLink]) -> None:
    assert expand_context([], mini_graph, max_expansions=5) == []
    assert expand_context([("x", 0.5)], [], max_expansions=5) == []
    assert expand_context([("test_chunk_a", 0.5)], mini_graph, max_expansions=0) == []


def test_expanded_chunk_model_fields() -> None:
    e = ExpandedChunk(
        chunk_id="x",
        expanded_from="y",
        relation="complementare",
        note="n",
        source_rank=3,
    )
    assert e.chunk_id == "x"
    assert e.source_rank == 3
