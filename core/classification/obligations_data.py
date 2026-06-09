"""Adempimenti AI Act per ruolo — DATO STATICO CURATO (verificato su EUR-Lex).

NON generato: niente map_and_assemble, niente generate_subquery. Le due liste
(provider / deployer) sono dato strutturato; `get_obligations(role)` le ritorna
con i tag di condizione e, se passato un retriever, popola il testo-fonte via
fetch_by_chunk_ids dell'articolo citato (e dell'eventuale chunk GDPR collegato).

Le condizioni NON sono risolte: la card mostra tutte le voci del ruolo con il
tag, il DPO valuta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import ObligationItem

if TYPE_CHECKING:
    from core.hybrid_retriever import HybridRetriever

AI_ACT_URN = "eli/reg/2024/1689/oj"
GDPR_URN = "eli/reg/2016/679/oj"
GDPR_ART35 = f"{GDPR_URN}__art_35"  # DPIA — collegamento per 26(9)

VALID_ROLES = ("provider", "deployer")
DEFAULT_ROLE = "deployer"


@dataclass(frozen=True)
class _Spec:
    article: str
    paragraph: str | None
    title: str
    description: str
    condition: str | None        # None = "sempre"
    gdpr_link: str | None = None
    note: str | None = None


# --------------------------------------------------------------------------- #
# PROVIDER (fornitore) — chunk_id = __art_<n>
# --------------------------------------------------------------------------- #
PROVIDER_SPECS: list[_Spec] = [
    _Spec("Art. 9", None, "Sistema di gestione dei rischi",
          "processo iterativo per tutto il ciclo di vita", None),
    _Spec("Art. 10", None, "Dati e governance dei dati",
          "dataset pertinenti/rappresentativi, gestione bias",
          "solo se usa training con dati"),
    _Spec("Art. 11", None, "Documentazione tecnica",
          "redigere/aggiornare doc tecnica (All. IV) pre-mercato", None,
          note="I contenuti minimi sono nell'Allegato IV, non presente nel corpus."),
    _Spec("Art. 12", None, "Conservazione registrazioni (logging)",
          "registrazione automatica eventi", None),
    _Spec("Art. 13", None, "Trasparenza e info ai deployer",
          "istruzioni per l'uso interpretabili", None),
    _Spec("Art. 14", None, "Sorveglianza umana",
          "progettare per supervisione efficace", None),
    _Spec("Art. 15", None, "Accuratezza, robustezza, cibersicurezza",
          "livelli adeguati per il ciclo di vita", None),
    _Spec("Art. 16", None, "Obblighi generali del fornitore",
          "norma ombrello, conformità Sez. 2 + dati identificativi", None),
    _Spec("Art. 17", None, "Sistema di gestione qualità (QMS)",
          "QMS documentato", None, note="PMI: forma semplificata"),
    _Spec("Art. 18", None, "Conservazione dei documenti",
          "doc a disposizione autorità per 10 anni", None),
    _Spec("Art. 19", None, "Conservazione log generati",
          "conservare i log del sistema",
          "se i log sono sotto controllo del fornitore"),
    _Spec("Art. 20", None, "Azioni correttive e info",
          "correttive + informare autorità/distributori",
          "in caso di non conformità/rischio"),
    _Spec("Art. 21", None, "Cooperazione con le autorità",
          "fornire info/doc su richiesta", "su richiesta autorità"),
    _Spec("Art. 22", None, "Rappresentante autorizzato",
          "designare rappresentante UE", "solo fornitori paesi terzi"),
    _Spec("Art. 43", None, "Valutazione della conformità",
          "sottoporre a valutazione pre-mercato", None,
          note="procedura dipende dal tipo"),
    _Spec("Art. 47", None, "Dichiarazione di conformità UE",
          "redigere dichiarazione scritta", None),
    _Spec("Art. 48", None, "Marcatura CE", "apporre marcatura CE", None),
    _Spec("Art. 49", None, "Registrazione",
          "registrare sé e il sistema nella banca dati UE", None),
    _Spec("Art. 72", None, "Monitoraggio post-commercializzazione",
          "sistema di monitoraggio documentato", None),
    _Spec("Art. 73", None, "Segnalazione incidenti gravi",
          "segnalare alle autorità di vigilanza",
          "al verificarsi di incidente grave"),
]

# --------------------------------------------------------------------------- #
# DEPLOYER (utilizzatore) — chunk_id = __art_26 per i 26(x), __art_27 per FRIA
# --------------------------------------------------------------------------- #
DEPLOYER_SPECS: list[_Spec] = [
    _Spec("Art. 26", "1", "Uso conforme alle istruzioni",
          "misure tecn./organizzative per usare secondo istruzioni", None),
    _Spec("Art. 26", "2", "Sorveglianza umana",
          "affidare a persone competenti/formate/con autorità", None),
    _Spec("Art. 26", "4", "Pertinenza dati di input",
          "input pertinenti e rappresentativi", "se controlla i dati di input"),
    _Spec("Art. 26", "5", "Monitoraggio e segnalazione",
          "monitorare; sospendere+informare in caso di rischio; segnalare incidenti",
          "scatta su rischio/incidente; istituti finanziari via normativa settoriale"),
    _Spec("Art. 26", "6", "Conservazione log", "conservare log ≥ 6 mesi",
          "se i log sono sotto controllo del deployer"),
    _Spec("Art. 26", "7", "Informazione dei lavoratori",
          "informare rappresentanti/lavoratori prima dell'uso",
          "solo datore di lavoro che usa sul luogo di lavoro"),
    _Spec("Art. 26", "8", "Registrazione banca dati UE",
          "adempiere art. 49; non usare se non registrato",
          "solo autorità pubbliche / organi UE"),
    _Spec("Art. 26", "9", "Uso info per la DPIA",
          "usare info art. 13 per la DPIA",
          "obbligo DPIA esterno all'AI Act (nasce dal GDPR)",
          gdpr_link=GDPR_ART35,
          note="si collega al GDPR (DPIA, art. 35) — incrocio AI Act↔GDPR in "
               "arrivo nel prossimo layer"),
    _Spec("Art. 26", "10", "Autorizzazione identificazione biometrica a posteriori",
          "autorizzazione giud./amm.",
          "solo forze dell'ordine + post-remote biometric",
          note="rinvio alla Direttiva (UE) 2016/680 (forze dell'ordine), FUORI "
               "corpus; caso di nicchia"),
    _Spec("Art. 26", "11", "Informazione delle persone fisiche",
          "informare chi è soggetto a decisioni del sistema",
          "sistemi All. III che prendono/assistono decisioni su persone"),
    _Spec("Art. 26", "12", "Cooperazione con le autorità",
          "cooperare nelle azioni relative al sistema", None),
    _Spec("Art. 27", None, "Valutazione d'impatto diritti fondamentali (FRIA)",
          "svolgere FRIA pre-uso + notificare",
          "organismi di diritto pubblico; privati con servizi pubblici; deployer "
          "All. III 5(b)/5(c); esclusi All. III punto 2"),
]

_BY_ROLE: dict[str, list[_Spec]] = {
    "provider": PROVIDER_SPECS,
    "deployer": DEPLOYER_SPECS,
}

_ART_NUM_RE = re.compile(r"Art\.\s*(\d+)")


def _chunk_for(article: str) -> str:
    m = _ART_NUM_RE.search(article)
    if not m:
        raise ValueError(f"articolo non parsabile: {article!r}")
    return f"{AI_ACT_URN}__art_{m.group(1)}"


def _spec_to_item(s: _Spec) -> ObligationItem:
    return ObligationItem(
        article=s.article,
        title=s.title,
        description=s.description,
        paragraph=s.paragraph,
        condition=s.condition,
        gdpr_link=s.gdpr_link,
        note=s.note,
        source_chunk_id=_chunk_for(s.article),
    )


def get_obligations(
    role: str = DEFAULT_ROLE,
    retriever: "HybridRetriever | None" = None,
) -> list[ObligationItem]:
    """Ritorna la lista curata di adempimenti del ruolo, con i tag di condizione.

    Args:
        role: "provider" (costruttore) o "deployer" (utilizzatore, default).
        retriever: se fornito, popola `source_text` (testo-fonte dell'articolo
            citato) e, per le voci con `gdpr_link`, `gdpr_source_text` (puntatore
            statico navigabile, nessuna sintesi cross-norma).

    Le condizioni NON sono risolte: tutte le voci del ruolo sono restituite.
    """
    role = role.strip().lower()
    if role not in _BY_ROLE:
        raise ValueError(f"role non valido: {role!r}. Validi: {VALID_ROLES}")

    items = [_spec_to_item(s) for s in _BY_ROLE[role]]

    if retriever is not None:
        ids: list[str] = []
        for it in items:
            if it.source_chunk_id and it.source_chunk_id not in ids:
                ids.append(it.source_chunk_id)
            if it.gdpr_link and it.gdpr_link not in ids:
                ids.append(it.gdpr_link)
        hits = retriever.fetch_by_chunk_ids(ids)
        text_by_id = {h.chunk_id: (h.payload or {}).get("text", "") for h in hits}
        for it in items:
            it.source_text = text_by_id.get(it.source_chunk_id)
            if it.gdpr_link:
                it.gdpr_source_text = text_by_id.get(it.gdpr_link)

    return items
