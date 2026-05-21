"""Ragas W7 — quantitative generation eval su 38 query positive.

REQUISITI: pip install ragas langchain_anthropic langchain_huggingface
(non aggiunti a pyproject.toml volontariamente: lo spike-script segnala,
il dev installa nel venv. Vedi RAGAS_RUN_NOTES.md.)

Due step separati per disaccoppiare la generazione (costosa, ~$0.30)
dalla valutazione Ragas (riusabile, ~$0.30):

- Step 1 `generate` → `data/benchmark/ragas_pipeline_outputs_v1.json`
- Step 2 `judge` → `ragas_results_v1.json` + `ragas_aggregates_v1.json`

CLI:
    python spike/run_ragas_eval.py                  # cache miss → 1+2; cache hit → solo 2
    python spike/run_ragas_eval.py --generate       # solo 1 (overwrite cache)
    python spike/run_ragas_eval.py --judge          # solo 2 (richiede cache)
    python spike/run_ragas_eval.py --force-regenerate  # 1 (overwrite) + 2

Spec di riferimento: RAGAS_RUN_NOTES.md. Pattern: smoke_gold_comparison.py.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("ragas_eval")

GOLD_PATH = ROOT / "data/benchmark/gold_answers_v1.json"
OUTPUTS_PATH = ROOT / "data/benchmark/ragas_pipeline_outputs_v1.json"
RESULTS_PATH = ROOT / "data/benchmark/ragas_results_v1.json"
AGGREGATES_PATH = ROOT / "data/benchmark/ragas_aggregates_v1.json"

COLLECTION = "italian_legal_v1_hybrid"
BM25_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
EMBEDDINGS_MODEL = "BAAI/bge-m3"
JUDGE_MODEL = "claude-sonnet-4-6"
RAGAS_CACHE_DIR = ".ragas_cache"
EXPECTED_POSITIVE = 38


def load_positive_entries() -> list[dict]:
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    positives = [e for e in data if e.get("query_type") == "positive"]
    if len(positives) != EXPECTED_POSITIVE:
        raise RuntimeError(
            f"Attese {EXPECTED_POSITIVE} entry positive, trovate {len(positives)} "
            f"in {GOLD_PATH}."
        )
    return positives


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


def _load_env() -> None:
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        log.info("Caricato .env da %s", env_path)


def step_generate() -> None:
    _load_env()
    provider_choice = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider_choice != "anthropic":
        raise RuntimeError(
            "Ragas eval è cloud-only (provider=anthropic). "
            f"Trovato LLM_PROVIDER={provider_choice!r}. Aggiusta .env o env."
        )

    entries = load_positive_entries()
    log.info("Step 1 generate — %d query positive, provider=anthropic, reranker MPS.",
             len(entries))

    from core.serving import build_default_pipeline

    retriever = build_retriever("mps")
    pipeline = build_default_pipeline(retriever)

    outputs: list[dict] = []
    for entry in entries:
        qid = entry["qid"]
        question = entry["question"]
        log.info("=== %s: %s", qid, question)
        t0 = time.perf_counter()
        try:
            resp = pipeline.query(question)
        except Exception as exc:  # noqa: BLE001 — fail loud per spike
            raise RuntimeError(f"Pipeline fallita su {qid}: {exc}") from exc
        wall_ms = (time.perf_counter() - t0) * 1000

        contexts: list[str] = []
        for h in resp.retrieval_result[: pipeline._top_k]:
            txt = (h.payload.get("text") or "").strip()
            if not txt:
                raise RuntimeError(
                    f"{qid}: chunk {h.chunk_id} senza payload['text']; "
                    "Ragas faithfulness richiede testo integrale."
                )
            contexts.append(txt)

        log.info(
            "[%s] ctx=%d, out_tok=%d, total=%.0fms, wall=%.0fms",
            qid, len(contexts), resp.generation_meta.n_output_tokens,
            resp.timings_ms["total_ms"], wall_ms,
        )

        outputs.append({
            "qid": qid,
            "question": question,
            "contexts": contexts,
            "answer": resp.annotated_answer,
            "ground_truth": entry.get("gold_answer", ""),
            "has_corpus_limit_declaration": entry.get(
                "has_corpus_limit_declaration", False
            ),
        })

    payload = {
        "metadata": {
            "date": date.today().isoformat(),
            "provider": "anthropic",
            "model": pipeline._llm.model_name,
            "n_queries": len(outputs),
            "topology": "S1 reranker MPS",
            "top_k": pipeline._top_k,
            "rerank_top_k": pipeline._rerank_top_k,
            "use_graph": pipeline.use_graph,
            "max_output_tokens": pipeline._max_tokens,
        },
        "outputs": outputs,
    }
    OUTPUTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Scritto %s (%d outputs).", OUTPUTS_PATH, len(outputs))


def _stats(values: list[float]) -> dict[str, float]:
    sv = sorted(values)
    n = len(sv)
    if n >= 2:
        q = statistics.quantiles(sv, n=4)
        p25, p75 = q[0], q[2]
    else:
        p25 = p75 = sv[0]
    return {
        "mean": statistics.fmean(sv),
        "median": statistics.median(sv),
        "p25": p25,
        "p75": p75,
        "min": min(sv),
        "max": max(sv),
    }


def step_judge() -> None:
    if not OUTPUTS_PATH.is_file():
        raise RuntimeError(
            f"Cache pipeline assente: {OUTPUTS_PATH}. "
            "Esegui prima `python spike/run_ragas_eval.py --generate`."
        )
    _load_env()

    payload = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    outputs = payload["outputs"]
    log.info("Step 2 judge — %d query in cache, judge=%s, embeddings=%s.",
             len(outputs), JUDGE_MODEL, EMBEDDINGS_MODEL)

    from anthropic import Anthropic
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.cache import DiskCacheBackend
    from ragas.llms import llm_factory
    from ragas.metrics import answer_relevancy, faithfulness

    samples = [
        {
            "user_input": o["question"],
            "retrieved_contexts": o["contexts"],
            "response": o["answer"],
            "reference": o["ground_truth"],
        }
        for o in outputs
    ]
    dataset = EvaluationDataset.from_list(samples)

    # Judge: Sonnet 4.6 via SDK Anthropic diretto + ragas.llms.llm_factory.
    # Scelta judge: spec voleva Opus 4.7 (RAGAS_RUN_NOTES.md nota 8) ma il
    # primo tentativo è morto a $2.32 con credito esaurito senza scrivere
    # output. Sonnet 4.6 è ~5× più economico (stima ~$0.50-0.70 totale) e
    # sufficiente per faithfulness/answer_relevancy su dominio legale IT.
    # Deviazione documentata nel report W7.
    # Caching: DiskCacheBackend su .ragas_cache/ rende il rilancio idempotente
    # — call già pagate vengono riusate, protegge il budget se la run muore.
    # max_tokens=4096: default ragas 1024 basso per output strutturati JSON.
    # InstructorModelArgs default: temperature=0.01, top_p=0.1, max_tokens=1024.
    # Sonnet 4.6 rifiuta temperature+top_p insieme (400 "cannot both be
    # specified"): pop top_p, tieni temperature=0.01 per determinismo.
    # Opus 4.7 rifiuterebbe entrambi (vedi memoria opus_4_7_api_quirks).
    anthropic_client = Anthropic()  # legge ANTHROPIC_API_KEY da env
    judge_llm = llm_factory(
        JUDGE_MODEL,
        provider="anthropic",
        client=anthropic_client,
        max_tokens=4096,
        cache=DiskCacheBackend(cache_dir=str(ROOT / RAGAS_CACHE_DIR)),
    )
    judge_llm.model_args.pop("top_p", None)
    judge_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

    log.info("Lancio ragas.evaluate (faithfulness + answer_relevancy)…")
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=judge_llm,
        embeddings=judge_embeddings,
    )

    df = result.to_pandas()
    rows = df.to_dict(orient="records")
    if len(rows) != len(outputs):
        raise RuntimeError(
            f"Ragas ha restituito {len(rows)} righe, attese {len(outputs)}."
        )

    per_query: list[dict] = []
    for o, row in zip(outputs, rows, strict=True):
        per_query.append({
            "qid": o["qid"],
            "faithfulness": float(row["faithfulness"]),
            "answer_relevancy": float(row["answer_relevancy"]),
            "has_corpus_limit_declaration": o["has_corpus_limit_declaration"],
        })

    metadata = {
        "date": date.today().isoformat(),
        "judge": JUDGE_MODEL,
        "embeddings": EMBEDDINGS_MODEL,
        "metrics": ["faithfulness", "answer_relevancy"],
    }
    RESULTS_PATH.write_text(
        json.dumps({"metadata": metadata, "results": per_query},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Scritto %s.", RESULTS_PATH)

    group_a = [r for r in per_query if not r["has_corpus_limit_declaration"]]
    group_b = [r for r in per_query if r["has_corpus_limit_declaration"]]

    def block(rs: list[dict]) -> dict:
        return {
            "n": len(rs),
            "faithfulness": _stats([r["faithfulness"] for r in rs]),
            "answer_relevancy": _stats([r["answer_relevancy"] for r in rs]),
        }

    aggregates = {
        "metadata": metadata,
        "group_a_non_limit": block(group_a),
        "group_b_limit": block(group_b),
        "global_all_38": block(per_query),
    }
    AGGREGATES_PATH.write_text(
        json.dumps(aggregates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Scritto %s.", AGGREGATES_PATH)

    print()
    header = (f"{'Gruppo':<24} {'n':>4} "
              f"{'faith median':>13} {'faith mean':>11} "
              f"{'rel median':>11} {'rel mean':>10}")
    print(header)
    print("-" * len(header))
    for name, b in [
        ("A non-limite", aggregates["group_a_non_limit"]),
        ("B limite",     aggregates["group_b_limit"]),
        ("Globale (38)", aggregates["global_all_38"]),
    ]:
        f = b["faithfulness"]
        r = b["answer_relevancy"]
        print(
            f"{name:<24} {b['n']:>4} "
            f"{f['median']:>13.3f} {f['mean']:>11.3f} "
            f"{r['median']:>11.3f} {r['mean']:>10.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ragas W7 eval: step 1 generate + step 2 judge"
    )
    parser.add_argument("--generate", action="store_true",
                        help="Run solo step 1 (overwrite cache).")
    parser.add_argument("--judge", action="store_true",
                        help="Run solo step 2 (richiede cache).")
    parser.add_argument("--force-regenerate", action="store_true",
                        help="Overwrite cache + run judge.")
    args = parser.parse_args()

    n_flags = sum([args.generate, args.judge, args.force_regenerate])
    if n_flags > 1:
        raise SystemExit("Flag mutuamente esclusivi: usane al più uno.")

    if args.force_regenerate:
        step_generate()
        step_judge()
    elif args.generate:
        step_generate()
    elif args.judge:
        step_judge()
    else:
        if OUTPUTS_PATH.is_file():
            log.info("Cache trovata in %s. Skip step 1, run step 2.", OUTPUTS_PATH)
        else:
            log.info("Cache assente. Run step 1 + step 2.")
            step_generate()
        step_judge()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
