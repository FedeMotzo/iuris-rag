"""BAAI/bge-m3 encoder con instruction prefix italiano obbligatorio.

Singleton pattern: la prima istanziazione carica il modello (~6s da cache), le
successive riusano l'istanza in `_singleton`. Device auto-detect su Mac M-series.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class BgeM3Encoder:
    """Encoder bge-m3 con instruction prefix italiano obbligatorio."""

    INSTRUCTION_PREFIX = "Rappresenta questo testo legale italiano per il recupero: "
    MODEL_NAME = "BAAI/bge-m3"
    VECTOR_SIZE = 1024

    _singleton: "BgeM3Encoder | None" = None

    def __init__(self, device: str | None = None) -> None:
        self._device = device or _detect_device()
        self._model: SentenceTransformer | None = None

    @classmethod
    def get(cls, device: str | None = None) -> "BgeM3Encoder":
        if cls._singleton is None:
            cls._singleton = cls(device=device)
        return cls._singleton

    def _ensure_loaded(self) -> "SentenceTransformer":
        if self._model is None:
            logger.info("Loading %s on %s (first call)", self.MODEL_NAME, self._device)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME, device=self._device)
        return self._model

    def encode(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        """Aggiunge il prefix a ciascun testo, encoda, ritorna vettori normalizzati."""
        if not texts:
            return []
        model = self._ensure_loaded()
        prefixed = [self.INSTRUCTION_PREFIX + t for t in texts]
        embeddings = model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self._release_device_cache()
        return embeddings.tolist()

    def _release_device_cache(self) -> None:
        """PyTorch su MPS non rilascia automaticamente i buffer cached fra chiamate:
        per job long-running questo può produrre OOM apparenti. Svuota dopo ogni encode().
        """
        if self._device != "mps":
            return
        try:
            import torch
            torch.mps.empty_cache()
        except (ImportError, AttributeError):
            pass


def _detect_device() -> str:
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"
