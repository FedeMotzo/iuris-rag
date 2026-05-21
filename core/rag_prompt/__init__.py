"""Costruzione prompt RAG (system + user) per la pipeline serving W5."""

from .builder import build_user_prompt
from .templates import (
    CHUNK_END_MARKER,
    CHUNK_HEADER_FMT,
    CHUNK_HEADER_TEXT_SEP,
    CHUNK_SEP,
    HIERARCHY_JOIN,
    load_system_prompt,
)

__all__ = [
    "CHUNK_END_MARKER",
    "CHUNK_HEADER_FMT",
    "CHUNK_HEADER_TEXT_SEP",
    "CHUNK_SEP",
    "HIERARCHY_JOIN",
    "build_user_prompt",
    "load_system_prompt",
]
