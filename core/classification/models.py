"""Dataclass della card di classificazione UC1 (single-norm AI Act).

Strutture sottili e JSON-serializzabili. La logica vive in `judge.py` (giudizio
a insieme chiuso) e `builder.py` (assemblaggio card). Vedi redesign Step 4:
il verdetto (sez. 1-3) deriva dal GIUDIZIO per-candidato, non dalle citazioni.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Sez. 7 — costante (non un verdetto vincolante).
DISCLAIMER_DEFAULT = (
    "Questa card raccoglie evidenza normativa a supporto della classificazione "
    "effettuata dal DPO / titolare; non è un verdetto vincolante né una "
    "consulenza legale. La decisione finale spetta al DPO."
)

# Sez. 6 — limite dichiarato CONTESTUALE: mostrato solo quando il giudizio
# segnala il pathway art. 6(1) (rinvio a normativa settoriale fuori corpus).
# Il limite Allegato IV NON è di classificazione: vive come note sull'obbligo
# Art. 11 (provider) in obligations_data.
ART6_1_SAFETY_LIMIT = (
    "Possibile alto rischio ex art. 6(1) come componente di sicurezza di un "
    "prodotto regolato da normativa di armonizzazione settoriale (es. "
    "dispositivo medico): tale normativa è fuori corpus, la classificazione su "
    "quel pathway non è verificabile sui riferimenti recuperati."
)


# --------------------------------------------------------------------------- #
# Giudizio per-candidato (insieme chiuso)
# --------------------------------------------------------------------------- #

@dataclass
class AnnexJudgment:
    point: int
    applies: bool
    reason: str
    cite: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProhibitedPracticeJudgment:
    """Una delle pratiche vietate dell'art. 5, giudicata sì/no (come un punto
    Allegato III). `practice` è l'etichetta a..h."""

    practice: str          # "a".."h"
    label: str
    applies: bool
    reason: str
    cite: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlausibilityJudgment:
    plausible: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClassificationJudgment:
    """Esito del giudizio per-candidato sul set fisso di norme."""

    annex_iii: list[AnnexJudgment]                      # sempre 8 punti (1-8)
    prohibited_practices: list[ProhibitedPracticeJudgment]  # sempre 8 pratiche (a-h)
    art6_1_safety_component: PlausibilityJudgment
    art6_3_exception: PlausibilityJudgment

    def applied_annex(self) -> list[AnnexJudgment]:
        """Punti Allegato III con applies=true (post-validazione)."""
        return [a for a in self.annex_iii if a.applies]

    def applied_practices(self) -> list[ProhibitedPracticeJudgment]:
        """Pratiche vietate con applies=true (post-validazione)."""
        return [p for p in self.prohibited_practices if p.applies]

    @property
    def high_risk_annex(self) -> bool:
        return bool(self.applied_annex())

    @property
    def prohibited(self) -> bool:
        return bool(self.applied_practices())

    def to_dict(self) -> dict:
        return {
            "annex_iii": [a.to_dict() for a in self.annex_iii],
            "prohibited_practices": [p.to_dict() for p in self.prohibited_practices],
            "art6_1_safety_component": self.art6_1_safety_component.to_dict(),
            "art6_3_exception": self.art6_3_exception.to_dict(),
        }


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #

@dataclass
class ObligationItem:
    """Sez. 4 — una voce di adempimento (DATO STATICO CURATO, per ruolo).

    Le condizioni (`condition`) NON sono risolte: la card mostra tutte le voci
    del ruolo con il loro tag, il DPO valuta. `source_text`/`gdpr_source_text`
    sono il testo-fonte espandibile, popolato via fetch_by_chunk_ids.
    """

    article: str                          # "Art. 9" / "Art. 26"
    title: str = ""                       # rubrica curata
    description: str = ""                  # descrizione curata
    paragraph: str | None = None          # "1".."12" per 26(x), None altrove
    condition: str | None = None          # None = "sempre"; testo = condizionato
    gdpr_link: str | None = None          # chunk_id GDPR collegato (puntatore statico)
    note: str | None = None               # nota/tag aggiuntivo
    source_chunk_id: str | None = None    # chunk_id dell'articolo citato (AI Act)
    source_text: str | None = None        # testo-fonte dell'articolo (da fetch)
    gdpr_source_text: str | None = None   # testo-fonte del chunk GDPR collegato (da fetch)

    @property
    def label(self) -> str:
        """Etichetta leggibile: 'Art. 26(9)' se c'è paragraph, 'Art. 9' altrimenti."""
        return f"{self.article}({self.paragraph})" if self.paragraph else self.article

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClassificationCard:
    """Card di CLASSIFICAZIONE UC1 (sez. 1-3 + 6-7). Gli adempimenti (sez. 4)
    sono un'operazione separata: `get_obligations(role)`, non più qui."""

    verdict: str                        # sez. 1 (testo-evidenza)
    prohibited_flag: bool               # sez. 1 (art. 5, dal giudizio)
    annex_iii_category: str | None      # sez. 2 (punto/i + perché, dal giudizio)
    art6_3_exception: str | None        # sez. 3 (solo se ≥1 area Allegato III)
    declared_limits: list[str]          # sez. 6
    disclaimer: str                     # sez. 7

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "prohibited_flag": self.prohibited_flag,
            "annex_iii_category": self.annex_iii_category,
            "art6_3_exception": self.art6_3_exception,
            "declared_limits": list(self.declared_limits),
            "disclaimer": self.disclaimer,
        }


@dataclass
class ClassificationResult:
    """Esito di `RAGPipeline.classify()`: SOLO classificazione (no adempimenti).

    Gli adempimenti si ottengono separatamente con `RAGPipeline.get_obligations`.
    """

    system_description: str
    judgment: ClassificationJudgment
    card: ClassificationCard
    high_risk_annex: bool  # alto rischio via Allegato III (NON assoluto)

    @property
    def obligations_applicable(self) -> bool:
        """Adempimenti Capo III pertinenti: alto rischio Allegato III E non
        vietata (una pratica vietata rende gli adempimenti non pertinenti)."""
        return self.high_risk_annex and not self.card.prohibited_flag

    def to_dict(self) -> dict:
        """Vista JSON-serializzabile (per artefatti spike / UI)."""
        return {
            "system_description": self.system_description,
            "high_risk_annex": self.high_risk_annex,
            "obligations_applicable": self.obligations_applicable,
            "judgment": self.judgment.to_dict(),
            "card": self.card.to_dict(),
        }
