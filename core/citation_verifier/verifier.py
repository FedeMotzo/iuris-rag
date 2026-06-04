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

from core.citation_marker import CITE_PATTERN
from .models import CitationMarker, VerificationResult


def _split_cite_tokens(content: str) -> list[str]:
    """Spezza il contenuto di un bracket in token-cite.

    Additivo: splitta su ';' e ',' e strippa un eventuale prefisso "cite:"
    ripetuto → gestisce `[cite:A, cite:B]`, `[cite:A; cite:B]` e le code
    descrittive `[cite:A, paragrafo 1]` (il secondo token resta separato).
    """
    tokens: list[str] = []
    for raw in re.split(r"[;,]", content):
        t = raw.strip()
        if t.lower().startswith("cite:"):
            t = t[len("cite:"):].strip()
        if t:
            tokens.append(t)
    return tokens


def _token_verified(token: str, context_set: set[str]) -> bool:
    """True se un chunk_id noto è PREFISSO del token al confine.

    Tollera la coda descrittiva (es. "ID, paragrafo 1", "ID par. 2") ma solo
    verso id realmente recuperati, e il carattere dopo il prefisso deve essere
    un separatore → niente falsi positivi tipo art_3 vs art_35.
    """
    for known in context_set:
        if token == known:
            return True
        if token.startswith(known) and token[len(known):len(known) + 1] in " ,;":
            return True
    return False


def _classify_bracket(content: str, context_set: set[str]) -> bool:
    """True se il bracket è verificato: nessun token-cite compatto resta
    irrisolto. Un token con spazio interno non risolto è trattato come coda
    descrittiva (ignorato); un token compatto non risolto (es. id abbreviato
    "art_7") conta come unverified → bracket non verificato."""
    has_unverified = False
    for tok in _split_cite_tokens(content):
        if _token_verified(tok, context_set):
            continue
        if " " not in tok:
            has_unverified = True
    return not has_unverified


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
        verified = _classify_bracket(chunk_id, context_set)
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
