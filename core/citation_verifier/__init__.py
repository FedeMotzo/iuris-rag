"""Citation verifier deterministico — validazione strutturale dei marker
`[cite:CHUNK_ID]` contro il contesto retrieval. No LLM."""

from .models import CitationMarker, VerificationResult
from .verifier import CITE_PATTERN, verify_citations

__all__ = [
    "CITE_PATTERN",
    "CitationMarker",
    "VerificationResult",
    "verify_citations",
]
