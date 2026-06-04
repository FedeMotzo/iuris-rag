"""Output strutturato cross-norma v1.2 (step 3) — renderizzabile come collapsible.

Trasforma i gruppi mini (già normalizzati) in una struttura per-norma /
per-articolo, con grouping output-level (più mini sullo stesso articolo → una
sezione, body = concatenazione semplice), orientamento deterministico (zero LLM)
e verifica citazioni per-sezione.

La struttura è JSON-serializzabile (`to_dict`) per la UI Streamlit.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass, field

from core.citation_verifier import verify_citations

from .map_assemble import _extract_cites, _parse_article


@dataclass
class GroupView:
    """Input minimale per la presentation: una mini su un gruppo."""

    source: str          # norm_id
    sub_query: str
    body: str            # testo mini (marker già normalizzati+chiusi)
    hit_chunk_ids: list[str]
    score: float = 0.0   # best score reranker del gruppo (per ranking output)
    truncated: bool = False


@dataclass
class ArticleSection:
    article: str         # "Art. 27" / "Allegato III punto 5" / "Artt. 44-49"
    rubric: str
    body: str
    cites: list[str]
    verified: bool
    score: float = 0.0
    truncated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormSection:
    norm_id: str
    short_name: str
    articles: list[ArticleSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "norm_id": self.norm_id,
            "short_name": self.short_name,
            "articles": [a.to_dict() for a in self.articles],
        }


@dataclass
class CrossNormPresentation:
    orientation: str
    norms: list[NormSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "orientation": self.orientation,
            "norms": [n.to_dict() for n in self.norms],
        }

    @property
    def all_verified(self) -> bool:
        return all(a.verified for n in self.norms for a in n.articles)


_BODY_SEP = "\n\n"


def _norm_order(detected_norms: list[str], present_sources: list[str]) -> list[str]:
    """Norme in ordine di rilevazione; eventuali source extra appese in coda."""
    order = list(detected_norms) + [s for s in present_sources if s not in detected_norms]
    seen: set[str] = set()
    out: list[str] = []
    for s in order:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def build_presentation(
    detected_norms: list[str],
    group_views: list[GroupView],
    short_names: dict[str, str],
    orientation_label: str | None = None,
) -> CrossNormPresentation:
    """Grouping per (source, articolo) + verifica per-sezione + orientamento.

    Più mini sullo stesso (source, articolo) → UNA `ArticleSection`, body =
    concatenazione semplice (nessuna dedup fuzzy; merge map-level differito).
    Allegati: sezioni distinte (label diversa per punto → bucket distinti).
    """
    # bucket (source, label) → dati aggregati, ordine di prima comparsa
    buckets: "OrderedDict[tuple[str, str], dict]" = OrderedDict()
    for gv in group_views:
        label, rubric, sort_key = _parse_article(gv.sub_query)
        key = (gv.source, label)
        b = buckets.get(key)
        if b is None:
            buckets[key] = {
                "rubric": rubric, "bodies": [gv.body],
                "hits": list(gv.hit_chunk_ids), "sort_key": sort_key,
                "score": gv.score, "truncated": gv.truncated,
            }
        else:
            b["bodies"].append(gv.body)
            for h in gv.hit_chunk_ids:
                if h not in b["hits"]:
                    b["hits"].append(h)
            if len(rubric) > len(b["rubric"]):
                b["rubric"] = rubric
            b["score"] = max(b["score"], gv.score)
            b["truncated"] = b["truncated"] or gv.truncated

    present_sources = [s for (s, _) in buckets]
    norms: list[NormSection] = []
    for nid in _norm_order(detected_norms, present_sources):
        items = [(label, b) for (s, label), b in buckets.items() if s == nid]
        if not items:
            continue
        items.sort(key=lambda x: x[1]["sort_key"])
        articles: list[ArticleSection] = []
        for label, b in items:
            body = _BODY_SEP.join(b["bodies"])
            uni = set(b["hits"])
            vr = verify_citations(body, uni)
            articles.append(ArticleSection(
                article=label, rubric=b["rubric"], body=body,
                cites=_extract_cites(body), verified=vr.all_verified,
                score=b["score"], truncated=b["truncated"],
            ))
        norms.append(NormSection(
            norm_id=nid, short_name=short_names.get(nid, nid), articles=articles,
        ))

    orientation = _build_orientation(norms, orientation_label)
    return CrossNormPresentation(orientation=orientation, norms=norms)


_ORIENT_TOP_N = 3


def _build_orientation(norms: list[NormSection], label: str | None) -> str:
    """Template compatto deterministico: per norma → conteggio + top-3 rubriche
    (per best-score di sezione) + "…e altri N". Nessuna sintesi interpretativa."""
    head = label or f"Scenario attiva {len(norms)} norme:"
    lines = [head]
    for ns in norms:
        n = len(ns.articles)
        top = sorted(ns.articles, key=lambda a: -a.score)[:_ORIENT_TOP_N]
        items = ", ".join(
            f"{a.rubric} ({a.article})" if a.rubric else a.article for a in top
        )
        rest = n - len(top)
        tail = f", …e altri {rest}" if rest > 0 else ""
        lines.append(f"- {ns.short_name} ({n} istituti): {items}{tail}")
    return "\n".join(lines)
