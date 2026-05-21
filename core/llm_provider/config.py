"""Caricamento configurazione LLM provider da `.env` in repo root.

Env vars riconosciute (vedi `.env.example`):

- `LLM_PROVIDER`: "anthropic" | "ollama"  (default: "anthropic")
- `ANTHROPIC_API_KEY`: required se provider = anthropic
- `ANTHROPIC_MODEL`: default "claude-sonnet-4-6"
- `OLLAMA_BASE_URL`: default "http://localhost:11434"
- `OLLAMA_MODEL`: default "qwen2.5:14b"
- `OLLAMA_NUM_CTX`: default 8192
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider, LLMProviderError
from .ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = {"anthropic", "ollama"}


def _repo_root() -> Path:
    # core/llm_provider/config.py → repo_root è 2 parents sopra
    return Path(__file__).resolve().parents[2]


def load_provider_from_env(env_path: Path | None = None) -> LLMProvider:
    """Carica `.env` e istanzia il provider configurato.

    `env_path` opzionale per i test; in produzione il `.env` è cercato
    in repo root (un livello sopra `core/`).
    """
    if env_path is None:
        env_path = _repo_root() / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        logger.info("Caricato env da %s", env_path)
    else:
        logger.info("Nessun .env trovato in %s — uso solo variabili di ambiente", env_path)

    provider_name = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider_name not in _VALID_PROVIDERS:
        raise LLMProviderError(
            f"LLM_PROVIDER non valido: {provider_name!r}. "
            f"Valori ammessi: {sorted(_VALID_PROVIDERS)}."
        )

    if provider_name == "anthropic":
        return _build_anthropic()
    return _build_ollama()


def _build_anthropic() -> AnthropicProvider:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise LLMProviderError(
            "LLM_PROVIDER=anthropic ma ANTHROPIC_API_KEY non impostata. "
            "Aggiungi la chiave in .env (copia .env.example) "
            "oppure esporta la variabile d'ambiente. "
            "Chiave ottenibile da https://console.anthropic.com/."
        )
    model = (os.environ.get("ANTHROPIC_MODEL") or AnthropicProvider.DEFAULT_MODEL).strip()
    return AnthropicProvider(api_key=api_key, model=model)


def _build_ollama() -> OllamaProvider:
    base_url = (os.environ.get("OLLAMA_BASE_URL") or OllamaProvider.DEFAULT_BASE_URL).strip()
    model = (os.environ.get("OLLAMA_MODEL") or OllamaProvider.DEFAULT_MODEL).strip()
    num_ctx_raw = os.environ.get("OLLAMA_NUM_CTX")
    if num_ctx_raw:
        try:
            num_ctx = int(num_ctx_raw)
        except ValueError as exc:
            raise LLMProviderError(
                f"OLLAMA_NUM_CTX non è un intero valido: {num_ctx_raw!r}"
            ) from exc
    else:
        num_ctx = OllamaProvider.DEFAULT_NUM_CTX
    return OllamaProvider(model=model, base_url=base_url, num_ctx=num_ctx)
