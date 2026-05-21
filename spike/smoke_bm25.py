"""Smoke test BM25 nativo Qdrant (FastEmbed Qdrant/bm25) — settimana 3.

Crea una collection temporanea `italian_legal_v1_smoke` con SOLO sparse
vector BM25, ingerisce gli stessi 858 chunk del corpus v1, esegue 4 query
smoke e droppa la collection.

Uso:
    spike/.venv/bin/python spike/smoke_bm25.py

Prerequisito: `docker-compose up -d qdrant` deve essere attivo.
"""

from __future__ import annotations

import logging
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastembed import SparseTextEmbedding  # noqa: E402
from qdrant_client import QdrantClient, models  # noqa: E402

from core.chunking import Chunk, chunk_document, chunk_recitals  # noqa: E402
from core.eur_lex_parser import parse_articles, parse_recitals  # noqa: E402
from core.italian_legal_parser import parse_akn  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("smoke_bm25")

SMOKE_COLLECTION = "italian_legal_v1_smoke"
SPARSE_VECTOR_NAME = "bm25"
BM25_MODEL_NAME = "Qdrant/bm25"

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


def chunk_id_to_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, chunk_id))


def chunk_to_payload(chunk: Chunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "source_type": chunk.source_type,
        "chunk_type": chunk.chunk_type,
        "doc_urn": chunk.doc_urn,
        "article_eid": chunk.article_eid,
        "para_eids": chunk.para_eids,
        "hierarchy_path": chunk.hierarchy_path,
        "metadata": chunk.metadata,
    }


def ensure_smoke_collection(client: QdrantClient) -> None:
    if client.collection_exists(SMOKE_COLLECTION):
        log.warning("Smoke collection already exists, dropping for clean slate")
        client.delete_collection(SMOKE_COLLECTION)
    log.info("Creating sparse-only collection %s", SMOKE_COLLECTION)
    client.create_collection(
        collection_name=SMOKE_COLLECTION,
        vectors_config={},
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            ),
        },
    )


def ingest_sparse(
    chunks: list[Chunk],
    client: QdrantClient,
    bm25: SparseTextEmbedding,
    *,
    batch_size: int = 64,
) -> int:
    total = len(chunks)
    n_batches = (total + batch_size - 1) // batch_size
    upserted = 0

    for bi in range(n_batches):
        start = bi * batch_size
        end = min(start + batch_size, total)
        batch = chunks[start:end]
        texts = [c.text for c in batch]
        embeddings = list(bm25.passage_embed(texts))

        points = []
        for c, emb in zip(batch, embeddings, strict=True):
            sparse = models.SparseVector(
                indices=emb.indices.tolist(),
                values=emb.values.tolist(),
            )
            points.append(
                models.PointStruct(
                    id=chunk_id_to_point_id(c.chunk_id),
                    vector={SPARSE_VECTOR_NAME: sparse},
                    payload=chunk_to_payload(c),
                )
            )
        client.upsert(collection_name=SMOKE_COLLECTION, points=points, wait=True)
        upserted += len(points)
        if (bi + 1) % 5 == 0 or bi == n_batches - 1:
            log.info("Ingested batch %d/%d (total %d/%d)", bi + 1, n_batches, upserted, total)

    return upserted


# ---------------------------------------------------------------------------
# Smoke queries
# ---------------------------------------------------------------------------

SMOKE_QUERIES = [
    {
        "id": 1,
        "query": "art 24-bis 231",
        "expected_chunk_id": "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis",
        "match": "exact",
    },
    {
        "id": 2,
        "query": "D.Lgs 231",
        "expected_doc_urn": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
        "match": "doc_urn",
    },
    {
        "id": 3,
        "query": "art. 25-undecies",
        "expected_chunk_id": "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies",
        "match": "exact",
    },
    {
        "id": 4,
        "query": "art 35 GDPR",
        "expected_chunk_id": "eli/reg/2016/679/oj__art_35",
        "match": "exact",
    },
]


def search_query(
    client: QdrantClient,
    bm25: SparseTextEmbedding,
    query: str,
    *,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    emb = next(bm25.query_embed(query))
    sparse = models.SparseVector(
        indices=emb.indices.tolist(),
        values=emb.values.tolist(),
    )
    res = client.query_points(
        collection_name=SMOKE_COLLECTION,
        query=sparse,
        using=SPARSE_VECTOR_NAME,
        limit=top_k,
        with_payload=["chunk_id", "doc_urn", "article_eid"],
    )
    out = []
    for p in res.points:
        out.append((p.payload.get("chunk_id", "?"), p.score, p.payload.get("doc_urn", "?")))
    return out


def verdict_for(q: dict, hits: list[tuple[str, float, str]]) -> bool:
    if q["match"] == "exact":
        return any(h[0] == q["expected_chunk_id"] for h in hits)
    if q["match"] == "doc_urn":
        return any(h[2] == q["expected_doc_urn"] for h in hits)
    return False


def show_tokenization(bm25: SparseTextEmbedding, text: str, label: str) -> None:
    """Debug helper: stampa la tokenizzazione FastEmbed BM25.

    FastEmbed espone `model.tokenize()` internamente; usiamo l'hook documentato
    `_tokenize` se presente, altrimenti facciamo il match indices↔testo.
    """
    print(f"\n[TOKENIZATION] {label}: {text!r}")
    try:
        emb = next(bm25.query_embed(text))
        # Qdrant/bm25 in FastEmbed espone i token sorgenti tramite _tokenizer
        # ma il metodo pubblico cambia tra versioni: tentiamo varie strade.
        tokens = None
        for attr in ("_tokenize_and_stem", "_stem", "raw_tokenize"):
            if hasattr(bm25, attr):
                try:
                    tokens = getattr(bm25, attr)([text])
                    break
                except Exception:
                    pass
        if tokens is None:
            # Fallback: usa il modello sottostante
            model = getattr(bm25, "model", None)
            if model is not None:
                for attr in ("tokenize", "_tokenize"):
                    if hasattr(model, attr):
                        try:
                            tokens = getattr(model, attr)([text])
                            break
                        except Exception:
                            pass
        print(f"  → indices: {emb.indices.tolist()}")
        print(f"  → values:  {[round(float(v), 4) for v in emb.values.tolist()]}")
        if tokens is not None:
            print(f"  → tokens:  {tokens}")
        else:
            print("  → (tokens non esposti dall'API pubblica di FastEmbed)")
    except Exception as e:
        print(f"  ERROR: {e}")


def main() -> int:
    t_start = time.monotonic()

    chunks = load_all_chunks()
    log.info("Loaded %d chunks from corpus v1", len(chunks))

    log.info("Loading FastEmbed BM25 model: %s", BM25_MODEL_NAME)
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL_NAME)

    client = QdrantClient(host="localhost", port=6333)
    ensure_smoke_collection(client)

    n = ingest_sparse(chunks, client, bm25, batch_size=64)
    log.info("Ingested %d sparse points in %.1fs", n, time.monotonic() - t_start)

    # ----- run queries -----
    print("\n" + "=" * 72)
    print(f"SMOKE BM25 — {len(SMOKE_QUERIES)} query")
    print("=" * 72)

    results = []
    for q in SMOKE_QUERIES:
        hits = search_query(client, bm25, q["query"], top_k=10)
        passed = verdict_for(q, hits)
        results.append((q, hits, passed))

        print(f"\n--- Query #{q['id']}: {q['query']!r} ---")
        if q["match"] == "exact":
            print(f"  Expected (top-10 contiene): {q['expected_chunk_id']}")
        else:
            print(f"  Expected (top-10 contiene doc_urn): {q['expected_doc_urn']}")
        print(f"  {'rank':>4}  {'score':>8}  chunk_id")
        for i, (cid, score, _urn) in enumerate(hits, start=1):
            mark = " ✓" if (
                (q["match"] == "exact" and cid == q["expected_chunk_id"])
                or (q["match"] == "doc_urn" and _urn == q["expected_doc_urn"])
            ) else ""
            print(f"  {i:>4}  {score:>8.4f}  {cid}{mark}")
        print(f"  VERDETTO: {'PASS' if passed else 'FAIL'}")

    # ----- summary -----
    n_pass = sum(1 for _, _, p in results if p)
    print("\n" + "=" * 72)
    print(f"RISULTATO: {n_pass}/{len(SMOKE_QUERIES)} pass")
    print("=" * 72)

    if n_pass == len(SMOKE_QUERIES):
        print("\n→ PROCEDI con Qdrant nativo (BM25 sparse vector via FastEmbed Qdrant/bm25).")
    else:
        print("\n→ FALLBACK rank_bm25 con tokenizer regex [a-zA-Z0-9_-]+")
        print("\nDebug tokenizzazione FastEmbed sulle query fallite:")
        for q, hits, passed in results:
            if passed:
                continue
            show_tokenization(bm25, q["query"], f"query #{q['id']}")
            # Mostra anche il testo del chunk atteso
            if q["match"] == "exact":
                expected_text = next(
                    (c.text for c in chunks if c.chunk_id == q["expected_chunk_id"]),
                    None,
                )
                if expected_text is not None:
                    snippet = expected_text[:300].replace("\n", " ")
                    show_tokenization(bm25, snippet, f"payload chunk {q['expected_chunk_id']} (first 300 char)")

    # ----- cleanup -----
    log.info("Dropping smoke collection %s", SMOKE_COLLECTION)
    client.delete_collection(SMOKE_COLLECTION)

    return 0 if n_pass == len(SMOKE_QUERIES) else 1


if __name__ == "__main__":
    sys.exit(main())
