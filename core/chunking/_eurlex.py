"""EUR-Lex document → Chunks (articles + recitals)."""

from __future__ import annotations

import logging
import re

from core.eur_lex_parser import (
    EurLexAnnex,
    EurLexArticle,
    EurLexComma,
    EurLexDocument,
    EurLexRecital,
)

from ._tokenizer import count_tokens
from .chunker import CHUNK_TOKEN_THRESHOLD, Chunk, greedy_group_by_threshold

logger = logging.getLogger(__name__)

_CELEX_RE = re.compile(r"^3(\d{4})([A-Z])(\d{4})$")
_TYPE_MAP = {"R": "reg", "L": "dir", "D": "dec"}


def chunk_eurlex_document(doc: EurLexDocument) -> list[Chunk]:
    doc_urn = _celex_to_doc_urn(doc.metadata.celex)
    chunks: list[Chunk] = []

    for chapter in doc.chapters:
        chapter_label = _chapter_label(chapter.number, chapter.title)
        for article in chapter.articles:
            article_chunks = _chunk_article(
                article=article,
                doc_urn=doc_urn,
                hierarchy_prefix=[chapter_label] if chapter_label else [],
            )
            chunks.extend(article_chunks)

    for annex in doc.annexes:
        chunks.append(_make_annex_chunk(annex, doc_urn))

    return chunks


def _make_annex_chunk(annex: EurLexAnnex, doc_urn: str) -> Chunk:
    tokens = count_tokens(annex.text)
    if tokens > CHUNK_TOKEN_THRESHOLD:
        logger.warning(
            "Annex %s in %s: %d tokens > threshold %d, kept whole (no per-letter split)",
            annex.annex_id, doc_urn, tokens, CHUNK_TOKEN_THRESHOLD,
        )
    # hierarchy a 2 livelli per annex splittati per punto (es. "III__point_4"):
    # livello 1 = allegato intero, livello 2 = singolo punto.
    if "__point_" in annex.annex_id:
        root_id = annex.annex_id.split("__point_", 1)[0]
        root_title = annex.metadata.get("annex_title", annex.title)
        hierarchy = [
            f"Allegato {root_id} - {root_title}",
            f"Allegato {root_id}, punto {annex.metadata.get('point')}: {annex.title}".rstrip(": "),
        ]
    else:
        hierarchy = [f"Allegato {annex.annex_id} - {annex.title}"]
    return Chunk(
        chunk_id=f"{doc_urn}__annex_{annex.annex_id}",
        text=annex.text,
        source_type="eurlex",
        chunk_type="annex",
        doc_urn=doc_urn,
        article_eid=f"annex_{annex.annex_id}",
        para_eids=[],
        hierarchy_path=hierarchy,
        metadata={"annex_id": annex.annex_id, "tokens": tokens, **annex.metadata},
    )


def chunk_eurlex_recitals(recitals: list[EurLexRecital]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for r in recitals:
        doc_urn = _celex_to_doc_urn(r.celex)
        text = f"Considerando {r.number}\n\n{r.text}"
        tokens = count_tokens(text)
        if tokens > CHUNK_TOKEN_THRESHOLD:
            logger.info(
                "Oversized recital %d (%s): %d tokens", r.number, r.celex, tokens,
            )
        chunks.append(Chunk(
            chunk_id=f"{doc_urn}__recital_{r.number}",
            text=text,
            source_type="eurlex",
            chunk_type="recital",
            doc_urn=doc_urn,
            article_eid=None,
            para_eids=[],
            hierarchy_path=[f"Considerando {r.number}"],
            metadata={"recital_number": r.number, "tokens": tokens},
        ))
    return chunks


def _chunk_article(
    *, article: EurLexArticle, doc_urn: str, hierarchy_prefix: list[str]
) -> list[Chunk]:
    article_label = f"art. {article.number}"
    hierarchy_path = [*hierarchy_prefix, article_label]
    base_metadata = {
        "article_number": article.number,
        "rubrica": article.rubrica,
    }

    full_text = _render_article_text(article, list(article.commi))
    total_tokens = count_tokens(full_text)

    if total_tokens <= CHUNK_TOKEN_THRESHOLD:
        return [Chunk(
            chunk_id=f"{doc_urn}__{article.eid}",
            text=full_text,
            source_type="eurlex",
            chunk_type="article",
            doc_urn=doc_urn,
            article_eid=article.eid,
            para_eids=[],
            hierarchy_path=hierarchy_path,
            metadata={**base_metadata, "tokens": total_tokens},
        )]

    # Monoblock: nessun comma numerato estratto (anche col fallback "__body"
    # singolo: niente da splittare, l'unica unità è il body intero).
    is_fallback_body = (
        len(article.commi) == 1 and article.commi[0].number is None
    )
    if not article.commi or is_fallback_body:
        logger.info(
            "Monoblock article %s in %s: %d tokens, no commi to split",
            article.eid, doc_urn, total_tokens,
        )
        return [Chunk(
            chunk_id=f"{doc_urn}__{article.eid}",
            text=full_text,
            source_type="eurlex",
            chunk_type="article",
            doc_urn=doc_urn,
            article_eid=article.eid,
            para_eids=[],
            hierarchy_path=hierarchy_path,
            metadata={**base_metadata, "tokens": total_tokens, "oversize": True},
        )]

    logger.info(
        "Splitting article %s in %s: %d tokens across %d commi",
        article.eid, doc_urn, total_tokens, len(article.commi),
    )
    return _split_article_by_commi(
        article=article,
        doc_urn=doc_urn,
        hierarchy_path=hierarchy_path,
        base_metadata=base_metadata,
    )


def _split_article_by_commi(
    *,
    article: EurLexArticle,
    doc_urn: str,
    hierarchy_path: list[str],
    base_metadata: dict,
) -> list[Chunk]:
    commi = list(article.commi)
    rendered = [_render_comma(c) for c in commi]
    per_comma_tokens = [count_tokens(t) for t in rendered]

    groups = greedy_group_by_threshold(
        list(zip(rendered, per_comma_tokens, strict=True)),
        threshold=CHUNK_TOKEN_THRESHOLD,
    )

    chunks: list[Chunk] = []
    for gi, idx_group in enumerate(groups):
        sub_commi = [commi[i] for i in idx_group]
        text = _render_article_text(article, sub_commi)
        tokens = count_tokens(text)
        first_num, last_num = sub_commi[0].number, sub_commi[-1].number
        chunk_id = f"{doc_urn}__{article.eid}__paras_{first_num}_{last_num}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            text=text,
            source_type="eurlex",
            chunk_type="article_group",
            doc_urn=doc_urn,
            article_eid=article.eid,
            para_eids=[c.eid for c in sub_commi],
            hierarchy_path=hierarchy_path,
            metadata={
                **base_metadata,
                "tokens": tokens,
                "group_index": gi,
                "group_count": len(groups),
                "first_comma": first_num,
                "last_comma": last_num,
            },
        ))
    return chunks


def _render_article_text(article: EurLexArticle, commi: list[EurLexComma]) -> str:
    parts: list[str] = []
    header = f"Articolo {article.number}"
    if article.rubrica:
        header = f"{header} - {article.rubrica}"
    parts.append(header)
    for c in commi:
        if c.text:
            parts.append(_render_comma(c))
    return "\n\n".join(parts)


def _render_comma(c: EurLexComma) -> str:
    text = c.text.strip()
    if c.number is None:
        return text
    if text.startswith(f"{c.number}.") or text.startswith(f"{c.number} "):
        return text
    return f"{c.number}. {text}"


def _chapter_label(number: str | None, title: str | None) -> str | None:
    if not number and not title:
        return None
    if number and title:
        return f"Capo {number} - {title}"
    if number:
        return f"Capo {number}"
    return title


def _celex_to_doc_urn(celex: str) -> str:
    m = _CELEX_RE.match(celex)
    if not m:
        return f"celex/{celex}"
    year, letter, number = m.group(1), m.group(2), m.group(3)
    doc_type = _TYPE_MAP.get(letter, letter.lower())
    return f"eli/{doc_type}/{year}/{int(number)}/oj"
