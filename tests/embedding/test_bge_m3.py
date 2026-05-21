"""Tests for `BgeM3Encoder`. Caricano il modello vero — il primo test è lento."""

from __future__ import annotations

import math

import pytest

from core.embedding.bge_m3 import BgeM3Encoder


@pytest.fixture(scope="module")
def encoder() -> BgeM3Encoder:
    """Module-scoped encoder: paga il caricamento del modello una volta sola."""
    return BgeM3Encoder()


def test_lazy_loading():
    enc = BgeM3Encoder()
    assert enc._model is None, "model should not be loaded before first encode() call"


def test_encode_shape_and_normalization(encoder):
    vectors = encoder.encode(["frase di prova in italiano"])
    assert len(vectors) == 1
    vec = vectors[0]
    assert len(vec) == BgeM3Encoder.VECTOR_SIZE == 1024
    norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(norm, 1.0, abs_tol=1e-3), f"vector not normalized: |v|={norm}"


def test_prefix_is_applied(encoder):
    """`encode([t])` deve coincidere con encoding manuale di `prefix + t`."""
    raw_text = "definizione di dato personale"
    via_encoder = encoder.encode([raw_text])[0]

    # Encoding manuale equivalente: bypassa il prefix interno e applicalo a mano.
    model = encoder._ensure_loaded()
    prefixed = encoder.INSTRUCTION_PREFIX + raw_text
    manual = model.encode(
        [prefixed], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )[0].tolist()

    assert len(via_encoder) == len(manual)
    cos = sum(a * b for a, b in zip(via_encoder, manual, strict=True))
    assert cos > 0.9999, f"prefix not applied as expected: cos={cos}"
