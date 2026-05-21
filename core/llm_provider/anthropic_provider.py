"""Provider Anthropic — default cloud W5 (Claude Sonnet 4.6).

Usa l'SDK ufficiale `anthropic` con `messages.stream()`. Mappa
`stop_reason` Anthropic in `finish_reason` neutrale del nostro
`GenerationResult`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

from .base import GenerationChunk, LLMProvider, LLMProviderError

if TYPE_CHECKING:
    import anthropic

logger = logging.getLogger(__name__)

_STOP_REASON_MAP = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_use": "stop",
    "pause_turn": "stop",
}


class AnthropicProvider(LLMProvider):
    """Wrapper sopra Claude via SDK ufficiale Anthropic.

    Streaming first-class: `messages.stream()` con `text_stream` per i
    delta + `get_final_message()` per usage + stop_reason.
    """

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        max_retries: int = 2,
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise LLMProviderError(
                "AnthropicProvider richiede api_key non vuota. "
                "Imposta ANTHROPIC_API_KEY nel file .env (vedi .env.example)."
            )
        import anthropic as _anthropic

        self._anthropic = _anthropic
        self._client = _anthropic.Anthropic(
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout_s,
        )
        self._model = model
        self._last_meta: dict | None = None
        logger.info("AnthropicProvider init model=%s timeout=%.0fs", model, timeout_s)

    # ----------------------------------------------------- public API

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.0,
    ) -> Iterator[GenerationChunk]:
        self._last_meta = None
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            kwargs["system"] = system

        logger.debug("anthropic stream model=%s max_tokens=%d", self._model, max_tokens)

        try:
            with self._client.messages.stream(**kwargs) as stream:
                last_text = ""
                for delta in stream.text_stream:
                    if not delta:
                        continue
                    yield GenerationChunk(text=delta, is_final=False)
                    last_text = delta

                final = stream.get_final_message()
                stop_reason = getattr(final, "stop_reason", None) or "end_turn"
                usage = getattr(final, "usage", None)
                self._last_meta = {
                    "n_input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                    "n_output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                    "finish_reason": _STOP_REASON_MAP.get(stop_reason, "other"),
                }
                # Marker finale: emette un chunk vuoto con is_final=True per
                # segnalare la chiusura dello stream a consumer che vogliano
                # distinguere "fine messaggio" da "fine iteratore".
                yield GenerationChunk(text="", is_final=True)
                _ = last_text  # silenzia warning unused
        except self._anthropic.APITimeoutError as exc:
            raise LLMProviderError(
                f"Anthropic API timeout dopo {self._client.timeout}s: {exc}"
            ) from exc
        except self._anthropic.RateLimitError as exc:
            raise LLMProviderError(
                "Anthropic API rate limit raggiunto. "
                "Riprova fra qualche secondo o riduci il throughput."
            ) from exc
        except self._anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API error: {exc}") from exc

    def _last_stream_meta(self) -> dict:
        if self._last_meta is None:
            raise LLMProviderError(
                "AnthropicProvider._last_stream_meta chiamato prima del termine di uno stream"
            )
        return self._last_meta
