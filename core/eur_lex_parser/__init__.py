"""EUR-Lex HTML rendering parser (initial OJ + consolidated templates)."""

from .models import (
    EurLexAnnex,
    EurLexArticle,
    EurLexChapter,
    EurLexComma,
    EurLexDocument,
    EurLexMetadata,
    EurLexRecital,
    Template,
)
from .parser import (
    EurLexParseError,
    UnknownTemplateError,
    parse_annex_iii_aiact,
    parse_articles,
    parse_recitals,
)

__all__ = [
    "parse_articles",
    "parse_recitals",
    "parse_annex_iii_aiact",
    "EurLexDocument",
    "EurLexMetadata",
    "EurLexChapter",
    "EurLexArticle",
    "EurLexComma",
    "EurLexRecital",
    "EurLexAnnex",
    "Template",
    "EurLexParseError",
    "UnknownTemplateError",
]
