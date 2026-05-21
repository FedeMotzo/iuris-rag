"""Unit test per `core/llm_provider`.

Niente chiamate API reali (no costi, no flakiness). Mock dell'SDK
Anthropic per AnthropicProvider, mock di `httpx.stream` / `httpx.get`
per OllamaProvider.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import httpx
import pytest

from core.llm_provider import (
    AnthropicProvider,
    GenerationChunk,
    GenerationResult,
    LLMProvider,
    LLMProviderError,
    OllamaProvider,
)
from core.llm_provider.config import load_provider_from_env


# ============================================================ AnthropicProvider


class _FakeAnthropicUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeAnthropicFinalMessage:
    def __init__(self, stop_reason: str, input_tokens: int, output_tokens: int) -> None:
        self.stop_reason = stop_reason
        self.usage = _FakeAnthropicUsage(input_tokens, output_tokens)


class _FakeAnthropicStream:
    """Context manager che simula `client.messages.stream(...)`."""

    def __init__(
        self,
        deltas: list[str],
        stop_reason: str = "end_turn",
        input_tokens: int = 100,
        output_tokens: int = 30,
    ) -> None:
        self._deltas = deltas
        self._stop_reason = stop_reason
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    @property
    def text_stream(self):
        yield from self._deltas

    def get_final_message(self) -> _FakeAnthropicFinalMessage:
        return _FakeAnthropicFinalMessage(
            self._stop_reason, self._input_tokens, self._output_tokens,
        )


@contextmanager
def _patched_anthropic_client(fake_stream: _FakeAnthropicStream | Exception):
    """Patcha l'attributo `_client.messages.stream` di un AnthropicProvider già istanziato."""
    yield fake_stream


def _make_anthropic_provider(stream_or_exc) -> AnthropicProvider:
    """Crea provider con client mockato. `stream_or_exc` può essere uno stream finto
    o un'eccezione da sollevare alla chiamata."""
    p = AnthropicProvider(api_key="sk-test")
    mock_client = MagicMock()
    if isinstance(stream_or_exc, Exception):
        mock_client.messages.stream.side_effect = stream_or_exc
    else:
        mock_client.messages.stream.return_value = stream_or_exc
    p._client = mock_client
    return p


def test_anthropic_generate_stream_yields_chunks_then_final() -> None:
    deltas = ["Ciao ", "mondo", "."]
    p = _make_anthropic_provider(_FakeAnthropicStream(deltas))

    chunks = list(p.generate_stream(prompt="ignored"))

    assert [c.text for c in chunks] == ["Ciao ", "mondo", ".", ""]
    assert [c.is_final for c in chunks] == [False, False, False, True]


def test_anthropic_generate_returns_full_result() -> None:
    deltas = ["Risposta ", "lunga."]
    p = _make_anthropic_provider(
        _FakeAnthropicStream(deltas, input_tokens=42, output_tokens=7)
    )

    r = p.generate(prompt="ignored", max_tokens=100)

    assert isinstance(r, GenerationResult)
    assert r.text == "Risposta lunga."
    assert r.n_input_tokens == 42
    assert r.n_output_tokens == 7
    assert r.ttft_ms >= 0
    assert r.total_ms >= r.ttft_ms
    assert r.provider == "anthropic"
    assert r.model == AnthropicProvider.DEFAULT_MODEL
    assert r.finish_reason == "stop"


def test_anthropic_finish_reason_mapping() -> None:
    p = _make_anthropic_provider(
        _FakeAnthropicStream(["x"], stop_reason="max_tokens")
    )
    r = p.generate(prompt="ignored")
    assert r.finish_reason == "length"

    p2 = _make_anthropic_provider(
        _FakeAnthropicStream(["x"], stop_reason="stop_sequence")
    )
    r2 = p2.generate(prompt="ignored")
    assert r2.finish_reason == "stop"

    p3 = _make_anthropic_provider(
        _FakeAnthropicStream(["x"], stop_reason="unknown_reason")
    )
    r3 = p3.generate(prompt="ignored")
    assert r3.finish_reason == "other"


def test_anthropic_api_error_becomes_provider_error() -> None:
    import anthropic as _anthropic

    fake_response = MagicMock()
    fake_request = MagicMock()
    err = _anthropic.APIError(
        message="boom", request=fake_request, body=None,
    )
    p = _make_anthropic_provider(err)

    with pytest.raises(LLMProviderError, match="Anthropic API error"):
        list(p.generate_stream(prompt="x"))


def test_anthropic_missing_api_key_at_init_raises() -> None:
    with pytest.raises(LLMProviderError, match="api_key"):
        AnthropicProvider(api_key="")


def test_anthropic_last_meta_before_stream_raises() -> None:
    p = AnthropicProvider(api_key="sk-test")
    with pytest.raises(LLMProviderError):
        p._last_stream_meta()


# =============================================================== OllamaProvider


class _FakeStreamResponse:
    """Mocka l'oggetto ritornato da `httpx.stream(...)` come context manager."""

    def __init__(self, jsonl_lines: list[str], status_code: int = 200) -> None:
        self._lines = jsonl_lines
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err",
                request=MagicMock(),
                response=MagicMock(status_code=self.status_code, text="error"),
            )

    def iter_lines(self):
        yield from self._lines


def _fake_tags_response(model_names: list[str]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"models": [{"name": n} for n in model_names]}
    return resp


def test_ollama_init_verifies_model_exists() -> None:
    with patch("httpx.get", return_value=_fake_tags_response(["qwen2.5:14b"])):
        p = OllamaProvider(model="qwen2.5:14b")
    assert p.provider_name == "ollama"
    assert p.model_name == "qwen2.5:14b"


def test_ollama_init_missing_model_raises_actionable() -> None:
    with patch("httpx.get", return_value=_fake_tags_response(["llama3:latest"])):
        with pytest.raises(LLMProviderError, match="ollama pull"):
            OllamaProvider(model="qwen2.5:14b")


def test_ollama_init_connect_refused_raises() -> None:
    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(LLMProviderError, match="non raggiungibile"):
            OllamaProvider(model="qwen2.5:14b")


def _make_ollama_provider(num_ctx: int = 8192) -> OllamaProvider:
    with patch("httpx.get", return_value=_fake_tags_response(["qwen2.5:14b"])):
        return OllamaProvider(model="qwen2.5:14b", num_ctx=num_ctx)


def test_ollama_generate_stream_parses_jsonl() -> None:
    p = _make_ollama_provider()
    lines = [
        json.dumps({"response": "ciao "}),
        json.dumps({"response": "mondo"}),
        json.dumps({
            "response": "",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 50,
            "eval_count": 12,
        }),
    ]
    with patch("httpx.stream", return_value=_FakeStreamResponse(lines)):
        chunks = list(p.generate_stream(prompt="x"))

    assert [c.text for c in chunks] == ["ciao ", "mondo", ""]
    assert chunks[-1].is_final is True
    assert chunks[0].is_final is False


def test_ollama_generate_aggregates_token_counts() -> None:
    p = _make_ollama_provider()
    lines = [
        json.dumps({"response": "a"}),
        json.dumps({"response": "b"}),
        json.dumps({
            "response": "",
            "done": True,
            "done_reason": "length",
            "prompt_eval_count": 33,
            "eval_count": 21,
        }),
    ]
    with patch("httpx.stream", return_value=_FakeStreamResponse(lines)):
        r = p.generate(prompt="x")

    assert r.text == "ab"
    assert r.n_input_tokens == 33
    assert r.n_output_tokens == 21
    assert r.finish_reason == "length"
    assert r.provider == "ollama"


def test_ollama_passes_num_ctx_in_options() -> None:
    p = _make_ollama_provider(num_ctx=4096)
    captured: dict = {}

    def fake_stream(method, url, json=None, timeout=None):
        captured["json"] = json
        return _FakeStreamResponse([
            f'{{"response": "", "done": true, "done_reason": "stop", '
            f'"prompt_eval_count": 0, "eval_count": 0}}'
        ])

    with patch("httpx.stream", side_effect=fake_stream):
        list(p.generate_stream(prompt="x", max_tokens=200, temperature=0.5))

    options = captured["json"]["options"]
    assert options["num_ctx"] == 4096
    assert options["num_predict"] == 200
    assert options["temperature"] == 0.5


def test_ollama_connect_error_during_stream_raises() -> None:
    p = _make_ollama_provider()
    with patch("httpx.stream", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(LLMProviderError, match="non raggiungibile"):
            list(p.generate_stream(prompt="x"))


# ================================================================== load_provider_from_env


@pytest.fixture
def clean_env(monkeypatch):
    for k in (
        "LLM_PROVIDER",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_NUM_CTX",
    ):
        monkeypatch.delenv(k, raising=False)


def test_config_anthropic_without_key_raises(clean_env, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    with pytest.raises(LLMProviderError, match="ANTHROPIC_API_KEY"):
        load_provider_from_env(env_path=tmp_path / "nonexistent.env")


def test_config_invalid_provider_raises(clean_env, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(LLMProviderError, match="LLM_PROVIDER non valido"):
        load_provider_from_env(env_path=tmp_path / "nonexistent.env")


def test_config_ollama_defaults(clean_env, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    # OllamaProvider verifica modello in init: mocchiamo httpx.get
    with patch("httpx.get", return_value=_fake_tags_response(["qwen2.5:14b"])):
        p = load_provider_from_env(env_path=tmp_path / "nonexistent.env")
    assert isinstance(p, OllamaProvider)
    assert p.model_name == "qwen2.5:14b"


def test_config_ollama_invalid_num_ctx_raises(clean_env, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "non-un-intero")
    with pytest.raises(LLMProviderError, match="OLLAMA_NUM_CTX"):
        load_provider_from_env(env_path=tmp_path / "nonexistent.env")


def test_config_default_is_anthropic(clean_env, tmp_path, monkeypatch) -> None:
    # LLM_PROVIDER non settato → default anthropic → senza key → errore chiaro
    with pytest.raises(LLMProviderError, match="ANTHROPIC_API_KEY"):
        load_provider_from_env(env_path=tmp_path / "nonexistent.env")


def test_provider_implements_interface() -> None:
    assert issubclass(AnthropicProvider, LLMProvider)
    assert issubclass(OllamaProvider, LLMProvider)


def test_generation_chunk_immutable() -> None:
    c = GenerationChunk(text="x", is_final=False)
    with pytest.raises(Exception):
        c.text = "y"  # type: ignore[misc]
