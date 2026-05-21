"""Parse EUR-Lex HTML renderings (initial OJ + consolidated templates) into tree models."""

from __future__ import annotations

import logging
import re

from lxml import html as lxml_html

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
from .xpath_queries import (
    ARTICLE_MARKER_CLASSES,
    ARTICLE_NOISE_CLASSES,
    ARTICLE_PARAGRAPH_CLASSES,
    CHAPTER_TITLE_CLASSES,
    ELI_TITLE_CLASS,
    XPATH_ARTICLE_SUBDIVISIONS,
    XPATH_ELI_MAIN_TITLE,
    XPATH_RECITALS,
    XPATH_SELF_ELI,
    XPATH_TOPLEVEL_CHAPTERS,
)

logger = logging.getLogger(__name__)


class EurLexParseError(Exception):
    """Failed to parse an EUR-Lex HTML document."""


class UnknownTemplateError(EurLexParseError):
    """The HTML contains no known template marker class."""


_WS_RE = re.compile(r"\s+")
_ARTICLE_NUM_RE = re.compile(r"Articolo\s+(\d+(?:[-\w]+)?)", re.IGNORECASE)
_CAPO_NUM_RE = re.compile(r"CAPO\s+([IVXLCDM]+)", re.IGNORECASE)
_COMMA_PREFIX_RE = re.compile(r"^\s*(\d+(?:bis|ter|quater|quinquies)?)\.\s+", re.IGNORECASE)
_RECITAL_PREFIX_RE = re.compile(r"^\s*\(\s*\d+\s*\)\s*")


def parse_articles(html_bytes: bytes, template: Template, celex: str) -> EurLexDocument:
    if template not in ARTICLE_MARKER_CLASSES:
        raise UnknownTemplateError(
            f"Unknown template {template!r}; expected one of {tuple(ARTICLE_MARKER_CLASSES)}"
        )

    try:
        root = lxml_html.fromstring(html_bytes)
    except (lxml_html.etree.ParserError, ValueError) as exc:
        raise EurLexParseError(f"HTML parse failed for CELEX {celex!r}: {exc}") from exc

    marker_class = ARTICLE_MARKER_CLASSES[template]
    if not root.xpath(f'//*[contains(concat(" ", normalize-space(@class), " "), " {marker_class} ")]'):
        # The other template's marker may have been picked up by a wrong caller.
        other = "initial" if template == "consolidated" else "consolidated"
        other_class = ARTICLE_MARKER_CLASSES[other]
        if root.xpath(f'//*[contains(concat(" ", normalize-space(@class), " "), " {other_class} ")]'):
            raise UnknownTemplateError(
                f"CELEX {celex!r}: template={template!r} but document looks like {other!r}"
            )
        raise UnknownTemplateError(
            f"CELEX {celex!r}: no known article marker class found in HTML"
        )

    logger.info("Parsing %s (%s template)", celex, template)

    article_elements = root.xpath(XPATH_ARTICLE_SUBDIVISIONS)
    articles_by_eid: dict[str, EurLexArticle] = {}
    for el in article_elements:
        article = _parse_article(el, template)
        articles_by_eid[article.eid] = article

    if not articles_by_eid:
        raise EurLexParseError(
            f"CELEX {celex!r}: no articles extracted (template misidentified?)"
        )

    chapter_elements = root.xpath(XPATH_TOPLEVEL_CHAPTERS)
    chapters: list[EurLexChapter] = []
    claimed_articles: set[str] = set()
    for ch_el in chapter_elements:
        chapter = _parse_chapter(ch_el, articles_by_eid)
        claimed_articles.update(a.eid for a in chapter.articles)
        chapters.append(chapter)

    leftover = [a for eid, a in articles_by_eid.items() if eid not in claimed_articles]
    if leftover:
        # Articles not nested under any cpt_* (rare; keep them under a synthetic root).
        chapters.append(EurLexChapter(eid="", number=None, title=None, articles=tuple(leftover)))
    if not chapters:
        chapters.append(
            EurLexChapter(eid="", number=None, title=None, articles=tuple(articles_by_eid.values()))
        )

    metadata = _extract_metadata(root, celex, template)
    annexes = _parse_annexes_if_aiact(root, celex)
    logger.info(
        "Found %d articles, %d chapters, %d annexes",
        len(articles_by_eid), len(chapters), len(annexes),
    )
    return EurLexDocument(metadata=metadata, chapters=tuple(chapters), annexes=tuple(annexes))


def _parse_annexes_if_aiact(root, celex: str) -> list[EurLexAnnex]:
    """Ad-hoc: solo l'Allegato III dell'AI Act (Reg. UE 2024/1689).

    Per ogni altro documento ritorna `[]`. Nessuna euristica generica.
    """
    if celex != "32024R1689":
        return []
    return parse_annex_iii_aiact(root)


def parse_annex_iii_aiact(root) -> list[EurLexAnnex]:
    """Estrae l'Allegato III dell'AI Act splittato per macro-punto.

    Hard-coded per la struttura HTML osservata in `32024R1689.html`:
    `<div id="anx_III">` con due `<p class="oj-doc-ti">` (header + titolo),
    un `<p class="oj-normal">` introduttivo, e 8 `<table>` figlie dirette
    (uno per ciascun macro-punto, con sotto-tabelle per le lettere).

    Ritorna una lista di 8 `EurLexAnnex`, uno per macro-punto. Granularità
    ferma al punto (non scende a lettera). Coerente con `chunk_recitals`:
    una entry per unità semantica indipendente.
    """
    candidates = root.xpath('//*[@id="anx_III"]')
    if not candidates:
        return []
    div = candidates[0]

    titles = [_clean_text(t.text_content()) for t in div.xpath('./p[@class="oj-doc-ti"]')]
    annex_title = titles[1] if len(titles) > 1 else "Sistemi di IA ad alto rischio"

    point_tables = div.findall("./table")
    out: list[EurLexAnnex] = []
    for i, t in enumerate(point_tables, start=1):
        rendered = _render_annex_table(t, indent=0)
        if not rendered:
            continue
        # Title del punto = topic prima dei ":" del primo paragrafo, cap a 60 char
        cells = t.xpath("./tbody/tr/td") or t.xpath(".//tr/td")
        body_text = ""
        if len(cells) >= 2:
            paras = cells[1].xpath("./p")
            if paras:
                body_text = _clean_text(paras[0].text_content())
        point_title = _annex_point_title(body_text, max_chars=60)
        n_letters = len(cells[1].xpath("./table")) if len(cells) >= 2 else 0

        header = f"Allegato III, punto {i}: {point_title}".rstrip(": ")
        text = f"{header}\n\n{rendered}".strip()
        out.append(EurLexAnnex(
            annex_id=f"III__point_{i}",
            title=point_title,
            text=text,
            metadata={"point": i, "n_letters": n_letters, "annex_title": annex_title},
        ))
    return out


def _annex_point_title(body_text: str, max_chars: int = 60) -> str:
    """Estrae il topic del punto: parte prima del primo ':' del primo paragrafo,
    troncata a word-boundary entro `max_chars`.
    """
    if not body_text:
        return ""
    head = body_text.split(":", 1)[0].strip()
    if len(head) <= max_chars:
        return head
    truncated = head[:max_chars]
    last_ws = truncated.rfind(" ")
    return (truncated[:last_ws] if last_ws > 0 else truncated).rstrip()


def _render_annex_table(table, indent: int) -> str:
    """Renderizza un punto (o lettera) dell'Allegato III, con eventuali sub-tables annidate.

    Struttura attesa: `<tbody><tr><td>{marker}</td><td>{body}</td></tr></tbody>`.
    `marker` = `1.`/`a)`/..., `body` = paragrafi + eventuali sub-tables (lettere).
    """
    cells = table.xpath("./tbody/tr/td") or table.xpath(".//tr/td")
    if len(cells) < 2:
        return ""
    marker = _clean_text(cells[0].text_content())
    if not marker:
        return ""

    body_cell = cells[1]
    direct_paragraphs = [
        _clean_text(p.text_content())
        for p in body_cell.xpath("./p")
    ]
    main_text = " ".join(p for p in direct_paragraphs if p)

    pad = "    " * indent
    lines = [f"{pad}{marker} {main_text}".rstrip()]

    for nested in body_cell.xpath("./table"):
        sub = _render_annex_table(nested, indent=indent + 1)
        if sub:
            lines.append(sub)

    return "\n".join(lines)


def parse_recitals(html_bytes: bytes, celex: str) -> list[EurLexRecital]:
    try:
        root = lxml_html.fromstring(html_bytes)
    except (lxml_html.etree.ParserError, ValueError) as exc:
        raise EurLexParseError(f"HTML parse failed for CELEX {celex!r}: {exc}") from exc

    elements = root.xpath(XPATH_RECITALS)
    recitals: list[EurLexRecital] = []
    for el in elements:
        eid = el.get("id") or ""
        if not eid.startswith("rct_"):
            continue
        suffix = eid[len("rct_"):]
        if not suffix.isdigit():
            continue
        number = int(suffix)
        text = _clean_text(_text_without_noise(el))
        text = _RECITAL_PREFIX_RE.sub("", text, count=1)
        recitals.append(EurLexRecital(eid=eid, number=number, text=text, celex=celex))

    logger.info("Found %d recitals", len(recitals))
    return recitals


def _parse_article(el, template: Template) -> EurLexArticle:
    eid = el.get("id", "")
    number = eid[len("art_"):] if eid.startswith("art_") else eid

    marker_class = ARTICLE_MARKER_CLASSES[template]
    marker_el = _first_child_by_class(el, marker_class)
    if marker_el is not None:
        if match := _ARTICLE_NUM_RE.search(marker_el.text_content()):
            number = match.group(1)

    rubrica_el = _first_child_by_class(el, ELI_TITLE_CLASS)
    rubrica = _clean_text(rubrica_el.text_content()) if rubrica_el is not None else None

    commi = tuple(_parse_commi(el, eid))
    return EurLexArticle(
        eid=eid, number=number, rubrica=rubrica or None, commi=commi
    )


def _parse_commi(article_el, article_eid: str):
    yielded = False
    for child in article_el.iterchildren():
        classes = (child.get("class") or "").split()
        # Skip the article number marker and the rubrica.
        if any(
            c in classes
            for c in ARTICLE_MARKER_CLASSES.values()
        ):
            continue
        if ELI_TITLE_CLASS in classes:
            continue
        # Skip inline noise (modref/footnote/signatory/doc-end).
        if ARTICLE_NOISE_CLASSES.intersection(classes):
            continue
        # `<p>` children that don't look like commi: drop.
        if child.tag == "p" and not ARTICLE_PARAGRAPH_CLASSES.intersection(classes):
            continue
        # Accept <div class="norm"> (consolidated) and unclassed <div> (initial).
        text = _clean_text(_text_without_noise(child))
        if not text:
            continue
        match = _COMMA_PREFIX_RE.match(text)
        if not match:
            continue
        number = match.group(1)
        body = text[match.end():]
        yielded = True
        yield EurLexComma(
            eid=f"{article_eid}__para_{number}",
            number=number,
            text=body,
        )

    if yielded:
        return

    # Fallback per articoli senza commi numerati (es. art_113 AI Act: paragrafi oj-normal + tabelle a/b/c).
    body_parts: list[str] = []
    for child in article_el.iterchildren():
        classes = (child.get("class") or "").split()
        if any(c in classes for c in ARTICLE_MARKER_CLASSES.values()):
            continue
        if ELI_TITLE_CLASS in classes:
            continue
        if ARTICLE_NOISE_CLASSES.intersection(classes):
            continue
        text = _clean_text(_text_without_noise(child))
        if text:
            body_parts.append(text)
    body_text = "\n\n".join(body_parts)
    if body_text:
        yield EurLexComma(
            eid=f"{article_eid}__body",
            number=None,
            text=body_text,
        )


def _parse_chapter(el, articles_by_eid: dict[str, EurLexArticle]) -> EurLexChapter:
    eid = el.get("id", "")
    first_child = el.xpath("./*[1]")
    number: str | None = None
    if first_child:
        if match := _CAPO_NUM_RE.search(first_child[0].text_content()):
            number = match.group(1)

    title: str | None = None
    for child in el.iterchildren():
        classes = (child.get("class") or "").split()
        if any(cls in classes for cls in CHAPTER_TITLE_CLASSES):
            text = _clean_text(child.text_content())
            # The label "CAPO X" itself sometimes wears `title-division-1`; ignore it.
            if number and text.upper().startswith(f"CAPO {number}"):
                continue
            if not text:
                continue
            title = text
            break

    nested_article_ids = [
        a.get("id", "")
        for a in el.xpath('.//div[starts-with(@id, "art_")]')
    ]
    seen: set[str] = set()
    chapter_articles: list[EurLexArticle] = []
    for art_id in nested_article_ids:
        if art_id in seen:
            continue
        seen.add(art_id)
        if art := articles_by_eid.get(art_id):
            chapter_articles.append(art)

    return EurLexChapter(
        eid=eid,
        number=number,
        title=title,
        articles=tuple(chapter_articles),
    )


def _extract_metadata(root, celex: str, template: Template) -> EurLexMetadata:
    title_el = root.xpath(XPATH_ELI_MAIN_TITLE)
    title = _clean_text(title_el[0].text_content()) if title_el else None

    eli: str | None = None
    for href in root.xpath(XPATH_SELF_ELI):
        # Heuristic: prefer ELI URIs that mention the digits of the celex.
        digits = "".join(c for c in celex if c.isdigit())
        if digits and digits[-4:] in href:
            eli = href
            break

    doc_type = _infer_doc_type(title)

    return EurLexMetadata(
        celex=celex,
        eli=eli,
        doc_type=doc_type,
        title=title,
        template=template,
        language="it",
    )


def _infer_doc_type(title: str | None) -> str:
    if not title:
        return ""
    upper = title.upper()
    if "REGOLAMENTO" in upper:
        return "regulation"
    if "DIRETTIVA" in upper:
        return "directive"
    if "DECISIONE" in upper:
        return "decision"
    return ""


def _first_child_by_class(el, class_name: str):
    for child in el.iterchildren():
        if class_name in (child.get("class") or "").split():
            return child
    return None


def _text_without_noise(el) -> str:
    parts: list[str] = []

    def walk(node, include_tail: bool) -> None:
        if not isinstance(node.tag, str):
            if include_tail and node.tail:
                parts.append(node.tail)
            return
        classes = (node.get("class") or "").split()
        if ARTICLE_NOISE_CLASSES.intersection(classes):
            # Skip the node entirely (text + descendants). The tail still belongs
            # to the parent's text flow and is kept.
            if include_tail and node.tail:
                parts.append(node.tail)
            return
        if node.text:
            parts.append(node.text)
        for child in node:
            walk(child, include_tail=True)
        if include_tail and node.tail:
            parts.append(node.tail)

    walk(el, include_tail=False)
    return "".join(parts)


def _clean_text(text: str) -> str:
    return _WS_RE.sub(" ", text.replace("\xa0", " ")).strip()
