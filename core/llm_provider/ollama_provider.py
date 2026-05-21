"""Provider Ollama — fallback locale W5 (Qwen2.5-14B Q4_K_M).

`num_ctx=8192` di default per evitare la patologia di KV cache invalida
osservata nello smoke MPS (`spike/MPS_COABITATION_RESULTS.md`, raccomandazione
2026-05-19). Streaming via `/api/generate` JSON-lines.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import httpx

from .base import GenerationChunk, LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

_OLLAMA_DONE_REASON_MAP = {
    "stop": "stop",
    "length": "length",
}


class OllamaProvider(LLMProvider):
    """Wrapper HTTP sopra Ollama `/api/generate` in streaming."""

    DEFAULT_MODEL = "qwen2.5:14b"
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_NUM_CTX = 8192

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        num_ctx: int = DEFAULT_NUM_CTX,
        timeout_s: float = 120.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._num_ctx = num_ctx
        self._timeout = httpx.Timeout(
            connect=10.0, read=timeout_s, write=10.0, pool=10.0,
        )
        self._last_meta: dict | None = None
        logger.info(
            "OllamaProvider init model=%s base_url=%s num_ctx=%d timeout=%.0fs",
            model, self._base_url, num_ctx, timeout_s,
        )
        self._verify_model_available()

    # ----------------------------------------------------- public API

    @property
    def provider_name(self) -> str:
        return "ollama"

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
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self._num_ctx,
            },
        }
        if system is not None:
            payload["system"] = system

        logger.debug(
            "ollama stream model=%s num_ctx=%d num_predict=%d",
            self._model, self._num_ctx, max_tokens,
        )

        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            ) as r:
                r.raise_for_status()
                for raw in r.iter_lines():
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("Ollama line non JSON, ignorata: %r", raw[:120])
                        continue
                    delta = obj.get("response", "") or ""
                    done = bool(obj.get("done"))
                    if delta:
                        yield GenerationChunk(text=delta, is_final=False)
                    if done:
                        done_reason = obj.get("done_reason") or "stop"
                        self._last_meta = {
                            "n_input_tokens": int(obj.get("prompt_eval_count", 0) or 0),
                            "n_output_tokens": int(obj.get("eval_count", 0) or 0),
                            "finish_reason": _OLLAMA_DONE_REASON_MAP.get(
                                done_reason, "other"
                            ),
                        }
                        yield GenerationChunk(text="", is_final=True)
                        return
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Ollama non raggiungibile su {self._base_url}. "
                f"Verifica che il daemon sia attivo (`ollama serve` o "
                f"app desktop). Dettaglio: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                f"Ollama timeout dopo {self._timeout.read}s su {self._base_url}. "
                f"Considera di aumentare timeout_s o ridurre max_tokens. "
                f"Dettaglio: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                f"Ollama HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc

    def _last_stream_meta(self) -> dict:
        if self._last_meta is None:
            raise LLMProviderError(
                "OllamaProvider._last_stream_meta chiamato prima del termine di uno stream"
            )
        return self._last_meta

    # ----------------------------------------------------- internal

    def _verify_model_available(self) -> None:
        """Controlla che il modello sia installato su Ollama via `/api/tags`."""
        try:
            r = httpx.get(f"{self._base_url}/api/tags", timeout=10.0)
            r.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Ollama non raggiungibile su {self._base_url}. "
                f"Verifica che il daemon sia attivo (`ollama serve` o "
                f"app desktop). Dettaglio: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Errore interrogando {self._base_url}/api/tags: {exc}"
            ) from exc

        names = {m.get("name") for m in r.json().get("models", [])}
        if self._model not in names:
            raise LLMProviderError(
                f"Modello {self._model} non trovato in Ollama. "
                f"Esegui: `ollama pull {self._model}`. "
                f"Modelli installati: {sorted(n for n in names if n)}"
            )
