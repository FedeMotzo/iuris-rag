"""Probe del parser AKN su una norma italiana — diagnostico manuale.

    python scripts/probe_norm.py "urn:nir:stato:decreto.legislativo:2024-09-04;138"

Scarica via NormattivaClient (cache: data/cache/normattiva/), parsa con `parse_akn`,
raccoglie WARNING/INFO del parser e fa una scansione XPath indipendente per evidenziare
tag strutturali che il parser ignora silenziosamente.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from core.italian_legal_parser import parse_akn  # noqa: E402
from core.italian_legal_parser.xpath_queries import NSMAP  # noqa: E402
from core.normattiva_client import NormattivaClient  # noqa: E402

CACHE_DIR = REPO_ROOT / "data" / "cache" / "normattiva"

# Strutturali che il parser non gestisce: vogliamo sapere se esistono nel file.
STRUCTURAL_TAGS = (
    "part",
    "title",
    "section",
    "subsection",
    "book",
    "tome",
    "division",
)
STRUCTURAL_PARENTS = frozenset({"body", "part", "chapter"})
PARSER_LOGGER_NAME = "core.italian_legal_parser.parser"


class _RecordCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _fetch(urn: str) -> bytes:
    client = NormattivaClient(cache_dir=CACHE_DIR)
    return client.fetch_akn(urn)


def _parse_with_log_capture(xml_bytes: bytes):
    handler = _RecordCollector()
    parser_logger = logging.getLogger(PARSER_LOGGER_NAME)
    parser_logger.addHandler(handler)
    prev_level = parser_logger.level
    parser_logger.setLevel(logging.INFO)
    try:
        doc = parse_akn(xml_bytes)
    finally:
        parser_logger.removeHandler(handler)
        parser_logger.setLevel(prev_level)
    return doc, handler.records


def _print_metadata(doc) -> None:
    md = doc.metadata
    print("[1] METADATI")
    print(f"  urn               : {md.urn}")
    print(f"  doc_type          : {md.doc_type}")
    print(f"  number            : {md.number}")
    print(f"  date_promulgation : {md.date_promulgation}")
    print(f"  date_version      : {md.date_version}")
    title = (md.title or "")
    if len(title) > 200:
        title = title[:200] + "…"
    print(f"  title             : {title}")
    print()


def _print_counts(doc, xml_bytes: bytes) -> None:
    tree = etree.fromstring(xml_bytes)
    xml_articles = tree.findall(".//akn:article", NSMAP)
    parsed_articles = [a for ch in doc.chapters for a in ch.articles]

    print("[2] CONTEGGI")
    print(f"  <article> nell'XML (XPath) : {len(xml_articles)}")
    print(f"  Articoli parsati          : {len(parsed_articles)}")
    print(f"  Chapter parsati           : {len(doc.chapters)}")
    if len(xml_articles) == len(parsed_articles):
        print("  Match                     : OK")
    else:
        delta = len(xml_articles) - len(parsed_articles)
        print(f"  Match                     : WARNING (delta={delta:+d})")
    print()


def _print_unhandled_warnings(records: list[logging.LogRecord]) -> None:
    warnings = [r for r in records if r.levelno == logging.WARNING]
    print("[3] WARNING TAG NON GESTITI")
    print(f"  Totale warning: {len(warnings)}")

    by_tag: dict[str, list[str]] = defaultdict(list)
    for r in warnings:
        msg = r.getMessage()
        tag = _tag_from_warning(msg)
        by_tag[tag].append(msg)

    if not by_tag:
        print("  (nessuno)")
        print()
        return

    for tag, msgs in sorted(by_tag.items(), key=lambda x: -len(x[1])):
        examples = " | ".join(msgs[:3])
        print(f"  - {tag}: {len(msgs)} occorrenze")
        print(f"      esempi: {examples}")
    print()


def _tag_from_warning(msg: str) -> str:
    # Format: "Unhandled AKN element under <body>: <part> eId=..."
    if "<" in msg:
        try:
            return msg.split(">: <", 1)[1].split(">", 1)[0]
        except IndexError:
            pass
    return "?"


def _print_structural_scan(xml_bytes: bytes) -> None:
    tree = etree.fromstring(xml_bytes)
    print("[4] SCANSIONE STRUTTURALE INDIPENDENTE")
    print(f"  {'tag':12} | {'totale':>6} | strutturale (figlio di body/part/chapter)")
    print(f"  {'-'*12}-+-{'-'*6}-+-{'-'*42}")
    for tag in STRUCTURAL_TAGS:
        all_occurrences = tree.findall(f".//akn:{tag}", NSMAP)
        total = len(all_occurrences)
        structural = sum(
            1
            for el in all_occurrences
            if el.getparent() is not None
            and etree.QName(el.getparent().tag).localname in STRUCTURAL_PARENTS
        )
        print(f"  {tag:12} | {total:>6} | {structural}")
    print()


def _print_abrogated(doc, records: list[logging.LogRecord]) -> None:
    articles = [a for ch in doc.chapters for a in ch.articles]
    abrogated = [a for a in articles if a.is_abrogated]
    kept_active = [
        r for r in records if r.levelno == logging.INFO and "kept active" in r.getMessage()
    ]
    print("[5] ABROGATI")
    print(f"  is_abrogated=True             : {len(abrogated)}")
    print(f"  log INFO 'kept active'        : {len(kept_active)}")
    if abrogated:
        print(f"  primi 5 abrogati              : {[a.eid for a in abrogated[:5]]}")
    if kept_active:
        ex = [_eid_from_kept_active(r.getMessage()) for r in kept_active[:5]]
        print(f"  primi 5 'kept active'         : {ex}")
    print()


def _eid_from_kept_active(msg: str) -> str:
    # Format: "art {eid}: 'abrogat' found ..."
    if msg.startswith("art "):
        return msg[4:].split(":", 1)[0]
    return msg[:40]


def _print_sample_articles(doc) -> None:
    articles = [a for ch in doc.chapters for a in ch.articles]
    if not articles:
        print("[6] ARTICOLI CAMPIONE: nessun articolo parsato")
        return
    samples = [
        ("primo", articles[0]),
        ("metà ", articles[len(articles) // 2]),
        ("ultimo", articles[-1]),
    ]
    print("[6] ARTICOLI CAMPIONE")
    for label, art in samples:
        rubrica = (art.rubrica or "").strip()
        if len(rubrica) > 80:
            rubrica = rubrica[:80] + "…"
        print(
            f"  [{label}] eid={art.eid} number={art.number!r} "
            f"abrogated={art.is_abrogated} commi={len(art.commi)}"
        )
        print(f"           rubrica={rubrica!r}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe del parser AKN su una norma italiana.")
    parser.add_argument("urn", help="URN NIR, es. 'urn:nir:stato:decreto.legislativo:2024-09-04;138'")
    args = parser.parse_args()

    print(f"=== {args.urn} — Probe Output ===\n")
    print(f"Cache dir: {CACHE_DIR}\n")

    xml_bytes = _fetch(args.urn)
    print(f"XML scaricato: {len(xml_bytes):,} bytes\n")

    doc, records = _parse_with_log_capture(xml_bytes)

    _print_metadata(doc)
    _print_counts(doc, xml_bytes)
    _print_unhandled_warnings(records)
    _print_structural_scan(xml_bytes)
    _print_abrogated(doc, records)
    _print_sample_articles(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
