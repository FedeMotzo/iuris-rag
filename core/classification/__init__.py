"""Intake di classificazione UC1 (single-norm AI Act).

Entry di produzione: `RAGPipeline.classify()` (vedi core/serving/pipeline.py).
Flusso: set fisso → giudizio per-candidato (insieme chiuso) → card; il dossier
obblighi (sez. 4) è gated su high_risk.
"""

from .builder import build_classification_card
from .judge import (
    FIXED_SET_CHUNK_IDS,
    judge_classification,
    parse_judgment,
    validate_judgment,
)
from .obligations_data import (
    DEFAULT_ROLE,
    VALID_ROLES,
    get_obligations,
)
from .models import (
    ART6_1_SAFETY_LIMIT,
    DISCLAIMER_DEFAULT,
    AnnexJudgment,
    ClassificationCard,
    ClassificationJudgment,
    ClassificationResult,
    ObligationItem,
    PlausibilityJudgment,
    ProhibitedPracticeJudgment,
)

__all__ = [
    "ART6_1_SAFETY_LIMIT",
    "DEFAULT_ROLE",
    "DISCLAIMER_DEFAULT",
    "FIXED_SET_CHUNK_IDS",
    "VALID_ROLES",
    "get_obligations",
    "AnnexJudgment",
    "ClassificationCard",
    "ClassificationJudgment",
    "ClassificationResult",
    "ObligationItem",
    "PlausibilityJudgment",
    "ProhibitedPracticeJudgment",
    "build_classification_card",
    "judge_classification",
    "parse_judgment",
    "validate_judgment",
]
