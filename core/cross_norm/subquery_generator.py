"""Generazione sub-query mono-concetto LLM-assisted per cross-norma v1.2.

Cambio rispetto a v1.1: l'LLM emette una **lista** di sub-query mono-concetto
(1 per concetto saliente attivato dallo scenario) invece di una stringa
enciclopedica che enumera tutti gli istituti. Lo scopo è dare al rerank
cross-encoder un input ad ampiezza omogenea, evitando la svalutazione che
una sub-query multi-concetto induce sui chunk specifici (vedi diagnosi
spike/GRAPH_DIAGNOSIS_V1_2.md Verifica 9).

Contratto LLM: l'output è un JSON array di stringhe. Parser robusto: se il
modello sgarra (preamble, code fences, stringa singola), fallback a wrap in
lista di 1 elemento.

Caching:
- Il modulo legge il glossary una volta sola (lazy + cache).
- Niente caching delle risposte LLM qui (responsabilità del caller).
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_GLOSSARY_PATH = Path(__file__).resolve().parent / "norm_glossary.yaml"

# Tetto token in output del decomposer. Punto unico di verità: produzione
# (retriever.py) e script di validazione devono leggere QUESTO valore, mai
# hardcodarne uno proprio, così i due path non possono divergere.
SUBQUERY_MAX_TOKENS = 1500

PROMPT_TEMPLATE = """Devi generare sub-query mirate per il retrieval su corpus normativo italiano.

Norma target: {short_name}

Vocabolario tecnico tipico della norma {short_name}:
{vocabolario_bullet_list}

Query utente originale:
"{query}"

Compito: il vocabolario qui sopra è la CHECKLIST degli istituti della norma
{short_name}. Scorri OGNI voce: per ciascuna valuta se lo scenario la attiva
— anche implicitamente, quando il ruolo o il contesto giuridico dello scenario
fa scattare quell'istituto pur senza nominarlo. Per ogni istituto attivato
emetti UNA sub-query mono-concetto. NON fermarti alle prime voci dell'elenco:
gli istituti con numero d'articolo alto (obblighi del deployer, valutazioni
d'impatto, sanzioni, notifiche) vanno coperti quanto i primi. In dubbio,
includi: omettere un istituto dispositivo è peggio che includerne uno marginale.
NON emettere sub-query per mere definizioni di soggetti o termini (es.
definizione di fornitore/deployer ex art. 3, definizioni ex art. 4): genera
sub-query SOLO per istituti dispositivi — divieti, obblighi, valutazioni
d'impatto, basi giuridiche, ambito di applicazione, sanzioni, notifiche.
Completezza a livello di ARTICOLO: emetti UNA sola sub-query per ogni articolo
dispositivo attivato, e coprili TUTTI, anche quelli ad articolo alto. NON
suddividere un singolo articolo in più sub-query per commi, paragrafi o lettere:
un articolo = una sub-query; se un articolo ha più obblighi rilevanti,
riassumili nella stessa sub-query.
ECCEZIONE: i punti di un Allegato restano sub-query DISTINTE (un punto
d'allegato = un istituto), come già stabilito. La regola no-split vale per
commi/paragrafi/lettere di un articolo, non per i punti di allegato.

FORMA di ogni sub-query (tassativa):
- DICHIARATIVA, non interrogativa. Vietato "Quali...", "Quando...", "In che modo...".
- Struttura: <oggetto/rubrica dell'istituto> ex art. N {short_name}: <3-4 keyword di rubrica>.
- Includi sempre il numero d'articolo esplicito (ed eventuale comma/punto).
- NIENTE contesto applicativo dello scenario: vietati settori ("sanitario", "bancario"),
  strumenti ("chatbot", "sistema IA"), soggetti ("azienda", "regione"). Diluiscono il match.
- Rispecchia la terminologia della rubrica ufficiale dell'articolo quando la conosci.

GRANULARITÀ ALLEGATI: ogni punto specifico di un Allegato (es. Allegato III punto 5)
o sotto-voce dispositiva implicata riceve una sub-query DEDICATA che lo nomina
esplicitamente (es. "Allegato III punto 5 AI Act: accesso a servizi pubblici essenziali
e prestazioni"). NON accorparlo in una sub-query generale di classificazione.

Una sub-query per istituto. Se lo scenario ne attiva uno solo, emetti una sola sub-query.

Output: JSON array di stringhe, ognuna dichiarativa mono-concetto. Niente preamboli, solo l'array.

Esempio:
["Trattamento di categorie particolari di dati personali ex art. 9 GDPR: divieto, deroghe, dati sanitari.", "Valutazione d'impatto sulla protezione dei dati ex art. 35 GDPR: rischi elevati, obbligatorietà."]"""


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


_QUOTED_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*?)"', re.DOTALL)


def _strip_code_fences(s: str) -> str:
    """Rimuove fence ``` di apertura e ``` di chiusura, anche se sbilanciate."""
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s)
    return s.strip()


def _parse_subquery_list(text: str) -> list[str]:
    """Parsa l'output LLM come JSON array.

    Tolleranza:
    - code fences ``` opzionali (anche sbilanciati) rimossi
    - fallback: estrae ogni stringa fra doppi apici come elemento
    - se il payload è una stringa singola senza JSON (legacy V2), wrap in [s]
    """
    s = _strip_code_fences(text)
    # Tentativo 1: JSON puro
    try:
        arr = json.loads(s)
        if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
            cleaned = [x.strip() for x in arr if x and x.strip()]
            if cleaned:
                return cleaned
    except (json.JSONDecodeError, ValueError):
        pass
    # Tentativo 2: array troncato. Estrai tutte le stringhe fra doppi apici.
    # Resiste a trailing comma, mancata chiusura `]`, e contenuti multi-line.
    quoted = _QUOTED_STRING_RE.findall(s)
    if quoted:
        cleaned = [q.strip() for q in quoted if q and q.strip()]
        # Filtra elementi spuri (singoli caratteri, marker)
        cleaned = [c for c in cleaned if len(c) >= 10]
        if cleaned:
            return cleaned
    # Legacy V2: stringa singola
    if "\n" not in s and not s.startswith("["):
        return [s]
    # Fallback estremo: split per linee non vuote
    out: list[str] = []
    for raw in s.splitlines():
        line = raw.strip().lstrip("-*0123456789.) \t").strip().strip('"').strip("'").rstrip(",")
        if line and len(line) >= 10 and not line.startswith("```") and line not in {"[", "]"}:
            out.append(line)
    if out:
        return out
    raise ValueError(f"Impossibile parsare sub-query list da: {text[:200]!r}")


def generate_subquery(
    query: str,
    norm_id: str,
    llm_client: Any,
    glossary_path: Path = DEFAULT_GLOSSARY_PATH,
    max_tokens: int = SUBQUERY_MAX_TOKENS,
) -> list[str]:
    """Genera N sub-query mono-concetto per la norma target via LLM.

    Args:
        query: query utente originale.
        norm_id: chiave del norm_glossary.yaml (es. 'gdpr', 'ai_act').
        llm_client: oggetto con metodo `generate(prompt, system, max_tokens,
            temperature)` che ritorna un risultato con attributo `text`.
        glossary_path: path al norm_glossary.yaml.
        max_tokens: tetto sui token in output (default SUBQUERY_MAX_TOKENS,
            punto unico di verità condiviso con lo script di validazione).

    Returns:
        Lista di sub-query, una per concetto saliente. Mai vuota: se il
        prompt produce una sola stringa, viene wrappata in `[s]`.
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
    return _parse_subquery_list(text)
