"""Builder DETERMINISTICO della `ClassificationCard` (zero LLM).

Le sez. 1-3 derivano dal GIUDIZIO per-candidato (`ClassificationJudgment`); la
sez. 6 dai limiti dichiarati (+ pathway art. 6(1)). Gli adempimenti (sez. 4)
NON sono più qui: sono un'operazione separata, `get_obligations(role)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import (
    ART6_1_SAFETY_LIMIT,
    DISCLAIMER_DEFAULT,
    ClassificationCard,
)

if TYPE_CHECKING:
    from .models import ClassificationJudgment


def _clean(text: str) -> str:
    """Trim + rimuove la punteggiatura finale (evita doppi punti in concatenazione)."""
    return text.strip().rstrip(" .;:")


def build_classification_card(
    judgment: "ClassificationJudgment",
    *,
    declared_limits: tuple[str, ...] | list[str] = (),
    disclaimer: str = DISCLAIMER_DEFAULT,
) -> ClassificationCard:
    """Costruisce la card di classificazione dal giudizio. Puro/deterministico."""
    applied = judgment.applied_annex()  # già validati per appartenenza
    high_risk_annex = bool(applied)
    art6_1 = judgment.art6_1_safety_component
    practices = judgment.applied_practices()  # già validate per appartenenza
    prohibited_flag = bool(practices)

    # --- sez. 2 — categoria Allegato III (dai punti applies=true del giudizio)
    annex_iii_category: str | None = None
    if applied:
        parts = [
            f"Allegato III, punto {a.point}"
            + (f" — {_clean(a.reason)}" if _clean(a.reason) else "")
            for a in applied
        ]
        annex_iii_category = "; ".join(parts)

    # --- sez. 1 — verdetto a PRIORITÀ: vietata > Allegato III > art. 6(1) > nessuno
    if prohibited_flag:
        plist = "; ".join(
            f"{_clean(p.label)}" + (f" — {_clean(p.reason)}" if _clean(p.reason) else "")
            for p in practices
        )
        verdict = (
            f"PRATICA VIETATA ex art. 5: {plist}. Il sistema non può essere "
            "immesso sul mercato né usato."
        )
        if high_risk_annex:
            pts = ", ".join(f"punto {a.point}" for a in applied)
            verdict += f" (rientrerebbe anche in Allegato III {pts}, ma resta vietato)."
    elif high_risk_annex:
        verdict = (
            "Aree Allegato III potenzialmente rilevanti dal giudizio sui "
            f"riferimenti del set di classificazione: {annex_iii_category}. "
            "Verificare l'eccezione art. 6(3). Decisione finale al DPO."
        )
    elif art6_1.plausible:
        reason = _clean(art6_1.reason)
        suffix = f" {reason}." if reason else ""
        verdict = (
            "Non risulta alto rischio per Allegato III; POSSIBILE alto rischio "
            "per via art. 6(1) (componente di sicurezza / dispositivo medico), "
            f"NON verificabile nel corpus — da approfondire.{suffix} "
            "Decisione finale al DPO."
        )
    else:
        verdict = (
            "Non risulta alto rischio (né Allegato III né altra via nei "
            "riferimenti). Decisione finale al DPO."
        )

    # --- sez. 3 — eccezione art. 6(3): renderizza la CONCLUSIONE del giudice
    art6_3_exception: str | None = None
    if high_risk_annex:
        ex = judgment.art6_3_exception
        reason = _clean(ex.reason)
        tail = f": {reason}." if reason else "."
        if ex.plausible:
            art6_3_exception = f"Possibile deroga ex art. 6(3){tail}"
        else:
            art6_3_exception = f"Eccezione art. 6(3) non applicabile{tail}"

    # --- sez. 6 — limiti dichiarati (+ pathway art. 6(1) se plausibile)
    limits = list(declared_limits)
    if art6_1.plausible:
        reason = _clean(art6_1.reason)
        note = ART6_1_SAFETY_LIMIT + (f" Motivo del giudizio: {reason}" if reason else "")
        limits.append(note)

    return ClassificationCard(
        verdict=verdict,
        prohibited_flag=prohibited_flag,
        annex_iii_category=annex_iii_category,
        art6_3_exception=art6_3_exception,
        declared_limits=limits,
        disclaimer=disclaimer,
    )
