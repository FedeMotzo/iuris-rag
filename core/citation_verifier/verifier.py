"""Verifica strutturale delle citazioni `[cite:CHUNK_ID]` nell'output LLM.

Politica v1: soft warning — le citazioni con chunk_id non presente nel contesto
retrieval vengono marcate inline come `[cite:X NON VERIFICATA]`, MAI rimosse.
Hard block / hard fail sono fuori scope v1.

Nessun LLM, nessun embedding, nessuna normalizzazione del riferimento normativo.
Solo regex + set membership.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import CitationMarker, VerificationResult

# Marker [cite:CHUNK_ID] — il chunk_id non può contenere whitespace né ']',
# deve essere non vuoto. Case-sensitive (i chunk_id del corpus lo sono).
CITE_PATTERN = re.compile(r"\[cite:([^\]\s]+)\]")


def verify_citations(
    llm_output: str,
    retrieval_context: Iterable[str],
) -> VerificationResult:
    """Verifica che ogni [cite:CHUNK_ID] corrisponda a un chunk_id nel contesto.

    Args:
        llm_output: testo grezzo prodotto dall'LLM.
        retrieval_context: chunk_id usati per il prompt RAG (set o list).

    Returns:
        VerificationResult con markers estratti, annotated_text con eventuali
        soft-warning inline, e contatori aggregati.
    """
    context_set = set(retrieval_context)

    markers: list[CitationMarker] = []
    for m in CITE_PATTERN.finditer(llm_output):
        chunk_id = m.group(1)
        verified = chunk_id in context_set
        markers.append(CitationMarker(
            chunk_id=chunk_id,
            span_start=m.start(),
            span_end=m.end(),
            verified=verified,
            reason="ok" if verified else "unknown_chunk_id",
        ))

    annotated_text = _build_annotated(llm_output, markers)

    n_total = len(markers)
    n_verified = sum(1 for x in markers if x.verified)
    n_unverified = n_total - n_verified

    return VerificationResult(
        original_text=llm_output,
        annotated_text=annotated_text,
        markers=markers,
        n_total=n_total,
        n_verified=n_verified,
        n_unverified=n_unverified,
        all_verified=(n_unverified == 0),
    )


def _build_annotated(text: str, markers: list[CitationMarker]) -> str:
    """Inserisce `NON VERIFICATA` dentro ogni marker unverified preservando
    gli offset originali. Lavora da fine a inizio per evitare slittamenti.
    """
    out = text
    for m in sorted(markers, key=lambda x: x.span_start, reverse=True):
        if m.verified:
            continue
        # Sostituisce [cite:X] con [cite:X NON VERIFICATA]
        original = f"[cite:{m.chunk_id}]"
        replacement = f"[cite:{m.chunk_id} NON VERIFICATA]"
        out = out[:m.span_start] + replacement + out[m.span_end:]
    return out
