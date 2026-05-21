"""Corpus ingestion audit — read-only diagnostic.

Confronta il contenuto della collection Qdrant `italian_legal_v1_hybrid`
con i sorgenti corpus v1 (HTML EUR-Lex + XML AKN Normattiva). Produce
gap report per norma + cross-reference con `gold_answers_v1.json`.

Output: stampe su stdout, raccolte poi a mano in
`spike/CORPUS_INGESTION_AUDIT.md`. Niente modifiche a Qdrant.

    spike/.venv/bin/python spike/audit_corpus.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.eur_lex_parser.parser import parse_articles, parse_recitals  # noqa: E402
from core.italian_legal_parser.parser import parse_akn  # noqa: E402

COLLECTION = "italian_legal_v1_hybrid"
GOLD_PATH = ROOT / "data/benchmark/gold_answers_v1.json"

EURLEX_DIR = ROOT / "data/cache/eurlex/IT"
NORMATTIVA_DIR = ROOT / "data/cache/normattiva"

# Mappa prefisso URN → (label, sorgente)
NORMS = [
    ("eli/reg/2016/679/oj", "GDPR (Reg UE 2016/679)"),
    ("eli/reg/2024/1689/oj", "AI Act (Reg UE 2024/1689)"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy (D.Lgs 196/2003)"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "D.Lgs 138/2024 (NIS2)"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]

SOURCE_FILES = {
    "eli/reg/2016/679/oj": {
        "articles": EURLEX_DIR / "02016R0679-20160504.html",  # consolidated
        "recitals": EURLEX_DIR / "32016R0679.html",            # initial
        "celex": "32016R0679",
        "template_articles": "consolidated",
    },
    "eli/reg/2024/1689/oj": {
        "articles": EURLEX_DIR / "32024R1689.html",            # initial (no consolidated IT)
        "recitals": EURLEX_DIR / "32024R1689.html",
        "annex_source": EURLEX_DIR / "32024R1689.html",
        "celex": "32024R1689",
        "template_articles": "initial",
    },
    "akn/it/act/decreto_legislativo/stato/2003-06-30/196": {
        "xml": NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2003-06-30_196.xml",
    },
    "akn/it/act/decreto_legislativo/stato/2001-06-08/231": {
        "xml": NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2001-06-08_231.xml",
    },
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138": {
        "xml": NORMATTIVA_DIR / "urn_nir_stato_decreto.legislativo_2024-09-04_138.xml",
    },
    "akn/it/act/legge/stato/2025-09-23/132": {
        "xml": NORMATTIVA_DIR / "urn_nir_stato_legge_2025-09-23_132.xml",
    },
}


def fetch_qdrant_inventory() -> list[dict]:
    """Scroll completo della collection. Ritorna lista di dict per chunk."""
    from qdrant_client import QdrantClient
    client = QdrantClient(host="localhost", port=6333)
    chunks: list[dict] = []
    offset = None
    while True:
        pts, offset = client.scroll(
            COLLECTION, limit=512, offset=offset,
            with_payload=["chunk_id", "chunk_type", "article_eid"],
            with_vectors=False,
        )
        for p in pts:
            chunks.append(p.payload)
        if offset is None:
            break
    return chunks


def classify(chunk_id: str) -> tuple[str, str]:
    """Ritorna (norma_prefix, unit_type) per un chunk_id.

    unit_type ∈ {article, article_fragment, recital, annex, annex_point, other}
    """
    norm_prefix = next((p for p, _ in NORMS if chunk_id.startswith(p + "__")), "?")
    if "__art_" in chunk_id and "__paras_" in chunk_id:
        unit = "article_fragment"
    elif "__art_" in chunk_id:
        unit = "article"
    elif "__recital_" in chunk_id:
        unit = "recital"
    elif "__annex_" in chunk_id and "__point_" in chunk_id:
        unit = "annex_point"
    elif "__annex_" in chunk_id:
        unit = "annex"
    else:
        unit = "other"
    return norm_prefix, unit


def expected_eurlex(prefix: str) -> dict:
    """Estrai art_N e recital_N attesi dai sorgenti HTML."""
    src = SOURCE_FILES[prefix]
    art_html = src["articles"].read_bytes()
    doc = parse_articles(art_html, src["template_articles"], src["celex"])
    articles = []
    for ch in doc.chapters:
        for a in ch.articles:
            articles.append(a.eid)

    rec_html = src["recitals"].read_bytes()
    # Il parser emette eid `rct_N`; la chunking converte in `recital_N`
    # nel chunk_id Qdrant. Normalizzo per il confronto.
    recitals = [r.eid.replace("rct_", "recital_") for r in parse_recitals(rec_html, src["celex"])]

    annexes: list[str] = []
    if "annex_source" in src:
        # Heuristica diretta sull'HTML: cerca id="anx_N" o anchor di allegato.
        # AI Act dichiara 13 annex con id come `anx_I`..`anx_XIII` o anchor
        # testuali `ANNEX I`..`ANNEX XIII` nel rendering iniziale.
        html_text = src["annex_source"].read_text(encoding="utf-8", errors="ignore")
        roman = re.findall(r'id="anx_([IVX]+)"', html_text)
        annexes = sorted(set(roman), key=_roman_to_int)
    return {"articles": articles, "recitals": recitals, "annexes": annexes}


def _roman_to_int(r: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    out = 0
    for i, ch in enumerate(r):
        v = vals[ch]
        if i + 1 < len(r) and vals[r[i + 1]] > v:
            out -= v
        else:
            out += v
    return out


def expected_akn(prefix: str) -> dict:
    """Estrai art_eid attesi dal XML AKN, segnalando gli abrogati."""
    src = SOURCE_FILES[prefix]
    doc = parse_akn(src["xml"].read_bytes())
    articles: list[str] = []
    abrogated: list[str] = []
    for ch in doc.chapters:
        for a in ch.articles:
            articles.append(a.eid)
            if a.is_abrogated:
                abrogated.append(a.eid)
    return {"articles": articles, "abrogated": abrogated}


def gap_to_priority(chunks_by_norm: dict, expected_by_norm: dict, gold_data: list) -> list[dict]:
    """Compute gap + impact sul benchmark per ogni norma."""
    # gold_chunks da query positive
    positive_gold: dict[str, set[str]] = defaultdict(set)  # qid → set(chunk_id)
    chunk_to_qids: dict[str, set[str]] = defaultdict(set)
    for entry in gold_data:
        if entry.get("query_type") != "positive":
            continue
        qid = entry["qid"]
        for g in entry.get("gold_chunks", []):
            cid = g.get("chunk_id")
            if cid:
                positive_gold[qid].add(cid)
                chunk_to_qids[cid].add(qid)

    rows = []
    for prefix, label in NORMS:
        eff = chunks_by_norm.get(prefix, {})
        exp = expected_by_norm.get(prefix, {})
        gap_art = sorted(set(exp.get("articles", [])) - set(eff.get("articles_eids", set())))
        gap_rec = sorted(set(exp.get("recitals", [])) - set(eff.get("recitals_eids", set())),
                         key=lambda s: int(re.search(r'\d+$', s).group()) if re.search(r'\d+$', s) else 0)
        gap_ann = sorted(set(exp.get("annexes", [])) - set(eff.get("annexes_eids", set())),
                         key=_roman_to_int)
        n_gap = len(gap_art) + len(gap_rec) + len(gap_ann)

        # impatto benchmark: quali gold_chunks puntano a unità mancanti?
        impacted_qids: set[str] = set()
        # ricostruisci chunk_id "atteso" e vedi se manca
        eff_all_chunk_ids = eff.get("all_chunk_ids", set())
        for cid, qids in chunk_to_qids.items():
            if cid.startswith(prefix + "__") and cid not in eff_all_chunk_ids:
                impacted_qids |= qids

        rows.append({
            "prefix": prefix, "label": label,
            "gap_articles": gap_art, "gap_recitals": gap_rec, "gap_annexes": gap_ann,
            "n_gap": n_gap, "impacted_qids": sorted(impacted_qids),
            "n_total_expected": len(exp.get("articles", [])) + len(exp.get("recitals", [])) + len(exp.get("annexes", [])),
        })
    return rows


def main() -> int:
    print("=" * 70)
    print("Step 1 — Inventario chunk in Qdrant")
    print("=" * 70)
    inv = fetch_qdrant_inventory()
    print(f"Totale chunk scrolled: {len(inv)}")

    by_norm: dict[str, dict] = defaultdict(lambda: {
        "article": 0, "article_fragment": 0, "recital": 0,
        "annex": 0, "annex_point": 0, "other": 0,
        "articles_eids": set(), "recitals_eids": set(), "annexes_eids": set(),
        "all_chunk_ids": set(),
    })
    for p in inv:
        cid = p["chunk_id"]
        prefix, unit = classify(cid)
        if prefix == "?":
            continue
        by_norm[prefix][unit] += 1
        by_norm[prefix]["all_chunk_ids"].add(cid)
        suffix = cid[len(prefix) + 2:]  # dopo "__"
        if unit == "article":
            by_norm[prefix]["articles_eids"].add(suffix)
        elif unit == "article_fragment":
            # mappa al base article eid (es. art_57__paras_1_15 → art_57)
            base = suffix.split("__paras_", 1)[0]
            by_norm[prefix]["articles_eids"].add(base)
        elif unit == "recital":
            by_norm[prefix]["recitals_eids"].add(suffix)
        elif unit in ("annex", "annex_point"):
            m = re.match(r'annex_([IVX]+)', suffix)
            if m:
                by_norm[prefix]["annexes_eids"].add(m.group(1))

    print(f"\n{'Norma':<45} {'art':>5} {'a_frag':>7} {'rec':>5} {'anx':>4} {'anx_pt':>7} {'oth':>5} {'tot':>5}")
    print("-" * 90)
    for prefix, label in NORMS:
        d = by_norm.get(prefix, {})
        tot = sum(d.get(k, 0) for k in ("article","article_fragment","recital","annex","annex_point","other"))
        print(f"{label:<45} {d.get('article',0):>5} {d.get('article_fragment',0):>7} "
              f"{d.get('recital',0):>5} {d.get('annex',0):>4} {d.get('annex_point',0):>7} "
              f"{d.get('other',0):>5} {tot:>5}")

    print("\n" + "=" * 70)
    print("Step 2 — Confronto con atteso (per norma)")
    print("=" * 70)
    expected: dict[str, dict] = {}
    for prefix, label in NORMS:
        if prefix.startswith("eli/"):
            expected[prefix] = expected_eurlex(prefix)
        else:
            expected[prefix] = expected_akn(prefix)
            expected[prefix]["recitals"] = []
            expected[prefix]["annexes"] = []
        exp = expected[prefix]
        eff = by_norm[prefix]
        gap_art = sorted(set(exp.get("articles", [])) - eff["articles_eids"])
        gap_rec = sorted(set(exp.get("recitals", [])) - eff["recitals_eids"],
                         key=lambda s: int(re.search(r'\d+$', s).group()) if re.search(r'\d+$', s) else 0)
        gap_ann = sorted(set(exp.get("annexes", [])) - eff["annexes_eids"], key=_roman_to_int)
        print(f"\n### {label}  ({prefix})")
        print(f"  Attesi   : art={len(exp.get('articles',[]))} rec={len(exp.get('recitals',[]))} ann={len(exp.get('annexes',[]))}")
        print(f"  Effettivi: art={len(eff['articles_eids'])} rec={len(eff['recitals_eids'])} ann={len(eff['annexes_eids'])}")
        if "abrogated" in exp and exp["abrogated"]:
            print(f"  Abrogati nel sorgente AKN: {len(exp['abrogated'])} → {exp['abrogated'][:10]}{'...' if len(exp['abrogated'])>10 else ''}")
        print(f"  Gap articoli ({len(gap_art)}): {gap_art if gap_art else '∅'}")
        print(f"  Gap recital  ({len(gap_rec)}): {gap_rec[:20]}{'...' if len(gap_rec)>20 else ''}")
        print(f"  Gap annex    ({len(gap_ann)}): {gap_ann}")

    print("\n" + "=" * 70)
    print("Step 3 — Verifica Allegati AI Act")
    print("=" * 70)
    ai = "eli/reg/2024/1689/oj"
    exp_ai = expected[ai]
    eff_ai = by_norm[ai]
    expected_annexes = exp_ai.get("annexes", [])
    print(f"{'Annex':<8} {'in HTML':>9} {'chunk in Qdrant':>17} {'gap':>10}")
    print("-" * 50)
    for ann in expected_annexes:
        in_qdrant = ann in eff_ai["annexes_eids"]
        # count chunk for this annex
        n_chunks = sum(1 for cid in eff_ai["all_chunk_ids"] if re.match(rf'{ai}__annex_{ann}(__|$)', cid))
        gap_label = "OK" if in_qdrant else "MANCA"
        print(f"{ann:<8} {'sì':>9} {n_chunks:>17} {gap_label:>10}")

    print("\n" + "=" * 70)
    print("Step 4 — Diagnosi gap (classificazione)")
    print("=" * 70)
    # diagnostica pratica: per ogni norma, prova a leggere fonte e cercare se l'articolo mancante è abrogato
    for prefix, label in NORMS:
        exp = expected[prefix]
        eff = by_norm[prefix]
        gap_art = sorted(set(exp.get("articles", [])) - eff["articles_eids"])
        gap_rec = sorted(set(exp.get("recitals", [])) - eff["recitals_eids"],
                         key=lambda s: int(re.search(r'\d+$', s).group()) if re.search(r'\d+$', s) else 0)
        gap_ann = sorted(set(exp.get("annexes", [])) - eff["annexes_eids"], key=_roman_to_int)
        if not (gap_art or gap_rec or gap_ann):
            continue
        print(f"\n### {label}")
        abrog = set(exp.get("abrogated", []))
        for a in gap_art:
            if a in abrog:
                print(f"  - {a}: causa (b) ABROGATO nel sorgente AKN")
            else:
                print(f"  - {a}: causa da indagare (verosimilmente (a) parser/ingestion)")
        for r in gap_rec:
            print(f"  - {r}: causa da indagare (parser recitals?)")
        for a in gap_ann:
            print(f"  - annex_{a}: causa (d) configurazione ingestione — solo Annex III parsato in v1 (`parse_annex_iii_aiact`)")

    print("\n" + "=" * 70)
    print("Step 5 — Impatto benchmark + priorità")
    print("=" * 70)
    gold_data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    rows = gap_to_priority(by_norm, expected, gold_data)
    print(f"{'Norma':<45} {'gap':>5} {'%':>6} {'query impacted':<30} {'priority'}")
    print("-" * 110)
    for r in rows:
        pct = (r["n_gap"] / r["n_total_expected"] * 100) if r["n_total_expected"] else 0
        # priorità: ALTA se impatta query benchmark, MEDIA se gap >0 ma nessuna query, BASSA se gap=0
        if r["n_gap"] == 0:
            prio = "—"
        elif r["impacted_qids"]:
            prio = f"ALTA ({len(r['impacted_qids'])} query)"
        else:
            prio = "MEDIA"
        qids_str = ",".join(r["impacted_qids"][:10]) + ("..." if len(r["impacted_qids"]) > 10 else "")
        print(f"{r['label']:<45} {r['n_gap']:>5} {pct:>5.1f}% {qids_str:<30} {prio}")

    # global summary
    total_gap = sum(r["n_gap"] for r in rows)
    all_impacted = set()
    for r in rows:
        all_impacted |= set(r["impacted_qids"])
    print(f"\nTOTALE gap: {total_gap} chunk attesi non in Qdrant")
    print(f"TOTALE query benchmark impattate: {len(all_impacted)} → {sorted(all_impacted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
