"""Generazione sub-query LLM-assisted per cross-norma v1.1.

Prompt template validato manualmente su Q68 (vedi spike/test_subquery_q68.md).
Inietta il vocabolario tecnico della norma target dal `norm_glossary.yaml`.

L'LLM client accettato è qualunque oggetto che esponga un metodo
`generate(prompt, system=None, max_tokens, temperature) -> obj` dove `obj`
ha attributo `text` (compatibile con `core.llm_provider.LLMProvider`).
Test/uso non-LLM possono passare un duck-type stub.

Caching:
- Il modulo legge il glossary una volta sola (lazy + cache).
- Niente caching delle risposte LLM qui (responsabilità del caller).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_GLOSSARY_PATH = Path(__file__).resolve().parent / "norm_glossary.yaml"

PROMPT_TEMPLATE = """Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: {short_name}

Vocabolario tecnico tipico della norma {short_name}:
{vocabolario_bullet_list}

Query utente originale:
"{query}"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nella norma {short_name} per questo scenario, usando il vocabolario tecnico della norma sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus {short_name}.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sulla norma {short_name}, non su altre norme."""


@lru_cache(maxsize=4)
def _load_glossary(path_str: str) -> dict[str, dict]:
    path = Path(path_str)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"norm_glossary atteso dict, trovato {type(data).__name__}")
    return data


def _build_prompt(query: str, norm_id: str, glossary_path: Path) -> str:
    glossary = _load_glossary(str(glossary_path))
    entry = glossary.get(norm_id)
    if entry is None:
        raise KeyError(
            f"norm_id={norm_id!r} non trovato in {glossary_path}. "
            f"Chiavi disponibili: {sorted(glossary.keys())}"
        )
    short_name = entry.get("short_name") or norm_id
    voci = entry.get("vocabolario") or []
    bullet_list = "\n".join(f"- {v}" for v in voci)
    return PROMPT_TEMPLATE.format(
        short_name=short_name,
        vocabolario_bullet_list=bullet_list,
        query=query,
    )


def generate_subquery(
    query: str,
    norm_id: str,
    llm_client: Any,
    glossary_path: Path = DEFAULT_GLOSSARY_PATH,
    max_tokens: int = 200,
) -> str:
    """Genera sub-query mirata per la norma target via LLM.

    Args:
        query: query utente originale.
        norm_id: chiave del norm_glossary.yaml (es. 'gdpr', 'ai_act').
        llm_client: oggetto con metodo `generate(prompt, system, max_tokens,
            temperature)` che ritorna un risultato con attributo `text`.
        glossary_path: path al norm_glossary.yaml.
        max_tokens: tetto sui token in output (default 200).

    Returns:
        Sub-query come stringa, 1-2 frasi, idealmente <= 50 parole.
    """
    prompt = _build_prompt(query, norm_id, glossary_path)
    logger.info("generate_subquery norm_id=%s query_len=%d", norm_id, len(query))
    result = llm_client.generate(
        prompt=prompt,
        system=None,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    text = getattr(result, "text", None)
    if text is None:
        raise ValueError(
            f"llm_client.generate() ritorno senza attributo `text`: {result!r}"
        )
    return text.strip()
