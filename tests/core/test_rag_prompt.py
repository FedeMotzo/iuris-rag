"""Test per `core/rag_prompt`."""

from __future__ import annotations

import pytest

from core.hybrid_retriever.types import RetrievalHit, RetrievalResult
from core.normative_graph.models import ExpandedChunk
from core.rag_prompt import build_user_prompt, load_system_prompt
from core.rag_prompt.templates import load_system_prompt as _ls


def _hit(chunk_id: str, hierarchy: list[str], text: str, rank: int = 1) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id,
        score=1.0,
        payload={"hierarchy_path": hierarchy, "text": text, "chunk_id": chunk_id},
        rank=rank,
    )


# ---------------------------------------------------------- system prompt


def test_load_system_prompt_it_non_vuoto_e_contiene_cite() -> None:
    s = load_system_prompt("it")
    assert s
    assert "cite" in s.lower()
    assert "italiano" in s.lower()


def test_load_system_prompt_cached() -> None:
    # cache_clear è disponibile su funzioni decorate con lru_cache
    _ls.cache_clear()
    first = _ls("it")
    info1 = _ls.cache_info()
    second = _ls("it")
    info2 = _ls.cache_info()
    assert first is second  # stessa istanza per la cache hit
    assert info2.hits == info1.hits + 1


def test_load_system_prompt_lang_inesistente_raises() -> None:
    with pytest.raises(FileNotFoundError, match="system_prompt"):
        load_system_prompt("xx")


# ---------------------------------------------------------- user prompt


def test_build_user_prompt_three_chunks_format() -> None:
    rr = RetrievalResult([
        _hit("a/art_1", ["Capo I", "art. 1"], "Testo articolo 1.", rank=1),
        _hit("b/art_2", ["Capo II", "art. 2"], "Testo articolo 2.", rank=2),
        _hit("c/art_3", ["Allegato", "punto 3"], "Testo punto 3.", rank=3),
    ])
    out = build_user_prompt("Cos'è la DPIA?", rr)

    assert "Domanda: Cos'è la DPIA?" in out
    assert "Contesto normativo (3 riferimenti):" in out
    for cid in ("a/art_1", "b/art_2", "c/art_3"):
        assert f"[chunk_id: {cid}]" in out
    assert "Capo I > art. 1" in out
    assert "---" in out
    assert "===" in out
    assert "[cite:CHUNK_ID]" in out


def test_build_user_prompt_empty_retrieval_does_not_crash() -> None:
    rr = RetrievalResult([])
    out = build_user_prompt("Q vuota", rr)
    assert "Contesto normativo (0 riferimenti):" in out
    assert "(nessun riferimento normativo recuperato)" in out
    # nessuna eccezione, segnaposto presente


def test_build_user_prompt_include_expanded_emette_sezione() -> None:
    rr = RetrievalResult(
        [_hit("a/art_1", ["art. 1"], "T1", rank=1)],
        expanded_chunks=[
            ExpandedChunk(
                chunk_id="b/art_99",
                expanded_from="a/art_1",
                relation="rinvia_a",
                note="rinvio formale",
                source_rank=1,
            ),
        ],
    )
    out = build_user_prompt("Q", rr, include_expanded=True)
    assert "Riferimenti correlati (graph espansione)" in out
    assert "b/art_99" in out
    assert "rinvia_a" in out
    assert "rinvio formale" in out


def test_build_user_prompt_include_expanded_false_omette_sezione() -> None:
    rr = RetrievalResult(
        [_hit("a/art_1", ["art. 1"], "T1", rank=1)],
        expanded_chunks=[
            ExpandedChunk(
                chunk_id="b/art_99",
                expanded_from="a/art_1",
                relation="rinvia_a",
                note="rinvio",
                source_rank=1,
            ),
        ],
    )
    out = build_user_prompt("Q", rr, include_expanded=False)
    assert "Riferimenti correlati" not in out
    assert "b/art_99" not in out


def test_build_user_prompt_include_expanded_true_ma_lista_vuota_omette_header() -> None:
    rr = RetrievalResult(
        [_hit("a/art_1", ["art. 1"], "T1", rank=1)],
        expanded_chunks=[],
    )
    out = build_user_prompt("Q", rr, include_expanded=True)
    assert "Riferimenti correlati" not in out


def test_build_user_prompt_caratteri_speciali_italiani() -> None:
    rr = RetrievalResult([
        _hit(
            "x/art_2-bis",
            ["Capo III - Disposizioni d'attuazione"],
            "Il trattamento dev'essere proporzionato all'obiettivo perseguito.",
            rank=1,
        ),
    ])
    out = build_user_prompt("Dell'attuazione, cosa cambia?", rr)
    assert "x/art_2-bis" in out
    assert "dev'essere" in out
    assert "Dell'attuazione" in out
