"""Test output strutturato cross-norma (presentation): grouping, struttura,
orientamento, verifica per-sezione. Zero LLM."""

from __future__ import annotations

import json

from core.cross_norm.presentation import (
    ArticleSection,
    CrossNormPresentation,
    GroupView,
    build_presentation,
)

_AI = "eli/reg/2024/1689/oj"
_GD = "eli/reg/2016/679/oj"
_NIS = "akn/it/act/decreto_legislativo/stato/2024-09-04/138"
_SHORT = {"gdpr": "GDPR", "ai_act": "AI Act", "nis2": "NIS2"}


def _gv(source, sub_query, body, hits, score=0.0, truncated=False):
    return GroupView(source=source, sub_query=sub_query, body=body,
                     hit_chunk_ids=hits, score=score, truncated=truncated)


# ----------------------------------------------------------- grouping per articolo

def test_grouping_merges_same_article() -> None:
    """3 mini su NIS2 art_24 → UNA ArticleSection, body concatenato."""
    gvs = [
        _gv("nis2", "Misure di gestione del rischio ex art. 24 D.Lgs 138/2024: x.",
            f"Analisi del rischio [cite:{_NIS}__art_24].", [f"{_NIS}__art_24"]),
        _gv("nis2", "Sicurezza supply chain ex art. 24 comma 2 lett. d D.Lgs 138/2024: y.",
            f"Catena di approvvigionamento [cite:{_NIS}__art_24].", [f"{_NIS}__art_24"]),
        _gv("nis2", "Continuità operativa ex art. 24 comma 2 lett. c D.Lgs 138/2024: z.",
            f"Backup e disaster recovery [cite:{_NIS}__art_24].", [f"{_NIS}__art_24"]),
    ]
    pres = build_presentation(["nis2"], gvs, _SHORT)
    assert len(pres.norms) == 1
    arts = pres.norms[0].articles
    assert len(arts) == 1                       # 3 mini → 1 sezione
    assert arts[0].article == "Art. 24"
    assert arts[0].body.count("[cite:") == 3    # concatenazione, niente dedup
    assert "Analisi del rischio" in arts[0].body and "Backup" in arts[0].body


def test_annex_sections_stay_distinct() -> None:
    gvs = [
        _gv("ai_act", "Allegato III punto 5 AI Act: servizi essenziali.",
            f"[cite:{_AI}__annex_III__point_5].", [f"{_AI}__annex_III__point_5"]),
        _gv("ai_act", "Allegato III punto 6 AI Act: contrasto.",
            f"[cite:{_AI}__annex_III__point_6].", [f"{_AI}__annex_III__point_6"]),
    ]
    pres = build_presentation(["ai_act"], gvs, _SHORT)
    labels = [a.article for a in pres.norms[0].articles]
    assert labels == ["Allegato III punto 5", "Allegato III punto 6"]


def test_article_and_norm_ordering() -> None:
    gvs = [
        _gv("ai_act", "FRIA ex art. 27 AI Act: x.", f"[cite:{_AI}__art_27].", [f"{_AI}__art_27"]),
        _gv("gdpr", "DPIA ex art. 35 GDPR: y.", f"[cite:{_GD}__art_35].", [f"{_GD}__art_35"]),
        _gv("ai_act", "Classificazione ex art. 6 AI Act: z.", f"[cite:{_AI}__art_6].", [f"{_AI}__art_6"]),
    ]
    pres = build_presentation(["gdpr", "ai_act"], gvs, _SHORT)   # ordine rilevazione: gdpr, ai_act
    assert [n.norm_id for n in pres.norms] == ["gdpr", "ai_act"]
    assert [a.article for a in pres.norms[1].articles] == ["Art. 6", "Art. 27"]


# ----------------------------------------------------------- verifica per-sezione

def test_per_section_verified_true_and_false() -> None:
    gvs = [
        _gv("gdpr", "DPIA ex art. 35 GDPR: x.",
            f"Obbligatoria [cite:{_GD}__art_35].", [f"{_GD}__art_35"]),   # ok
        _gv("ai_act", "FRIA ex art. 27 AI Act: y.",
            f"Vedi [cite:{_AI}__art_99].", [f"{_AI}__art_27"]),           # cita fuori universo
    ]
    pres = build_presentation(["gdpr", "ai_act"], gvs, _SHORT)
    by = {(n.norm_id, a.article): a for n in pres.norms for a in n.articles}
    assert by[("gdpr", "Art. 35")].verified is True
    assert by[("ai_act", "Art. 27")].verified is False
    assert pres.all_verified is False


# ----------------------------------------------------------- orientamento

def test_orientation_template_deterministic() -> None:
    gvs = [
        _gv("gdpr", "DPIA ex art. 35 GDPR: x.", f"[cite:{_GD}__art_35].", [f"{_GD}__art_35"]),
        _gv("ai_act", "FRIA ex art. 27 AI Act: y.", f"[cite:{_AI}__art_27].", [f"{_AI}__art_27"]),
    ]
    pres = build_presentation(["gdpr", "ai_act"], gvs, _SHORT)
    o = pres.orientation
    assert o.startswith("Scenario attiva 2 norme:")
    assert "- GDPR (1 istituti):" in o and "(Art. 35)" in o
    assert "- AI Act (1 istituti):" in o and "(Art. 27)" in o


def test_orientation_compact_top3_and_rest() -> None:
    # 5 articoli GDPR con score crescente → top-3 per score + "…e altri 2"
    gvs = [
        _gv("gdpr", f"R ex art. {n} GDPR: x.", f"[cite:{_GD}__art_{n}].",
            [f"{_GD}__art_{n}"], score=s)
        for n, s in [(5, 0.1), (6, 0.9), (9, 0.8), (32, 0.7), (35, 0.2)]
    ]
    pres = build_presentation(["gdpr"], gvs, _SHORT)
    o = pres.orientation
    assert "- GDPR (5 istituti):" in o
    assert "…e altri 2" in o
    # i top-3 per score sono art 6, 9, 32 (0.9/0.8/0.7), non 5/35
    assert "(Art. 6)" in o and "(Art. 9)" in o and "(Art. 32)" in o
    assert "(Art. 5)" not in o and "(Art. 35)" not in o


def test_truncated_propagates_to_article_section() -> None:
    gvs = [_gv("gdpr", "DPIA ex art. 35 GDPR: x.", f"[cite:{_GD}__art_35].",
               [f"{_GD}__art_35"], truncated=True)]
    pres = build_presentation(["gdpr"], gvs, _SHORT)
    assert pres.norms[0].articles[0].truncated is True


# ----------------------------------------------------------- serializzazione

def test_to_dict_json_serializable() -> None:
    gvs = [_gv("gdpr", "DPIA ex art. 35 GDPR: x.", f"[cite:{_GD}__art_35].", [f"{_GD}__art_35"])]
    pres = build_presentation(["gdpr"], gvs, _SHORT)
    d = pres.to_dict()
    s = json.dumps(d, ensure_ascii=False)           # non deve sollevare
    d2 = json.loads(s)
    assert d2["norms"][0]["articles"][0]["article"] == "Art. 35"
    assert set(d2.keys()) == {"orientation", "norms"}
    assert set(d2["norms"][0]["articles"][0].keys()) == {
        "article", "rubric", "body", "cites", "verified", "score", "truncated",
    }