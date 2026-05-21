"""Ingest il corpus v1 in Qdrant.

Uso:
    spike/.venv/bin/python scripts/ingest_corpus.py [--reset]

Prerequisito: `docker-compose up -d qdrant` deve essere stato lanciato prima.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.chunking import Chunk, chunk_document, chunk_recitals  # noqa: E402
from core.embedding import BgeM3Encoder  # noqa: E402
from core.eur_lex_parser import parse_articles, parse_recitals  # noqa: E402
from core.italian_legal_parser import parse_akn  # noqa: E402
from core.vector_store import (  # noqa: E402
    ensure_collection,
    get_client,
    ingest_chunks,
    reset_collection,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ingest_corpus")

NORMATTIVA_DIR = ROOT / "data" / "cache" / "normattiva"
EURLEX_DIR = ROOT / "data" / "cache" / "eurlex" / "IT"

NORMATTIVA_FILES = [
    NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2003-06-30_196.xml",
    NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2001-06-08_231.xml",
    NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2024-09-04_138.xml",
    NORMATTIVA_DIR / "urn_nir_stato_legge_2025-09-23_132.xml",
]

EURLEX_ARTICLE_FILES = [
    (EURLEX_DIR / "02016R0679-20160504.html", "consolidated", "32016R0679"),
    (EURLEX_DIR / "32024R1689.html", "initial", "32024R1689"),
]

EURLEX_RECITAL_FILES = [
    (EURLEX_DIR / "32016R0679.html", "32016R0679"),
    (EURLEX_DIR / "32024R1689.html", "32024R1689"),
]


def load_all_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []

    for path in NORMATTIVA_FILES:
        if not path.exists():
            log.warning("Missing Normattiva file: %s", path)
            continue
        log.info("Parsing AKN: %s", path.name)
        doc = parse_akn(path.read_bytes())
        chunks.extend(chunk_document(doc))

    for path, template, celex in EURLEX_ARTICLE_FILES:
        if not path.exists():
            log.warning("Missing EUR-Lex article file: %s", path)
            continue
        log.info("Parsing EUR-Lex articles: %s (%s)", path.name, template)
        doc = parse_articles(path.read_bytes(), template=template, celex=celex)
        chunks.extend(chunk_document(doc))

    for path, celex in EURLEX_RECITAL_FILES:
        if not path.exists():
            log.warning("Missing EUR-Lex recital file: %s", path)
            continue
        log.info("Parsing EUR-Lex recitals: %s", path.name)
        recitals = parse_recitals(path.read_bytes(), celex=celex)
        chunks.extend(chunk_recitals(recitals))

    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset", action="store_true",
        help="Droppa la collection prima di reingestare (clean slate)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Embedding batch size (default: 8; lower if MPS OOM)",
    )
    parser.add_argument(
        "--device", choices=["auto", "mps", "cpu"], default="auto",
        help="Device per bge-m3 (default: auto = MPS se disponibile, altrimenti CPU)",
    )
    args = parser.parse_args()

    t_start = time.monotonic()

    chunks = load_all_chunks()
    log.info("Loaded %d chunks from corpus v1", len(chunks))

    by_source = Counter(c.source_type for c in chunks)
    by_type = Counter(c.chunk_type for c in chunks)
    log.info("By source_type: %s", dict(by_source))
    log.info("By chunk_type: %s", dict(by_type))

    client = get_client()
    if args.reset:
        reset_collection(client)
    else:
        ensure_collection(client)

    device = None if args.device == "auto" else args.device
    encoder = BgeM3Encoder.get(device=device)
    log.info("Using device=%s, batch_size=%d", encoder._device, args.batch_size)
    n_upserted = ingest_chunks(chunks, client, encoder, batch_size=args.batch_size)

    elapsed = time.monotonic() - t_start
    log.info("Done: %d chunks upserted in %.1fs (%.2fs/chunk)",
             n_upserted, elapsed, elapsed / max(n_upserted, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
