"""sanity_check_corpus.py — Verifica integrità collection Qdrant
italian_legal_v1_hybrid post-ingestion.

Lanciato manualmente dopo ogni re-ingestion. Exit 0 se tutto verde,
1 altrimenti.

Esegue 4 verifiche:
1. Tutti i gold_chunks del benchmark v3 esistono in Qdrant
2. Conteggio chunk totale = aspettativa (865 post-W4)
3. Conteggio chunk per doc_urn vs distribuzione attesa
4. Validità formato chunk_id (regex)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "data/benchmark/gold_answers_v3.json"
COLLECTION = "italian_legal_v1_hybrid"

# Configurazione aspettative (deterministiche)
EXPECTED_TOTAL_CHUNKS = 865

# Conteggio chunk per doc_urn — baseline misurata 2026-05-26.
# Aggiornare se cambia la composizione del corpus.
EXPECTED_PER_NORM = {
    "akn/it/act/decreto_legislativo/stato/2001-06-08/231": 110,
    "akn/it/act/decreto_legislativo/stato/2003-06-30/196": 107,
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138": 45,
    "akn/it/act/legge/stato/2025-09-23/132": 28,
    "eli/reg/2016/679/oj": 272,
    "eli/reg/2024/1689/oj": 303,
}

# Formato canonico chunk_id:
#   AKN:     akn/it/act/{tipo}/stato/{data}/{numero}__art_{id}[__paras_X_Y]
#   EUR-Lex: eli/{reg|dir|dec}/{anno}/{num}/oj__{art_X|recital_N|annex_X}[__paras_X_Y][__point_N]
# Esempi reali nel corpus:
#   akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis
#   akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_1_11
#   eli/reg/2016/679/oj__recital_84
#   eli/reg/2024/1689/oj__art_27
#   eli/reg/2024/1689/oj__annex_III__point_1
CHUNK_ID_REGEX = re.compile(
    r"^(?:akn|eli)/[a-z0-9/_.-]+"
    r"__(?:"
    r"art_[a-zA-Z0-9._-]+(?:__paras_[a-zA-Z0-9_-]+_[a-zA-Z0-9_-]+)?"
    r"|recital_\d+"
    r"|annex_[A-Z]+(?:__point_\d+)?"
    r")$"
)


def check_1_gold_chunks_exist(client: QdrantClient, gold_path: Path) -> bool:
    """Tutti i gold_chunks del benchmark v3 sono in Qdrant?"""
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold_chunk_ids: set[str] = set()
    for entry in gold:
        for gc in entry.get("gold_chunks", []):
            cid = gc.get("chunk_id")
            if cid:
                gold_chunk_ids.add(cid)

    missing: list[str] = []
    for cid in sorted(gold_chunk_ids):
        flt = models.Filter(must=[
            models.FieldCondition(key="chunk_id", match=models.MatchValue(value=cid))
        ])
        pts, _ = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=flt,
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        if not pts:
            missing.append(cid)

    if missing:
        print(f"FAIL check 1: {len(missing)} gold chunk_id mancanti in Qdrant:")
        for cid in missing[:10]:
            print(f"  - {cid}")
        if len(missing) > 10:
            print(f"  ... e altri {len(missing) - 10}")
        return False
    print(f"OK check 1: tutti i {len(gold_chunk_ids)} gold chunk_id sono presenti in Qdrant")
    return True


def check_2_total_count(client: QdrantClient) -> bool:
    """Conteggio totale chunk == EXPECTED_TOTAL_CHUNKS?"""
    info = client.get_collection(COLLECTION)
    actual = info.points_count
    if actual != EXPECTED_TOTAL_CHUNKS:
        print(f"FAIL check 2: conteggio totale {actual} vs atteso {EXPECTED_TOTAL_CHUNKS}")
        return False
    print(f"OK check 2: conteggio totale = {actual}")
    return True


def _scroll_payloads(client: QdrantClient, fields: list[str]) -> list[dict]:
    """Scroll completo della collection con sottoinsieme payload."""
    out: list[dict] = []
    offset = None
    while True:
        pts, offset = client.scroll(
            collection_name=COLLECTION,
            limit=500,
            with_payload=fields,
            with_vectors=False,
            offset=offset,
        )
        for p in pts:
            out.append(p.payload or {})
        if offset is None:
            break
    return out


def check_3_per_norm(client: QdrantClient) -> bool:
    """Conteggio chunk per doc_urn coerente con aspettativa.

    Se EXPECTED_PER_NORM è vuoto, popola da Qdrant attuale e stampa
    per documentazione (run baseline). Se popolato, confronta.
    """
    payloads = _scroll_payloads(client, ["doc_urn"])
    counts: dict[str, int] = {}
    for p in payloads:
        urn = p.get("doc_urn", "UNKNOWN")
        counts[urn] = counts.get(urn, 0) + 1

    if not EXPECTED_PER_NORM:
        print("INFO check 3: EXPECTED_PER_NORM vuoto, distribuzione corrente:")
        for urn, n in sorted(counts.items()):
            print(f"  {urn}: {n}")
        print("Aggiornare EXPECTED_PER_NORM dopo prima run baseline.")
        return True

    mismatches: list[tuple[str, int, int]] = []
    for urn, expected in EXPECTED_PER_NORM.items():
        actual = counts.get(urn, 0)
        if actual != expected:
            mismatches.append((urn, expected, actual))
    extra = sorted(set(counts) - set(EXPECTED_PER_NORM))
    if extra:
        for urn in extra:
            mismatches.append((urn, 0, counts[urn]))

    if mismatches:
        print(f"FAIL check 3: {len(mismatches)} norme con conteggio diverso da atteso:")
        for urn, exp, act in mismatches:
            print(f"  {urn}: atteso={exp}, attuale={act}")
        return False
    print(f"OK check 3: conteggio per norma coerente con aspettativa "
          f"({len(EXPECTED_PER_NORM)} norme)")
    return True


def check_4_chunk_id_format(client: QdrantClient) -> bool:
    """Tutti i chunk_id rispettano il formato canonico?"""
    payloads = _scroll_payloads(client, ["chunk_id"])
    invalid: list[str] = []
    for p in payloads:
        cid = p.get("chunk_id", "")
        if not CHUNK_ID_REGEX.match(cid):
            invalid.append(cid)

    if invalid:
        print(f"FAIL check 4: {len(invalid)} chunk_id non rispettano il formato canonico:")
        for cid in invalid[:10]:
            print(f"  - {cid}")
        if len(invalid) > 10:
            print(f"  ... e altri {len(invalid) - 10}")
        return False
    print(f"OK check 4: tutti i {len(payloads)} chunk_id rispettano il formato canonico")
    return True


def main() -> int:
    client = QdrantClient(host="localhost", port=6333, timeout=10)
    print(f"Sanity check su collection '{COLLECTION}'")
    print("=" * 70)

    results = [
        check_1_gold_chunks_exist(client, GOLD_PATH),
        check_2_total_count(client),
        check_3_per_norm(client),
        check_4_chunk_id_format(client),
    ]

    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Risultato: {passed}/{total} verifiche passate")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
