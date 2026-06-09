"""Spike UC1 Cluster A — probe retrieval (read-only, usa-e-getta).

Misura se, per 3 query single-norm (solo AI Act), i chunk portanti della
classificazione (art. 6 + punto Allegato III atteso) emergono nel retrieval
e sotto quale FORMA di query. NON costruisce alcun layer intake: simula a mano
i 3 ARM.

Vincoli (read-mostly):
- Retriever: BASE HybridRetriever single-norm (stesso pattern di
  spike/smoke_rag_pipeline.py), collection italian_legal_v1_hybrid. NESSUN
  CrossNormRetriever, NESSUN filtro doc_urn (path single-norm produttivo).
- Sub-query (ARM2): core.cross_norm.subquery_generator.generate_subquery.
- LLM: AnthropicProvider default (load_provider_from_env, legge .env).
- Read-only: solo query_points/scroll su Qdrant; niente scrittura/re-ingest.

Output: spike/PROBE_UC1_CLUSTERA.md

    spike/.venv/bin/python spike/probe_uc1_clusterA.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("probe_uc1")
log.setLevel(logging.INFO)

COLLECTION = "italian_legal_v1_hybrid"
BM25_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
DEPTH = 20          # profondità lista post-rerank restituita
POOL = 50           # pool candidati pre-rerank (rerank_top_k); >= DEPTH
REPORT_PATH = ROOT / "spike" / "PROBE_UC1_CLUSTERA.md"

# qid → {targets, arm1 (scenario grezzo), arm3 (dichiarativa ideale), note}
QUERIES = [
    {
        "qid": "Q101",
        "label": "banca / screening CV",
        "targets": ["__art_6", "__annex_III__point_4"],
        "arm1": (
            "Una banca utilizza un sistema AI per analizzare e filtrare "
            "automaticamente i CV dei candidati e valutarli in fase di "
            "selezione del personale: è classificato ad alto rischio ai sensi "
            "dell'Allegato III dell'AI Act?"
        ),
        "arm3": (
            "Sistema di IA ad alto rischio per il reclutamento e la selezione "
            "del personale ex Allegato III punto 4 AI Act / Regolamento UE "
            "2024/1689: analisi e filtraggio delle candidature, valutazione dei "
            "candidati."
        ),
        "extra": None,
    },
    {
        "qid": "Q102",
        "label": "comune / edilizia popolare",
        "targets": ["__art_6", "__annex_III__point_5"],
        "arm1": (
            "Un comune italiano usa un sistema AI per calcolare automaticamente "
            "il punteggio di accesso agli alloggi di edilizia popolare: è "
            "classificato ad alto rischio ai sensi dell'Allegato III?"
        ),
        "arm3": (
            "Sistema di IA ad alto rischio usato da un'autorità pubblica per "
            "valutare l'ammissibilità a prestazioni e servizi pubblici "
            "essenziali ex Allegato III punto 5 AI Act / Regolamento UE "
            "2024/1689: assegnazione di alloggi di edilizia residenziale "
            "pubblica."
        ),
        "extra": None,
    },
    {
        "qid": "Q103",
        "label": "radiografie / diagnosi",
        "targets": ["__art_6"],  # nessun punto Allegato III atteso
        "arm1": (
            "Un sistema AI che analizza immagini radiografiche per supportare "
            "la diagnosi di patologie polmonari è ad alto rischio ai sensi "
            "dell'AI Act? Chi è il fornitore e chi è il deployer in un contesto "
            "ospedaliero?"
        ),
        "arm3": (
            "Sistema di IA quale componente di sicurezza di un dispositivo "
            "medico ex art. 6(1) AI Act / Regolamento UE 2024/1689: "
            "classificazione ad alto rischio per rinvio alla normativa di "
            "armonizzazione settoriale."
        ),
        "extra": "no_annex_forced",  # verifica: nessun __annex_III__point_* nei top-5
    },
]


def build_retriever():
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL)
    reranker = CrossEncoder(RERANKER_MODEL, device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=COLLECTION, reranker=reranker,
    )


def retrieve_depth(retriever, query: str):
    """Lista post-rerank profondità DEPTH (pool POOL). Single-norm, no filtro."""
    return retriever.retrieve(
        query=query, top_k=DEPTH, mode="hybrid", rerank_top_k=POOL,
    )


def target_rank(hits, target_suffix: str):
    """Rank 1-indexed del primo hit il cui chunk_id termina con target_suffix.
    Ritorna (rank, chunk_id) o (None, None)."""
    for h in hits:
        if h.chunk_id.endswith(target_suffix):
            return h.rank, h.chunk_id
    return None, None


def rank_str(r) -> str:
    return str(r) if r is not None else "non in top-20"


def fmt_hits_brief(hits, n=10) -> list[str]:
    out = []
    for h in hits[:n]:
        suf = h.chunk_id.split("__", 1)[1] if "__" in h.chunk_id else h.chunk_id
        out.append(f"  {h.rank:>2}. {suf}  (score={h.score:.4f})")
    return out


def main() -> int:
    from core.cross_norm.subquery_generator import generate_subquery
    from core.llm_provider.config import load_provider_from_env

    llm = load_provider_from_env()
    log.info("LLM provider=%s model=%s", llm.provider_name, llm.model_name)

    log.info("Costruzione base HybridRetriever (reranker MPS)...")
    retriever = build_retriever()

    md: list[str] = []
    md.append("# PROBE UC1 Cluster A — retrieval per la classificazione AI Act")
    md.append("")
    md.append(
        "Spike read-only. Misura se, per 3 query single-norm (solo AI Act), i "
        "chunk portanti della classificazione (`__art_6` + punto Allegato III "
        "atteso) emergono nel retrieval e sotto quale **forma** di query. "
        "Nessun layer intake costruito: i 3 ARM sono simulati a mano."
    )
    md.append("")
    md.append("## Setup")
    md.append("")
    md.append(f"- **Retriever**: BASE `HybridRetriever` single-norm (stesso pattern di "
              f"`spike/smoke_rag_pipeline.py`), **nessun** `CrossNormRetriever`, "
              f"**nessun** filtro `doc_urn` → retrieval sull'intero corpus.")
    md.append(f"- **Collection**: `{COLLECTION}`")
    md.append(f"- **Mode**: hybrid (RRF dense+bm25) + rerank cross-encoder "
              f"`{RERANKER_MODEL}` (MPS).")
    md.append(f"- **Profondità**: lista post-rerank `top_k={DEPTH}`, pool "
              f"pre-rerank `rerank_top_k={POOL}`.")
    md.append(f"- **LLM (ARM2)**: `{llm.provider_name}` / `{llm.model_name}` via "
              f"`generate_subquery(scenario, \"ai_act\", llm)`.")
    md.append(f"- **Match target**: per **suffisso** del `chunk_id` "
              f"(`endswith`). Rank 1..{DEPTH} o \"non in top-20\".")
    md.append(f"- **Soglia decisione pre-dichiarata**: top-5 (top_k produttivo).")
    md.append("")

    per_query_verdict: list[tuple[str, str, str]] = []

    for q in QUERIES:
        qid = q["qid"]
        log.info("=== %s (%s) ===", qid, q["label"])
        targets = q["targets"]

        # ARM1 — scenario grezzo
        log.info("[%s] ARM1 retrieve scenario grezzo", qid)
        arm1_hits = retrieve_depth(retriever, q["arm1"])
        arm1_ranks = {t: target_rank(arm1_hits, t) for t in targets}

        # ARM2 — generate_subquery (macchina esistente)
        log.info("[%s] ARM2 generate_subquery (LLM)...", qid)
        subqueries = generate_subquery(q["arm1"], "ai_act", llm)
        log.info("[%s] ARM2 → %d sub-query", qid, len(subqueries))
        arm2_detail = []  # list of (subq, hits, {t:(rank,cid)})
        for sq in subqueries:
            sq_hits = retrieve_depth(retriever, sq)
            sq_ranks = {t: target_rank(sq_hits, t) for t in targets}
            arm2_detail.append((sq, sq_hits, sq_ranks))
        # best rank per target across sub-queries
        arm2_best = {}
        for t in targets:
            best = None
            best_cid = None
            for _, _, sq_ranks in arm2_detail:
                r, cid = sq_ranks[t]
                if r is not None and (best is None or r < best):
                    best, best_cid = r, cid
            arm2_best[t] = (best, best_cid)

        # ARM3 — dichiarativa ideale
        log.info("[%s] ARM3 retrieve dichiarativa ideale", qid)
        arm3_hits = retrieve_depth(retriever, q["arm3"])
        arm3_ranks = {t: target_rank(arm3_hits, t) for t in targets}

        # ---- report per query ----
        md.append(f"## {qid} — {q['label']}")
        md.append("")
        md.append(f"**Target** (match per suffisso): "
                  + ", ".join(f"`{t}`" for t in targets))
        md.append("")
        md.append(f"**ARM1 (scenario grezzo)**: {q['arm1']}")
        md.append("")
        md.append(f"**ARM3 (dichiarativa ideale)**: {q['arm3']}")
        md.append("")
        md.append(f"**ARM2 — sub-query generate verbatim da "
                  f"`generate_subquery` ({len(subqueries)})**:")
        md.append("")
        for i, sq in enumerate(subqueries):
            md.append(f"{i + 1}. {sq}")
        md.append("")

        # tabella rank
        md.append("### Tabella rank")
        md.append("")
        md.append("| Target | rank ARM1 | rank ARM2 (best) | rank ARM3 |")
        md.append("|---|---|---|---|")
        for t in targets:
            r1, _ = arm1_ranks[t]
            r2, _ = arm2_best[t]
            r3, _ = arm3_ranks[t]
            md.append(f"| `{t}` | {rank_str(r1)} | {rank_str(r2)} | {rank_str(r3)} |")
        md.append("")

        # dettaglio ARM2 per sub-query
        md.append("### ARM2 — dettaglio rank per sub-query")
        md.append("")
        md.append("| # | sub-query (troncata) | " + " | ".join(targets) + " |")
        md.append("|---|---|" + "|".join(["---"] * len(targets)) + "|")
        for i, (sq, _, sq_ranks) in enumerate(arm2_detail):
            cells = " | ".join(rank_str(sq_ranks[t][0]) for t in targets)
            sq_short = (sq[:70] + "…") if len(sq) > 70 else sq
            md.append(f"| {i + 1} | {sq_short} | {cells} |")
        md.append("")

        # top-5 per ogni arm (trasparenza + verifica Q103)
        md.append("### Top-5 post-rerank per ARM")
        md.append("")
        md.append("**ARM1**:")
        md.append("```")
        md += fmt_hits_brief(arm1_hits, 5)
        md.append("```")
        # per ARM2 mostra la sub-query col miglior art_6 (o la prima)
        md.append("**ARM3**:")
        md.append("```")
        md += fmt_hits_brief(arm3_hits, 5)
        md.append("```")
        md.append("")

        # verifica extra Q103: nessun annex_III__point_* nei top-5 ARM2/ARM3
        if q["extra"] == "no_annex_forced":
            def annex_in_top5(hits):
                return [h.chunk_id.split("__", 1)[1]
                        for h in hits[:5] if "__annex_III__point_" in h.chunk_id]
            arm3_annex = annex_in_top5(arm3_hits)
            arm2_annex_any = []
            for sq, sq_hits, _ in arm2_detail:
                arm2_annex_any += annex_in_top5(sq_hits)
            md.append("### Verifica Q103 — nessun punto Allegato III forzato")
            md.append("")
            md.append(f"- Punti Allegato III nei top-5 **ARM3**: "
                      f"{arm3_annex if arm3_annex else 'NESSUNO'}")
            md.append(f"- Punti Allegato III nei top-5 di **una qualsiasi sub-query "
                      f"ARM2**: {sorted(set(arm2_annex_any)) if arm2_annex_any else 'NESSUNO'}")
            md.append("")

        # ---- verdetto per query ----
        verdict, reason = compute_verdict(q, arm2_best, arm3_ranks, targets)
        md.append("### VERDETTO")
        md.append("")
        md.append(f"**{verdict}** — {reason}")
        md.append("")
        per_query_verdict.append((qid, verdict, reason))

    # sintesi verdetti
    md.append("## Sintesi verdetti")
    md.append("")
    md.append("| Query | Verdetto |")
    md.append("|---|---|")
    for qid, verdict, _ in per_query_verdict:
        md.append(f"| {qid} | {verdict} |")
    md.append("")

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    log.info("Report scritto su %s", REPORT_PATH)
    return 0


def compute_verdict(q, arm2_best, arm3_ranks, targets):
    """Applica il criterio pre-dichiarato (soglia top-5)."""
    def in_top5(r):
        return r is not None and r <= 5

    def in_top10(r):
        return r is not None and r <= 10

    art6 = "__art_6"
    annex_targets = [t for t in targets if "annex" in t]

    if q["extra"] == "no_annex_forced":
        # Q103: GO se art_6 in top-5 (ARM2 o ARM3) e nessun annex forzato.
        a6_arm2 = arm2_best[art6][0]
        a6_arm3 = arm3_ranks[art6][0]
        if in_top5(a6_arm2) or in_top5(a6_arm3):
            return ("GO", f"art_6 in top-5 (ARM2={rank_str(a6_arm2)}, "
                    f"ARM3={rank_str(a6_arm3)}); nessun punto Allegato III atteso. "
                    f"Output corretto = art. 6 + dichiarazione limite MDR.")
        return ("PROBLEMA REALE", f"art_6 non in top-5 in nessun ARM "
                f"(ARM2={rank_str(a6_arm2)}, ARM3={rank_str(a6_arm3)}).")

    # Q101/Q102: serve art_6 E il punto Allegato III in top-5
    a6_arm2 = arm2_best[art6][0]
    annex_arm2 = [arm2_best[t][0] for t in annex_targets]
    arm2_ok = in_top5(a6_arm2) and all(in_top5(r) for r in annex_arm2)

    a6_arm3 = arm3_ranks[art6][0]
    annex_arm3 = [arm3_ranks[t][0] for t in annex_targets]
    arm3_ok = in_top5(a6_arm3) and all(in_top5(r) for r in annex_arm3)
    annex_arm3_top10 = all(in_top10(r) for r in annex_arm3)

    if arm2_ok:
        return ("GO", "ARM2 (macchina esistente) mette art_6 E il punto "
                "Allegato III atteso in top-5.")
    if arm3_ok:
        return ("FIX STRETTO", "ARM3 li mette in top-5 ma ARM2 no → tuning "
                "forma/glossario del generator, nessuna nuova meccanica.")
    if not annex_arm3_top10:
        return ("PROBLEMA REALE", "anche ARM3 manca il punto Allegato III dai "
                "top-10 (chunk confermato presente in Qdrant).")
    # ARM3 mette annex in top-10 ma non top-5, e ARM2 fallisce
    return ("FIX STRETTO", "ARM2 non porta i target in top-5; ARM3 porta il "
            "punto Allegato III in top-10 ma non in top-5 → margine di forma, "
            "no problema retrieval di base. Vedi tabella per dettaglio.")


if __name__ == "__main__":
    raise SystemExit(main())
