"""Unit test trigger lessicale multi-norma.

Test deterministici (regex only), nessuna dipendenza esterna.
"""

from __future__ import annotations

import pytest

from core.cross_norm.multi_norm_trigger import detect_norms


# Query reali del benchmark v3 (Q68-Q71, Q9) + sentinelle mono-norma e zero-norma.

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)

Q69 = (
    "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale "
    "NIS2 per il settore sanitario, intende impiegare un sistema di IA per "
    "supportare le attività di farmacovigilanza con dati provenienti da "
    "operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai "
    "sensi di AI Act, GDPR e NIS2?"
)

Q70 = (
    "Una banca italiana intende affidare in outsourcing a un fornitore "
    "extra-UE la gestione di un sistema di IA per il rilevamento di "
    "operazioni sospette di riciclaggio: quali profili AI Act, GDPR, "
    "NIS2 e 231 deve considerare in fase di selezione del fornitore?"
)

Q71 = (
    "Una regione italiana intende mettere in produzione un sistema di IA "
    "per supportare l'attribuzione di punteggi nelle graduatorie di "
    "accesso ai servizi residenziali per anziani: quali sono i principali "
    "profili giuridici da considerare integrando GDPR, AI Act, L. 132/2025 "
    "e NIS2?"
)

Q9 = (
    "Quali sono i reati presupposto in materia di trattamento illecito di "
    "dati personali ai sensi del 231?"
)


def test_q68_three_norms() -> None:
    norms = detect_norms(Q68)
    assert set(norms) == {"ai_act", "gdpr", "l_132_2025"}
    assert norms == sorted(norms, key=lambda n: ["gdpr", "ai_act", "dlgs_231",
                                                  "nis2", "codice_privacy",
                                                  "l_132_2025"].index(n))


def test_q69_three_norms() -> None:
    assert set(detect_norms(Q69)) == {"ai_act", "gdpr", "nis2"}


def test_q70_four_norms() -> None:
    assert set(detect_norms(Q70)) == {"ai_act", "gdpr", "nis2", "dlgs_231"}


def test_q71_four_norms() -> None:
    assert set(detect_norms(Q71)) == {"ai_act", "gdpr", "nis2", "l_132_2025"}


def test_q9_two_norms_includes_231() -> None:
    """Q9 deve rilevare 231 + almeno una norma sui dati (codice_privacy o gdpr)."""
    norms = set(detect_norms(Q9))
    assert "dlgs_231" in norms
    # accetta sia codice_privacy ("trattamento illecito di dati") sia gdpr
    assert norms & {"codice_privacy", "gdpr"}, (
        f"attesa anche codice_privacy o gdpr, ottenuto {norms}"
    )
    assert len(norms) >= 2


# ----------------------------------------------------- mono-norma e zero-norma

def test_mono_norm_gdpr_only() -> None:
    """Query con una sola norma → lista di 1 elemento (sotto soglia trigger)."""
    q = "Cos'è una DPIA secondo il GDPR?"
    assert detect_norms(q) == ["gdpr"]


def test_zero_norm_query() -> None:
    """Query generica senza norma esplicita → lista vuota."""
    q = "Quando serve fare una valutazione d'impatto?"
    assert detect_norms(q) == []


# ----------------------------------------------------- determinismo dell'ordine

def test_order_deterministic() -> None:
    """L'ordine segue NORM_PATTERNS, non l'ordine di apparizione nella query."""
    # Q71 cita GDPR prima di AI Act ma l'ordine ritornato è gdpr poi ai_act
    # (ordine NORM_PATTERNS).
    norms = detect_norms(Q71)
    assert norms.index("gdpr") < norms.index("ai_act")
    assert norms.index("ai_act") < norms.index("nis2")
    assert norms.index("nis2") < norms.index("l_132_2025")


# ----------------------------------------------------- ortografia robusta

@pytest.mark.parametrize("variant", [
    "GDPR",
    "gdpr",
    "Regolamento UE 2016/679",
    "Regolamento (UE) 2016/679",
    "Reg. UE 2016/679",
    "RGPD",
])
def test_gdpr_variants(variant: str) -> None:
    assert "gdpr" in detect_norms(f"Cosa prevede {variant} in materia di sanità?")


@pytest.mark.parametrize("variant", [
    "AI Act",
    "ai act",
    "Regolamento UE 2024/1689",
    "Regolamento (UE) 2024/1689",
])
def test_ai_act_variants(variant: str) -> None:
    assert "ai_act" in detect_norms(f"Cosa prevede {variant} per il settore sanitario?")


@pytest.mark.parametrize("variant", [
    "D.Lgs 231",
    "D. Lgs. 231",
    "231/2001",
    "231-2001",
    "responsabilità amministrativa degli enti",
    "reato presupposto",
    "reati presupposto",
])
def test_dlgs_231_variants(variant: str) -> None:
    assert "dlgs_231" in detect_norms(f"Cosa prevede {variant} in caso di reato?")


@pytest.mark.parametrize("variant", [
    "NIS2",
    "NIS 2",
    "D.Lgs 138/2024",
    "D.Lgs 138",
])
def test_nis2_variants(variant: str) -> None:
    assert "nis2" in detect_norms(f"Cosa prevede {variant} per gli operatori essenziali?")


@pytest.mark.parametrize("variant", [
    "Codice Privacy",
    "Codice della Privacy",
    "D.Lgs 196/2003",
    "D.Lgs 196",
    "196/2003",
    "trattamento illecito di dati personali",
])
def test_codice_privacy_variants(variant: str) -> None:
    assert "codice_privacy" in detect_norms(f"Cosa prevede il {variant}?")


@pytest.mark.parametrize("variant", [
    "L. 132/2025",
    "Legge 132/2025",
    "132/2025",
])
def test_l_132_2025_variants(variant: str) -> None:
    assert "l_132_2025" in detect_norms(f"Cosa prevede la {variant} per l'IA in sanità?")
