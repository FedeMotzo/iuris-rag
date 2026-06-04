"""Subset v1.2 paid run — 19 query, fusion z-normalized + gated.

Per ogni query: detect_norms, retrieve (cross-norm v1.2 o fallback), gen
Sonnet 4.6 max_tokens=4000, judge RAGAS.

Telemetria per ogni query target:
- fusion_stats (n_below_floor, n_after_floor_per_source, low_signal_sources,
  n_normalized, n_gated, z_top_k_*).
- sub_queries per norma (list[str]).
- per i 5 gold mancanti v1.1, fusion_rank + classificazione A/B/C/D.

Costo atteso: ~$1.50.

    spike/.venv/bin/python spike/run_subset_v1_2.py
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("subset_v1_2")
log.setLevel(logging.INFO)

GOLD_PATH = ROOT / "data/benchmark/gold_answers_v3.json"
CASSETTE_PATH = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"
OUTPUTS_PATH = ROOT / "spike/data/subset_v1_2_outputs.json"

COLLECTION = "italian_legal_v1_hybrid"
TOP_K_GEN = 5
TOP_K_RESCUE = 20
MAX_OUTPUT_TOKENS = 4000

# 19 query del subset v1.1
SUBSET = [
    # Target cross-norma (6)
    "Q9", "Q25", "Q68", "Q69", "Q70", "Q71",
    # Sentinelle mainstream (4)
    "Q6", "Q7", "Q63", "Q87",
    # Corpus_limit (2)
    "Q43", "Q94",
    # Mono-stress (3)
    "Q34", "Q35", "Q38",
    # Gold-recital (4)
    "Q1", "Q3", "Q8", "Q29",
]

CASSETTE_LABELS = {
    "Q9": "q9", "Q68": "q68", "Q69": "q69", "Q70": "q70", "Q71": "q71",
}

_SHORT_TO_ID = {
    "GDPR": "gdpr", "AI Act": "ai_act", "D.Lgs 231/2001": "dlgs_231",
    "NIS2": "nis2", "Codice Privacy": "codice_privacy", "L. 132/2025": "l_132_2025",
}

NORM_TO_DOC_URN = {
    "gdpr": "eli/reg/2016/679/oj",
    "ai_act": "eli/reg/2024/1689/oj",
    "dlgs_231": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
    "nis2": "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    "codice_privacy": "akn/it/act/decreto_legislativo/stato/2003-06-30/196",
    "l_132_2025": "akn/it/act/legge/stato/2025-09-23/132",
}

# 5 gold mancanti v1.1 (dal brief)
MISSING_V11 = [
    ("Q68", "eli/reg/2024/1689/oj__art_6"),
    ("Q68", "eli/reg/2016/679/oj__art_9"),
    ("Q69", "eli/reg/2024/1689/oj__art_6"),
    ("Q70", "eli/reg/2016/679/oj__art_44"),
    ("Q70", "akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies"),
    ("Q71", "eli/reg/2024/1689/oj__annex_III__point_5"),
]


class _Res:
    def __init__(self, text: str):
        self.text = text
        self.n_input_tokens = 0
        self.n_output_tokens = 0
        self.finish_reason = "stop"


class CassetteOrLiveLLM:
    """Wrapper LLMProvider con cassette per sub-query Q9/Q68/Q69/Q70/Q71."""

    def __init__(self, live_provider, cassette: dict):
        self._live = live_provider
        self._cassette = cassette
        self.current_label: str | None = None
        self.subquery_calls: list[dict] = []

    @property
    def provider_name(self): return self._live.provider_name
    @property
    def model_name(self): return self._live.model_name

    def generate(self, prompt, system=None, max_tokens=500, temperature=0.0):
        norm_id = self._infer_norm(prompt)
        if norm_id is not None:
            key = f"{self.current_label}:{norm_id}" if self.current_label else None
            if key and key in self._cassette:
                self.subquery_calls.append({"key": key, "source": "cassette"})
                val = self._cassette[key]
                if isinstance(val, list):
                    return _Res(json.dumps(val, ensure_ascii=False))
                return _Res(val)
            res = self._live.generate(prompt=prompt, system=system,
                                      max_tokens=max_tokens, temperature=temperature)
            self.subquery_calls.append({"key": key or f"?:{norm_id}", "source": "live"})
            return res
        return self._live.generate(prompt=prompt, system=system,
                                   max_tokens=max_tokens, temperature=temperature)

    @staticmethod
    def _infer_norm(prompt: str) -> str | None:
        for line in prompt.splitlines():
            if line.startswith("Norma target:"):
                tail = line[len("Norma target:"):].strip()
                for short, nid in _SHORT_TO_ID.items():
                    if tail.startswith(short):
                        return nid
                return None
        return None


def _classify_gold_abcd(gold_id: str, qid: str, sub_queries_by_norm: dict,
                        fusion_rank: int | None) -> dict:
    """Categorie A/B/C/D per i 5 gold mancanti v1.1.

    A: concetto nominato + rank ≤5
    B: concetto nominato + rank >5 (o assente)
    C: concetto NON nominato + non in top-5
    D: NON nominato + in top-5 (recuperato da global)
    """
    # Norm del gold dal chunk_id
    norm_id = None
    for nid, urn in NORM_TO_DOC_URN.items():
        if gold_id.startswith(urn):
            norm_id = nid
            break
    # Numero articolo / punto allegato
    art_match = re.search(r"art_([0-9a-z\-]+)", gold_id)
    art_num = art_match.group(1) if art_match else None
    point_match = re.search(r"point_(\d+)", gold_id)
    point_num = point_match.group(1) if point_match else None

    named = False
    sub_qs = sub_queries_by_norm.get(norm_id, [])
    joined = " ".join(sub_qs).lower()
    if art_num:
        if re.search(rf"art(?:\.|icolo)?\s*{re.escape(art_num)}\b", joined):
            named = True
    if point_num and re.search(rf"punto\s*{re.escape(point_num)}\b", joined):
        named = True
    if not named and "annex_III" in gold_id and re.search(r"allegato\s+iii", joined):
        # solo "Allegato III" senza punto → NON considera nominato il singolo punto
        pass

    in_top5 = fusion_rank is not None and fusion_rank <= 5
    if named and in_top5:
        cat = "A"
    elif named and not in_top5:
        cat = "B"
    elif not named and in_top5:
        cat = "D"
    else:
        cat = "C"
    return {"category": cat, "named": named, "in_top5": in_top5,
            "norm": norm_id, "art_num": art_num or point_num,
            "fusion_rank": fusion_rank}


def step_retrieve_generate() -> list[dict]:
    from dotenv import load_dotenv
    env = ROOT / ".env"
    if env.is_file():
        load_dotenv(env, override=False)

    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.citation_verifier import verify_citations
    from core.cross_norm import CrossNormRetriever, detect_norms
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.hybrid_retriever.types import RetrievalResult
    from core.llm_provider.config import load_provider_from_env
    from core.rag_prompt import build_user_prompt, load_system_prompt

    gold = {e["qid"]: e for e in json.loads(GOLD_PATH.read_text(encoding="utf-8"))}
    cassette = json.loads(CASSETTE_PATH.read_text(encoding="utf-8"))

    log.info("Loading models (bge-m3 + bm25 + reranker)...")
    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    hybrid = HybridRetriever(client, encoder, bm25, COLLECTION, reranker=reranker)

    live = load_provider_from_env()
    llm = CassetteOrLiveLLM(live, cassette)
    system_prompt = load_system_prompt("it")
    log.info("Provider=%s model=%s", llm.provider_name, llm.model_name)

    cross_norm = CrossNormRetriever(
        hybrid_retriever=hybrid, llm_client=llm,
        top_k_per_norm=20, top_k_global=20, top_k_final=20,
        rerank_top_k_per_norm=20, rerank_top_k_global=20,
    )

    outputs: list[dict] = []
    for i, qid in enumerate(SUBSET, 1):
        entry = gold[qid]
        question = entry["question"]
        gold_ids = [g["chunk_id"] for g in entry.get("gold_chunks", []) if g.get("chunk_id")]
        gold_set = set(gold_ids)
        norms = detect_norms(question)
        path = "cross-norm" if len(norms) >= 2 else "fallback"
        llm.current_label = CASSETTE_LABELS.get(qid)

        log.info("[%d/%d] %s norms=%s path=%s", i, len(SUBSET), qid, norms, path)

        top20 = cross_norm.retrieve(question, top_k=TOP_K_RESCUE)
        ranked_ids = [h.chunk_id for h in top20]
        retrieved_chunks = [
            {"rank": h.rank, "chunk_id": h.chunk_id, "score": float(h.score),
             "is_gold": h.chunk_id in gold_set}
            for h in top20
        ]
        n_gold = len(gold_ids)
        rescue = (len(gold_set & set(ranked_ids[:TOP_K_RESCUE])) / n_gold
                  if n_gold else None)
        rescue_at_5 = (len(gold_set & set(ranked_ids[:TOP_K_GEN])) / n_gold
                       if n_gold else None)

        # Trace estesa (solo per cross-norm path)
        trace_summary = {}
        if path == "cross-norm" and cross_norm.last_trace:
            tr = cross_norm.last_trace
            trace_summary = {
                "sub_queries": {k: list(v) for k, v in tr.get("sub_queries", {}).items()},
                "fusion_stats": tr.get("fusion_stats", {}),
            }

        # Generazione top-5 fused
        top5 = RetrievalResult(list(top20)[:TOP_K_GEN])
        contexts = [(h.payload.get("text") or "").strip() for h in top5]
        user_prompt = build_user_prompt(question, top5, include_expanded=False)
        gen = llm._live.generate(prompt=user_prompt, system=system_prompt,
                                 max_tokens=MAX_OUTPUT_TOKENS, temperature=0.0)
        verification = verify_citations(gen.text, retrieval_context={h.chunk_id for h in top5})
        answer = verification.annotated_text

        outputs.append({
            "qid": qid, "query_type": entry["query_type"], "question": question,
            "gold_chunks": entry.get("gold_chunks", []),
            "retrieved_chunks": retrieved_chunks, "contexts": contexts,
            "answer": answer, "ground_truth": entry.get("gold_answer", ""),
            "has_corpus_limit_declaration": entry.get("has_corpus_limit_declaration", False),
            "use_case": entry.get("use_case", ""), "detect_norms": norms, "path": path,
            "rescue_ratio": rescue, "rescue_at_5": rescue_at_5,
            "n_gold": n_gold,
            "gold_in_top20": sorted(gold_set & set(ranked_ids[:TOP_K_RESCUE])),
            "gold_missing_top20": sorted(gold_set - set(ranked_ids[:TOP_K_RESCUE])),
            "trace_summary": trace_summary,
        })

    # Classifica A/B/C/D per i 5 mancanti v1.1
    by_qid = {o["qid"]: o for o in outputs}
    abcd_rows = []
    for qid, gold_id in MISSING_V11:
        o = by_qid.get(qid)
        if o is None:
            continue
        ranked_ids = [c["chunk_id"] for c in o["retrieved_chunks"]]
        fusion_rank = ranked_ids.index(gold_id) + 1 if gold_id in ranked_ids else None
        sq_by_norm = o.get("trace_summary", {}).get("sub_queries", {})
        cls = _classify_gold_abcd(gold_id, qid, sq_by_norm, fusion_rank)
        cls["qid"] = qid
        cls["gold"] = gold_id
        abcd_rows.append(cls)

    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "provider": llm.provider_name, "model": llm.model_name,
        "top_k_gen": TOP_K_GEN, "top_k_rescue": TOP_K_RESCUE,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "subquery_calls": llm.subquery_calls, "n_queries": len(outputs),
    }
    OUTPUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUTS_PATH.write_text(
        json.dumps({"metadata": meta, "outputs": outputs, "abcd_telemetry": abcd_rows},
                   indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    log.info("Outputs scritti: %s", OUTPUTS_PATH)
    return outputs


def step_judge(outputs: list[dict]) -> dict:
    sys.path.insert(0, str(ROOT / "spike"))
    import run_ragas_eval_v2 as R
    from langchain_huggingface import HuggingFaceEmbeddings

    R._load_env()
    client, tracker = R.build_tracked_client(enable_caching=False)
    judge = R.build_judge(client)
    embeddings = HuggingFaceEmbeddings(model_name=R.EMBEDDINGS_MODEL)

    log.info("RAGAS judge su %d outputs...", len(outputs))
    rows = R._evaluate_batch(outputs, judge, embeddings)
    for o, row in zip(outputs, rows, strict=True):
        o["faithfulness"] = float(row["faithfulness"]) if row.get("faithfulness") is not None else None
        o["answer_relevancy"] = float(row["answer_relevancy"]) if row.get("answer_relevancy") is not None else None
    cost = R.cost_from_tracker(tracker)
    log.info("Judge done. n_calls=%d cost≈$%.3f", tracker["n_calls"], cost)
    return {"usd": cost, "n_calls": tracker["n_calls"]}


def main() -> int:
    outputs = step_retrieve_generate()
    cost = step_judge(outputs)
    payload = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    payload["outputs"] = outputs
    payload["metadata"]["judge_cost"] = cost
    OUTPUTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    log.info("DONE. judge cost=%s", cost)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
