"""Test per core/citation_renderer e core/citation_marker."""
from __future__ import annotations

import json
import pathlib

import pytest

from core.citation_marker import CITE_PATTERN, has_dangling_cite
from core.citation_renderer import (
    _norm_names,
    cite_label,
    norm_label,
    render_cites,
    render_cites_default,
)

# doc_urn delle 6 norme (fonte: norm_glossary.yaml)
_GDPR = "eli/reg/2016/679/oj"
_AI = "eli/reg/2024/1689/oj"
_D231 = "akn/it/act/decreto_legislativo/stato/2001-06-08/231"
_NIS2 = "akn/it/act/decreto_legislativo/stato/2024-09-04/138"
_CP = "akn/it/act/decreto_legislativo/stato/2003-06-30/196"
_L132 = "akn/it/act/legge/stato/2025-09-23/132"

# Fixture minima senza I/O per i test di cite_label
_NAMES: dict[str, str] = {
    _GDPR: "GDPR",
    _AI: "AI Act",
    _D231: "D.Lgs 231/2001",
    _NIS2: "NIS2",
    _CP: "Codice Privacy",
    _L132: "L. 132/2025",
}

_PRES_DIR = pathlib.Path(__file__).parent.parent / "spike" / "runs" / "paid_subset_v1"


# ─────────────────────────── norm_label ────────────────────────────────────

@pytest.mark.parametrize("short_name,expected", [
    ("GDPR / Regolamento UE 2016/679", "GDPR"),
    ("AI Act / Regolamento UE 2024/1689", "AI Act"),
    ("D.Lgs 231/2001 / responsabilità amministrativa degli enti", "D.Lgs 231/2001"),
    ("NIS2 / D.Lgs 138/2024", "NIS2"),
    ("Codice Privacy / D.Lgs 196/2003", "Codice Privacy"),
    ("L. 132/2025 / Disposizioni nazionali in materia di intelligenza artificiale", "L. 132/2025"),
])
def test_norm_label(short_name: str, expected: str) -> None:
    assert norm_label(short_name) == expected


# ─────────────────────────── _norm_names dal glossary ──────────────────────

@pytest.mark.parametrize("doc_urn,expected", [
    (_GDPR, "GDPR"),
    (_AI, "AI Act"),
    (_D231, "D.Lgs 231/2001"),
    (_NIS2, "NIS2"),
    (_CP, "Codice Privacy"),
    (_L132, "L. 132/2025"),
])
def test_norm_names_from_glossary(doc_urn: str, expected: str) -> None:
    assert _norm_names()[doc_urn] == expected


# ─────────────────────────── cite_label: forme ─────────────────────────────

def test_cite_label_art_N() -> None:
    assert cite_label(f"{_GDPR}__art_6", _NAMES) == "art. 6 GDPR"


def test_cite_label_art_N_suffix_octies() -> None:
    assert cite_label(f"{_CP}__art_25-octies", _NAMES) == "art. 25-octies Codice Privacy"


def test_cite_label_art_N_suffix_ter() -> None:
    assert cite_label(f"{_CP}__art_2-ter", _NAMES) == "art. 2-ter Codice Privacy"


def test_cite_label_art_N_paras_collapse() -> None:
    """__paras_X_Y collassa all'articolo."""
    assert cite_label(f"{_GDPR}__art_38__paras_1_11", _NAMES) == "art. 38 GDPR"


def test_cite_label_art_N_suffix_and_paras_collapse() -> None:
    """art con suffix latin + __paras_ → conserva suffix, collassa paras."""
    assert cite_label(f"{_CP}__art_25-undecies__paras_1_6", _NAMES) == "art. 25-undecies Codice Privacy"


def test_cite_label_annex_III() -> None:
    assert cite_label(f"{_AI}__annex_III", _NAMES) == "Allegato III AI Act"


def test_cite_label_annex_III_point_5() -> None:
    assert cite_label(f"{_AI}__annex_III__point_5", _NAMES) == "Allegato III, punto 5 AI Act"


def test_cite_label_recital_N() -> None:
    assert cite_label(f"{_GDPR}__recital_45", _NAMES) == "considerando 45 GDPR"


def test_cite_label_unknown_doc_urn_raw() -> None:
    chunk_id = "unknown/urn__art_1"
    assert cite_label(chunk_id, _NAMES) == chunk_id


def test_cite_label_unknown_form_raw() -> None:
    chunk_id = f"{_GDPR}__schedule_2"
    assert cite_label(chunk_id, _NAMES) == chunk_id


def test_cite_label_no_separator_raw() -> None:
    chunk_id = "chunk_without_separator"
    assert cite_label(chunk_id, _NAMES) == chunk_id


def test_cite_label_descriptor_tail_raw() -> None:
    """CITE_PATTERN cattura 'ID, par. 1'; parte non riconosciuta → grezzo."""
    chunk_id = f"{_GDPR}__art_6, par. 1"
    assert cite_label(chunk_id, _NAMES) == chunk_id


# ─────────────────────────── render_cites ──────────────────────────────────

def test_render_cites_single() -> None:
    text = f"Vedi [cite:{_GDPR}__art_6]."
    assert render_cites(text, _NAMES) == "Vedi art. 6 GDPR."


def test_render_cites_multiple() -> None:
    text = f"[cite:{_GDPR}__art_6] e [cite:{_AI}__recital_28]."
    assert render_cites(text, _NAMES) == "art. 6 GDPR e considerando 28 AI Act."


def test_render_cites_no_markers() -> None:
    text = "Nessuna citazione."
    assert render_cites(text, _NAMES) == text


def test_render_cites_repeated_marker() -> None:
    text = f"[cite:{_GDPR}__art_6] e ancora [cite:{_GDPR}__art_6]."
    assert render_cites(text, _NAMES) == "art. 6 GDPR e ancora art. 6 GDPR."


def test_render_cites_annex_point() -> None:
    text = f"[cite:{_AI}__annex_III__point_5] sistemi ad alto rischio."
    assert render_cites(text, _NAMES) == "Allegato III, punto 5 AI Act sistemi ad alto rischio."


# ─────────────────────────── CITE_PATTERN (citation_marker) ────────────────

def test_cite_pattern_standard() -> None:
    m = CITE_PATTERN.search(f"[cite:{_GDPR}__art_6]")
    assert m is not None
    assert m.group(1) == f"{_GDPR}__art_6"


def test_cite_pattern_descriptor_tail_captured() -> None:
    """La coda descrittiva è catturata dal gruppo 1 (invariato da verifier)."""
    m = CITE_PATTERN.search(f"[cite:{_GDPR}__art_6, par. 1]")
    assert m is not None
    assert m.group(1) == f"{_GDPR}__art_6, par. 1"


def test_cite_pattern_empty_ignored() -> None:
    assert CITE_PATTERN.search("[cite:]") is None


def test_cite_pattern_leading_space_ignored() -> None:
    assert CITE_PATTERN.search("[cite: foo]") is None


# ─────────────────────────── E2E: 12 artefatti ─────────────────────────────

_PRESENTATIONS = sorted(_PRES_DIR.glob("*.presentation.json"))


def test_e2e_twelve_files_found() -> None:
    assert len(_PRESENTATIONS) == 12, (
        f"Attesi 12 file presentation.json, trovati {len(_PRESENTATIONS)}"
    )


def test_e2e_no_residual_cite_markers() -> None:
    """render_cites_default → zero marker ben formati residui su tutti i 12 file."""
    for path in _PRESENTATIONS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for norm in data["norms"]:
            for article in norm["articles"]:
                rendered = render_cites_default(article["body"])
                residual = CITE_PATTERN.findall(rendered)
                assert residual == [], (
                    f"Marker ben formati residui in {path.name} "
                    f"/ {norm['norm_id']} / {article['article']!r}: {residual}"
                )


def test_e2e_q3_art6_label_present() -> None:
    """Q3 Art. 6 GDPR → body renderizzato contiene 'art. 6 GDPR'."""
    data = json.loads((_PRES_DIR / "Q3.presentation.json").read_text(encoding="utf-8"))
    art6 = next(
        a
        for n in data["norms"]
        for a in n["articles"]
        if a["article"] == "Art. 6"
    )
    rendered = render_cites_default(art6["body"])
    assert "art. 6 GDPR" in rendered


def test_e2e_has_dangling_containment() -> None:
    """has_dangling_cite becca esattamente Q71/gdpr/Art.6 e Art.32 (e nient'altro)."""
    found = []
    for path in _PRESENTATIONS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for norm in data["norms"]:
            for art in norm["articles"]:
                if has_dangling_cite(art["body"]):
                    found.append((path.stem.replace(".presentation", ""), norm["norm_id"], art["article"]))
    assert found == [
        ("Q71", "gdpr", "Art. 6"),
        ("Q71", "gdpr", "Art. 32"),
    ], f"Dangling attesi: 2 in Q71/gdpr, trovati: {found}"


def test_has_dangling_cite_basic() -> None:
    assert has_dangling_cite("testo [cite:") is True
    assert has_dangling_cite("testo [cite:ID]") is False
    assert has_dangling_cite("testo senza marker") is False


def test_e2e_original_bodies_contain_markers() -> None:
    """Verifica che i body originali abbiano marker → i test e2e non sono vacui."""
    found_any = False
    for path in _PRESENTATIONS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for norm in data["norms"]:
            for article in norm["articles"]:
                if "[cite:" in article["body"]:
                    found_any = True
                    break
    assert found_any, "Nessun marker [cite: trovato nei body originali"
