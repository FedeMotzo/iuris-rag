"""Prototipo map-reduce paid (Haiku 4.5 map + Sonnet 4.6 reduce).

Gating: scarta sub-query con top-1 reranker < 0.5.
Map: mini-risposta per ogni sub-query sopravvissuta sui suoi top-3.
Reduce: sintesi finale dalle mini-risposte.

Misure: faith per mini, faith finale (judge max_tokens alzato), ar finale,
coverage per gold, lunghezze, costi.

Hard stop $5 — niente meccanismo di controllo runtime; valutare costi
preventivi prima di lanciare.

    spike/.venv/bin/python spike/ceiling_mapreduce.py
"""
from __future__ import annotations

import json
import logging
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUBQ_FILE = ROOT / "spike/data/declarative_subqueries.json"
GOLD_FILE = ROOT / "data/benchmark/gold_answers_v3.json"
OUT = ROOT / "spike/data/ceiling_mapreduce_results.json"

SIGLA_PATTERNS = [
    ("gdpr", re.compile(r"\bGDPR\b", re.IGNORECASE)),
    ("ai_act", re.compile(r"\bAI\s*Act\b", re.IGNORECASE)),
    ("l_132_2025", re.compile(r"\bL\.?\s*132/2025\b", re.IGNORECASE)),
    ("dlgs_231", re.compile(r"\bD\.?\s*Lgs\.?\s*231/2001\b", re.IGNORECASE)),
    ("nis2", re.compile(r"\bNIS2\b|\bD\.?\s*Lgs\.?\s*138/2024\b", re.IGNORECASE)),
]
NORM_TO_DOC_URN = {
    "gdpr": "eli/reg/2016/679/oj",
    "ai_act": "eli/reg/2024/1689/oj",
    "dlgs_231": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
    "nis2": "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    "l_132_2025": "akn/it/act/legge/stato/2025-09-23/132",
}
GOLDS = {
    "Q68": [
        ("eli/reg/2024/1689/oj__art_6", "AI Act art_6"),
        ("eli/reg/2016/679/oj__art_9", "GDPR art_9"),
        ("eli/reg/2024/1689/oj__art_27", "AI Act art_27"),
        ("eli/reg/2016/679/oj__art_35", "GDPR art_35"),
        ("akn/it/act/legge/stato/2025-09-23/132__art_7", "L.132 art_7"),
    ],
    "Q69": [("eli/reg/2024/1689/oj__art_6", "AI Act art_6")],
    "Q70": [
        ("eli/reg/2016/679/oj__art_44", "GDPR art_44"),
        ("akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies", "231 art_25-octies"),
    ],
    "Q71": [("eli/reg/2024/1689/oj__annex_III__point_5", "AnnexIII point_5")],
}

GATE_THRESHOLD = 0.5
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

MAP_PROMPT = """Sei un consulente normativo. Scrivi una mini-risposta focalizzata sull'istituto indicato, usando ESCLUSIVAMENTE i 3 estratti normativi sotto.

Focus normativo: {sub_query}

Estratti normativi (top-3 rerankati):
{contexts}

Istruzioni:
- 3-6 frasi, dense, no preamboli.
- Ogni affermazione chiusa da [cite:CHUNK_ID] usando l'identificativo esatto del chunk-fonte.
- Se gli estratti NON rispondono al focus dichiarato sopra, scrivi una sola frase: "Gli estratti non rispondono al focus." e termina.
"""

REDUCE_PROMPT = """Sintetizza una risposta finale per lo scenario sotto, integrando le mini-risposte normative qui sotto.

Scenario:
{question}

Mini-risposte (una per istituto attivato):
{mini_blocks}

Istruzioni:
- Risposta organica, strutturata per istituto.
- PRESERVA le citazioni [cite:CHUNK_ID] presenti nelle mini-risposte.
- NON aggiungere informazioni esterne alle mini-risposte.
- Lunghezza target: 1200-2500 parole.
"""

COVERAGE_PROMPT = """Stabilisci se la risposta affronta in modo SOSTANZIALE le previsioni dell'articolo target.

Articolo target: {label}
Rubrica/oggetto:
{rubric}

Estratto dell'articolo target (primo blocco):
{article_text}

Risposta da valutare:
---
{answer}
---

Criteri:
- ADDRESSED: la risposta tratta sostanzialmente almeno una previsione specifica dell'articolo target (anche senza citarne il numero), con almeno un'affermazione che ne riproduca la sostanza dispositiva.
- NOT_ADDRESSED: l'articolo è ignorato o solo accennato in modo generico.

Output (TASSATIVO): una sola riga in questo formato:
VEREDICT: ADDRESSED|NOT_ADDRESSED
REASON: <max 200 caratteri>
"""


def _norm_of_subq(text):
    earliest = None
    for nid, pat in SIGLA_PATTERNS:
        m = pat.search(text)
        if m and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), nid)
    return earliest[1] if earliest else None


def _format_contexts(chunks: list[tuple[str, str]]) -> str:
    """chunks: list[(chunk_id, text)] → formattato con header [chunk_id]."""
    parts = []
    for cid, text in chunks:
        parts.append(f"[{cid}]\n{text.strip()}\n")
    return "\n".join(parts)


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger("mapreduce")
    log.setLevel(logging.INFO)

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)

    from anthropic import Anthropic
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient, models
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    cli_q = QdrantClient(host="localhost", port=6333, timeout=60)
    anthropic = Anthropic()

    def call_llm(model, prompt, max_tokens, system=None, retry=2):
        last_err = None
        for attempt in range(retry):
            try:
                kwargs = dict(model=model, max_tokens=max_tokens, temperature=0.0,
                              messages=[{"role": "user", "content": prompt}])
                if system:
                    kwargs["system"] = system
                msg = anthropic.messages.create(**kwargs)
                text = msg.content[0].text if msg.content else ""
                return text, msg.usage.input_tokens, msg.usage.output_tokens
            except Exception as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise last_err

    # Cost tracking
    cost_usage = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "calls": 0})
    # pricing per 1M tokens (approx)
    PRICING = {
        HAIKU_MODEL: {"in": 1.00, "out": 5.00},
        SONNET_MODEL: {"in": 3.00, "out": 15.00},
    }

    def track(model, n_in, n_out):
        cu = cost_usage[model]
        cu["input_tokens"] += n_in; cu["output_tokens"] += n_out; cu["calls"] += 1

    def cost_usd():
        total = 0.0
        for m, u in cost_usage.items():
            if m in PRICING:
                total += (u["input_tokens"] / 1_000_000) * PRICING[m]["in"]
                total += (u["output_tokens"] / 1_000_000) * PRICING[m]["out"]
        return total

    # === Retrieve + rerank locale (free) ===
    print("Loading models (free)...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    hybrid = HybridRetriever(cli_q, enc, bm, "italian_legal_v1_hybrid", reranker=rr)

    raw = json.loads(SUBQ_FILE.read_text())
    gold_data = {e["qid"]: e for e in json.loads(GOLD_FILE.read_text())}

    def fetch_text(cid):
        flt = models.Filter(must=[models.FieldCondition(
            key="chunk_id", match=models.MatchValue(value=cid))])
        pts, _ = cli_q.scroll(collection_name="italian_legal_v1_hybrid",
                              scroll_filter=flt, limit=1, with_payload=True)
        return (pts[0].payload.get("text", ""), pts[0].payload) if pts else ("", {})

    queries_data = {}
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        question = gold_data[qid]["question"]
        sqs_filt = []
        for src_norm, sqs in raw[qid]["subqueries_by_norm"].items():
            for sq_idx, sq in enumerate(sqs):
                if _norm_of_subq(sq) != src_norm:
                    continue
                sqs_filt.append((src_norm, sq_idx, sq))

        print(f"\n[{qid}] sub-query filtrate: {len(sqs_filt)}; retrieve+rerank...")
        items = []
        for src_norm, sq_idx, sq in sqs_filt:
            doc_urn = NORM_TO_DOC_URN[src_norm]
            hits = hybrid.retrieve(query=sq, top_k=5, mode="hybrid",
                                   rerank_top_k=20, filter_doc_urn=doc_urn)
            top3 = list(hits)[:3]
            if not top3:
                continue
            items.append({
                "src": src_norm, "sq_idx": sq_idx, "sub_query": sq,
                "top3": [(h.chunk_id, float(h.score)) for h in top3],
                "top1_score": float(top3[0].score),
            })
        # gate
        kept = [it for it in items if it["top1_score"] >= GATE_THRESHOLD]
        print(f"  gate (top1 ≥ {GATE_THRESHOLD}): {len(kept)}/{len(items)} sopravvivono")
        queries_data[qid] = {"question": question, "items": kept, "items_all_n": len(items)}

    # === MAP: Haiku per ogni sub-query sopravvissuta ===
    print("\n" + "=" * 80)
    print("MAP (Haiku)")
    print("=" * 80)
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = queries_data[qid]
        print(f"\n[{qid}] MAP su {len(qd['items'])} sub-query...")
        for it in qd["items"]:
            chunks = []
            for cid, score in it["top3"]:
                txt, _ = fetch_text(cid)
                chunks.append((cid, txt))
            prompt = MAP_PROMPT.format(sub_query=it["sub_query"],
                                       contexts=_format_contexts(chunks))
            text, n_in, n_out = call_llm(HAIKU_MODEL, prompt, max_tokens=400)
            track(HAIKU_MODEL, n_in, n_out)
            it["mini_answer"] = text.strip()
            it["contexts_text"] = [t for _, t in chunks]
        print(f"  done. cumulative cost ≈ ${cost_usd():.3f}")
        if cost_usd() > 4.5:
            print("WARN: cost > $4.5, stopping before reduce.")
            break

    # === REDUCE: Sonnet per ogni query ===
    print("\n" + "=" * 80)
    print("REDUCE (Sonnet 4.6)")
    print("=" * 80)
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = queries_data[qid]
        if cost_usd() > 4.5:
            qd["final_answer"] = ""
            continue
        mini_blocks = []
        for i, it in enumerate(qd["items"]):
            mini_blocks.append(f"[MINI #{i} — focus: {it['sub_query']}]\n{it['mini_answer']}\n")
        prompt = REDUCE_PROMPT.format(question=qd["question"],
                                       mini_blocks="\n".join(mini_blocks))
        text, n_in, n_out = call_llm(SONNET_MODEL, prompt, max_tokens=4000)
        track(SONNET_MODEL, n_in, n_out)
        qd["final_answer"] = text.strip()
        print(f"  [{qid}] reduce done. ans_chars={len(qd['final_answer'])}; cumulative ${cost_usd():.3f}")

    # === MEASURES ===
    sys.path.insert(0, str(ROOT / "spike"))
    import run_ragas_eval_v2 as R
    from langchain_huggingface import HuggingFaceEmbeddings
    R._load_env()

    # A: RAGAS faithfulness PER MINI (sub_query as user_input, top-3 as contexts)
    print("\n" + "=" * 80)
    print("A — RAGAS faithfulness PER MINI")
    print("=" * 80)
    mini_outputs = []
    for qid, qd in queries_data.items():
        for it in qd["items"]:
            mini_outputs.append({
                "qid": qid, "sq_idx": it["sq_idx"], "sub_query": it["sub_query"],
                "question": it["sub_query"],  # RAGAS user_input
                "contexts": it["contexts_text"],
                "answer": it["mini_answer"],
                "ground_truth": it["sub_query"],
            })
    print(f"  miniresponses: {len(mini_outputs)}")
    client_a, tracker_a = R.build_tracked_client(enable_caching=False)
    judge_a = R.build_judge(client_a)
    embeddings = HuggingFaceEmbeddings(model_name=R.EMBEDDINGS_MODEL)
    mini_rows = R._evaluate_batch(mini_outputs, judge_a, embeddings)
    faith_per_mini = []
    for o, row in zip(mini_outputs, mini_rows, strict=True):
        f = row.get("faithfulness")
        f_val = float(f) if f is not None and f == f else None
        o["faithfulness"] = f_val
        if f_val is not None:
            faith_per_mini.append(f_val)
    ragas_a_cost = R.cost_from_tracker(tracker_a)
    log.info("RAGAS A done. cost≈$%.3f calls=%d", ragas_a_cost, tracker_a["n_calls"])

    # B+C: RAGAS faithfulness + ar on FINAL answer (judge with higher max_tokens)
    print("\n" + "=" * 80)
    print("B+C — RAGAS sulla risposta finale (judge max_tokens=8192)")
    print("=" * 80)
    final_outputs = []
    for qid, qd in queries_data.items():
        if not qd.get("final_answer"):
            continue
        # contesti: tutti i top-3 unique
        all_texts = []
        seen = set()
        for it in qd["items"]:
            for cid, txt in zip([c for c, _ in it["top3"]], it["contexts_text"]):
                if cid not in seen:
                    seen.add(cid); all_texts.append(txt)
        final_outputs.append({
            "qid": qid, "question": qd["question"],
            "contexts": all_texts,
            "answer": qd["final_answer"],
            "ground_truth": gold_data[qid].get("gold_answer", ""),
            "n_chunk_ctx": len(all_texts),
        })
    client_b, tracker_b = R.build_tracked_client(enable_caching=False)
    # build judge with higher max_tokens
    from ragas.cache import DiskCacheBackend
    from ragas.llms import llm_factory
    judge_b = llm_factory(R.JUDGE_MODEL, provider="anthropic", client=client_b,
                          max_tokens=8192,
                          cache=DiskCacheBackend(cache_dir=str(ROOT / R.RAGAS_CACHE_DIR)))
    judge_b.model_args.pop("top_p", None)
    final_rows = R._evaluate_batch(final_outputs, judge_b, embeddings)
    for o, row in zip(final_outputs, final_rows, strict=True):
        f = row.get("faithfulness"); a = row.get("answer_relevancy")
        o["faithfulness"] = float(f) if f is not None and f == f else None
        o["answer_relevancy"] = float(a) if a is not None and a == a else None
    ragas_b_cost = R.cost_from_tracker(tracker_b)
    log.info("RAGAS B done. cost≈$%.3f calls=%d", ragas_b_cost, tracker_b["n_calls"])

    # D: coverage per gold
    print("\n" + "=" * 80)
    print("D — Coverage per gold")
    print("=" * 80)
    coverage = []
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = queries_data[qid]
        # union dei top-3 ID di tutte le sub-query sopravvissute = context coverage
        in_ctx = set()
        for it in qd["items"]:
            for cid, _ in it["top3"]:
                in_ctx.add(cid)
        for gold_id, label in GOLDS[qid]:
            row = {"qid": qid, "gold_id": gold_id, "label": label}
            if gold_id not in in_ctx:
                row["state"] = "NOT_IN_CONTEXT"; coverage.append(row); continue
            txt, payload = fetch_text(gold_id)
            hp = payload.get("hierarchy_path", [])
            rubric = " > ".join(hp) if isinstance(hp, list) else str(hp)
            prompt = COVERAGE_PROMPT.format(
                label=label, rubric=rubric, article_text=txt[:1500],
                answer=qd.get("final_answer", ""))
            text, n_in, n_out = call_llm(SONNET_MODEL, prompt, max_tokens=200)
            track(SONNET_MODEL, n_in, n_out)
            verdict = "NOT_ADDRESSED"
            for line in text.splitlines():
                if line.upper().startswith("VEREDICT:"):
                    v = line.split(":", 1)[1].strip().upper()
                    if "ADDRESSED" in v and "NOT" not in v:
                        verdict = "ADDRESSED"
            row["state"] = "ADDRESSED" if verdict == "ADDRESSED" else "DROWNED"
            row["judge_raw"] = text.strip()
            coverage.append(row)
            print(f"  {qid} {label} → {row['state']}")

    # === OUTPUT ===
    print("\n" + "=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    print(f"{'qid':<5}{'n_mini':>8}{'faith_med':>11}{'faith_min':>11}"
          f"{'faith_final':>13}{'ar_final':>10}{'ans_chars':>12}")
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        qd = queries_data[qid]
        mfaith = [it.get("faithfulness") for it in qd["items"]
                  if it.get("faithfulness") is not None]
        n_mini = len(qd["items"])
        med = statistics.median(mfaith) if mfaith else float("nan")
        mn = min(mfaith) if mfaith else float("nan")
        fin = next((o for o in final_outputs if o["qid"] == qid), None)
        ff = fin.get("faithfulness") if fin else None
        fa = fin.get("answer_relevancy") if fin else None
        ans_chars = len(qd.get("final_answer", ""))
        ff_s = f"{ff:.3f}" if ff is not None else "nan"
        fa_s = f"{fa:.3f}" if fa is not None else "nan"
        print(f"{qid:<5}{n_mini:>8}{med:>11.3f}{mn:>11.3f}{ff_s:>13}{fa_s:>10}{ans_chars:>12}")

    n_addr = sum(1 for r in coverage if r["state"] == "ADDRESSED")
    n_drown = sum(1 for r in coverage if r["state"] == "DROWNED")
    n_notin = sum(1 for r in coverage if r["state"] == "NOT_IN_CONTEXT")
    print("\nCOVERAGE (su 9):")
    for r in coverage:
        print(f"  {r['qid']} {r['label']:<22} → {r['state']}")
    print(f"\nADDRESSED: {n_addr}/9  DROWNED: {n_drown}/9  NOT_IN_CONTEXT: {n_notin}/9")
    print(f"Confronto: dump semplice = ADDRESSED 7/9, DROWNED 1, NOT_IN_CONTEXT 1, faith nan")

    print("\nCOSTI:")
    for m, u in cost_usage.items():
        c = (u["input_tokens"] / 1_000_000) * PRICING[m]["in"] + \
            (u["output_tokens"] / 1_000_000) * PRICING[m]["out"]
        print(f"  {m:<35} calls={u['calls']:<4} in={u['input_tokens']:>8} "
              f"out={u['output_tokens']:>6}  ≈ ${c:.3f}")
    print(f"  RAGAS A (mini)     calls={tracker_a['n_calls']:<4}  ≈ ${ragas_a_cost:.3f}")
    print(f"  RAGAS B (final)    calls={tracker_b['n_calls']:<4}  ≈ ${ragas_b_cost:.3f}")
    print(f"  TOTALE ≈ ${cost_usd() + ragas_a_cost + ragas_b_cost:.3f}")

    OUT.write_text(json.dumps({
        "queries": queries_data, "final_outputs": final_outputs, "coverage": coverage,
        "cost_usage": dict(cost_usage),
        "ragas_a_cost": ragas_a_cost, "ragas_b_cost": ragas_b_cost,
        "total_cost": cost_usd() + ragas_a_cost + ragas_b_cost,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
