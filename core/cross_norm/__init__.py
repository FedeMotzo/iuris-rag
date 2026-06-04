"""Cross-norm retrieval v1.2 — trigger + sub-query LLM + gruppi per-sub-query."""

from .multi_norm_trigger import detect_norms
from .presentation import (
    ArticleSection,
    CrossNormPresentation,
    GroupView,
    NormSection,
    build_presentation,
)
from .retriever import CrossNormResult, CrossNormRetriever, SubQueryGroup
from .subquery_generator import generate_subquery

__all__ = [
    "ArticleSection",
    "CrossNormPresentation",
    "CrossNormResult",
    "CrossNormRetriever",
    "GroupView",
    "NormSection",
    "SubQueryGroup",
    "build_presentation",
    "detect_norms",
    "generate_subquery",
]
