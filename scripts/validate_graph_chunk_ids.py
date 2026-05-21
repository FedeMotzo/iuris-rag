"""Valida che tutti i chunk_id del graph esistano in `italian_legal_v1_hybrid`.

Uso:
    spike/.venv/bin/python scripts/validate_graph_chunk_ids.py

Esce con codice 1 se ci sono placeholder `<CHUNK_ID_...>` o chunk_id mancanti
nella collection.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient, models  # noqa: E402

from core.normative_graph import load_graph  # noqa: E402
from core.vector_store import HYBRID_COLLECTION_NAME  # noqa: E402


def main() -> int:
    links = load_graph()
    used: set[str] = set()
    for l in links:
        used.add(l.from_chunk)
        used.add(l.to_chunk)

    placeholders = sorted(c for c in used if c.startswith("<") and c.endswith(">"))
    if placeholders:
        print("ERRORE: placeholder non risolti nel graph YAML:")
        for p in placeholders:
            print(f"  - {p}")
        return 1

    client = QdrantClient(host="localhost", port=6333, timeout=5)
    if not client.collection_exists(HYBRID_COLLECTION_NAME):
        print(f"ERRORE: collection `{HYBRID_COLLECTION_NAME}` inesistente")
        return 1

    verified: list[str] = []
    missing: list[str] = []
    for cid in sorted(used):
        flt = models.Filter(must=[
            models.FieldCondition(key="chunk_id", match=models.MatchValue(value=cid)),
        ])
        pts, _ = client.scroll(
            collection_name=HYBRID_COLLECTION_NAME,
            limit=1,
            with_payload=False,
            scroll_filter=flt,
        )
        if pts:
            verified.append(cid)
        else:
            missing.append(cid)

    print(f"Chunk_id verificati: {len(verified)}/{len(used)}")
    for c in verified:
        print(f"  ✓ {c}")
    if missing:
        print()
        print(f"Chunk_id MANCANTI nella collection: {len(missing)}")
        for c in missing:
            print(f"  ✗ {c}")
        return 1

    print()
    print("OK — tutti i chunk_id del graph esistono nella collection.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
