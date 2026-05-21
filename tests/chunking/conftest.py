"""Shared fixtures: parse the static corpus once per test session."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.eur_lex_parser import (
    EurLexDocument,
    EurLexRecital,
    parse_articles,
    parse_recitals,
)
from core.italian_legal_parser import AKNDocument, parse_akn

ROOT = Path(__file__).resolve().parents[2]
NORMATTIVA_DIR = ROOT / "data" / "cache" / "normattiva"
EURLEX_DIR = ROOT / "data" / "cache" / "eurlex" / "IT"

NORMATTIVA_FILES = {
    "dlgs_196_2003_codice_privacy": NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2003-06-30_196.xml",
    "dlgs_231_2001": NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2001-06-08_231.xml",
    "dlgs_138_2024_nis2": NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2024-09-04_138.xml",
    "l_132_2025": NORMATTIVA_DIR / "urn_nir_stato_legge_2025-09-23_132.xml",
}

EURLEX_ARTICLES = {
    "gdpr_consolidated": (EURLEX_DIR / "02016R0679-20160504.html", "consolidated", "32016R0679"),
    "ai_act_initial": (EURLEX_DIR / "32024R1689.html", "initial", "32024R1689"),
}

EURLEX_RECITALS = {
    "gdpr_initial": (EURLEX_DIR / "32016R0679.html", "32016R0679"),
    "ai_act_initial": (EURLEX_DIR / "32024R1689.html", "32024R1689"),
}


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"Corpus file missing: {path}")
    return path


@pytest.fixture(scope="session")
def akn_docs() -> dict[str, AKNDocument]:
    out: dict[str, AKNDocument] = {}
    for key, path in NORMATTIVA_FILES.items():
        out[key] = parse_akn(_require(path).read_bytes())
    return out


@pytest.fixture(scope="session")
def eurlex_article_docs() -> dict[str, EurLexDocument]:
    out: dict[str, EurLexDocument] = {}
    for key, (path, template, celex) in EURLEX_ARTICLES.items():
        out[key] = parse_articles(_require(path).read_bytes(), template=template, celex=celex)
    return out


@pytest.fixture(scope="session")
def eurlex_recitals() -> dict[str, list[EurLexRecital]]:
    out: dict[str, list[EurLexRecital]] = {}
    for key, (path, celex) in EURLEX_RECITALS.items():
        out[key] = parse_recitals(_require(path).read_bytes(), celex=celex)
    return out
