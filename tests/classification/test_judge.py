"""Unit test del giudizio a insieme chiuso: parse + validazione (DoD a).

Include la decomposizione dell'art. 5 in 8 pratiche vietate (a-h).
Nessun LLM, nessun Qdrant.
"""

from __future__ import annotations

import json

import pytest

from core.classification.judge import (
    FIXED_SET_CHUNK_IDS,
    PROHIBITED_PRACTICES,
    parse_judgment,
    validate_judgment,
)

URN = "eli/reg/2024/1689/oj"
P4 = f"{URN}__annex_III__point_4"
ART5 = f"{URN}__art_5__paras_1_3"


def _practices(*, f_applies=False, f_cite=None):
    out = []
    for k, _label in PROHIBITED_PRACTICES:
        if k == "f" and f_applies:
            out.append({"practice": "f", "applies": True,
                        "reason": "inferenza emozioni sul lavoro", "cite": f_cite})
        else:
            out.append({"practice": k, "applies": False, "reason": "no", "cite": None})
    return out


def _full_judgment_dict(*, p4_applies=False, p4_cite=None,
                        f_applies=False, f_cite=None, art6_1=False, art6_3=False):
    annex = [{"point": n, "applies": False, "reason": f"p{n}", "cite": None}
             for n in range(1, 9)]
    if p4_applies:
        annex[3] = {"point": 4, "applies": True, "reason": "occupazione", "cite": p4_cite}
    return {
        "annex_iii": annex,
        "prohibited_practices": _practices(f_applies=f_applies, f_cite=f_cite),
        "art6_1_safety_component": {"plausible": art6_1, "reason": "mdr"},
        "art6_3_exception": {"plausible": art6_3, "reason": "deroga"},
    }


# --------------------------------------------------------------------------- #
# parse_judgment
# --------------------------------------------------------------------------- #

def test_parse_clean_json_8_annex_8_practices():
    j = parse_judgment(json.dumps(_full_judgment_dict(p4_applies=True, p4_cite=P4)))
    assert len(j.annex_iii) == 8
    assert len(j.prohibited_practices) == 8
    assert [p.practice for p in j.prohibited_practices] == list("abcdefgh")
    assert j.annex_iii[3].applies is True


def test_parse_practice_f_applies():
    j = parse_judgment(json.dumps(_full_judgment_dict(f_applies=True, f_cite=ART5)))
    pf = next(p for p in j.prohibited_practices if p.practice == "f")
    assert pf.applies is True and pf.cite == ART5
    assert "emozioni" in pf.label.lower()


def test_parse_dirty_json_with_fence_and_prose():
    raw = ("Ecco:\n```json\n" + json.dumps(_full_judgment_dict(art6_1=True)) + "\n```\nfine.")
    j = parse_judgment(raw)
    assert j.art6_1_safety_component.plausible is True
    assert len(j.prohibited_practices) == 8


def test_parse_fills_missing_practices():
    d = _full_judgment_dict()
    d["prohibited_practices"] = [d["prohibited_practices"][0]]  # solo "a"
    j = parse_judgment(json.dumps(d))
    assert len(j.prohibited_practices) == 8
    assert all(not p.applies for p in j.prohibited_practices)


def test_parse_invalid_raises():
    with pytest.raises((ValueError, json.JSONDecodeError)):
        parse_judgment("non c'è nessun json qui")


# --------------------------------------------------------------------------- #
# validate_judgment — verifica per appartenenza
# --------------------------------------------------------------------------- #

def test_validate_practice_keeps_valid_cite():
    j = parse_judgment(json.dumps(_full_judgment_dict(f_applies=True, f_cite=ART5)))
    validate_judgment(j, set(FIXED_SET_CHUNK_IDS))
    assert j.prohibited
    assert [p.practice for p in j.applied_practices()] == ["f"]


def test_validate_practice_drops_invalid_cite():
    j = parse_judgment(json.dumps(_full_judgment_dict(f_applies=True, f_cite="urn:fake")))
    validate_judgment(j, set(FIXED_SET_CHUNK_IDS))
    assert j.prohibited is False


def test_validate_practice_drops_null_cite():
    j = parse_judgment(json.dumps(_full_judgment_dict(f_applies=True, f_cite=None)))
    validate_judgment(j, set(FIXED_SET_CHUNK_IDS))
    assert j.prohibited is False


def test_validate_annex_membership_unchanged():
    j = parse_judgment(json.dumps(_full_judgment_dict(p4_applies=True, p4_cite=P4)))
    validate_judgment(j, set(FIXED_SET_CHUNK_IDS))
    assert j.high_risk_annex is True


def test_fixed_set_and_practice_count():
    assert len(FIXED_SET_CHUNK_IDS) == 11
    assert len(PROHIBITED_PRACTICES) == 8
    assert ART5 in FIXED_SET_CHUNK_IDS
