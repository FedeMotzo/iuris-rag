"""Smoke gold comparison (W6).

Esegue le 5 query selezionate dallo spec
(`spike/SMOKE_GOLD_COMPARISON_SPEC.md`) contro la pipeline RAG cloud
(`provider=anthropic`, `claude-sonnet-4-6`) e produce
`spike/SMOKE_GOLD_COMPARISON.md` pronto per la lettura/giudizio
umano (Federico).

1 run per query, no warmup interno (la pipeline ce l'ha già).
top_k=5, rerank_top_k=20, use_graph=False, max_output_tokens=1000.

Lo script popola solo i campi automatici (recall@5, citazioni
strutturali, finish_reason, token, annotated_answer, gold_answer e
checklist sostantive in stato vuoto `- [ ]`). I campi di giudizio
umano restano placeholder.

    spike/.venv/bin/python spike/smoke_gold_comparison.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("smoke_gold_comparison")

COLLECTION = "italian_legal_v1_hybrid"
BM25_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
TARGET_QIDS = ["Q6", "Q1", "Q9", "Q43", "Q47"]
GOLD_PATH = ROOT / "data/benchmark/gold_answers_v1.json"
SPEC_PATH = ROOT / "spike/SMOKE_GOLD_COMPARISON_SPEC.md"
RESULTS_PATH = ROOT / "spike/SMOKE_GOLD_COMPARISON.md"

# Checklist sostantive pre-compilate dallo spec (sezione "Checklist
# sostantive"). Copiate verbatim qui per tenere lo script
# self-contained; la spec resta la fonte di verità.
CHECKLISTS: dict[str, list[str]] = {
    "Q6": [
        "informa/consiglia titolare e dipendenti sugli obblighi",
        "sorveglia osservanza GDPR + politiche interne (incl. sensibilizzazione/formazione)",
        "fornisce parere su DPIA e ne sorveglia svolgimento (art. 35)",
        "coopera con autorità di controllo, funge da punto di contatto",
        "riferimento art. 39 GDPR",
    ],
    "Q1": [
        "art. 6 par. 2 AI Act come fonte del meccanismo",
        "rinvio ad Allegato III come elenco operativo",
        "menziona almeno 2-3 settori dell'Allegato (istruzione, occupazione, accesso a servizi essenziali, law enforcement, biometria, infrastrutture critiche)",
        "art. 6 par. 3: eccezione \"rischio non significativo\" + condizioni",
        "NON confonde con art. 5 (pratiche vietate) e NON usa considerando come fonte dispositiva",
    ],
    "Q9": [
        "cita art. 24-bis D.Lgs 231/2001 come fonte",
        "menziona delitti informatici / trattamento illecito dati come categoria",
        "indica sanzioni 231 (pecuniarie e/o interdittive)",
        "**dichiara esplicitamente che il dettaglio degli articoli del codice penale richiamati non è incluso nel corpus normativo di riferimento**",
        "NON inventa contenuti dell'art. 25-undecies (anti-allucinazione)",
    ],
    "Q43": [
        "cita GDPR (Regolamento UE 2016/679) come fonte principale UE",
        "cita D.Lgs 196/2003 (Codice Privacy) come integrazione nazionale italiana",
        "indica oggetto del GDPR: protezione persone fisiche nel trattamento dei dati personali + libera circolazione",
        "menziona diritti/libertà fondamentali, in particolare diritto alla protezione dei dati personali",
        "dichiara selettività/limite del corpus E NON espone contenuto dispositivo specifico (basi giuridiche, diritti, sicurezza, DPIA, sanzioni) come se fosse supportato dai chunk recuperati",
    ],
    "Q47": [
        "dichiara esplicitamente che l'articolo non esiste nel corpus",
        "NON inventa contenuto plausibile",
        "non finge di aver trovato il riferimento",
        "(opzionale, non conta nel totale) suggerisce articoli vicini realmente esistenti",
    ],
}


def load_gold() -> dict[str, dict]:
    """Carica gold_answers_v1.json e restituisce {qid: entry} per i TARGET_QIDS.

    Fail loud se manca una qid attesa.
    """
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    by_qid = {q["qid"]: q for q in data}
    missing = [qid for qid in TARGET_QIDS if qid not in by_qid]
    if missing:
        raise RuntimeError(
            f"Gold dataset {GOLD_PATH} non contiene le qid attese: {missing}"
        )
    return {qid: by_qid[qid] for qid in TARGET_QIDS}


def build_retriever(reranker_device: str):
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL)
    log.info("Reranker device=%s", reranker_device)
    reranker = CrossEncoder(RERANKER_MODEL, device=reranker_device, max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    return HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=COLLECTION, reranker=reranker,
    )


def gold_chunk_ids(entry: dict) -> list[str]:
    return [g["chunk_id"] for g in entry.get("gold_chunks", []) if g.get("chunk_id")]


def main() -> int:
    # Carica .env PRIMA di decidere la topologia. load_dotenv usa override=False,
    # quindi env vars già esportate dalla shell vincono sulla .env.
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        log.info("Caricato .env da %s", env_path)

    provider_choice = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider_choice != "anthropic":
        raise RuntimeError(
            "Smoke gold comparison è cloud-only (provider=anthropic). "
            f"Trovato LLM_PROVIDER={provider_choice!r}. Aggiusta .env o env."
        )
    reranker_device = "mps"
    log.info("Smoke gold comparison — provider=%s (reranker %s)",
             provider_choice, reranker_device.upper())

    gold = load_gold()

    from core.serving import build_default_pipeline

    retriever = build_retriever(reranker_device)
    pipeline = build_default_pipeline(retriever)

    # Per-query results, raccolti prima di emettere il markdown.
    rows: list[dict] = []
    for qid in TARGET_QIDS:
        entry = gold[qid]
        question = entry["question"]
        gold_ids = gold_chunk_ids(entry)
        log.info("=== %s: %s", qid, question)
        t0 = time.perf_counter()
        try:
            resp = pipeline.query(question)
        except Exception as exc:  # noqa: BLE001 — fail loud per smoke
            raise RuntimeError(
                f"Pipeline fallita su {qid} ({question!r}): {exc}"
            ) from exc
        wall_ms = (time.perf_counter() - t0) * 1000

        top5_ids = [h.chunk_id for h in resp.retrieval_result][:5]
        hit = next((c for c in top5_ids if c in set(gold_ids)), None)
        recall_at_5 = hit is not None

        log.info(
            "[%s] retrieval=%.0fms gen=%.0fms verify=%.0fms total=%.0fms "
            "n_cite=%d/%d all_verified=%s recall@5=%s wall=%.0fms",
            qid, resp.timings_ms["retrieval_ms"],
            resp.timings_ms["generate_ms"], resp.timings_ms["verify_ms"],
            resp.timings_ms["total_ms"], resp.verification.n_verified,
            resp.verification.n_total, resp.verification.all_verified,
            recall_at_5, wall_ms,
        )

        rows.append({
            "qid": qid,
            "question": question,
            "gold_ids": gold_ids,
            "gold_answer": entry.get("gold_answer", ""),
            "top5": [
                {
                    "chunk_id": h.chunk_id,
                    "hierarchy": " > ".join(h.payload.get("hierarchy_path") or []),
                }
                for h in resp.retrieval_result[:5]
            ],
            "recall_at_5": recall_at_5,
            "n_verified": resp.verification.n_verified,
            "n_total": resp.verification.n_total,
            "all_verified": resp.verification.all_verified,
            "finish_reason": resp.generation_meta.finish_reason,
            "n_output_tokens": resp.generation_meta.n_output_tokens,
            "ttft_ms": resp.generation_meta.ttft_ms,
            "total_ms": resp.timings_ms["total_ms"],
            "annotated_answer": resp.annotated_answer,
        })

    # ---------- Render markdown ----------
    out: list[str] = []
    out.append("# Smoke gold comparison — risultati")
    out.append("")
    out.append("Data: 2026-05-20")
    out.append(
        f"Provider: **{pipeline._llm.provider_name}** "
        f"({pipeline._llm.model_name}), top_k={pipeline._top_k}, "
        f"rerank_top_k={pipeline._rerank_top_k}, "
        f"use_graph={pipeline.use_graph}, "
        f"max_output_tokens={pipeline._max_tokens}. "
        "1 run/query, no warmup interno aggiuntivo."
    )
    out.append("")
    out.append(f"Spec di riferimento: [`{SPEC_PATH.name}`]({SPEC_PATH.name}).")
    out.append("")
    out.append("Campi automatici popolati dallo script. Campi di giudizio "
               "umano (`checklist N/M`, citazioni semantiche, allucinazioni, "
               "commento, verdict) restano placeholder da compilare a mano.")
    out.append("")

    # Tabella riassuntiva
    out.append("## Tabella riassuntiva")
    out.append("")
    out.append(
        "| qid | recall@5 | n_verified/n_total | finish_reason | "
        "output_tokens | checklist N/M | dich. limite | allucinazione |"
    )
    out.append(
        "|---|---|---|---|---|---|---|---|"
    )
    for r in rows:
        m_total = len(CHECKLISTS[r["qid"]])
        out.append(
            f"| {r['qid']} | {r['recall_at_5']} | "
            f"{r['n_verified']}/{r['n_total']} | {r['finish_reason']} | "
            f"{r['n_output_tokens']} | _/{m_total} | — | — |"
        )
    out.append("")

    # Sezioni per query
    for r in rows:
        qid = r["qid"]
        out.append(f"## {qid}")
        out.append("")
        out.append(f"**Query**: {r['question']}")
        out.append("")
        out.append(
            f"**Automatic**: recall@5={r['recall_at_5']}, "
            f"n_verified={r['n_verified']}/{r['n_total']}, "
            f"all_verified={r['all_verified']}, "
            f"finish_reason={r['finish_reason']}, "
            f"output_tokens={r['n_output_tokens']}, "
            f"TTFT={r['ttft_ms']:.0f}ms, total={r['total_ms']:.0f}ms."
        )
        out.append("")
        out.append("**Top-5 chunk recuperati (post-rerank)**:")
        out.append("")
        for h in r["top5"]:
            marker = " ← gold" if h["chunk_id"] in set(r["gold_ids"]) else ""
            hier = f" ({h['hierarchy']})" if h["hierarchy"] else ""
            out.append(f"- `{h['chunk_id']}`{hier}{marker}")
        out.append("")
        out.append("**Gold chunks attesi**:")
        out.append("")
        if r["gold_ids"]:
            for cid in r["gold_ids"]:
                out.append(f"- `{cid}`")
        else:
            out.append("- _(nessuno — query negative)_")
        out.append("")
        out.append("**Annotated answer**:")
        out.append("")
        out.append("```")
        out.append(r["annotated_answer"].strip())
        out.append("```")
        out.append("")
        out.append("**Gold answer**:")
        out.append("")
        out.append("```")
        out.append((r["gold_answer"] or "").strip())
        out.append("```")
        out.append("")
        out.append("**Checklist sostantiva** (spuntare a mano dopo lettura):")
        out.append("")
        for item in CHECKLISTS[qid]:
            out.append(f"- [ ] {item}")
        out.append("")
        out.append("**Citazioni semantiche** (per max 4 cite: OK | weak | wrong):")
        out.append("")
        out.append("- _placeholder_")
        out.append("")
        out.append("**Allucinazioni semantiche** (claim non supportata dai "
                   "chunk recuperati; sì/no + nota):")
        out.append("")
        out.append("- _placeholder_")
        out.append("")
        out.append("**Commento** (1-2 righe):")
        out.append("")
        out.append("- _placeholder_")
        out.append("")

    out.append("## Verdict finale")
    out.append("")
    out.append("- **GO / NO-GO**: _placeholder_")
    out.append("- **Motivazione (1 riga)**: _placeholder_")
    out.append("")

    RESULTS_PATH.write_text("\n".join(out), encoding="utf-8")
    log.info("Risultati scritti su %s", RESULTS_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
