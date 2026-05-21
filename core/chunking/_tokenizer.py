"""Cached `BAAI/bge-m3` tokenizer used to enforce the chunk token budget."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_tokenizer():
    from transformers import AutoTokenizer  # lazy import: heavy dependency
    return AutoTokenizer.from_pretrained("BAAI/bge-m3")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(get_tokenizer().encode(text, add_special_tokens=False))
