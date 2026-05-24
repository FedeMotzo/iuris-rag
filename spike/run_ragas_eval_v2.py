"""Ragas eval v2 — 100 query, **2 metriche** (faithfulness + answer_relevancy).

Riuso di `spike/run_ragas_eval.py` (W7 step_judge) con due modifiche:

1. **(d) context_precision rimossa** dalla pipeline Ragas. Il dry-run Q51
   ha mostrato $0.13/sample con 3 metriche (proiezione $13 su 100, 13×
   sopra spec). Per ridurre cost a target $2-4, droppiamo
   context_precision (la dimensione retrieval-quality è già coperta
   da R@5/R@10/R@20/MRR computati in fase F.1 su tutte le 100 query —
   vedi `spike/BENCHMARK_W3_v2.md`).

2. **(e) Anthropic prompt caching** attivato via wrapping di
   `client.messages.create`. Marca il blocco user content come
   `cache_control: ephemeral`. Efficace solo se i prompt Ragas
   condividono prefissi ≥1024 token tra call (osservato empiricamente
   nel dry-run; vedi `spike/PHASE_F2_PREFLIGHT.md`).

Input: `data/benchmark/ragas_pipeline_outputs_v2.json` (fase F.1).
Output: `data/benchmark/ragas_results_v2.json` + `ragas_aggregates_v2.json`.

REQUISITI: ragas, langchain_huggingface, anthropic, instructor.

    spike/.venv/bin/python spike/run_ragas_eval_v2.py --dry-sample Q52
    spike/.venv/bin/python spike/run_ragas_eval_v2.py --judge

Modalità dev (subset 20 query — legge ragas_pipeline_outputs_v2_subset.json
prodotto da `run_pipeline_v2.py --subset`, scrive results/aggregates
con suffisso `_subset`):

    spike/.venv/bin/python spike/run_ragas_eval_v2.py --judge \
        --subset data/benchmark/subset_dev.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("ragas_eval_v2")

OUTPUTS_PATH = ROOT / "data/benchmark/ragas_pipeline_outputs_v2.json"
RESULTS_PATH = ROOT / "data/benchmark/ragas_results_v2.json"
AGGREGATES_PATH = ROOT / "data/benchmark/ragas_aggregates_v2.json"
GOLD_V2_PATH = ROOT / "data/benchmark/gold_answers_v2.json"

JUDGE_MODEL = "claude-sonnet-4-6"
EMBEDDINGS_MODEL = "BAAI/bge-m3"
RAGAS_CACHE_DIR = ".ragas_cache_v2"

# Sonnet 4.6 pricing (Anthropic public, USD per M tokens)
PRICE_IN = 3.0
PRICE_OUT = 15.0

NORM_PREFIXES = [
    ("eli/reg/2016/679/oj", "GDPR"),
    ("eli/reg/2024/1689/oj", "AI Act"),
    ("akn/it/act/decreto_legislativo/stato/2003-06-30/196", "Codice Privacy"),
    ("akn/it/act/decreto_legislativo/stato/2001-06-08/231", "D.Lgs 231/2001"),
    ("akn/it/act/decreto_legislativo/stato/2024-09-04/138", "NIS2"),
    ("akn/it/act/legge/stato/2025-09-23/132", "L. 132/2025"),
]


def norm_of(chunk_id: str) -> str:
    for pre, label in NORM_PREFIXES:
        if chunk_id.startswith(pre + "__"):
            return label
    return "?"


def _load_env() -> None:
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def build_tracked_client(enable_caching: bool = False):
    """Wrappa Anthropic client per:
    - accumulare token usage (incluso cache_creation / cache_read)
    - opzionalmente iniettare `cache_control: ephemeral` sui blocchi
      user/system content (Anthropic prompt caching, prefix-based)

    Caching **OFF di default** dopo PHASE_F2_PREFLIGHT.md: i prompt
    Ragas tra le 3 call per sample hanno prefisso diverso (extract
    statements, verify statements, generate question) — cache_read_tokens
    rimaneva 0% pagando l'overhead 1.25× di cache_creation. Strumentazione
    tracker mantenuta per visibilità anche con caching OFF.
    """
    from anthropic import Anthropic
    client = Anthropic()
    tracker = {
        "in_tokens": 0, "out_tokens": 0, "n_calls": 0,
        "cache_creation_tokens": 0, "cache_read_tokens": 0,
    }

    orig_create = client.messages.create

    def _inject_cache_control(kwargs: dict) -> dict:
        """Converte user-content da stringa a [block + cache_control]."""
        messages = kwargs.get("messages")
        if not messages:
            return kwargs
        new_msgs = []
        for m in messages:
            content = m.get("content")
            role = m.get("role")
            if role == "user" and isinstance(content, str):
                new_msgs.append({
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"},
                    }],
                })
            elif role == "system" and isinstance(content, str):
                # System prompt cached anch'esso (raramente cambia tra call)
                new_msgs.append({
                    "role": "system",
                    "content": [{
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"},
                    }],
                })
            else:
                new_msgs.append(m)
        kwargs["messages"] = new_msgs
        return kwargs

    def tracked_create(*args, **kwargs):
        if enable_caching:
            kwargs = _inject_cache_control(kwargs)
        resp = orig_create(*args, **kwargs)
        try:
            usage = resp.usage
            tracker["in_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
            tracker["out_tokens"] += int(getattr(usage, "output_tokens", 0) or 0)
            tracker["cache_creation_tokens"] += int(
                getattr(usage, "cache_creation_input_tokens", 0) or 0
            )
            tracker["cache_read_tokens"] += int(
                getattr(usage, "cache_read_input_tokens", 0) or 0
            )
            tracker["n_calls"] += 1
        except Exception:  # noqa: BLE001
            pass
        return resp

    client.messages.create = tracked_create
    return client, tracker


def build_judge(client):
    from ragas.cache import DiskCacheBackend
    from ragas.llms import llm_factory
    judge = llm_factory(
        JUDGE_MODEL,
        provider="anthropic",
        client=client,
        max_tokens=4096,
        cache=DiskCacheBackend(cache_dir=str(ROOT / RAGAS_CACHE_DIR)),
    )
    judge.model_args.pop("top_p", None)
    return judge


def build_dataset_from_outputs(outputs: list[dict]):
    from ragas import EvaluationDataset
    samples = [
        {
            "user_input": o["question"],
            "retrieved_contexts": o["contexts"],
            "response": o["answer"],
            "reference": o["ground_truth"],
        }
        for o in outputs
    ]
    return EvaluationDataset.from_list(samples)


def cost_from_tracker(tracker: dict) -> float:
    """Cost effettivo includendo discount Anthropic per cache_read.

    Pricing Sonnet 4.6 (Anthropic public):
    - input standard:      $3.00/Mtok
    - cache_creation:      $3.75/Mtok (1.25× input — overhead di scrittura)
    - cache_read:          $0.30/Mtok (0.1× input — sconto 90%)
    - output:              $15.00/Mtok

    `usage.input_tokens` Anthropic SDK già esclude cache_creation_input_tokens
    e cache_read_input_tokens — sono tre contatori distinti. Sommo le 3
    componenti separatamente.
    """
    return (
        tracker["in_tokens"] / 1_000_000 * PRICE_IN
        + tracker["cache_creation_tokens"] / 1_000_000 * (PRICE_IN * 1.25)
        + tracker["cache_read_tokens"] / 1_000_000 * (PRICE_IN * 0.1)
        + tracker["out_tokens"] / 1_000_000 * PRICE_OUT
    )


def step_dry_run(qid: str) -> None:
    _load_env()
    payload = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    outputs = payload["outputs"]
    target = next((o for o in outputs if o["qid"] == qid), None)
    if not target:
        raise RuntimeError(f"qid {qid} non trovato in {OUTPUTS_PATH.name}")

    log.info("Dry-run su 1 sample: qid=%s", qid)
    log.info("question: %s", target["question"][:80])

    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness

    dataset = build_dataset_from_outputs([target])
    client, tracker = build_tracked_client(enable_caching=True)
    judge = build_judge(client)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

    log.info("Lancio ragas.evaluate su 1 sample (2 metriche, caching ON)…")
    t0 = time.perf_counter()
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=judge,
        embeddings=embeddings,
    )
    elapsed = time.perf_counter() - t0
    log.info("Wall-time: %.1f s", elapsed)

    df = result.to_pandas()
    row = df.to_dict(orient="records")[0]

    cost = cost_from_tracker(tracker)
    proj_100 = cost * 100
    cache_ratio = (
        tracker["cache_read_tokens"]
        / max(1, tracker["in_tokens"] + tracker["cache_read_tokens"] + tracker["cache_creation_tokens"])
    )

    print()
    print("=" * 70)
    print(f"Dry-run result — {qid}")
    print("=" * 70)
    print(f"faithfulness     : {row.get('faithfulness', 'N/A')}")
    print(f"answer_relevancy : {row.get('answer_relevancy', 'N/A')}")
    print(f"wall time        : {elapsed:.1f}s")
    print(f"n LLM calls      : {tracker['n_calls']}")
    print(f"input tokens     : {tracker['in_tokens']:,} (standard, non cached)")
    print(f"cache_creation   : {tracker['cache_creation_tokens']:,}")
    print(f"cache_read       : {tracker['cache_read_tokens']:,}  ← se >0, caching effettivo")
    print(f"output tokens    : {tracker['out_tokens']:,}")
    print(f"cache_read ratio : {cache_ratio*100:.1f}% degli input totali")
    print(f"actual cost      : ${cost:.4f}")
    print(f"proj 100 samp    : ~${proj_100:.2f}")
    threshold = 4.00  # nuovo target post-(d)+(e)
    if proj_100 > threshold:
        print(f"\n⚠ ALERT: proiezione ${proj_100:.2f} > target post-(d)+(e) ${threshold:.2f}")
        print("   Conferma esplicita richiesta prima di --judge.")


def _stats(values: list[float]) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None,
                "max": None, "p10": None, "p90": None, "std": None}
    sv = sorted(vals)
    n = len(sv)
    return {
        "n": n,
        "mean": statistics.fmean(sv),
        "median": statistics.median(sv),
        "min": min(sv),
        "max": max(sv),
        "p10": sv[max(0, int(0.10 * n) - 1)],
        "p90": sv[min(n - 1, int(0.90 * n))],
        "std": statistics.pstdev(sv) if n > 1 else 0.0,
    }


BATCH_SIZE = 10
COST_THRESHOLD_AT_80 = 12.0


def _evaluate_batch(batch_outputs: list[dict], judge, embeddings) -> list[dict]:
    """Esegue ragas.evaluate su 1 batch, ritorna per-query rows."""
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness
    dataset = build_dataset_from_outputs(batch_outputs)
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=judge,
        embeddings=embeddings,
    )
    df = result.to_pandas()
    return df.to_dict(orient="records")


def step_judge(skip_existing: bool = False,
               subset: set[str] | None = None,
               report_path: Path | None = None) -> None:
    if not OUTPUTS_PATH.is_file():
        raise RuntimeError(f"Pipeline outputs assenti: {OUTPUTS_PATH}.")
    _load_env()

    payload = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    outputs = payload["outputs"]
    if subset is not None:
        outputs = [o for o in outputs if o["qid"] in subset]
        log.info("Subset filter applied: %d/%d outputs", len(outputs), len(payload["outputs"]))
    elif len(outputs) != 100:
        raise RuntimeError(f"Atteso 100 outputs, trovato {len(outputs)}.")
    log.info("Judge — %d query, judge=%s, embeddings=%s.",
             len(outputs), JUDGE_MODEL, EMBEDDINGS_MODEL)

    # --- skip-existing: precarica risultati già scritti ---
    per_query: list[dict] = []
    done_qids: set[str] = set()
    if skip_existing and RESULTS_PATH.is_file():
        prev = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        per_query = list(prev.get("results", []))
        done_qids = {r["qid"] for r in per_query}
        log.info("Skip-existing: %d qid già in cache, ripresa da query %d",
                 len(done_qids), len(done_qids) + 1)

    to_process = [o for o in outputs if o["qid"] not in done_qids]
    if not to_process:
        log.info("Tutti i 100 sample già processati. Skip eval, vado a aggregati+report.")
        # ricrea tracker fittizio (lettura dal metadata pre-esistente se serve)
        tracker = {"in_tokens": 0, "out_tokens": 0, "n_calls": 0,
                   "cache_creation_tokens": 0, "cache_read_tokens": 0}
    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        client, tracker = build_tracked_client(enable_caching=False)
        judge = build_judge(client)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

        out_by_qid = {o["qid"]: o for o in outputs}
        n_total = len(to_process)
        log.info("Eval (caching OFF) su %d sample, batch=%d, soglia stop=$%.2f @ sample 80",
                 n_total, BATCH_SIZE, COST_THRESHOLD_AT_80)

        t0 = time.perf_counter()
        for batch_start in range(0, n_total, BATCH_SIZE):
            batch = to_process[batch_start:batch_start + BATCH_SIZE]
            batch_qids = [o["qid"] for o in batch]
            log.info("Batch %d-%d: %s",
                     len(per_query) + 1, len(per_query) + len(batch),
                     ",".join(batch_qids))
            rows = _evaluate_batch(batch, judge, embeddings)
            if len(rows) != len(batch):
                raise RuntimeError(f"Batch: {len(rows)} rows vs {len(batch)} input")

            for o, row in zip(batch, rows, strict=True):
                per_query.append({
                    "qid": o["qid"],
                    "query_type": o["query_type"],
                    "faithfulness": float(row["faithfulness"]) if row.get("faithfulness") is not None else None,
                    "answer_relevancy": float(row["answer_relevancy"]) if row.get("answer_relevancy") is not None else None,
                    "has_corpus_limit_declaration": o["has_corpus_limit_declaration"],
                    "use_case": out_by_qid[o["qid"]].get("use_case", ""),
                })

            # Save incrementale ad ogni batch
            partial_meta = {
                "date": date.today().isoformat(),
                "judge": JUDGE_MODEL,
                "embeddings": EMBEDDINGS_MODEL,
                "metrics": ["faithfulness", "answer_relevancy"],
                "n_samples": len(per_query),
                "wall_time_s": round(time.perf_counter() - t0, 1),
                "cost_usd_running": round(cost_from_tracker(tracker), 4),
                "n_llm_calls": tracker["n_calls"],
                "input_tokens": tracker["in_tokens"],
                "cache_creation_tokens": tracker["cache_creation_tokens"],
                "cache_read_tokens": tracker["cache_read_tokens"],
                "output_tokens": tracker["out_tokens"],
                "prompt_caching": "disabled",
                "status": "in_progress",
            }
            RESULTS_PATH.write_text(
                json.dumps({"metadata": partial_meta, "results": per_query},
                           indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            current_cost = cost_from_tracker(tracker)
            log.info("Cost cumulativo: $%.4f (n_calls=%d, %d/%d sample)",
                     current_cost, tracker["n_calls"], len(per_query), 100)

            # Soglia stop @ sample 80
            if len(per_query) >= 80 and current_cost > COST_THRESHOLD_AT_80:
                raise RuntimeError(
                    f"⚠ ANOMALIA: cost cumulativo ${current_cost:.2f} > soglia "
                    f"${COST_THRESHOLD_AT_80} @ sample {len(per_query)}. "
                    "Run fermato. Stato salvato in results_v2.json. "
                    "Rilancia con --judge --skip-existing dopo verifica."
                )

        elapsed = time.perf_counter() - t0
        log.info("Eval finita: %d sample in %.0fs", len(per_query), elapsed)

    cost = cost_from_tracker(tracker)
    elapsed = locals().get("elapsed", 0.0)
    run_meta = {
        "date": date.today().isoformat(),
        "judge": JUDGE_MODEL,
        "embeddings": EMBEDDINGS_MODEL,
        "metrics": ["faithfulness", "answer_relevancy"],
        "n_samples": len(per_query),
        "wall_time_s": round(elapsed, 1),
        "cost_usd": round(cost, 4),
        "n_llm_calls": tracker["n_calls"],
        "input_tokens": tracker["in_tokens"],
        "cache_creation_tokens": tracker["cache_creation_tokens"],
        "cache_read_tokens": tracker["cache_read_tokens"],
        "output_tokens": tracker["out_tokens"],
        "prompt_caching": "disabled",
        "status": "completed",
        "batch_size": BATCH_SIZE,
        "skip_existing_used": skip_existing,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    RESULTS_PATH.write_text(
        json.dumps({"metadata": run_meta, "results": per_query},
                   indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log.info("Scritto %s", RESULTS_PATH)

    # ---- Aggregati ----
    def block(rs: list[dict]) -> dict:
        return {
            "n": len(rs),
            "faithfulness": _stats([r["faithfulness"] for r in rs]),
            "answer_relevancy": _stats([r["answer_relevancy"] for r in rs]),
        }

    global_block = block(per_query)
    by_qtype = {
        "positive": block([r for r in per_query if r["query_type"] == "positive"]),
        "negative": block([r for r in per_query if r["query_type"] == "negative"]),
        "edge": block([r for r in per_query if r["query_type"] == "edge"]),
    }
    by_corpus_limit = {
        "true": block([r for r in per_query if r["has_corpus_limit_declaration"]]),
        "false": block([r for r in per_query if not r["has_corpus_limit_declaration"]]),
    }
    by_use_case: dict[str, dict] = {}
    bucket: dict[str, list[dict]] = defaultdict(list)
    for r in per_query:
        bucket[r["use_case"]].append(r)
    for uc, rs in bucket.items():
        by_use_case[uc] = block(rs)

    # Per norma toccata: lookup dal dataset gold_answers_v2
    gold = json.loads(GOLD_V2_PATH.read_text(encoding="utf-8"))
    gold_by_qid = {e["qid"]: e for e in gold}
    by_norm: dict[str, list[dict]] = defaultdict(list)
    for r in per_query:
        e = gold_by_qid.get(r["qid"], {})
        norms = {norm_of(g["chunk_id"]) for g in e.get("gold_chunks", [])} - {"?"}
        for n in norms:
            by_norm[n].append(r)
    by_norm_agg = {n: block(rs) for n, rs in by_norm.items()}

    # v1 / v2 split
    v1_results = [r for r in per_query if int(r["qid"][1:]) <= 50]
    v2_results = [r for r in per_query if int(r["qid"][1:]) > 50]

    aggregates = {
        "metadata": run_meta,
        "global": global_block,
        "by_query_type": by_qtype,
        "by_has_corpus_limit": by_corpus_limit,
        "by_use_case": by_use_case,
        "by_norm": by_norm_agg,
        "v1_subset": block(v1_results),
        "v2_subset": block(v2_results),
    }
    AGGREGATES_PATH.write_text(
        json.dumps(aggregates, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log.info("Scritto %s", AGGREGATES_PATH)

    # Print summary stdout
    print()
    print("=" * 75)
    print(f"Eval v2 finished — cost ${cost:.2f}, {elapsed:.0f}s, "
          f"{tracker['n_calls']} LLM calls")
    print("=" * 75)
    _f = lambda v: "n/a" if v is None else f"{v:.3f}"
    g = global_block
    print(f"\nGlobal (n={g['n']}):")
    for metric in ("faithfulness", "answer_relevancy"):
        s = g[metric]
        print(f"  {metric:<20} n={s['n']:>3} median={_f(s['median'])} "
              f"mean={_f(s['mean'])} min={_f(s['min'])} max={_f(s['max'])}")

    print("\nPer query_type:")
    for qt in ("positive", "negative", "edge"):
        s = by_qtype[qt]
        if s["n"] == 0:
            print(f"  {qt:<10} n=  0 (skip)")
            continue
        fm = s["faithfulness"]["median"]
        rm = s["answer_relevancy"]["median"]
        print(f"  {qt:<10} n={s['n']:>3} faith={_f(fm)} rel={_f(rm)}")

    # bottom-5 per metrica
    print()
    for metric in ("faithfulness", "answer_relevancy"):
        rs = [r for r in per_query if r[metric] is not None]
        bottom = sorted(rs, key=lambda r: r[metric])[:5]
        print(f"Bottom-5 {metric}:")
        for r in bottom:
            print(f"  {r['qid']:<5} {metric}={r[metric]:.3f} "
                  f"qt={r['query_type']:<8} cluster={r['use_case'][:40]}")

    # Report W7_v2
    if report_path is None:
        report_path = ROOT / "spike/BENCHMARK_RAGAS_W7_v2.md"
    write_report(report_path, run_meta, per_query, aggregates)


def _v1_w7_archived() -> dict:
    """Aggregati v1 (38 positive) W7 archived da BENCHMARK_RAGAS_W7.md.

    Numeri storici copiati a mano (file in `data/benchmark/BENCHMARK_RAGAS_W7.md`).
    """
    return {
        "global_38_positive": {
            "faithfulness": {"median": 0.944, "mean": None},
            "answer_relevancy": {"median": 0.763, "mean": None},
        },
        "group_a_27_non_limit": {
            "faithfulness": {"median": 0.952, "mean": None},
            "answer_relevancy": {"median": 0.812, "mean": None},
        },
        "group_b_11_limit": {
            "faithfulness": {"median": 0.824, "mean": None},
            "answer_relevancy": {"median": 0.705, "mean": None},
        },
    }


def write_report(path: Path, run_meta: dict, per_query: list[dict], aggregates: dict) -> None:
    """Genera spike/BENCHMARK_RAGAS_W7_v2.md."""
    L: list[str] = []
    L.append("# BENCHMARK RAGAS W7 v2 — eval Ragas su gold_answers_v2.json")
    L.append("")
    L.append(f"**Date:** {run_meta['date']}")
    L.append(f"**Finished (UTC):** {run_meta['finished_utc']}")
    L.append(f"**Judge:** `{run_meta['judge']}` · embeddings `{run_meta['embeddings']}`")
    L.append(f"**Metriche:** {', '.join(run_meta['metrics'])} (2)")
    L.append(f"**Cost reale:** ${run_meta['cost_usd']:.4f} · "
             f"LLM calls {run_meta['n_llm_calls']} · "
             f"wall {run_meta['wall_time_s']:.0f}s · "
             f"prompt_caching={run_meta['prompt_caching']}")
    L.append("")
    L.append("### Note metodologiche")
    L.append("")
    L.append("- **`context_precision` non inclusa**: spec F.2 originale chiedeva 3 metriche, "
             "ma il dry-run Q51 ha mostrato $0.132/sample (proiezione $13.20 su 100, 13× sopra spec). "
             "Drop context_precision per ridurre cost a target $2-4. La dimensione retrieval-quality "
             "resta coperta da R@5/R@10/R@20/MRR computati in F.1 su 100 query "
             "(vedi `spike/BENCHMARK_W3_v2.md`).")
    L.append("- **Anthropic prompt caching tentato, disabilitato**: il dry-run Q52+Q70 ha mostrato "
             "`cache_read_input_tokens=0` su tutte le call. I prompt Ragas tra extract-statements, "
             "verify-statements e generate-question hanno prefisso strutturalmente diverso → 0% cache "
             "hit pagando +25% overhead di cache_creation. Caching disabilitato, instrumentazione "
             "tracker mantenuta. Dettaglio in `spike/PHASE_F2_PREFLIGHT.md`.")
    L.append("- **100 query full coverage**, no stratified subset. Save incrementale per "
             f"resilienza ai crash (batch={run_meta.get('batch_size','?')}).")
    L.append("")

    L.append("## 1. Sintesi globale (100 query)")
    L.append("")
    g = aggregates["global"]
    L.append("| metrica | n | median | mean | p10 | p90 | min | max | std |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for m in ("faithfulness", "answer_relevancy"):
        s = g[m]
        L.append(f"| {m} | {s['n']} | {s['median']:.3f} | {s['mean']:.3f} | "
                 f"{s['p10']:.3f} | {s['p90']:.3f} | {s['min']:.3f} | "
                 f"{s['max']:.3f} | {s['std']:.3f} |")
    L.append("")

    L.append("## 2. Per query_type")
    L.append("")
    L.append("| type | n | faith median | faith mean | rel median | rel mean |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for qt in ("positive", "negative", "edge"):
        b = aggregates["by_query_type"][qt]
        if b["n"] == 0:
            continue
        L.append(f"| {qt} | {b['n']} | {b['faithfulness']['median']:.3f} | "
                 f"{b['faithfulness']['mean']:.3f} | {b['answer_relevancy']['median']:.3f} | "
                 f"{b['answer_relevancy']['mean']:.3f} |")
    L.append("")

    L.append("## 3. Per cluster v2 (use_case, proxy)")
    L.append("")
    L.append("Nota: nel dataset v2 ogni qid ha use_case unico (n=1 per use_case). "
             "Per cluster-level analysis vera servirebbe mappare qid→cluster dai metadata di "
             "`candidates_v2_curated.json` (rinviato a v1.1 / iterazione successiva).")
    L.append("")
    L.append("| use_case | n | faith | rel |")
    L.append("|---|---:|---:|---:|")
    for uc in sorted(aggregates["by_use_case"].keys()):
        b = aggregates["by_use_case"][uc]
        fm = b["faithfulness"]["median"]
        rm = b["answer_relevancy"]["median"]
        L.append(f"| {uc[:55]} | {b['n']} | {fm:.3f} | {rm:.3f} |")
    L.append("")

    L.append("## 4. Per has_corpus_limit_declaration")
    L.append("")
    L.append("| flag | n | faith median | faith mean | rel median | rel mean |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for flag in ("false", "true"):
        b = aggregates["by_has_corpus_limit"][flag]
        if b["n"] == 0:
            continue
        L.append(f"| {flag} | {b['n']} | {b['faithfulness']['median']:.3f} | "
                 f"{b['faithfulness']['mean']:.3f} | {b['answer_relevancy']['median']:.3f} | "
                 f"{b['answer_relevancy']['mean']:.3f} |")
    L.append("")

    L.append("## 5. Per norma toccata")
    L.append("")
    L.append("| norma | n | faith median | rel median |")
    L.append("|---|---:|---:|---:|")
    for n in sorted(aggregates["by_norm"].keys()):
        b = aggregates["by_norm"][n]
        L.append(f"| {n} | {b['n']} | {b['faithfulness']['median']:.3f} | "
                 f"{b['answer_relevancy']['median']:.3f} |")
    L.append("")

    L.append("## 6. Confronto v1 W7 archived ↔ v1 ricalcolato F.2")
    L.append("")
    L.append("Le 50 query v1 (Q1-Q50) includono 38 positive + 10 negative + 2 edge. "
             "Il W7 archived ha valutato solo le 38 positive; per confronto omogeneo, "
             "filtro v1_subset alle stesse 38 positive sul ricalcolato.")
    L.append("")
    archived = _v1_w7_archived()
    v1_pos_recalc = [r for r in per_query
                     if int(r["qid"][1:]) <= 50 and r["query_type"] == "positive"]
    rc_faith = _stats([r["faithfulness"] for r in v1_pos_recalc])
    rc_rel = _stats([r["answer_relevancy"] for r in v1_pos_recalc])
    L.append("| metrica | W7 archived (38 pos) | F.2 ricalcolato (38 pos) | delta |")
    L.append("|---|---:|---:|---:|")
    arch_f = archived["global_38_positive"]["faithfulness"]["median"]
    arch_r = archived["global_38_positive"]["answer_relevancy"]["median"]
    df = rc_faith["median"] - arch_f
    dr = rc_rel["median"] - arch_r
    drift_f = "⚠ drift >0.05" if abs(df) > 0.05 else "ok"
    drift_r = "⚠ drift >0.05" if abs(dr) > 0.05 else "ok"
    L.append(f"| faithfulness median | {arch_f:.3f} | {rc_faith['median']:.3f} | "
             f"{df:+.3f} ({drift_f}) |")
    L.append(f"| answer_relevancy median | {arch_r:.3f} | {rc_rel['median']:.3f} | "
             f"{dr:+.3f} ({drift_r}) |")
    L.append("")

    L.append("## 7. Bottom-5 per metrica")
    L.append("")
    for metric in ("faithfulness", "answer_relevancy"):
        rs = [r for r in per_query if r[metric] is not None]
        bottom = sorted(rs, key=lambda r: r[metric])[:5]
        L.append(f"### Bottom-5 `{metric}`")
        L.append("")
        L.append("| qid | score | query_type | cluster (use_case) |")
        L.append("|---|---:|---|---|")
        for r in bottom:
            L.append(f"| {r['qid']} | {r[metric]:.3f} | {r['query_type']} | "
                     f"{r['use_case'][:55]} |")
        L.append("")

    L.append("## 8. Verdict")
    L.append("")
    L.append("Target SCOPE pivotato (vedi `SCOPE.md` Metriche di \"fatto\" post-2026-05-20):")
    L.append("- `faithfulness` ≥ 0.85")
    L.append("- `answer_relevancy` ≥ 0.80")
    L.append("- `context_precision` ≥ 0.80 (NON misurata in F.2, vedi note metodologiche)")
    L.append("")
    pos_block = aggregates["by_query_type"]["positive"]
    f_med = pos_block["faithfulness"]["median"]
    r_med = pos_block["answer_relevancy"]["median"]
    f_pass = f_med >= 0.85
    r_pass = r_med >= 0.80
    L.append(f"- faithfulness median (positive, n={pos_block['n']}): "
             f"**{f_med:.3f}** ({'✅ ≥0.85' if f_pass else '❌ <0.85'})")
    L.append(f"- answer_relevancy median (positive, n={pos_block['n']}): "
             f"**{r_med:.3f}** ({'✅ ≥0.80' if r_pass else '❌ <0.80'})")
    L.append("")
    if f_pass and r_pass:
        L.append("**Verdict: GO ready-with-followup per release v1.**")
    else:
        L.append("**Verdict: NOT-READY. Soglie sotto target — investigare bottom-5 per follow-up.**")
    L.append("")
    L.append("Follow-up identificati per v1.1 (vedi anche `ROADMAP_POST_V1.md` Finding W7):")
    L.append("- Runtime corpus_limit detection via LLM-as-judge (regex inaffidabile, vedi PHASE_F1_DIAGNOSTIC).")
    L.append("- Estensione corpus codice penale articoli richiamati da 231 (4+ candidate W7-prep richiedono il c.p.).")
    L.append("- Tuning system prompt per uniformare pattern lessicale \"dichiarazione di limite\".")
    L.append("- Eventuale context_precision in run successivo dedicato (se rilevante).")
    L.append("")

    L.append("## 9. Paired queries intenzionali design v2")
    L.append("")
    L.append("Da metadata di `candidates_v2_curated.json` (fase C):")
    paired = {
        "NIS2 art_38__paras_1_11 (sanzioni)": ("Q55", "Q83"),
        "NIS2 art_25 (notifica)": ("Q54", "Q57"),
        "L.132 art_9 (trattamento dati)": ("Q64", "Q67"),
    }
    L.append("| Tema | qid coppia | faith A | faith B | rel A | rel B |")
    L.append("|---|---|---:|---:|---:|---:|")
    by_qid = {r["qid"]: r for r in per_query}
    for theme, (qa, qb) in paired.items():
        a = by_qid.get(qa)
        b = by_qid.get(qb)
        if not a or not b:
            L.append(f"| {theme} | {qa},{qb} | n/a | n/a | n/a | n/a |")
            continue
        fa = a["faithfulness"] if a["faithfulness"] is not None else 0
        fb = b["faithfulness"] if b["faithfulness"] is not None else 0
        ra = a["answer_relevancy"] if a["answer_relevancy"] is not None else 0
        rb = b["answer_relevancy"] if b["answer_relevancy"] is not None else 0
        L.append(f"| {theme} | {qa},{qb} | {fa:.3f} | {fb:.3f} | {ra:.3f} | {rb:.3f} |")
    L.append("")

    L.append("---")
    L.append("")
    L.append("**Bias del dataset v2 verso il posizionamento DPO/legal mainstream**: la "
             "composizione delle 50 query nuove (Q51-Q100) privilegia 6 cluster mirati al target "
             "professional (NIS2, Codice Privacy lato italiano, L. 132/2025, cross-norma 3+, "
             "diritti dell'interessato, sanzioni). Aggregati v2 vs v1 W7 archived possono "
             "divergere proprio per questa scelta di copertura tematica, non solo per qualità "
             "pipeline. Quando comunicato esternamente, segnalare che il benchmark è progettato "
             "per stressare il sistema sul target professional italiano, non come golden truth "
             "neutrale.")
    L.append("")

    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    log.info("Scritto report %s", path)


def main() -> int:
    global OUTPUTS_PATH, RESULTS_PATH, AGGREGATES_PATH
    parser = argparse.ArgumentParser(description="Ragas eval v2 (100 query, 2 metriche)")
    parser.add_argument("--dry-sample", type=str, default=None,
                        help="qid singolo per dry-run + cost projection.")
    parser.add_argument("--judge", action="store_true",
                        help="Run full eval su 100 sample (batched, save incrementale).")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Resume: carica risultati esistenti, processa solo qid mancanti.")
    parser.add_argument("--subset", type=str, default=None,
                        help="Path YAML con lista qids. Legge pipeline_outputs_v2_subset.json, "
                             "scrive results/aggregates/report con suffisso _subset. "
                             "Le label dei gruppi A/B negli aggregati restano cosmetiche.")
    args = parser.parse_args()

    if args.dry_sample and args.judge:
        raise SystemExit("Flag mutuamente esclusivi: --dry-sample o --judge.")
    if not args.dry_sample and not args.judge:
        raise SystemExit("Specificare --dry-sample <qid> o --judge.")

    subset_qids: set[str] | None = None
    report_path: Path | None = None
    if args.subset:
        import yaml
        subset_path = Path(args.subset)
        if not subset_path.is_absolute():
            subset_path = ROOT / subset_path
        with subset_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        subset_qids = set(data["qids"])
        OUTPUTS_PATH = ROOT / "data/benchmark/ragas_pipeline_outputs_v2_subset.json"
        RESULTS_PATH = ROOT / "data/benchmark/ragas_results_v2_subset.json"
        AGGREGATES_PATH = ROOT / "data/benchmark/ragas_aggregates_v2_subset.json"
        report_path = ROOT / "spike/BENCHMARK_RAGAS_W7_v2_subset.md"
        log.info("Subset mode: %d qid da %s → input %s, output *_subset.*",
                 len(subset_qids), subset_path.name, OUTPUTS_PATH.name)

    if args.dry_sample:
        step_dry_run(args.dry_sample)
    else:
        step_judge(skip_existing=args.skip_existing,
                   subset=subset_qids, report_path=report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
