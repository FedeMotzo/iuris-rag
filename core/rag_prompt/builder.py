"""Builder del prompt utente RAG.

Lavora su `RetrievalResult` (lista di `RetrievalHit` + `expanded_chunks`
opzionale). Il system prompt vive in `templates.py` / `system_prompt.it.md`.

Niente flessibilità sullo schema dei chunk in v1: i separatori sono
fissati in `templates`. Modifiche al formato comportano nuovo test set
qualitativo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .templates import (
    CHUNK_END_MARKER,
    CHUNK_HEADER_FMT,
    CHUNK_HEADER_TEXT_SEP,
    CHUNK_SEP,
    HIERARCHY_JOIN,
)

if TYPE_CHECKING:
    from core.hybrid_retriever.types import RetrievalHit, RetrievalResult


_EXPANDED_HEADER = "Riferimenti correlati (graph espansione)"


def build_user_prompt(
    query: str,
    retrieval_result: "RetrievalResult",
    include_expanded: bool = False,
) -> str:
    """Costruisce il user prompt: domanda + contesto + istruzioni.

    Struttura:
        Domanda: <query>

        Contesto normativo (N riferimenti):

        <chunk 1>

        <chunk 2>
        ...

        [Riferimenti correlati (graph espansione):
         - [chunk_id]: relation — note
         ...]

        Rispondi alla domanda usando esclusivamente il contesto normativo
        fornito. Cita ogni affermazione con [cite:CHUNK_ID].

    `include_expanded=True` aggiunge la sezione "Riferimenti correlati"
    dopo i chunk principali, popolata da `retrieval_result.expanded_chunks`.
    Se la lista espansa è vuota la sezione non viene emessa anche con il
    flag True.
    """
    hits = list(retrieval_result)
    n = len(hits)

    parts: list[str] = []
    parts.append(f"Domanda: {query.strip()}")
    parts.append("")
    parts.append(f"Contesto normativo ({n} riferimenti):")
    parts.append("")

    if n == 0:
        parts.append("(nessun riferimento normativo recuperato)")
    else:
        chunk_blocks = [_format_chunk(h) for h in hits]
        parts.append(CHUNK_SEP.join(chunk_blocks))

    if include_expanded:
        expanded = getattr(retrieval_result, "expanded_chunks", None) or []
        if expanded:
            parts.append("")
            parts.append(f"{_EXPANDED_HEADER}:")
            for e in expanded:
                parts.append(
                    f"- [chunk_id: {e.chunk_id}]: {e.relation} — {e.note}"
                )

    parts.append("")
    parts.append(
        "Rispondi alla domanda usando esclusivamente il contesto normativo "
        "fornito. Cita ogni affermazione con [cite:CHUNK_ID]."
    )
    return "\n".join(parts)


def _format_chunk(hit: "RetrievalHit") -> str:
    header = CHUNK_HEADER_FMT.format(chunk_id=hit.chunk_id)
    hierarchy = HIERARCHY_JOIN.join(hit.payload.get("hierarchy_path") or [])
    text = (hit.payload.get("text") or "").strip()
    lines = [header]
    if hierarchy:
        lines.append(hierarchy)
    lines.append(CHUNK_HEADER_TEXT_SEP)
    lines.append(text)
    lines.append(CHUNK_END_MARKER)
    return "\n".join(lines)
