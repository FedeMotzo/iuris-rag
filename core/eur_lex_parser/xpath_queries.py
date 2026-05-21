"""XPath/CSS constants and template-keyed mappings for EUR-Lex HTML rendering."""

from __future__ import annotations

# Article markers: each template has a distinct class on the first child of
# the <div class="eli-subdivision" id="art_N"> wrapper.
#   consolidated: <p class="title-article-norm">Articolo N</p>
#   initial:      <p class="oj-ti-art">Articolo N</p>
ARTICLE_MARKER_CLASSES: dict[str, str] = {
    "consolidated": "title-article-norm",
    "initial": "oj-ti-art",
}

# All eli-subdivision elements whose id begins with "art_".
XPATH_ARTICLE_SUBDIVISIONS = (
    '//div[contains(concat(" ", normalize-space(@class), " "), " eli-subdivision ")]'
    '[starts-with(@id, "art_")]'
)

# Top-level chapters: <div id="cpt_X"> with no "." in the id (sub-sections are
# encoded as cpt_X.sct_Y / cpt_X.tit_Y and excluded from the chapter list).
XPATH_TOPLEVEL_CHAPTERS = '//div[starts-with(@id, "cpt_") and not(contains(@id, "."))]'

# Recitals: only present in the initial OJ template.
XPATH_RECITALS = '//div[contains(concat(" ", normalize-space(@class), " "), " eli-subdivision ")][starts-with(@id, "rct_")]'

# Document-level title (consistent across both templates).
XPATH_ELI_MAIN_TITLE = '//*[contains(concat(" ", normalize-space(@class), " "), " eli-main-title ")]'

# Self-referential ELI link in the document (used for metadata when present).
XPATH_SELF_ELI = '//a[starts-with(@href, "https://data.europa.eu/eli/")]/@href'

# Children of an <article> wrapper that carry the article rubrica.
ELI_TITLE_CLASS = "eli-title"

# Chapter title sources (the second meaningful child of cpt_X).
#   consolidated: <p class="title-division-2">
#   initial:      <div class="eli-title" id="cpt_X.tit_1">
CHAPTER_TITLE_CLASSES = ("title-division-2", "eli-title")

# Inline noise inside an article — must NOT leak into comma text.
ARTICLE_NOISE_CLASSES = frozenset({"modref", "footnote", "oj-doc-end", "oj-signatory"})

# Classes accepted as comma containers (paragraph wrappers inside an article).
# In the consolidated template they carry class="norm"; in the initial template
# they are bare <div> children without class.
ARTICLE_PARAGRAPH_CLASSES = frozenset({"norm"})
