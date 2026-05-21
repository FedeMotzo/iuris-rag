"""Interfaccia astratta `LLMProvider` + tipi di ritorno comuni.

Due implementazioni concrete in v1: `AnthropicProvider` (default cloud,
Claude Sonnet 4.6) e `OllamaProvider` (fallback locale, Qwen2.5-14B
Q4_K_M). Il modulo non sa nulla di reranker o MPS — la topologia
serving condizionale al provider vive nel pipeline serving (decisioni
W5 2026-05-19, voci 20-23 di PROJECT_CONTEXT.md).

Niente async in v1. Iterator sincrono. Async è W6+ se serve per
FastAPI streaming.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """Errore non recuperabile sollevato da un `LLMProvider`.

    Include: API key mancante/invalida, modello locale non installato,
    connessione rifiutata, rate limit definitivo, timeout, errore API.
    Il messaggio è inteso per essere mostrato direttamente all'utente
    (actionable, con istruzioni di rimedio dove applicabile).
    """


@dataclass(frozen=True)
class GenerationChunk:
    """Singolo delta dello stream di generazione."""

    text: str
    is_final: bool


@dataclass(frozen=True)
class GenerationResult:
    """Risultato completo di una generazione non-streaming."""

    text: str
    n_input_tokens: int
    n_output_tokens: int
    ttft_ms: float
    total_ms: float
    finish_reason: str  # "stop" | "length" | "error" | "other"
    provider: str
    model: str


class LLMProvider(ABC):
    """Provider LLM con generazione streaming + collect non-streaming."""

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.0,
    ) -> Iterator[GenerationChunk]:
        """Streaming generation. Yield un `GenerationChunk` per delta.

        L'ultimo chunk dello stream deve avere `is_final=True`. Eventuali
        metadati di chiusura (token counts, finish_reason) vanno memorizzati
        come stato interno del provider per essere riutilizzati da `generate()`.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    # ----------------------------------------------------- default helpers

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.0,
    ) -> GenerationResult:
        """Non-streaming: consuma `generate_stream` e ritorna risultato + metriche.

        TTFT e total_ms sono misurati qui con `time.perf_counter()`. Token
        counts e finish_reason sono attesi nello stato del provider dopo
        che lo stream è esaurito (popolati dalle implementazioni concrete
        in `_finalize_stream_state` o equivalente).
        """
        t0 = time.perf_counter()
        t_first: float | None = None
        chunks: list[str] = []
        for ch in self.generate_stream(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            if ch.text and t_first is None:
                t_first = time.perf_counter()
            chunks.append(ch.text)
        t_end = time.perf_counter()
        if t_first is None:
            t_first = t_end

        meta = self._last_stream_meta()
        return GenerationResult(
            text="".join(chunks),
            n_input_tokens=meta["n_input_tokens"],
            n_output_tokens=meta["n_output_tokens"],
            ttft_ms=(t_first - t0) * 1000.0,
            total_ms=(t_end - t0) * 1000.0,
            finish_reason=meta["finish_reason"],
            provider=self.provider_name,
            model=self.model_name,
        )

    @abstractmethod
    def _last_stream_meta(self) -> dict:
        """Ritorna i metadati dell'ultimo stream completato.

        Atteso: `{"n_input_tokens": int, "n_output_tokens": int,
        "finish_reason": str}`. Sollevare `LLMProviderError` se chiamato
        prima che uno stream sia stato consumato completamente.
        """
