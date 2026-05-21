"""Query expansion: concatena forme estese alle sigle/termini gergali presenti
nella query. Lookup statico da `aliases.yaml`.

Razionale: il corpus normativo italiano usa solo forme estese
("valutazione d'impatto sui diritti fondamentali"), mentre gli utenti reali
usano sigle ("FRIA"). Diagnostica Q19 ha confermato 0 occorrenze delle
sigle nel corpus → ponte lessicale necessario in pre-retrieval.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

_DEFAULT_ALIASES_PATH = Path(__file__).parent / "aliases.yaml"


@lru_cache(maxsize=4)
def load_aliases(path: Path | None = None) -> dict[str, list[str]]:
    """Carica aliases.yaml. Default: il file accanto al modulo.

    Ritorna dict {sigla: [forme_estese...]} in ordine YAML.
    Cached per path: la stessa istanza viene riusata tra chiamate.
    """
    p = path if path is not None else _DEFAULT_ALIASES_PATH
    data = yaml.safe_load(p.read_text())
    if data is None:
        return {}
    return {str(k): list(v) for k, v in data.items()}


def _key_is_multi_token(key: str) -> bool:
    return " " in key.strip()


def _key_matches(query: str, key: str) -> bool:
    """Single-token: word boundary case-insensitive. Multi-token: substring."""
    if _key_is_multi_token(key):
        return key.lower() in query.lower()
    pattern = r"\b" + re.escape(key) + r"\b"
    return re.search(pattern, query, flags=re.IGNORECASE) is not None


def expand_query(
    query: str,
    aliases: dict[str, list[str]] | None = None,
) -> str:
    """Espande sigle nella query concatenando le forme estese.

    Match case-insensitive sulle chiavi. Match word-boundary per token
    singoli; substring per chiavi multi-token (es. "scoring creditizio").
    Restituisce: query originale + " " + forme estese matchate, dedup
    preservando ordine di matching (= ordine delle chiavi nel YAML).
    Se nessun alias matcha, restituisce la query identica.
    Idempotente: applicare due volte non aggiunge duplicati.
    """
    if aliases is None:
        aliases = load_aliases()

    existing_lower = query.lower()
    additions: list[str] = []

    for key, forms in aliases.items():
        if not _key_matches(query, key):
            continue
        for form in forms:
            form_lower = form.lower()
            # Skip se la forma è già nella query (idempotenza) o se l'abbiamo
            # appena aggiunta in questa pass.
            if form_lower in existing_lower:
                continue
            if any(a.lower() == form_lower for a in additions):
                continue
            additions.append(form)

    if not additions:
        return query
    return query + " " + " ".join(additions)
