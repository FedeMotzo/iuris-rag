"""One-shot corpus stats for chunking strategy decisions.

Run from project root with the spike venv:
    spike/.venv/bin/python scripts/corpus_stats.py
"""

from __future__ import annotations

import json
import logging
import re
import statistics
import sys
from pathlib import Path

from lxml import etree
from lxml import html as lxml_html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.eur_lex_parser import parse_articles, parse_recitals  # noqa: E402
from core.italian_legal_parser import parse_akn  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("corpus_stats")

AKN_NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

NORMATTIVA_DIR = ROOT / "data" / "cache" / "normattiva"
EURLEX_DIR = ROOT / "data" / "cache" / "eurlex" / "IT"

NORMATTIVA_DOCS = [
    ("D.Lgs 231/2001", NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2001-06-08_231.xml"),
    ("D.Lgs 138/2024 (NIS2)", NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2024-09-04_138.xml"),
    ("L. 132/2025", NORMATTIVA_DIR / "urn_nir_stato_legge_2025-09-23_132.xml"),
]

EURLEX_ARTICLE_DOCS = [
    ("GDPR (consolidata)", EURLEX_DIR / "02016R0679-20160504.html", "consolidated", "32016R0679"),
    ("AI Act (iniziale)", EURLEX_DIR / "32024R1689.html", "initial", "32024R1689"),
]

EURLEX_RECITAL_DOCS = [
    ("GDPR (iniziale)", EURLEX_DIR / "32016R0679.html", "32016R0679"),
    ("AI Act (iniziale)", EURLEX_DIR / "32024R1689.html", "32024R1689"),
]


def _load_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained("BAAI/bge-m3")


def _count_tokens(tokenizer, text: str) -> int:
    if not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=False))


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100.0) * (len(s) - 1)))))
    return s[k]


def _dist(values: list[int]) -> dict:
    if not values:
        return {"p50": 0, "p90": 0, "p99": 0, "max": 0}
    return {
        "p50": _percentile(values, 50),
        "p90": _percentile(values, 90),
        "p99": _percentile(values, 99),
        "max": max(values),
    }


_WS_RE = re.compile(r"\s+")
_LETTER_RE = re.compile(r"(?:^|[\s\(])([a-z])\)\s", re.IGNORECASE)


def _clean(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _has_letter_list(text: str) -> bool:
    """Heuristic: at least two distinct letters in `a)` / `b)` / `c)` pattern."""
    letters = {m.group(1).lower() for m in _LETTER_RE.finditer(text or "")}
    return len(letters) >= 2


# ---------------------------------------------------------------------------
# AKN (Normattiva) processing
# ---------------------------------------------------------------------------

def _akn_article_raw_map(xml_bytes: bytes) -> dict[str, etree._Element]:
    root = etree.fromstring(xml_bytes)
    out: dict[str, etree._Element] = {}
    for el in root.iterfind(".//akn:article", AKN_NS):
        eid = el.get("eId")
        if eid:
            out[eid] = el
    return out


def _akn_article_raw_text(el: etree._Element) -> str:
    return _clean("".join(el.itertext()))


def _akn_article_has_points(el: etree._Element) -> bool:
    return el.find(".//akn:point", AKN_NS) is not None


def _akn_article_text_for_tokens(article, raw_el) -> str:
    parts: list[str] = []
    if article.rubrica:
        parts.append(article.rubrica)
    if article.commi:
        parts.extend(c.text for c in article.commi if c.text)
        return " ".join(parts)
    # Fallback for monoblock / unstructured articles.
    return _akn_article_raw_text(raw_el)


def process_akn_doc(name: str, path: Path, tokenizer):
    xml_bytes = path.read_bytes()
    doc = parse_akn(xml_bytes)
    raw_map = _akn_article_raw_map(xml_bytes)

    articles_info = []
    for chapter in doc.chapters:
        for art in chapter.articles:
            if art.is_abrogated:
                continue
            raw_el = raw_map.get(art.eid)
            if raw_el is None:
                log.warning("[%s] no raw element for %s — skipped", name, art.eid)
                continue
            full_text = _akn_article_text_for_tokens(art, raw_el)
            total_tokens = _count_tokens(tokenizer, full_text)
            comma_tokens = [_count_tokens(tokenizer, c.text) for c in art.commi if c.text]
            has_letters = _akn_article_has_points(raw_el)
            articles_info.append({
                "id": art.eid or art.number,
                "number": art.number,
                "tokens": total_tokens,
                "n_commi": len(art.commi),
                "comma_tokens": comma_tokens,
                "has_letters": has_letters,
                "is_monoblock": len(art.commi) == 0 and total_tokens > 1000,
            })
    return articles_info


# ---------------------------------------------------------------------------
# EUR-Lex processing
# ---------------------------------------------------------------------------

def _eurlex_article_raw_map(html_bytes: bytes) -> dict[str, lxml_html.HtmlElement]:
    root = lxml_html.fromstring(html_bytes)
    out: dict[str, lxml_html.HtmlElement] = {}
    for el in root.xpath('//div[starts-with(@id, "art_")]'):
        eid = el.get("id")
        if eid:
            out[eid] = el
    return out


def _eurlex_article_raw_text(el) -> str:
    return _clean(el.text_content())


def process_eurlex_articles(name: str, path: Path, template: str, celex: str, tokenizer):
    html_bytes = path.read_bytes()
    doc = parse_articles(html_bytes, template=template, celex=celex)
    raw_map = _eurlex_article_raw_map(html_bytes)

    articles_info = []
    for chapter in doc.chapters:
        for art in chapter.articles:
            raw_el = raw_map.get(art.eid)
            raw_text = _eurlex_article_raw_text(raw_el) if raw_el is not None else ""

            parts = []
            if art.rubrica:
                parts.append(art.rubrica)
            if art.commi:
                parts.extend(c.text for c in art.commi if c.text)
                full_text = " ".join(parts)
            else:
                # No structured commi parsed: fall back to the full raw block.
                full_text = raw_text or (art.rubrica or "")

            total_tokens = _count_tokens(tokenizer, full_text)
            comma_tokens = [_count_tokens(tokenizer, c.text) for c in art.commi if c.text]
            has_letters = _has_letter_list(raw_text)
            articles_info.append({
                "id": art.eid or art.number,
                "number": art.number,
                "tokens": total_tokens,
                "n_commi": len(art.commi),
                "comma_tokens": comma_tokens,
                "has_letters": has_letters,
                "is_monoblock": len(art.commi) == 0 and total_tokens > 1000,
            })
    return articles_info


def process_eurlex_recitals(name: str, path: Path, celex: str, tokenizer):
    html_bytes = path.read_bytes()
    recitals = parse_recitals(html_bytes, celex=celex)
    return [_count_tokens(tokenizer, r.text) for r in recitals]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def article_stats(doc_name: str, articles: list[dict]) -> dict:
    tokens = [a["tokens"] for a in articles]
    over_1000 = sum(1 for t in tokens if t > 1000)
    over_2000 = sum(1 for t in tokens if t > 2000)
    over_4000 = sum(1 for t in tokens if t > 4000)
    top5 = sorted(articles, key=lambda a: a["tokens"], reverse=True)[:5]
    return {
        "total": len(articles),
        "token_distribution": _dist(tokens),
        "over_1000": over_1000,
        "over_2000": over_2000,
        "over_4000": over_4000,
        "top_5_longest": [{"id": a["id"], "tokens": a["tokens"]} for a in top5],
    }


def long_article_details(doc_name: str, articles: list[dict]) -> list[dict]:
    out = []
    for a in articles:
        if a["tokens"] <= 1000:
            continue
        out.append({
            "doc": doc_name,
            "article_id": a["id"],
            "tokens": a["tokens"],
            "n_commi": a["n_commi"],
            "comma_tokens": _dist(a["comma_tokens"]) if a["comma_tokens"] else {"p50": 0, "p90": 0, "p99": 0, "max": 0},
            "has_letters": a["has_letters"],
            "is_monoblock": a["is_monoblock"],
        })
    return out


def recital_stats(tokens: list[int]) -> dict:
    return {
        "total": len(tokens),
        "token_distribution": _dist(tokens),
        "over_500": sum(1 for t in tokens if t > 500),
        "over_1000": sum(1 for t in tokens if t > 1000),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_article_table(stats: dict[str, dict]) -> None:
    print("\n## Articoli — distribuzione token per documento\n")
    print("| Documento | N. art | p50 | p90 | p99 | max | >1000 | >2000 | >4000 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, s in stats.items():
        d = s["token_distribution"]
        print(f"| {name} | {s['total']} | {d['p50']} | {d['p90']} | {d['p99']} | {d['max']} | {s['over_1000']} | {s['over_2000']} | {s['over_4000']} |")

    print("\n### Top 5 articoli più lunghi per documento\n")
    for name, s in stats.items():
        ids = ", ".join(f"{t['id']} ({t['tokens']}t)" for t in s["top_5_longest"])
        print(f"- **{name}**: {ids}")


def print_long_articles_table(details: list[dict]) -> None:
    print("\n## Articoli > 1000 token — struttura interna\n")
    if not details:
        print("_Nessun articolo > 1000 token._")
        return
    print("| Documento | Articolo | Token | N. commi | comma p50 | comma max | Lettere | Monoblocco |")
    print("|---|---|---:|---:|---:|---:|:-:|:-:|")
    details_sorted = sorted(details, key=lambda d: d["tokens"], reverse=True)
    for d in details_sorted:
        ct = d["comma_tokens"]
        print(f"| {d['doc']} | {d['article_id']} | {d['tokens']} | {d['n_commi']} | {ct['p50']} | {ct['max']} | {'sì' if d['has_letters'] else 'no'} | {'sì' if d['is_monoblock'] else 'no'} |")


def print_recital_table(stats: dict[str, dict]) -> None:
    print("\n## Considerando EUR-Lex — distribuzione token\n")
    print("| Documento | N. considerando | p50 | p90 | p99 | max | >500 | >1000 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, s in stats.items():
        d = s["token_distribution"]
        print(f"| {name} | {s['total']} | {d['p50']} | {d['p90']} | {d['p99']} | {d['max']} | {s['over_500']} | {s['over_1000']} |")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading BAAI/bge-m3 tokenizer...", file=sys.stderr)
    tokenizer = _load_tokenizer()

    all_articles: dict[str, list[dict]] = {}

    for name, path in NORMATTIVA_DOCS:
        if not path.exists():
            log.warning("Missing Normattiva file: %s", path)
            continue
        print(f"Processing AKN: {name}", file=sys.stderr)
        all_articles[name] = process_akn_doc(name, path, tokenizer)

    for name, path, template, celex in EURLEX_ARTICLE_DOCS:
        if not path.exists():
            log.warning("Missing EUR-Lex file: %s", path)
            continue
        print(f"Processing EUR-Lex articles: {name}", file=sys.stderr)
        all_articles[name] = process_eurlex_articles(name, path, template, celex, tokenizer)

    article_stats_by_doc = {name: article_stats(name, arts) for name, arts in all_articles.items()}
    long_details: list[dict] = []
    for name, arts in all_articles.items():
        long_details.extend(long_article_details(name, arts))

    recital_tokens_by_doc: dict[str, list[int]] = {}
    for name, path, celex in EURLEX_RECITAL_DOCS:
        if not path.exists():
            log.warning("Missing EUR-Lex recital file: %s", path)
            continue
        print(f"Processing EUR-Lex recitals: {name}", file=sys.stderr)
        recital_tokens_by_doc[name] = process_eurlex_recitals(name, path, celex, tokenizer)
    recital_stats_by_doc = {name: recital_stats(toks) for name, toks in recital_tokens_by_doc.items()}

    print_article_table(article_stats_by_doc)
    print_long_articles_table(long_details)
    print_recital_table(recital_stats_by_doc)

    out = {
        "articles": article_stats_by_doc,
        "long_articles_detail": long_details,
        "recitals": recital_stats_by_doc,
    }
    out_path = Path(__file__).with_name("corpus_stats_output.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nWrote {out_path.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
