"""Diagnostica corpus D.Lgs 231/2001 — gap analysis Qdrant vs sorgente AKN.

5 sezioni:
  A. inventario Qdrant per doc_urn 231
  B. inventario sorgente AKN (parser su `data/cache/normattiva/...231.xml`)
  C. gap analysis (set-diff)
  D. integrità degli articoli Q5-rilevanti nel sorgente
  E. simulazione chunker su quegli articoli (n chunk prodotti, oversize?)

Sola lettura: niente upsert, niente re-ingest, niente fix.

Uso:
    spike/.venv/bin/python scripts/diagnose_corpus_231.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qdrant_client import models  # noqa: E402

from core.chunking import chunk_document  # noqa: E402
from core.italian_legal_parser import parse_akn  # noqa: E402
from core.vector_store import HYBRID_COLLECTION_NAME, get_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("diag_231")

DOC_URN = "akn/it/act/decreto_legislativo/stato/2001-06-08/231"
SRC_PATH = ROOT / "data/cache/normattiva/urn_nir_stato_decreto.legislativo_2001-06-08_231.xml"
REPORT_PATH = ROOT / "spike/CORPUS_231_DIAG.md"

Q5_RELEVANT_EIDS = {
    "art_24",            # Indebita percezione, truffa
    "art_25",            # Concussione, induzione, corruzione
    "art_25-quinquies",  # Delitti contro la personalità individuale
    "art_25-septies",    # Omicidio/lesioni colpose violazione norme antinfortunistiche
}


def _eid_sort_key(eid: str):
    """Ordina art_1 < art_2 < ... < art_24 < art_24-bis < art_24-ter < art_25 ..."""
    s = eid.replace("art_", "")
    parts = s.split("-", 1)
    try:
        n = int(parts[0])
    except ValueError:
        n = 999
    suffix = parts[1] if len(parts) > 1 else ""
    # ordinamento alfabetico semplice del suffisso (bis < ter < quater < ...)
    suffix_order = ["", "bis", "ter", "quater", "quater.1", "quater.2",
                    "quinquies", "quinquies.1", "sexies", "septies",
                    "septies.1", "octies", "novies", "decies", "undecies",
                    "duodecies", "terdecies", "quaterdecies"]
    try:
        sidx = suffix_order.index(suffix)
    except ValueError:
        sidx = 999
    return (n, sidx, suffix)


# ---------------------------------------------------------------- Section A

def section_a_qdrant_inventory():
    log.info("=== Sezione A — Inventario Qdrant 231 ===")
    client = get_client()
    flt = models.Filter(must=[
        models.FieldCondition(
            key="doc_urn",
            match=models.MatchValue(value=DOC_URN),
        )
    ])
    all_pts = []
    offset = None
    while True:
        pts, offset = client.scroll(
            collection_name=HYBRID_COLLECTION_NAME,
            scroll_filter=flt,
            limit=512,
            offset=offset,
            with_payload=True,
        )
        all_pts.extend(pts)
        if offset is None:
            break

    rows = []
    seen_articles: set[str] = set()
    for p in all_pts:
        pl = p.payload or {}
        cid = pl.get("chunk_id", "")
        text = pl.get("text", "") or ""
        hier = " > ".join(pl.get("hierarchy_path") or [])
        ctype = pl.get("chunk_type", "")
        eid = pl.get("article_eid", "")
        if eid:
            seen_articles.add(eid)
        rows.append({
            "chunk_id": cid,
            "article_eid": eid,
            "chunk_type": ctype,
            "hierarchy": hier,
            "n_char": len(text),
            "approx_tok": len(text) // 4,
            "head": text[:100].replace("\n", " "),
        })
    rows.sort(key=lambda r: (_eid_sort_key(r["article_eid"]), r["chunk_id"]))
    log.info("  Qdrant: %d chunk, %d articoli distinti",
             len(rows), len(seen_articles))
    return rows, seen_articles


# ---------------------------------------------------------------- Section B

def section_b_source_inventory():
    log.info("=== Sezione B — Inventario sorgente AKN ===")
    xml_bytes = SRC_PATH.read_bytes()
    doc = parse_akn(xml_bytes)
    rows = []
    seen_articles: set[str] = set()
    for ch in doc.chapters:
        for a in ch.articles:
            seen_articles.add(a.eid)
            title = a.rubrica or ""
            # lunghezza testo: rendering article + commi (stessa logica chunker)
            text_estimate = (a.rubrica or "") + "\n\n" + "\n\n".join(
                c.text for c in a.commi
            )
            rows.append({
                "article_eid": a.eid,
                "chapter": ch.number or ch.eid,
                "title_head": title[:100].replace("\n", " "),
                "n_commi": len(a.commi),
                "n_char": len(text_estimate),
                "is_abrogated": a.is_abrogated,
            })
    rows.sort(key=lambda r: _eid_sort_key(r["article_eid"]))
    log.info("  Sorgente: %d articoli estraibili (chapters=%d)",
             len(rows), len(doc.chapters))
    return rows, seen_articles, doc


# ---------------------------------------------------------------- Section C

def section_c_gap_analysis(qdrant_articles, source_articles, source_rows):
    log.info("=== Sezione C — Gap analysis ===")
    only_qdrant = qdrant_articles - source_articles
    only_source = source_articles - qdrant_articles
    both = qdrant_articles & source_articles
    log.info("  Solo Qdrant (anomalia): %d", len(only_qdrant))
    log.info("  Solo sorgente (gap di ingestion): %d", len(only_source))
    log.info("  In entrambi (baseline ok): %d", len(both))

    src_by_eid = {r["article_eid"]: r for r in source_rows}
    gap_rows = []
    for eid in sorted(only_source, key=_eid_sort_key):
        src = src_by_eid.get(eid, {})
        flag = "[Q5_RELEVANT]" if eid in Q5_RELEVANT_EIDS else "[OTHER]"
        # Heuristica HR-related allargata (oltre i 4 chiave): art_25-* citati nella
        # consegna iniziale come potenzialmente rilevanti
        gap_rows.append({
            "article_eid": eid,
            "title_head": src.get("title_head", ""),
            "n_char": src.get("n_char", 0),
            "flag": flag,
        })
    return only_qdrant, only_source, both, gap_rows


# ---------------------------------------------------------------- Section D

def section_d_q5_integrity(doc):
    log.info("=== Sezione D — Integrità articoli Q5-rilevanti ===")
    by_eid = {a.eid: (ch, a) for ch in doc.chapters for a in ch.articles}
    rows = []
    for eid in sorted(Q5_RELEVANT_EIDS, key=_eid_sort_key):
        if eid not in by_eid:
            rows.append({
                "article_eid": eid,
                "present": False,
                "non_empty": False,
                "n_commi": 0,
                "n_char": 0,
                "oversize_est": False,
                "title": "",
            })
            log.info("  %s: ASSENTE nel sorgente", eid)
            continue
        ch, a = by_eid[eid]
        text = (a.rubrica or "") + "\n\n" + "\n\n".join(c.text for c in a.commi)
        n_char = len(text)
        approx_tok = n_char // 4
        rows.append({
            "article_eid": eid,
            "present": True,
            "non_empty": bool(text.strip()),
            "n_commi": len(a.commi),
            "n_char": n_char,
            "oversize_est": approx_tok > 2000,
            "title": (a.rubrica or "").replace("\n", " "),
        })
        log.info("  %s: present, commi=%d, char=%d (≈%d tok)%s",
                 eid, len(a.commi), n_char, approx_tok,
                 " OVERSIZE" if approx_tok > 2000 else "")
    return rows


# ---------------------------------------------------------------- Section E

def section_e_chunker_simulation(doc):
    log.info("=== Sezione E — Simulazione chunker su Q5-rilevanti ===")
    all_chunks = chunk_document(doc)
    by_eid: dict[str, list] = {}
    for c in all_chunks:
        if c.article_eid:
            by_eid.setdefault(c.article_eid, []).append(c)
    rows = []
    for eid in sorted(Q5_RELEVANT_EIDS, key=_eid_sort_key):
        chunks = by_eid.get(eid, [])
        if not chunks:
            rows.append({
                "article_eid": eid,
                "n_chunks": 0,
                "chunk_ids": [],
                "warnings": "NON estraibile dal chunker (assente o filtered)",
            })
            continue
        warnings = []
        for c in chunks:
            if c.metadata.get("oversize"):
                warnings.append(f"{c.chunk_id} OVERSIZE")
        rows.append({
            "article_eid": eid,
            "n_chunks": len(chunks),
            "chunk_ids": [c.chunk_id for c in chunks],
            "chunk_types": sorted({c.chunk_type for c in chunks}),
            "warnings": "; ".join(warnings) if warnings else "ok",
        })
        log.info("  %s: %d chunk(s), types=%s, warn=%s",
                 eid, len(chunks),
                 sorted({c.chunk_type for c in chunks}),
                 "; ".join(warnings) if warnings else "ok")
    return rows


# ---------------------------------------------------------------- Report MD

def build_markdown(qdrant_rows, source_rows, only_qdrant, only_source, both,
                   gap_rows, integrity_rows, sim_rows) -> str:
    L: list[str] = []
    L.append("# Diagnostica corpus D.Lgs 231/2001")
    L.append("")
    n_q5_gap = sum(1 for r in gap_rows if r["flag"] == "[Q5_RELEVANT]")
    n_q5_in_qdrant = sum(1 for eid in Q5_RELEVANT_EIDS if eid in both)
    L.append("## Sintesi esecutiva")
    L.append("")
    L.append(f"- Articoli in Qdrant (231): **{len(set(r['article_eid'] for r in qdrant_rows if r['article_eid']))}**")
    L.append(f"- Articoli estraibili dal sorgente: **{len(source_rows)}**")
    L.append(f"- Gap (solo sorgente, non ingerito): **{len(only_source)}**")
    L.append(f"- Anomalie (solo Qdrant, non estraibili oggi): **{len(only_qdrant)}**")
    L.append(f"- Articoli Q5-rilevanti nel gap: **{n_q5_gap}/4** ({sorted(eid for r in gap_rows if r['flag'] == '[Q5_RELEVANT]' for eid in [r['article_eid']])})")
    L.append(f"- Articoli Q5-rilevanti già in Qdrant: **{n_q5_in_qdrant}/4**")
    L.append("")

    # A
    L.append("## A — Inventario Qdrant")
    L.append("")
    L.append("| chunk_id | article_eid | chunk_type | hierarchy | n_char | ≈tok |")
    L.append("|---|---|---|---|---|---|")
    for r in qdrant_rows:
        cid = r["chunk_id"]
        cid_short = cid if len(cid) <= 80 else cid[:77] + "..."
        hier_short = r["hierarchy"] if len(r["hierarchy"]) <= 50 else r["hierarchy"][:47] + "..."
        L.append(f"| `{cid_short}` | {r['article_eid']} | {r['chunk_type']} | {hier_short} | {r['n_char']} | {r['approx_tok']} |")
    L.append(f"\n**Totale chunk in Qdrant: {len(qdrant_rows)} · articoli distinti: {len(set(r['article_eid'] for r in qdrant_rows if r['article_eid']))}**")
    L.append("")

    # B
    L.append("## B — Inventario sorgente AKN")
    L.append("")
    L.append("| article_eid | chapter | n_commi | n_char | abrog | title (head) |")
    L.append("|---|---|---|---|---|---|")
    for r in source_rows:
        t = r["title_head"]
        t_short = t if len(t) <= 60 else t[:57] + "..."
        L.append(f"| {r['article_eid']} | {r['chapter']} | {r['n_commi']} | {r['n_char']} | {'Y' if r['is_abrogated'] else 'N'} | {t_short} |")
    L.append(f"\n**Totale articoli estraibili: {len(source_rows)}**")
    L.append("")

    # C
    L.append("## C — Gap analysis")
    L.append("")
    L.append(f"- In entrambi (baseline ok): **{len(both)}**")
    L.append(f"- Solo Qdrant (anomalia, possibile chunk_id orfano): **{len(only_qdrant)}** — {sorted(only_qdrant, key=_eid_sort_key) if only_qdrant else '(nessuno)'}")
    L.append(f"- Solo sorgente (gap di ingestion): **{len(only_source)}**")
    L.append("")
    L.append("Articoli nel gap (estraibili ma non ingeriti):")
    L.append("")
    L.append("| article_eid | n_char | flag | title (head) |")
    L.append("|---|---|---|---|")
    for r in gap_rows:
        t = r["title_head"]
        t_short = t if len(t) <= 70 else t[:67] + "..."
        L.append(f"| {r['article_eid']} | {r['n_char']} | {r['flag']} | {t_short} |")
    L.append("")

    # D
    L.append("## D — Integrità articoli Q5-rilevanti nel sorgente")
    L.append("")
    L.append("| article_eid | present | non_empty | n_commi | n_char | oversize_est (>8000ch ≈ 2k tok) | title |")
    L.append("|---|---|---|---|---|---|---|")
    for r in integrity_rows:
        t = r["title"]
        t_short = t if len(t) <= 60 else t[:57] + "..."
        L.append(f"| {r['article_eid']} | {'Y' if r['present'] else 'N'} | {'Y' if r['non_empty'] else 'N'} | {r['n_commi']} | {r['n_char']} | {'Y' if r['oversize_est'] else 'N'} | {t_short} |")
    L.append("")

    # E
    L.append("## E — Simulazione chunker su Q5-rilevanti")
    L.append("")
    L.append("| article_eid | n_chunks | chunk_types | chunk_ids | warnings |")
    L.append("|---|---|---|---|---|")
    for r in sim_rows:
        cids = ", ".join(f"`{c}`" for c in r.get("chunk_ids", []))
        types = ", ".join(r.get("chunk_types", []))
        L.append(f"| {r['article_eid']} | {r['n_chunks']} | {types} | {cids} | {r['warnings']} |")
    L.append("")

    # Verdetto
    L.append("## Verdetto")
    L.append("")
    parser_problems = any(
        r["n_chunks"] == 0 or "OVERSIZE" in r["warnings"] or "NON estraibile" in r["warnings"]
        for r in sim_rows
    )
    n_q5_extractable = sum(1 for r in integrity_rows if r["present"] and r["non_empty"])
    n_q5_already_in = n_q5_in_qdrant

    if n_q5_extractable < len(Q5_RELEVANT_EIDS) or parser_problems:
        L.append(
            "**Scenario B-heavy**: parser ha gap o bug su uno o più dei 4 articoli "
            "Q5-rilevanti. Stima: 3-6h (fix parser + whitelist + re-ingest + test "
            "regressione)."
        )
    elif any(r["oversize_est"] for r in integrity_rows):
        L.append(
            "**Scenario B-light**: parser produce chunk corretti, ma uno o più "
            "articoli Q5-rilevanti sono oversize/monoblocco e potrebbero richiedere "
            "split aggiuntivo. Stima: 2-3h (whitelist + decisione chunking + "
            "re-ingest)."
        )
    elif n_q5_already_in == len(Q5_RELEVANT_EIDS) and len(only_source) == 0:
        L.append(
            f"**Scenario 0 — nessuna estensione corpus necessaria**. Tutti i "
            f"{len(Q5_RELEVANT_EIDS)}/4 articoli Q5-rilevanti sono **già in "
            f"Qdrant** come chunk article singoli (non oversize), il corpus 231 "
            f"è completo (109/109 articoli ingeriti, 0 gap). Il problema di Q5 "
            f"zero-recall **non è di corpus** ma di **retrieval**: la query usa "
            f"vocabolario \"AI/HR\" che non aggancia il vocabolario \"reati "
            f"presupposto/responsabilità ente\" del 231 (vedi diagnostica retrieval "
            f"Q5, `spike/Q5_RETRIEVAL_DIAG.md`). Il fix va cercato altrove: "
            f"annotazione gold + `core/terminology` (alias di dominio) e/o "
            f"`core/normative_graph` (link `L.132/2025 art.11 ↔ 231 art.24-bis`). "
            f"Stima: 0h su corpus, vedi prompt successivi su terminology/graph."
        )
    else:
        L.append(
            f"**Scenario A**: estensione = whitelist + re-ingest mirato. Tutti i "
            f"{len(Q5_RELEVANT_EIDS)} articoli Q5-rilevanti sono presenti nel "
            f"sorgente, parser li chunka correttamente, "
            f"{n_q5_already_in}/{len(Q5_RELEVANT_EIDS)} sono già in Qdrant. "
            f"Stima: ~1h."
        )
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- Main

def main() -> int:
    qdrant_rows, qdrant_articles = section_a_qdrant_inventory()
    source_rows, source_articles, doc = section_b_source_inventory()
    only_qdrant, only_source, both, gap_rows = section_c_gap_analysis(
        qdrant_articles, source_articles, source_rows,
    )
    integrity_rows = section_d_q5_integrity(doc)
    sim_rows = section_e_chunker_simulation(doc)

    report = build_markdown(
        qdrant_rows, source_rows, only_qdrant, only_source, both,
        gap_rows, integrity_rows, sim_rows,
    )
    print(report)
    REPORT_PATH.write_text(report + "\n", encoding="utf-8")
    log.info("Report salvato in %s", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
