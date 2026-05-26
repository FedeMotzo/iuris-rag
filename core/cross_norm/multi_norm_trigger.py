"""Trigger lessicale deterministico per query multi-norma (v1.1).

Rileva quali norme del corpus sono citate esplicitamente nella query
via pattern regex case-insensitive + word boundary. Niente LLM.

Le chiavi ritornate corrispondono alle chiavi del `norm_glossary.yaml`.
L'ordine di ritorno è deterministico (segue NORM_PATTERNS).

Convenzione: il trigger scatta a livello di pipeline solo se la lista
ritornata ha ≥2 elementi. Una sola norma rilevata → percorso standard
hybrid retriever; zero norme rilevate → percorso standard.
"""

from __future__ import annotations

import re

# Ordine di iterazione = ordine di ritorno (deterministico).
# Le chiavi sono gli ID norm del norm_glossary.yaml.
NORM_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "gdpr",
        re.compile(
            r"\b("
            r"GDPR"
            r"|RGPD"
            r"|Regolamento\s+\(?UE\)?\s+(?:n\.?\s*)?2016\s*/?\s*679"
            r"|Reg\.?\s+\(?UE\)?\s+(?:n\.?\s*)?2016\s*/?\s*679"
            r"|2016\s*/\s*679"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ai_act",
        re.compile(
            r"\b("
            r"AI\s+Act"
            r"|IA\s+Act"
            r"|Regolamento\s+\(?UE\)?\s+(?:n\.?\s*)?2024\s*/?\s*1689"
            r"|Reg\.?\s+\(?UE\)?\s+(?:n\.?\s*)?2024\s*/?\s*1689"
            r"|2024\s*/\s*1689"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "dlgs_231",
        re.compile(
            r"("
            r"\b231\s*[/\-]\s*2001\b"
            r"|\bD\.?\s*Lgs\.?\s*(?:n\.?\s*)?231\b"
            r"|\bDecreto\s+[Ll]egislativo\s+(?:n\.?\s*)?231(?:\s*[/\-]\s*2001)?\b"
            r"|\bresponsabilit[àa]\s+amministrativa\s+degli\s+enti\b"
            r"|\breat[oi][\s\-]presupposto\b"
            r"|\b(?:ai\s+sensi\s+del|sensi\s+del|del|ex|e)\s+231\b"
            r")",
            re.IGNORECASE,
        ),
    ),
    (
        "nis2",
        re.compile(
            r"\b("
            r"NIS\s*2"
            r"|NIS2"
            r"|D\.?\s*Lgs\.?\s*(?:n\.?\s*)?138\s*[/\-]\s*2024"
            r"|D\.?\s*Lgs\.?\s*(?:n\.?\s*)?138\b"
            r"|138\s*/\s*2024"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "codice_privacy",
        re.compile(
            r"("
            r"\bCodice\s+(?:della\s+)?[Pp]rivacy\b"
            r"|\bCodice\s+(?:in\s+materia\s+di\s+)?protezione\s+dei\s+dati\s+personali\b"
            r"|\bD\.?\s*Lgs\.?\s*(?:n\.?\s*)?196\s*[/\-]\s*2003\b"
            r"|\bD\.?\s*Lgs\.?\s*(?:n\.?\s*)?196\b"
            r"|\b196\s*/\s*2003\b"
            r"|\btrattamento\s+illecito\s+di\s+dati(?:\s+personali)?\b"
            r")",
            re.IGNORECASE,
        ),
    ),
    (
        "l_132_2025",
        re.compile(
            r"\b("
            r"L\.?\s+(?:n\.?\s+)?132\s*/\s*2025"
            r"|Legge\s+(?:n\.?\s+)?132\s*/\s*2025"
            r"|Legge\s+(?:n\.?\s+)?132\s+del\s+2025"
            r"|132\s*/\s*2025"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]


def detect_norms(query: str) -> list[str]:
    """Rileva norme citate esplicitamente nella query via pattern lessicale.

    Args:
        query: testo della query utente.

    Returns:
        Lista di norm_id (chiavi del norm_glossary.yaml) in ordine
        deterministico (definito da NORM_PATTERNS). Lista vuota se
        nessuna norma rilevata. Lista di un solo elemento se rilevata
        una sola norma.
    """
    detected: list[str] = []
    for norm_id, pat in NORM_PATTERNS:
        if pat.search(query):
            detected.append(norm_id)
    return detected
