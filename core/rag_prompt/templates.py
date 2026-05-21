"""System prompt loader + costanti di formato per il user prompt.

I separatori sono fissati: cambiarli implicherebbe ri-validare il prompting
del modello (Anthropic e Ollama hanno tolleranze diverse a stili di
contesto).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent

# Formato chunk (vedi docstring builder.build_user_prompt).
CHUNK_HEADER_FMT = "[chunk_id: {chunk_id}]"
HIERARCHY_JOIN = " > "
CHUNK_HEADER_TEXT_SEP = "---"
CHUNK_END_MARKER = "==="
CHUNK_SEP = "\n\n"


@lru_cache(maxsize=8)
def load_system_prompt(lang: str = "it") -> str:
    """Carica e cachea il system prompt per la lingua richiesta.

    Cerca `system_prompt.{lang}.md` accanto a questo modulo. Solleva
    `FileNotFoundError` con percorso esplicito se il file non esiste.
    """
    path = _MODULE_DIR / f"system_prompt.{lang}.md"
    if not path.is_file():
        raise FileNotFoundError(
            f"System prompt non trovato per lang={lang!r}: atteso {path}"
        )
    return path.read_text(encoding="utf-8").strip()
