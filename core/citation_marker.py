"""Shared regex for [cite:CHUNK_ID] markers — unica source of truth."""
from __future__ import annotations

import re

# Marker [cite:CHUNK_ID]: il contenuto deve iniziare con un char non-spazio
# (così [cite:] e [cite: foo] restano malformati). Tollera code descrittive.
CITE_PATTERN = re.compile(r"\[cite:([^\]\s][^\]]*)\]")


def has_dangling_cite(text: str) -> bool:
    """True se il testo contiene almeno un [cite: aperto senza ] di chiusura."""
    return text.count("[cite:") > len(CITE_PATTERN.findall(text))
