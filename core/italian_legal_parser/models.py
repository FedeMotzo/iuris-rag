"""Immutable data model for an Akoma Ntoso document tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DocumentMetadata:
    urn: str
    doc_type: str
    number: str
    date_promulgation: date | None = None
    date_version: date | None = None
    title: str | None = None


@dataclass(frozen=True)
class AKNComma:
    eid: str
    number: str
    text: str


@dataclass(frozen=True)
class AKNArticle:
    eid: str
    number: str
    rubrica: str | None = None
    commi: tuple[AKNComma, ...] = field(default_factory=tuple)
    is_abrogated: bool = False


@dataclass(frozen=True)
class AKNChapter:
    eid: str
    number: str | None = None
    title: str | None = None
    articles: tuple[AKNArticle, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AKNDocument:
    metadata: DocumentMetadata
    chapters: tuple[AKNChapter, ...] = field(default_factory=tuple)
