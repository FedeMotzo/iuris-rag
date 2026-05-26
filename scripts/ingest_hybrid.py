"""Ingest il corpus v1 in collection ibrida dense+sparse `italian_legal_v1_hybrid`.

Crea/aggiorna `italian_legal_v1_hybrid` con named vectors:
- `dense`: bge-m3 (1024 dim, Cosine)
- `bm25`: FastEmbed `Qdrant/bm25` sparse (modifier IDF)

La collection `italian_legal_v1` (baseline settimana 2) NON viene toccata.

Uso:
    spike/.venv/bin/python scripts/ingest_hybrid.py [--reset]

Prerequisito: `docker-compose up -d qdrant` deve essere attivo.
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

from fastembed import SparseTextEmbedding  # noqa: E402
from qdrant_client import models  # noqa: E402

from core.chunking import Chunk, chunk_document, chunk_recitals  # noqa: E402
from core.embedding import BgeM3Encoder  # noqa: E402
from core.eur_lex_parser import parse_articles, parse_recitals  # noqa: E402
from core.italian_legal_parser import parse_akn  # noqa: E402
from core.vector_store import (  # noqa: E402
    COLLECTION_NAME,
    DENSE_VECTOR_NAME,
    HYBRID_COLLECTION_NAME,
    SPARSE_VECTOR_NAME,
    ensure_hybrid_collection,
    get_client,
    ingest_chunks_hybrid,
    reset_hybrid_collection,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ingest_hybrid")

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

BM25_MODEL_NAME = "Qdrant/bm25"


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


# NOTE: post-W4 (annex_III split + NIS2 art_38 split), il corpus
# ha 865 chunk. Numero verificato 2026-05-25.
EXPECTED_CHUNKS = 865


def sanity_check_baseline(client) -> None:
    """Verifica che la baseline `italian_legal_v1` sia presente e intatta (865 punti)."""
    if not client.collection_exists(COLLECTION_NAME):
        log.warning("Baseline collection %s does not exist — non blocca l'hybrid ingestion",
                    COLLECTION_NAME)
        return
    info = client.get_collection(COLLECTION_NAME)
    n = info.points_count
    log.info("Baseline %s: %d points (preserved, non toccato)", COLLECTION_NAME, n)
    if n != EXPECTED_CHUNKS:
        log.warning("Atteso %d punti nella baseline, trovati %d", EXPECTED_CHUNKS, n)


def smoke_retrieval(client, encoder: BgeM3Encoder, bm25: SparseTextEmbedding) -> None:
    """Smoke functional dei 3 modi di interrogare la collection ibrida."""
    print("\n" + "=" * 60)
    print("SMOKE RETRIEVAL — italian_legal_v1_hybrid")
    print("=" * 60)

    # 1) dense puro
    q_dense = "diritti dell'interessato GDPR"
    print(f"\n[1] DENSE only — query: {q_dense!r}")
    [dvec] = encoder.encode([q_dense], batch_size=1)
    res = client.query_points(
        collection_name=HYBRID_COLLECTION_NAME,
        query=dvec,
        using=DENSE_VECTOR_NAME,
        limit=5,
        with_payload=["chunk_id", "doc_urn"],
    )
    for i, p in enumerate(res.points, 1):
        print(f"  {i}. score={p.score:.4f}  {p.payload['chunk_id']}")

    # 2) sparse puro
    q_sparse = "art 24-bis 231"
    print(f"\n[2] SPARSE only (BM25) — query: {q_sparse!r}")
    s_emb = next(bm25.query_embed(q_sparse))
    s_vec = models.SparseVector(indices=s_emb.indices.tolist(), values=s_emb.values.tolist())
    res = client.query_points(
        collection_name=HYBRID_COLLECTION_NAME,
        query=s_vec,
        using=SPARSE_VECTOR_NAME,
        limit=5,
        with_payload=["chunk_id", "doc_urn"],
    )
    any_231 = False
    for i, p in enumerate(res.points, 1):
        is_231 = "2001-06-08/231" in p.payload.get("doc_urn", "")
        any_231 = any_231 or is_231
        mark = " ✓ 231" if is_231 else ""
        print(f"  {i}. score={p.score:.4f}  {p.payload['chunk_id']}{mark}")
    print(f"  Sanity: almeno un chunk del D.Lgs 231/2001? {'YES' if any_231 else 'NO'}")

    # 3) hybrid RRF server-side
    q_hyb = "art 35 GDPR"
    print(f"\n[3] HYBRID prefetch dense+sparse + Fusion.RRF — query: {q_hyb!r}")
    [dvec_h] = encoder.encode([q_hyb], batch_size=1)
    s_emb_h = next(bm25.query_embed(q_hyb))
    s_vec_h = models.SparseVector(
        indices=s_emb_h.indices.tolist(),
        values=s_emb_h.values.tolist(),
    )
    res = client.query_points(
        collection_name=HYBRID_COLLECTION_NAME,
        prefetch=[
            models.Prefetch(query=dvec_h, using=DENSE_VECTOR_NAME, limit=20),
            models.Prefetch(query=s_vec_h, using=SPARSE_VECTOR_NAME, limit=20),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=5,
        with_payload=["chunk_id", "doc_urn"],
    )
    for i, p in enumerate(res.points, 1):
        print(f"  {i}. rrf_score={p.score:.4f}  {p.payload['chunk_id']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset", action="store_true",
        help="Droppa `italian_legal_v1_hybrid` prima di reingestare (clean slate)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Embedding batch size (default: 8, stessa taratura della baseline)",
    )
    parser.add_argument(
        "--device", choices=["auto", "mps", "cpu"], default="auto",
        help="Device per bge-m3 (default: auto)",
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
    sanity_check_baseline(client)

    if args.reset:
        reset_hybrid_collection(client)
    else:
        ensure_hybrid_collection(client)

    device = None if args.device == "auto" else args.device
    encoder = BgeM3Encoder.get(device=device)
    log.info("Using device=%s, batch_size=%d", encoder._device, args.batch_size)

    log.info("Loading FastEmbed BM25 model: %s (CPU)", BM25_MODEL_NAME)
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL_NAME)

    n_upserted = ingest_chunks_hybrid(chunks, client, encoder, bm25, batch_size=args.batch_size)

    info = client.get_collection(HYBRID_COLLECTION_NAME)
    n_final = info.points_count
    elapsed = time.monotonic() - t_start
    log.info("Done: %d chunks upserted in %.1fs (%.2fs/chunk). Collection count: %d",
             n_upserted, elapsed, elapsed / max(n_upserted, 1), n_final)
    if n_final != EXPECTED_CHUNKS:
        log.warning("Atteso %d punti in %s, trovati %d",
                    EXPECTED_CHUNKS, HYBRID_COLLECTION_NAME, n_final)

    smoke_retrieval(client, encoder, bm25)

    return 0


if __name__ == "__main__":
    sys.exit(main())
