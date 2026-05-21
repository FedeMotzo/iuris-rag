"""XPath constants and namespace map for Akoma Ntoso 3.0 (Normattiva flavour)."""

AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
NSMAP = {"akn": AKN_NS}

# Document-level metadata (FRBR blocks live under meta/identification).
# FRBRdate@name is empty in Normattiva — we select by FRBR block position, not by @name.
XPATH_FRBR_WORK = "./akn:meta/akn:identification/akn:FRBRWork"
XPATH_FRBR_EXPRESSION = "./akn:meta/akn:identification/akn:FRBRExpression"
XPATH_FRBR_URI = "./akn:FRBRuri/@value"
XPATH_FRBR_DATE = "./akn:FRBRdate/@date"
XPATH_FRBR_ALIAS_NIR = "./akn:meta/akn:identification/akn:FRBRWork/akn:FRBRalias[@name='urn:nir']/@value"

# Preface — human-readable title and document classification.
XPATH_PREFACE_DOC_TITLE = "./akn:preface//akn:docTitle"
XPATH_PREFACE_DOC_TYPE = "./akn:preface//akn:docType"
XPATH_PREFACE_DOC_NUMBER = "./akn:preface//akn:docNumber"

# Body structure.
XPATH_BODY = "./akn:body"
XPATH_ATTACHMENTS = ".//akn:attachments/akn:attachment"
XPATH_CHAPTERS = "./akn:chapter"
XPATH_ARTICLES = "./akn:article"
XPATH_ARTICLES_ANY = ".//akn:article"
XPATH_PARAGRAPHS = "./akn:paragraph"

# Article-internal fields.
XPATH_NUM = "./akn:num"
XPATH_HEADING = "./akn:heading"

# Tags handled explicitly by the parser. Anything else encountered at a
# structural position triggers a defensive warning.
HANDLED_BODY_CHILDREN = frozenset({"chapter", "article"})
HANDLED_CHAPTER_CHILDREN = frozenset({"num", "heading", "article", "chapter"})

# Heuristic marker for repealed articles (case-insensitive substring match).
ABROGATED_MARKER = "ABROGAT"
