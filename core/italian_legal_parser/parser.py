"""Parse an Akoma Ntoso XML document (Normattiva flavour) into an `AKNDocument` tree."""

from __future__ import annotations

import logging
import re
from datetime import date

from lxml import etree

from .models import AKNArticle, AKNChapter, AKNComma, AKNDocument, DocumentMetadata
from .xpath_queries import (
    ABROGATED_MARKER,
    AKN_NS,
    HANDLED_BODY_CHILDREN,
    HANDLED_CHAPTER_CHILDREN,
    NSMAP,
    XPATH_ARTICLES,
    XPATH_ARTICLES_ANY,
    XPATH_ATTACHMENTS,
    XPATH_BODY,
    XPATH_CHAPTERS,
    XPATH_FRBR_DATE,
    XPATH_FRBR_EXPRESSION,
    XPATH_FRBR_URI,
    XPATH_FRBR_WORK,
    XPATH_HEADING,
    XPATH_NUM,
    XPATH_PARAGRAPHS,
    XPATH_PREFACE_DOC_TITLE,
)

logger = logging.getLogger(__name__)

_URN_DOCTYPE_RE = re.compile(r"^/akn/[^/]+/act/([^/]+)/")
_URN_NUMBER_RE = re.compile(r"/act/[^/]+/[^/]+/[^/]+/([^/]+)(?:/|$)")
_ART_NUM_RE = re.compile(r"Art\.?\s*([^\s.]+)", re.IGNORECASE)


def parse_akn(xml_bytes: bytes) -> AKNDocument:
    root = etree.fromstring(xml_bytes)
    act = root.find(".//akn:act", NSMAP)
    if act is None:
        raise ValueError("akomaNtoso document has no <act> element")

    metadata = _parse_metadata(act)
    body = act.find(XPATH_BODY, NSMAP)
    if body is None:
        _log_attachments(act)
        return AKNDocument(metadata=metadata, chapters=())

    _warn_unhandled_body_children(body)
    chapters = tuple(_parse_chapter(c) for c in body.findall(XPATH_CHAPTERS, NSMAP))

    if not chapters:
        # No <chapter> structure: wrap all articles in a synthetic root chapter.
        articles = tuple(_parse_article(a) for a in body.findall(XPATH_ARTICLES, NSMAP))
        chapters = (AKNChapter(eid="", number=None, title=None, articles=articles),)

    _log_attachments(act)
    return AKNDocument(metadata=metadata, chapters=chapters)


def _log_attachments(act) -> None:
    count = len(act.findall(XPATH_ATTACHMENTS, NSMAP))
    if count == 0:
        return
    logger.info("Found %d attachments, skipped (out of scope v1)", count)


def _parse_metadata(act) -> DocumentMetadata:
    work = act.find(XPATH_FRBR_WORK, NSMAP)
    expression = act.find(XPATH_FRBR_EXPRESSION, NSMAP)

    urn = _first_xpath_value(work, XPATH_FRBR_URI) or ""
    date_promulgation = _parse_date(_first_xpath_value(work, XPATH_FRBR_DATE))
    date_version = _parse_date(_first_xpath_value(expression, XPATH_FRBR_DATE))

    doc_type = ""
    number = ""
    if urn:
        if m := _URN_DOCTYPE_RE.match(urn):
            doc_type = m.group(1)
        if m := _URN_NUMBER_RE.search(urn):
            number = m.group(1)

    title_el = act.find(XPATH_PREFACE_DOC_TITLE, NSMAP)
    title = _clean_text(_collect_text(title_el)) if title_el is not None else None

    return DocumentMetadata(
        urn=urn,
        doc_type=doc_type,
        number=number,
        date_promulgation=date_promulgation,
        date_version=date_version,
        title=title or None,
    )


def _parse_chapter(chapter_el) -> AKNChapter:
    _warn_unhandled_chapter_children(chapter_el)

    eid = chapter_el.get("eId", "")
    num_el = chapter_el.find(XPATH_NUM, NSMAP)
    heading_el = chapter_el.find(XPATH_HEADING, NSMAP)

    number = _clean_text(_collect_text(num_el)) if num_el is not None else None
    title = _clean_text(_collect_text(heading_el)) if heading_el is not None else None

    articles = tuple(_parse_article(a) for a in chapter_el.findall(XPATH_ARTICLES, NSMAP))
    return AKNChapter(eid=eid, number=number or None, title=title or None, articles=articles)


def _parse_article(article_el) -> AKNArticle:
    eid = article_el.get("eId", "")

    num_el = article_el.find(XPATH_NUM, NSMAP)
    raw_num = _clean_text(_collect_text(num_el)) if num_el is not None else ""
    number = _extract_article_number(raw_num, eid)

    heading_el = article_el.find(XPATH_HEADING, NSMAP)
    rubrica = _clean_text(_collect_text(heading_el)) if heading_el is not None else None

    commi: list[AKNComma] = []
    for para in article_el.findall(XPATH_PARAGRAPHS, NSMAP):
        para_eid = para.get("eId")
        para_num_el = para.find(XPATH_NUM, NSMAP)
        # Skip unnumbered paragraphs (typically Normattiva's `((` / `))` modification markers).
        if not para_eid or para_num_el is None:
            continue
        para_number = _clean_text(_collect_text(para_num_el)).rstrip(".")
        para_text = _clean_text(_collect_text(para))
        commi.append(AKNComma(eid=para_eid, number=para_number, text=para_text))

    is_abrogated = _detect_abrogated(article_el, eid, rubrica)

    return AKNArticle(
        eid=eid,
        number=number,
        rubrica=rubrica or None,
        commi=tuple(commi),
        is_abrogated=is_abrogated,
    )


# Strong markers (case-sensitive: Normattiva uses ALL-CAPS for repeal notices).
_HEADING_ABROGATED_MARKERS = (
    "ARTICOLO ABROGATO",
    "ABROGATO DAL",
    "ABROGATO DA",
)
_FIRST_PARAGRAPH_PREFIXES = (
    "((ARTICOLO ABROGATO",
    "(ARTICOLO ABROGATO",
    "ARTICOLO ABROGATO",
)


def _detect_abrogated(article_el, eid: str, rubrica: str | None) -> bool:
    """Mark an article as repealed only on strong, position-specific markers.

    Asymmetric cost: a false positive hides a still-active article from the
    retriever, which is much worse than a false negative (the reranker can
    handle a stray repealed article downstream). When in doubt → keep active.

    Conditions (any one is sufficient):
      (A) heading contains one of `_HEADING_ABROGATED_MARKERS` (case-sensitive).
      (B) the first <paragraph> body text starts with one of
          `_FIRST_PARAGRAPH_PREFIXES` after stripping whitespace.

    Anything else — inline mentions, ((PERIODO SOPPRESSO)) blocks, "abrogato"
    deep in a later comma, an abrogated parent chapter — keeps the article
    active. Such residual hits are emitted as INFO log lines for manual review.
    """
    if rubrica:
        for marker in _HEADING_ABROGATED_MARKERS:
            if marker in rubrica:
                return True

    first_para = article_el.find(XPATH_PARAGRAPHS, NSMAP)
    first_para_text = _clean_text(_collect_text(first_para)) if first_para is not None else ""
    stripped = first_para_text.lstrip()
    for prefix in _FIRST_PARAGRAPH_PREFIXES:
        if stripped.startswith(prefix):
            return True

    # Residual signal: "abrogat" appears somewhere in the article body but not
    # in a position we trust → flag for human review without marking.
    body_text = _collect_text(article_el)
    if ABROGATED_MARKER in body_text.upper():
        logger.info(
            "art %s: 'abrogat' found in body but not at start of first paragraph, kept active",
            eid,
        )
    return False


def _extract_article_number(raw_num: str, eid: str) -> str:
    if raw_num:
        if m := _ART_NUM_RE.search(raw_num):
            return m.group(1).rstrip(".")
        cleaned = raw_num.strip().rstrip(".")
        if cleaned:
            return cleaned
    # Fallback: derive from eId (e.g. "art_2-bis" → "2-bis").
    if eid.startswith("art_"):
        return eid[len("art_"):]
    return eid


def _warn_unhandled_body_children(body_el) -> None:
    for child in body_el:
        tag = _local_name(child)
        if tag in HANDLED_BODY_CHILDREN:
            continue
        if tag is etree.Comment or not isinstance(tag, str):
            continue
        logger.warning(
            "Unhandled AKN element under <body>: <%s> eId=%r (parent=<body>)",
            tag,
            child.get("eId"),
        )


def _warn_unhandled_chapter_children(chapter_el) -> None:
    for child in chapter_el:
        tag = _local_name(child)
        if tag in HANDLED_CHAPTER_CHILDREN:
            continue
        if not isinstance(tag, str):
            continue
        logger.warning(
            "Unhandled AKN element under <chapter>: <%s> eId=%r (parent=<chapter eId=%r>)",
            tag,
            child.get("eId"),
            chapter_el.get("eId"),
        )


def _local_name(el) -> str | None:
    if not isinstance(el.tag, str):
        return None
    return etree.QName(el.tag).localname


def _first_xpath_value(el, query: str) -> str | None:
    if el is None:
        return None
    result = el.xpath(query, namespaces=NSMAP)
    if not result:
        return None
    value = result[0]
    return value if isinstance(value, str) else str(value)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning("Unparseable FRBRdate value: %r", value)
        return None


def _collect_text(el) -> str:
    if el is None:
        return ""
    parts: list[str] = []
    for piece in el.itertext():
        if piece:
            parts.append(piece)
    return "".join(parts)


_WS_RE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()
