"""Sampling annotazione gold benchmark: query con almeno 1 gold 231/2001.

Trigger: curatela W7-prep ha rivelato 2 gold sbagliati (Q5, Q9 — entrambi
art_25-undecies reati ambientali su use case HR/AI). Possibile pattern di
allucinazione LLM-hint nella fase setup benchmark. Questo script
identifica TUTTE le query con gold 231 e produce un report per ispezione
visuale a colpo d'occhio.

NIENTE giudizio giuridico nello script. Federico valuta a mano.

Uso:
    spike/.venv/bin/python scripts/sample_annotation_231.py
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.vector_store import (  # noqa: E402
    HYBRID_COLLECTION_NAME,
    chunk_id_to_point_id,
    get_client,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("sample_231")

SRC = ROOT / "data/benchmark/gold_validated_v2.json"
OUT = ROOT / "spike/ANNOTATION_SAMPLING_231.md"
DOC_URN_231 = "akn/it/act/decreto_legislativo/stato/2001-06-08/231"

SHORTNAME = {
    "eli/reg/2016/679/oj": "GDPR",
    "eli/reg/2024/1689/oj": "AI Act",
    "akn/it/act/decreto_legislativo/stato/2001-06-08/231": "231/2001",
    "akn/it/act/decreto_legislativo/stato/2003-06-30/196": "196/2003",
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138": "NIS2 (D.Lgs 138/2024)",
    "akn/it/act/legge/stato/2025-09-23/132": "L. 132/2025",
}


def shortname(urn: str) -> str:
    return SHORTNAME.get(urn, urn)


def _eid_sort_key(eid: str):
    """art_1 < art_2 < ... < art_24 < art_24-bis < ..."""
    s = eid.replace("art_", "")
    parts = s.split("-", 1)
    try:
        n = int(parts[0])
    except ValueError:
        n = 999
    suffix = parts[1] if len(parts) > 1 else ""
    suffix_order = ["", "bis", "ter", "quater", "quater.1", "quater.2",
                    "quinquies", "quinquies.1", "sexies", "septies",
                    "septies.1", "octies", "novies", "decies", "undecies",
                    "duodecies", "terdecies", "quaterdecies"]
    try:
        sidx = suffix_order.index(suffix)
    except ValueError:
        sidx = 999
    return (n, sidx, suffix)


def fetch_texts(chunk_ids: list[str]) -> dict[str, str]:
    """Batch retrieve dei chunk text da Qdrant. Ritorna {chunk_id: text}."""
    if not chunk_ids:
        return {}
    client = get_client()
    id_map = {cid: chunk_id_to_point_id(cid) for cid in chunk_ids}
    pts = client.retrieve(
        collection_name=HYBRID_COLLECTION_NAME,
        ids=list(id_map.values()),
        with_payload=True,
    )
    by_pid = {str(p.id): (p.payload or {}).get("text", "") for p in pts}
    return {cid: by_pid.get(pid, "") for cid, pid in id_map.items()}


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    queries = data["queries"]
    log.info("Caricato %s (%d query)", SRC.name, len(queries))

    # ----- Sezione A: identificazione query 231-related ---------------------
    related = []
    for q in queries:
        gold_231 = [
            c for c in q.get("candidates", [])
            if c.get("doc_urn") == DOC_URN_231 and c.get("is_gold")
        ]
        if gold_231:
            related.append((q, gold_231))
    log.info("Query con almeno 1 gold 231: %d/%d", len(related), len(queries))

    # ----- Raccogli tutti i chunk_id da fetchare ----------------------------
    need_text: set[str] = set()
    for q, gold_231 in related:
        for c in q["candidates"]:
            # gold 231 → 300 char; non-gold 231 → 200 char (entrambi servono testo)
            if c.get("doc_urn") == DOC_URN_231:
                need_text.add(c["chunk_id"])
    texts = fetch_texts(sorted(need_text))
    log.info("Fetched text da Qdrant: %d chunk", len(texts))

    # ----- Stats globali (sezione C) ----------------------------------------
    article_gold_count: Counter[str] = Counter()
    article_to_qids: defaultdict[str, list[str]] = defaultdict(list)
    for q, gold_231 in related:
        for g in gold_231:
            article_gold_count[g["article_eid"]] += 1
            article_to_qids[g["article_eid"]].append(q["qid"])

    # ----- Build report -----------------------------------------------------
    L: list[str] = []
    L.append("# Sampling annotazione gold 231/2001 — benchmark v1")
    L.append("")
    L.append(
        f"Sorgente: `data/benchmark/gold_validated_v2.json` (50 query). "
        f"Filtro: candidates con `doc_urn = {DOC_URN_231}` e `is_gold=true`."
    )
    L.append("")
    L.append(
        "Output puramente diagnostico. Nessuna euristica di flagging — la "
        "valutazione giuridica di coerenza spetta alla revisione manuale."
    )
    L.append("")

    # ----- Sezione A --------------------------------------------------------
    L.append("## A — Query con almeno 1 gold 231/2001")
    L.append("")
    L.append("| qid | use_case | n_gold_231 | gold article_eid(s) |")
    L.append("|---|---|---:|---|")
    for q, gold_231 in related:
        eids = ", ".join(sorted({g["article_eid"] for g in gold_231},
                                 key=_eid_sort_key))
        L.append(f"| {q['qid']} | {q.get('use_case', '')} | {len(gold_231)} | {eids} |")
    L.append("")
    L.append(f"**Totale query 231-related: {len(related)}**")
    L.append("")

    # ----- Sezione B --------------------------------------------------------
    L.append("## B — Entry diagnostiche per ispezione")
    L.append("")
    for q, gold_231 in related:
        L.append(f"### {q['qid']} — {q.get('use_case', '')}")
        L.append("")
        L.append(f"**Query**: {q['query']}")
        L.append("")

        # Gold 231 attivi (testo 300 char)
        L.append(f"**Gold 231 attivi ({len(gold_231)})**:")
        L.append("")
        for g in sorted(gold_231, key=lambda c: _eid_sort_key(c["article_eid"])):
            cid = g["chunk_id"]
            text = texts.get(cid, "")[:300].replace("\n", " ")
            ellipsis = "..." if len(texts.get(cid, "")) > 300 else ""
            L.append(f"- `{cid}` ({g['article_eid']}):")
            L.append(f"  > {text}{ellipsis}")
        L.append("")

        # Altri gold non-231 (solo riferimenti)
        other_gold = [
            c for c in q["candidates"]
            if c.get("is_gold") and c.get("doc_urn") != DOC_URN_231
        ]
        L.append(f"**Altri gold non-231 ({len(other_gold)})**:")
        L.append("")
        if other_gold:
            for c in other_gold:
                L.append(
                    f"- `{c['chunk_id']}` ({shortname(c.get('doc_urn', ''))}, "
                    f"{c.get('article_eid', '')})"
                )
        else:
            L.append("- (nessuno: i gold di questa query sono solo 231)")
        L.append("")

        # Altri candidates 231 NON gold (testo 200 char)
        other_231 = [
            c for c in q["candidates"]
            if c.get("doc_urn") == DOC_URN_231 and not c.get("is_gold")
        ]
        L.append(f"**Altri candidates 231 NON gold ({len(other_231)})**:")
        L.append("")
        if other_231:
            for c in sorted(other_231, key=lambda x: _eid_sort_key(x["article_eid"])):
                cid = c["chunk_id"]
                text = texts.get(cid, "")[:200].replace("\n", " ")
                ellipsis = "..." if len(texts.get(cid, "")) > 200 else ""
                L.append(f"- `{cid}` ({c['article_eid']}):")
                L.append(f"  > {text}{ellipsis}")
        else:
            L.append("- (nessun altro candidate 231 in questa query)")
        L.append("")
        L.append("---")
        L.append("")

    # ----- Sezione C --------------------------------------------------------
    L.append("## C — Statistiche aggregate")
    L.append("")
    L.append(f"- Totale query con ≥1 gold 231: **{len(related)}**")
    L.append(f"- Articoli 231 distinti marcati gold: **{len(article_gold_count)}**")
    L.append(f"- Totale marker is_gold=true su 231: **{sum(article_gold_count.values())}**")
    L.append("")

    L.append("### Distribuzione gold per article_eid")
    L.append("")
    L.append("| article_eid | n_gold | qid(s) |")
    L.append("|---|---:|---|")
    for eid in sorted(article_gold_count, key=_eid_sort_key):
        L.append(
            f"| {eid} | {article_gold_count[eid]} | "
            f"{', '.join(sorted(set(article_to_qids[eid]), key=lambda q: int(q[1:])))} |"
        )
    L.append("")

    L.append("### Top-5 articoli 231 più ricorrenti come gold")
    L.append("")
    top5 = article_gold_count.most_common(5)
    if top5:
        L.append("| rank | article_eid | n_gold |")
        L.append("|---|---|---:|")
        for i, (eid, n) in enumerate(top5, 1):
            L.append(f"| {i} | {eid} | {n} |")
    L.append("")

    L.append("### Articoli 231 marcati gold solo in 1 query (potenziali outlier)")
    L.append("")
    singletons = [eid for eid, n in article_gold_count.items() if n == 1]
    if singletons:
        L.append("| article_eid | qid |")
        L.append("|---|---|")
        for eid in sorted(singletons, key=_eid_sort_key):
            qid = article_to_qids[eid][0]
            L.append(f"| {eid} | {qid} |")
    else:
        L.append("- (nessuno: tutti gli articoli compaiono in ≥2 query)")
    L.append("")

    report = "\n".join(L)
    print(report)
    OUT.write_text(report + "\n", encoding="utf-8")
    log.info("Report salvato in %s", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
