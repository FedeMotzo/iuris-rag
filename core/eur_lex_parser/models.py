"""Immutable data model for an EUR-Lex HTML rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Template = Literal["initial", "consolidated"]


@dataclass(frozen=True)
class EurLexMetadata:
    celex: str
    eli: str | None = None
    doc_type: str = ""
    title: str | None = None
    template: Template = "consolidated"
    language: str = "it"


@dataclass(frozen=True)
class EurLexComma:
    eid: str
    number: str | None
    text: str


@dataclass(frozen=True)
class EurLexArticle:
    eid: str
    number: str
    rubrica: str | None = None
    commi: tuple[EurLexComma, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EurLexChapter:
    eid: str
    number: str | None = None
    title: str | None = None
    articles: tuple[EurLexArticle, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EurLexAnnex:
    """Annesso di un atto EUR-Lex. In v1 popolato solo per Allegato III dell'AI Act."""

    annex_id: str  # numero romano, es. "III"
    title: str    # es. "Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2"
    text: str     # testo completo rerendered, con punti e sotto-lettere
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EurLexDocument:
    metadata: EurLexMetadata
    chapters: tuple[EurLexChapter, ...] = field(default_factory=tuple)
    annexes: tuple[EurLexAnnex, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EurLexRecital:
    eid: str
    number: int
    text: str
    celex: str
