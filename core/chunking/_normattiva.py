"""AKN (Normattiva) document → Chunks."""

from __future__ import annotations

import logging
import re

from core.italian_legal_parser import AKNArticle, AKNChapter, AKNComma, AKNDocument

from ._tokenizer import count_tokens
from .chunker import CHUNK_TOKEN_THRESHOLD, Chunk, greedy_group_by_threshold

logger = logging.getLogger(__name__)

_CAPO_RE = re.compile(r"^\s*CAPO\s+([IVXLCDM\d][\w-]*)", re.IGNORECASE)
_SEZIONE_RE = re.compile(r"^\s*SEZIONE\s+([IVXLCDM\d][\w-]*)", re.IGNORECASE)
_TITOLO_RE = re.compile(r"^\s*TITOLO\s+([IVXLCDM\d][\w-]*)", re.IGNORECASE)
_EMBEDDED_SEZIONE_RE = re.compile(r"\bSEZIONE\s+([IVXLCDM\d][\w-]*)", re.IGNORECASE)


def chunk_akn_document(doc: AKNDocument) -> list[Chunk]:
    doc_urn = doc.metadata.urn.lstrip("/")
    chunks: list[Chunk] = []

    current_capo: str | None = None
    current_sezione: str | None = None
    current_titolo: str | None = None

    for chapter in doc.chapters:
        capo, sezione, titolo = _resolve_chapter_labels(
            chapter, current_capo, current_sezione, current_titolo
        )
        current_capo, current_sezione, current_titolo = capo, sezione, titolo

        for article in chapter.articles:
            if article.is_abrogated:
                continue
            article_chunks = _chunk_article(
                article=article,
                doc_urn=doc_urn,
                hierarchy_prefix=[p for p in (current_titolo, current_capo, current_sezione) if p],
            )
            chunks.extend(article_chunks)

    return chunks


def _resolve_chapter_labels(
    chapter: AKNChapter,
    current_capo: str | None,
    current_sezione: str | None,
    current_titolo: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Reconstruct the (Titolo, Capo, Sezione) state after entering this chapter.

    D.Lgs 231/2001 flattens Capo and Sezione as sibling `<chapter>` nodes: a
    `num="SEZIONE II"` chapter that follows `num="Capo I"` is actually a
    sub-section of Capo I, not a sibling. We carry over the most recent Capo
    when a Sezione chapter is encountered.
    """
    num = chapter.number
    if num is None:
        if not chapter.eid:  # synthetic root inserted by the parser
            return current_capo, current_sezione, current_titolo
        logger.warning("Chapter %s has no <num>; keeping current hierarchy state", chapter.eid)
        return current_capo, current_sezione, current_titolo

    if m := _TITOLO_RE.match(num):
        # New Titolo resets Capo and Sezione.
        return current_capo, current_sezione, f"Titolo {m.group(1).upper()}"

    if m := _CAPO_RE.match(num):
        new_capo = f"Capo {m.group(1).upper()}"
        # Some Normattiva docs (231/2001) conflate "Capo I" + "Sezione I"
        # by placing the Sezione label inside the chapter heading text.
        embedded = _find_embedded_sezione(chapter.title)
        return new_capo, embedded, current_titolo

    if m := _SEZIONE_RE.match(num):
        return current_capo, f"Sezione {m.group(1).upper()}", current_titolo

    logger.warning(
        "Chapter %s: num=%r does not match Capo/Sezione/Titolo pattern; keeping state",
        chapter.eid, num,
    )
    return current_capo, current_sezione, current_titolo


def _find_embedded_sezione(title: str | None) -> str | None:
    if not title:
        return None
    m = _EMBEDDED_SEZIONE_RE.search(title)
    return f"Sezione {m.group(1).upper()}" if m else None


def _chunk_article(
    *, article: AKNArticle, doc_urn: str, hierarchy_prefix: list[str]
) -> list[Chunk]:
    article_label = f"art. {article.number}"
    hierarchy_path = [*hierarchy_prefix, article_label]
    base_metadata = {
        "article_number": article.number,
        "rubrica": article.rubrica,
    }

    article_eid = article.eid

    # Render full article text once to size it.
    full_text = _render_article_text(article, list(article.commi))
    total_tokens = count_tokens(full_text)

    if total_tokens <= CHUNK_TOKEN_THRESHOLD:
        return [Chunk(
            chunk_id=f"{doc_urn}__{article_eid}",
            text=full_text,
            source_type="normattiva",
            chunk_type="article",
            doc_urn=doc_urn,
            article_eid=article_eid,
            para_eids=[],
            hierarchy_path=hierarchy_path,
            metadata={**base_metadata, "tokens": total_tokens},
        )]

    if not article.commi:
        # Monoblocco oversize: keep as a single oversized chunk, log INFO.
        logger.info(
            "Monoblock article %s in %s: %d tokens, no commi to split",
            article_eid, doc_urn, total_tokens,
        )
        return [Chunk(
            chunk_id=f"{doc_urn}__{article_eid}",
            text=full_text,
            source_type="normattiva",
            chunk_type="article",
            doc_urn=doc_urn,
            article_eid=article_eid,
            para_eids=[],
            hierarchy_path=hierarchy_path,
            metadata={**base_metadata, "tokens": total_tokens, "oversize": True},
        )]

    logger.info(
        "Splitting article %s in %s: %d tokens across %d commi",
        article_eid, doc_urn, total_tokens, len(article.commi),
    )
    return _split_article_by_commi(
        article=article,
        doc_urn=doc_urn,
        hierarchy_path=hierarchy_path,
        base_metadata=base_metadata,
    )


def _split_article_by_commi(
    *,
    article: AKNArticle,
    doc_urn: str,
    hierarchy_path: list[str],
    base_metadata: dict,
) -> list[Chunk]:
    commi = list(article.commi)
    # Token cost of each comma as it will be rendered inside the chunk text.
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
            source_type="normattiva",
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


def _render_article_text(article: AKNArticle, commi: list[AKNComma]) -> str:
    parts: list[str] = []
    header = f"Art. {article.number}"
    if article.rubrica:
        header = f"{header} - {article.rubrica}"
    parts.append(header)
    for c in commi:
        if c.text:
            parts.append(_render_comma(c))
    return "\n\n".join(parts)


def _render_comma(c: AKNComma) -> str:
    text = c.text.strip()
    # If the parsed text already starts with the comma number, keep it as-is;
    # otherwise prepend "{n}. " for readability and consistent embedding context.
    if text.startswith(f"{c.number}.") or text.startswith(f"{c.number} "):
        return text
    return f"{c.number}. {text}"
