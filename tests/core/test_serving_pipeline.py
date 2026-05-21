"""Test per `core/serving/pipeline.py` e `core/serving/config.py`.

Mock di HybridRetriever e LLMProvider — nessuna chiamata API reale.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.hybrid_retriever.types import RetrievalHit, RetrievalResult
from core.llm_provider import (
    GenerationChunk,
    GenerationResult,
    LLMProvider,
)
from core.normative_graph.models import ExpandedChunk, GraphLink
from core.serving import RAGPipeline, RAGResponse, build_default_pipeline


# ---------------------------------------------------------- helpers / mock


def _hit(chunk_id: str, text: str = "T", rank: int = 1) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id,
        score=1.0,
        payload={"hierarchy_path": ["h"], "text": text, "chunk_id": chunk_id},
        rank=rank,
    )


def _make_retriever(hits: list[RetrievalHit], expanded: list[ExpandedChunk] | None = None):
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(hits, expanded_chunks=expanded)
    return retriever


class _FakeLLM(LLMProvider):
    """LLMProvider mockato: ritorna testo fisso + meta fissi."""

    def __init__(
        self,
        text: str = "Risposta [cite:a/art_1].",
        n_input: int = 100,
        n_output: int = 10,
        finish_reason: str = "stop",
        provider: str = "fake",
        model: str = "fake-1",
    ) -> None:
        self._text = text
        self._n_input = n_input
        self._n_output = n_output
        self._finish_reason = finish_reason
        self._provider = provider
        self._model = model
        # stato post-stream popolato dopo generate_stream
        self._meta: dict | None = None

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def generate_stream(self, prompt, system=None, max_tokens=500, temperature=0.0):
        # Split del testo in 3 delta arbitrari per testare streaming
        deltas = [self._text[:5], self._text[5:15], self._text[15:]]
        for d in deltas:
            if d:
                yield GenerationChunk(text=d, is_final=False)
        self._meta = {
            "n_input_tokens": self._n_input,
            "n_output_tokens": self._n_output,
            "finish_reason": self._finish_reason,
        }
        yield GenerationChunk(text="", is_final=True)

    def _last_stream_meta(self) -> dict:
        if self._meta is None:
            raise RuntimeError("stream non ancora completato")
        return self._meta


# ---------------------------------------------------------- query() non-streaming


def test_query_returns_full_rag_response() -> None:
    retriever = _make_retriever([_hit("a/art_1"), _hit("b/art_2", rank=2)])
    llm = _FakeLLM(text="Vedi [cite:a/art_1] e [cite:b/art_2].")
    pipe = RAGPipeline(retriever=retriever, llm_provider=llm)

    r = pipe.query("Q?")

    assert isinstance(r, RAGResponse)
    assert r.answer.startswith("Vedi [cite:a/art_1]")
    assert r.annotated_answer == r.answer  # entrambi verificati, no annotation
    assert r.verification.all_verified is True
    assert r.verification.n_total == 2
    assert r.generation_meta.provider == "fake"


def test_query_timings_populated_and_positive() -> None:
    retriever = _make_retriever([_hit("a/art_1")])
    llm = _FakeLLM()
    pipe = RAGPipeline(retriever=retriever, llm_provider=llm)

    r = pipe.query("Q?")

    for key in ("retrieval_ms", "generate_ms", "verify_ms", "total_ms"):
        assert key in r.timings_ms
        assert r.timings_ms[key] >= 0
    assert r.timings_ms["total_ms"] >= r.timings_ms["retrieval_ms"]


def test_query_unverified_citation_marks_annotated() -> None:
    retriever = _make_retriever([_hit("a/art_1")])
    llm = _FakeLLM(text="Vedi [cite:fantasia/art_99].")
    pipe = RAGPipeline(retriever=retriever, llm_provider=llm)

    r = pipe.query("Q?")

    assert r.verification.all_verified is False
    assert "NON VERIFICATA" in r.annotated_answer
    assert r.verification.n_unverified == 1


# ---------------------------------------------------------- use_graph


def test_use_graph_true_passes_include_expanded_to_builder() -> None:
    retriever = _make_retriever(
        [_hit("a/art_1")],
        expanded=[
            ExpandedChunk(
                chunk_id="b/art_99",
                expanded_from="a/art_1",
                relation="rinvia_a",
                note="x",
                source_rank=1,
            ),
        ],
    )
    llm = _FakeLLM(text="Pertinente [cite:b/art_99].")
    graph_link = GraphLink.model_validate(
        {"from": "a/art_1", "to": "b/art_99", "relation": "rinvia_a", "note": "x"}
    )
    pipe = RAGPipeline(
        retriever=retriever,
        llm_provider=llm,
        use_graph=True,
        graph_links=[graph_link],
    )

    with patch("core.serving.pipeline.build_user_prompt", wraps=__import__(
        "core.rag_prompt", fromlist=["build_user_prompt"]
    ).build_user_prompt) as spy:
        r = pipe.query("Q?")

    assert spy.called
    _, kwargs = spy.call_args
    assert kwargs["include_expanded"] is True
    # citation a expanded chunk è considerata valida (incluso in retrieval_context)
    assert r.verification.all_verified is True


def test_use_graph_false_passes_include_expanded_false() -> None:
    retriever = _make_retriever([_hit("a/art_1")])
    llm = _FakeLLM()
    pipe = RAGPipeline(retriever=retriever, llm_provider=llm, use_graph=False)

    with patch("core.serving.pipeline.build_user_prompt", wraps=__import__(
        "core.rag_prompt", fromlist=["build_user_prompt"]
    ).build_user_prompt) as spy:
        pipe.query("Q?")

    _, kwargs = spy.call_args
    assert kwargs["include_expanded"] is False


def test_use_graph_true_without_links_raises() -> None:
    retriever = _make_retriever([_hit("a/art_1")])
    llm = _FakeLLM()
    with pytest.raises(ValueError, match="graph_links"):
        RAGPipeline(retriever=retriever, llm_provider=llm, use_graph=True)


# ---------------------------------------------------------- query_stream


def test_query_stream_yields_chunks_then_final() -> None:
    retriever = _make_retriever([_hit("a/art_1"), _hit("b/art_2", rank=2)])
    llm = _FakeLLM(text="Vedi [cite:a/art_1] e [cite:b/art_2].")
    pipe = RAGPipeline(retriever=retriever, llm_provider=llm)

    events = list(pipe.query_stream("Q?"))
    kinds = [k for k, _ in events]
    assert kinds[-1] == "final"
    assert kinds[:-1].count("chunk") >= 2
    assert kinds[:-1].count("final") == 0


def test_query_stream_final_has_annotated_answer() -> None:
    retriever = _make_retriever([_hit("a/art_1")])
    llm = _FakeLLM(text="Vedi [cite:inesistente].")
    pipe = RAGPipeline(retriever=retriever, llm_provider=llm)

    events = list(pipe.query_stream("Q?"))
    kind, payload = events[-1]
    assert kind == "final"
    assert isinstance(payload, RAGResponse)
    assert "NON VERIFICATA" in payload.annotated_answer
    assert payload.generation_meta.n_output_tokens == 10


# ---------------------------------------------------------- build_default_pipeline


@pytest.fixture
def clean_env(monkeypatch):
    for k in (
        "LLM_PROVIDER",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_NUM_CTX",
        "RAG_TOP_K",
        "RAG_RERANK_TOP_K",
        "RAG_USE_GRAPH",
        "RAG_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(k, raising=False)


def test_build_default_pipeline_anthropic(clean_env, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    retriever = _make_retriever([_hit("a/art_1")])

    # patch load_provider_from_env scoperto in config.py per non aprire un
    # client Anthropic reale
    with patch(
        "core.serving.config.load_provider_from_env",
        return_value=_FakeLLM(provider="anthropic"),
    ):
        pipe = build_default_pipeline(retriever)

    assert isinstance(pipe, RAGPipeline)
    assert pipe.use_graph is False
    assert pipe._top_k == 5
    assert pipe._rerank_top_k == 20


def test_build_default_pipeline_use_graph_true(clean_env, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("RAG_USE_GRAPH", "true")
    monkeypatch.setenv("RAG_TOP_K", "3")
    retriever = _make_retriever([_hit("a/art_1")])

    with patch(
        "core.serving.config.load_provider_from_env",
        return_value=_FakeLLM(provider="anthropic"),
    ):
        pipe = build_default_pipeline(retriever)

    assert pipe.use_graph is True
    assert pipe._top_k == 3
    assert pipe._graph_links is not None and len(pipe._graph_links) > 0
