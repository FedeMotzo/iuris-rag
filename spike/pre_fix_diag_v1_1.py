"""PRE_FIX_DIAG_v1_1 — due diagnostiche indipendenti.

Parte 1: Q24, Q25, Q26, Q27, Q76, Q85
  - retrieval position dai F.2 archived outputs
  - corpus check: esiste il gold chunk in Qdrant?
  - estrazione riferimenti c.p. dal testo del chunk gold (regex)
  - classificazione: retrieval gap vs corpus gap

Parte 2: Q68-Q71 filtered retrieval per-norma
  - per ogni gold ASSENTE nel top-20 globale F.2
  - rilancio hybrid + reranker con filter doc_urn == <norma>
  - gold position nel filtered top-10

Prerequisiti:
  - Qdrant su localhost:6333, collection italian_legal_v1_hybrid
  - F.2 archived: data/benchmark/ragas_pipeline_outputs_v2.json
  - gold v3: data/benchmark/gold_answers_v3.json

    spike/.venv/bin/python spike/pre_fix_diag_v1_1.py
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("pre_fix_diag")

GOLD_PATH    = ROOT / "data/benchmark/gold_answers_v3.json"
F2_PATH      = ROOT / "data/benchmark/ragas_pipeline_outputs_v2.json"
REPORT_PATH  = ROOT / "spike/PRE_FIX_DIAG_v1_1.md"
COLLECTION   = "italian_legal_v1_hybrid"

# Regex reati c.p. richiamati nei chunk (es: "art. 615-ter c.p." / "art. 615-ter del codice penale")
CP_RE = re.compile(
    r"art(?:icolo|\.)\s*(\d+[\-\w]*(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|'[\w]+))?)"
    r"\s+(?:c\.p\.|cod(?:\.|ice)\s*pen(?:\.|ale)?)",
    re.IGNORECASE,
)

NORM_PREFIXES = [
    ("eli/reg/2016/679/oj",                                    "GDPR"),
    ("eli/reg/2024/1689/oj",                                   "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196",    "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231",    "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138",    "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132",                  "L. 132/2025"),
]
# map prefix → doc_urn value (same as prefix for these corpora)
PREFIX_TO_NORM = {p: n for p, n in NORM_PREFIXES}
NORM_TO_DOC_URN = {
    "GDPR":           "eli/reg/2016/679/oj",
    "AI Act":         "eli/reg/2024/1689/oj",
    "Codice Privacy": "akn/it/act/decreto_legislativo/stato/2003-06-30/196",
    "D.Lgs 231/2001": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
    "NIS2":           "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    "L. 132/2025":    "akn/it/act/legge/stato/2025-09-23/132",
}

PART1_QIDS = ["Q24", "Q25", "Q26", "Q27", "Q76", "Q85"]
PART2_QIDS = ["Q68", "Q69", "Q70", "Q71"]


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


# ---------------------------------------------------------------------------
# Qdrant helpers

def fetch_chunk_text(client, chunk_id: str) -> str | None:
    """Fetch text payload for a chunk_id via scroll with filter."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue
    res, _ = client.scroll(
        collection_name=COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))]),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    if res:
        return res[0].payload.get("text", "")
    return None


def chunk_exists(client, chunk_id: str) -> bool:
    return fetch_chunk_text(client, chunk_id) is not None


# ---------------------------------------------------------------------------
# Filtered hybrid retrieval helpers (bypass HybridRetriever for filter support)

def query_hybrid_filtered(client, encoder, bm25, reranker, query: str,
                           doc_urn: str, top_k: int = 10) -> list[dict]:
    """Hybrid RRF retrieval filtrato per doc_urn, con reranker top_k."""
    from qdrant_client import models
    from core.vector_store import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
    from core.terminology import expand_query

    query_exp = expand_query(query)
    [dvec] = encoder.encode([query_exp], batch_size=1)
    emb = next(bm25.query_embed(query_exp))
    svec = models.SparseVector(
        indices=emb.indices.tolist(),
        values=emb.values.tolist(),
    )

    filt = models.Filter(must=[
        models.FieldCondition(key="doc_urn", match=models.MatchValue(value=doc_urn))
    ])
    prefetch_limit = max(top_k * 2, 20)

    pts = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            models.Prefetch(query=dvec.tolist() if hasattr(dvec, 'tolist') else list(dvec),
                            using=DENSE_VECTOR_NAME, limit=prefetch_limit,
                            filter=filt),
            models.Prefetch(query=svec,
                            using=SPARSE_VECTOR_NAME, limit=prefetch_limit,
                            filter=filt),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=prefetch_limit,
        with_payload=True,
    ).points

    if not pts:
        return []

    # Rerank
    pairs = [(query_exp, (p.payload or {}).get("text", "")) for p in pts]
    scores = reranker.predict(pairs, show_progress_bar=False)
    ranked = sorted(zip(pts, scores), key=lambda x: float(x[1]), reverse=True)

    results = []
    for rank, (pt, sc) in enumerate(ranked[:top_k], start=1):
        payload = dict(pt.payload or {})
        results.append({
            "rank": rank,
            "chunk_id": payload.get("chunk_id", ""),
            "score": float(sc),
        })
    return results


# ---------------------------------------------------------------------------
# Main

def main() -> int:
    from qdrant_client import QdrantClient

    gold_entries = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    by_qid_gold = {e["qid"]: e for e in gold_entries}

    f2_data = json.loads(F2_PATH.read_text(encoding="utf-8"))
    by_qid_f2 = {o["qid"]: o for o in f2_data.get("outputs", [])}

    client = QdrantClient(host="localhost", port=6333)

    # -----------------------------------------------------------------------
    # PARTE 1: corpus check + retrieval gap su Q24,Q25,Q26,Q27,Q76,Q85
    # -----------------------------------------------------------------------
    log.info("=== PARTE 1: corpus check ===")

    part1_rows: list[dict] = []   # per tabella sintetica finale

    p1_sections: list[str] = []
    p1_sections.append("## Parte 1 — Q25 corpus check (6 query)")
    p1_sections.append("")
    p1_sections.append(
        "Source retrieval: F.2 archived (`ragas_pipeline_outputs_v2.json`, "
        "config produttiva v1.0 hybrid RRF + bge-reranker-v2-m3, top_k=20)."
    )
    p1_sections.append("")

    for qid in PART1_QIDS:
        entry = by_qid_gold.get(qid)
        f2 = by_qid_f2.get(qid)
        if not entry or not f2:
            p1_sections.append(f"### {qid}\n\n⚠ qid non trovato in gold v3 o F.2 output.\n")
            continue

        question = entry["question"]
        gold_chunks_meta = entry.get("gold_chunks", [])
        gold_ids = [g["chunk_id"] for g in gold_chunks_meta if g.get("chunk_id")]
        gold_set = set(gold_ids)

        # top-20 F.2
        ret_chunks = f2.get("retrieved_chunks", [])
        retrieved_ids = [c["chunk_id"] for c in ret_chunks]
        retrieved_set = set(retrieved_ids)

        p1_sections.append(f"### {qid}")
        p1_sections.append("")
        p1_sections.append(f"**Query**: {question}")
        p1_sections.append("")
        p1_sections.append(f"**Gold attesi** ({len(gold_ids)} chunk):")
        for cid in gold_ids:
            p1_sections.append(f"- `{cid}`  _({norm_of(cid)})_")
        p1_sections.append("")

        p1_sections.append("**Gold position nei top-20 produttivi v1.0** (F.2 archived):")
        for cid in gold_ids:
            if cid in retrieved_set:
                rank = retrieved_ids.index(cid) + 1
                score = next((c["score"] for c in ret_chunks if c["chunk_id"] == cid), "?")
                p1_sections.append(f"- `{cid}` → rank {rank} (score {score:.4f})")
            else:
                p1_sections.append(f"- `{cid}` → **ASSENTE** in top-20")
        p1_sections.append("")

        # Corpus check + c.p. extraction
        p1_sections.append("**Corpus check e riferimenti c.p.** (fetch da Qdrant):")
        p1_sections.append("")
        for cid in gold_ids:
            text = fetch_chunk_text(client, cid)
            in_corpus = text is not None
            cp_refs = CP_RE.findall(text) if text else []

            if not in_corpus:
                classification = "🔴 CORPUS GAP — chunk assente in Qdrant"
            elif cid not in retrieved_set:
                classification = "🟡 RETRIEVAL GAP — in corpus ma non nei top-20"
            else:
                rank = retrieved_ids.index(cid) + 1
                classification = f"✅ TROVATO — rank {rank}"

            p1_sections.append(f"**`{cid}`**")
            p1_sections.append(f"- Norma: {norm_of(cid)}")
            p1_sections.append(f"- In corpus: {'sì' if in_corpus else '**NO**'}")
            p1_sections.append(f"- Classificazione: {classification}")
            if cp_refs:
                p1_sections.append(f"- Riferimenti c.p. nel testo: {', '.join(sorted(set(cp_refs)))}")
            else:
                p1_sections.append("- Riferimenti c.p. nel testo: nessuno rilevato")
            p1_sections.append("")

            part1_rows.append({
                "qid": qid,
                "chunk_id": cid,
                "in_corpus": in_corpus,
                "retrieved": cid in retrieved_set,
                "rank": retrieved_ids.index(cid) + 1 if cid in retrieved_set else None,
                "cp_refs": cp_refs,
            })

    # tabella sintetica parte 1
    p1_sections.append("### Tabella sintetica Parte 1")
    p1_sections.append("")
    p1_sections.append("| qid | chunk_id | in corpus? | rank top-20 | classificazione | ref c.p. |")
    p1_sections.append("|---|---|:---:|:---:|---|---|")
    for r in part1_rows:
        in_c = "✅" if r["in_corpus"] else "❌"
        rank_s = str(r["rank"]) if r["rank"] else "ASSENTE"
        if not r["in_corpus"]:
            cls = "CORPUS GAP"
        elif not r["retrieved"]:
            cls = "RETRIEVAL GAP"
        else:
            cls = f"trovato rank {r['rank']}"
        cp = ", ".join(sorted(set(r["cp_refs"]))) if r["cp_refs"] else "—"
        cid_short = r["chunk_id"].split("__")[-1] if "__" in r["chunk_id"] else r["chunk_id"]
        p1_sections.append(f"| {r['qid']} | `…{cid_short}` | {in_c} | {rank_s} | {cls} | {cp} |")
    p1_sections.append("")

    n_corpus_gap = sum(1 for r in part1_rows if not r["in_corpus"])
    n_retrieval_gap = sum(1 for r in part1_rows if r["in_corpus"] and not r["retrieved"])
    n_found = sum(1 for r in part1_rows if r["retrieved"])
    p1_sections.append(
        f"**Conteggio**: {n_corpus_gap} corpus gap · "
        f"{n_retrieval_gap} retrieval gap · "
        f"{n_found} trovati nei top-20 "
        f"(totale gold: {len(part1_rows)})"
    )
    p1_sections.append("")

    # -----------------------------------------------------------------------
    # PARTE 2: filtered retrieval Q68-Q71
    # -----------------------------------------------------------------------
    log.info("=== PARTE 2: filtered retrieval Q68-Q71 ===")

    # Verifica payload schema prima di procedere
    info = client.get_collection(COLLECTION)
    schema = info.payload_schema
    log.info("Payload schema: %s", schema)
    if schema:
        log.info("doc_urn indexed: %s", "doc_urn" in schema)
    else:
        log.info("Nessun payload index — filtro via full scan (OK per diagnostica)")

    # Carica modelli (una sola volta)
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder

    BM25_MODEL     = "Qdrant/bm25"
    RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

    encoder  = BgeM3Encoder.get(device="mps")
    bm25     = SparseTextEmbedding(model_name=BM25_MODEL)
    reranker = CrossEncoder(RERANKER_MODEL, device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)

    p2_sections: list[str] = []
    p2_sections.append("## Parte 2 — Q68-Q71 filtered retrieval per-norma")
    p2_sections.append("")
    p2_sections.append(
        "Payload schema Qdrant: nessun payload index (`payload_schema={}`). "
        "Filtro su `doc_urn` via full scan — funzionale per diagnostica."
    )
    p2_sections.append("")

    # tabella summary parte 2
    summary_rows: list[dict] = []

    for qid in PART2_QIDS:
        entry = by_qid_gold.get(qid)
        f2    = by_qid_f2.get(qid)
        if not entry or not f2:
            p2_sections.append(f"### {qid}\n\n⚠ qid non trovato.\n")
            continue

        question = entry["question"]
        gold_chunks_meta = entry.get("gold_chunks", [])
        gold_ids = [g["chunk_id"] for g in gold_chunks_meta if g.get("chunk_id")]
        gold_set = set(gold_ids)

        ret_chunks = f2.get("retrieved_chunks", [])
        retrieved_ids = [c["chunk_id"] for c in ret_chunks]
        retrieved_set = set(retrieved_ids)

        # Gold ASSENTI nei top-20 globali
        absent_gold = [cid for cid in gold_ids if cid not in retrieved_set]

        p2_sections.append(f"### {qid} — Filtered retrieval per norme assenti")
        p2_sections.append("")
        p2_sections.append(f"**Query**: {question[:120]}")
        p2_sections.append("")
        p2_sections.append(f"**Gold totali**: {len(gold_ids)} · **Assenti in globale v1.0**: {len(absent_gold)}")
        p2_sections.append("")

        if not absent_gold:
            p2_sections.append("Tutti i gold trovati in top-20 globale. Filtered retrieval non necessario.")
            p2_sections.append("")
            continue

        # Raggruppa assenti per norma → filtered retrieval per ciascuna norma unica
        by_norm_absent: dict[str, list[str]] = defaultdict(list)
        for cid in absent_gold:
            by_norm_absent[norm_of(cid)].append(cid)

        for norm_label, norm_absent_ids in sorted(by_norm_absent.items()):
            doc_urn = NORM_TO_DOC_URN.get(norm_label)
            if not doc_urn:
                p2_sections.append(f"#### Norma: {norm_label}")
                p2_sections.append(f"⚠ doc_urn non mappato per `{norm_label}` — skip.")
                p2_sections.append("")
                continue

            log.info("[%s] filtered retrieval norm=%s (doc_urn=%s)", qid, norm_label, doc_urn)

            p2_sections.append(f"#### Norma: {norm_label}")
            p2_sections.append(f"- `doc_urn` filtro: `{doc_urn}`")
            p2_sections.append(f"- Gold attesi in questa norma: {', '.join(f'`{c}`' for c in norm_absent_ids)}")
            p2_sections.append("")

            filtered_hits = query_hybrid_filtered(
                client, encoder, bm25, reranker, question,
                doc_urn=doc_urn, top_k=10,
            )

            if not filtered_hits:
                p2_sections.append("_Nessun hit restituito con questo filtro._")
                p2_sections.append("")
                for cid in norm_absent_ids:
                    summary_rows.append({
                        "qid": qid, "norm": norm_label, "gold": cid,
                        "rank_global": "ASSENTE",
                        "rank_filtered": "ASSENTE (0 hit)",
                    })
                continue

            filtered_ids = [h["chunk_id"] for h in filtered_hits]
            filtered_set  = set(filtered_ids)

            p2_sections.append("**Top-10 retrieval con filter** `doc_urn=" + doc_urn + "`:")
            p2_sections.append("")
            p2_sections.append("| rank | chunk_id | score | gold? |")
            p2_sections.append("|---:|---|---:|:---:|")
            for h in filtered_hits:
                mark = "✓" if h["chunk_id"] in gold_set else "-"
                p2_sections.append(f"| {h['rank']} | `{h['chunk_id']}` | {h['score']:.4f} | {mark} |")
            p2_sections.append("")

            for cid in norm_absent_ids:
                if cid in filtered_set:
                    r_filt = filtered_ids.index(cid) + 1
                    rank_filtered = f"rank {r_filt}"
                else:
                    rank_filtered = "ASSENTE"
                p2_sections.append(f"**Gold `{cid}`** → filtered rank: {rank_filtered}")
                summary_rows.append({
                    "qid": qid, "norm": norm_label, "gold": cid,
                    "rank_global": "ASSENTE",
                    "rank_filtered": rank_filtered,
                })
            p2_sections.append("")

    # tabella sintetica parte 2
    p2_sections.append("### Tabella sintetica Parte 2")
    p2_sections.append("")
    p2_sections.append("| Query | Norma | Gold chunk | Rank globale v1.0 | Rank filtered |")
    p2_sections.append("|---|---|---|:---:|:---:|")
    for r in summary_rows:
        cid_short = r["gold"].split("__")[-1] if "__" in r["gold"] else r["gold"]
        p2_sections.append(
            f"| {r['qid']} | {r['norm']} | `…{cid_short}` | {r['rank_global']} | {r['rank_filtered']} |"
        )
    p2_sections.append("")

    rescued  = sum(1 for r in summary_rows if r["rank_filtered"] not in ("ASSENTE", "ASSENTE (0 hit)"))
    n_absent = len(summary_rows)
    ratio    = f"{rescued}/{n_absent}" if n_absent else "n/a"
    p2_sections.append(f"**Filtered rescue ratio**: {ratio} gold trovati in filtered top-10 / gold ASSENTI in globale top-20")
    p2_sections.append("")

    # -----------------------------------------------------------------------
    # Sintesi numerica finale
    # -----------------------------------------------------------------------
    syn: list[str] = []
    syn.append("## Sintesi numerica")
    syn.append("")
    syn.append("### Parte 1 — corpus gap vs retrieval gap (6 query, gold 231 e cross-norma)")
    syn.append("")
    syn.append(f"- Gold totali analizzati: **{len(part1_rows)}**")
    syn.append(f"- Corpus gap (chunk non in Qdrant): **{n_corpus_gap}**")
    syn.append(f"- Retrieval gap (in corpus, non nei top-20): **{n_retrieval_gap}**")
    syn.append(f"- Trovati nei top-20: **{n_found}**")
    syn.append("")
    syn.append("### Parte 2 — filtered rescue ratio (Q68-Q71)")
    syn.append("")
    syn.append(f"- Gold ASSENTI in globale top-20 analizzati: **{n_absent}**")
    syn.append(f"- Trovati in filtered top-10: **{rescued}**")
    syn.append(f"- Filtered rescue ratio: **{ratio}**")
    syn.append("")

    # -----------------------------------------------------------------------
    # Assembla file finale
    # -----------------------------------------------------------------------
    sections: list[str] = []
    sections.append("# PRE_FIX_DIAG v1.1 — corpus check + filtered retrieval")
    sections.append("")
    sections.append(
        "Branch: `diag/pre-fix-v1-1`. "
        "Nessun judge, nessuna generation, nessun commit a main."
    )
    sections.append("")
    sections.extend(p1_sections)
    sections.append("---")
    sections.append("")
    sections.extend(p2_sections)
    sections.append("---")
    sections.append("")
    sections.extend(syn)

    REPORT_PATH.write_text("\n".join(sections), encoding="utf-8")
    log.info("Report scritto: %s", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
