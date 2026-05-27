"""Misurazione subset cross-norma v1.1 — end-to-end (retrieval + gen + RAGAS).

12 query: 6 target cross-norma + 4 sentinelle + 2 corpus_limit.

Pipeline:
- HybridRetriever (reranker ATTIVO, config produzione)
- CrossNormRetriever (enable_cross_norm path): trigger → sub-query → RRF fusion
- Sub-query LLM: cassette V2 per Q68/Q69, live Sonnet 4.6 per le altre
  multi-norma. Generazione: live Sonnet 4.6 (annotated answer come F.2).
- RAGAS judge (Sonnet 4.6): faithfulness + answer_relevancy.

Per query registra: detect_norms, path (cross-norm/fallback), rescue ratio
(gold in top-20), faith, ar.

Output:
- data/benchmark/ragas_pipeline_outputs_cross_norm_v1_1.json (intermedio)
- spike/SUBSET_CROSS_NORM_V1_1_RESULTS.md (report)

    spike/.venv/bin/python spike/run_subset_cross_norm_v1_1.py

Costo target ~$1.20-1.50. Reranker richiede ~2.3GB su MPS.
"""

from __future__ import annotations

import json
import logging
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("subset_cn_v11")
log.setLevel(logging.INFO)

GOLD_PATH = ROOT / "data/benchmark/gold_answers_v3.json"
SUBSET_PATH = ROOT / "data/benchmark/subset_cross_norm_v1_1.yaml"
CASSETTE_PATH = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"
OUTPUTS_PATH = ROOT / "data/benchmark/ragas_pipeline_outputs_cross_norm_v1_1.json"
REPORT_PATH = ROOT / "spike/SUBSET_CROSS_NORM_V1_1_RESULTS.md"

COLLECTION = "italian_legal_v1_hybrid"
TOP_K_GEN = 5            # chunk passati all'LLM (default produzione)
TOP_K_RESCUE = 20        # finestra per rescue ratio
MAX_OUTPUT_TOKENS = 1000
SYSTEM_LANG = "it"

# qid → label cassette (solo Q68/Q69 hanno cassette V2; altri → live)
CASSETTE_LABELS = {"Q68": "q68", "Q69": "q69"}

_SHORT_TO_ID = {
    "GDPR": "gdpr", "AI Act": "ai_act", "D.Lgs 231/2001": "dlgs_231",
    "NIS2": "nis2", "Codice Privacy": "codice_privacy", "L. 132/2025": "l_132_2025",
}


class _Res:
    def __init__(self, text: str):
        self.text = text
        self.n_input_tokens = 0
        self.n_output_tokens = 0
        self.finish_reason = "stop"


class CassetteOrLiveLLM:
    """Wrapper su un LLMProvider reale.

    Per i prompt di sub-query (riconoscibili da 'Norma target:') usa la
    cassette se la chiave `<label>:<norm_id>` esiste, altrimenti chiama live.
    Per qualunque altro prompt (es. generation) chiama sempre live.
    """

    def __init__(self, live_provider, cassette: dict):
        self._live = live_provider
        self._cassette = cassette
        self.current_label: str | None = None
        self.subquery_calls: list[dict] = []

    @property
    def provider_name(self):
        return self._live.provider_name

    @property
    def model_name(self):
        return self._live.model_name

    def generate(self, prompt, system=None, max_tokens=500, temperature=0.0):
        norm_id = self._infer_norm(prompt)
        if norm_id is not None:
            key = f"{self.current_label}:{norm_id}" if self.current_label else None
            if key and key in self._cassette:
                self.subquery_calls.append({"key": key, "source": "cassette"})
                return _Res(self._cassette[key])
            res = self._live.generate(prompt=prompt, system=system,
                                      max_tokens=max_tokens, temperature=temperature)
            self.subquery_calls.append({
                "key": key or f"?:{norm_id}", "source": "live"})
            return res
        # non è una sub-query → generation, sempre live
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


def _median(vals: list[float]) -> float | None:
    v = [x for x in vals if x is not None]
    return statistics.median(v) if v else None


def step_retrieve_generate() -> list[dict]:
    import yaml
    from dotenv import load_dotenv
    env = ROOT / ".env"
    if env.is_file():
        load_dotenv(env, override=False)

    from qdrant_client import QdrantClient
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.hybrid_retriever.types import RetrievalResult
    from core.cross_norm import CrossNormRetriever, detect_norms
    from core.rag_prompt import build_user_prompt, load_system_prompt
    from core.citation_verifier import verify_citations
    from core.llm_provider.config import load_provider_from_env

    subset = yaml.safe_load(SUBSET_PATH.read_text(encoding="utf-8"))["qids"]
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
    cross_norm = CrossNormRetriever(
        hybrid_retriever=hybrid, llm_client=llm,
        top_k_final=TOP_K_RESCUE, rerank_top_k_per_norm=20, rerank_top_k_global=20,
    )
    system_prompt = load_system_prompt(SYSTEM_LANG)
    log.info("Provider=%s model=%s", llm.provider_name, llm.model_name)

    outputs: list[dict] = []
    for i, qid in enumerate(subset, 1):
        entry = gold[qid]
        question = entry["question"]
        gold_ids = [g["chunk_id"] for g in entry.get("gold_chunks", []) if g.get("chunk_id")]
        gold_set = set(gold_ids)

        norms = detect_norms(question)
        path = "cross-norm" if len(norms) >= 2 else "fallback"
        llm.current_label = CASSETTE_LABELS.get(qid)  # None → live sub-query

        log.info("[%d/12] %s norms=%s path=%s", i, qid, norms, path)

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

        # Generazione (top-5 del fusion) — annotated answer come F.2
        top5 = RetrievalResult(list(top20)[:TOP_K_GEN])
        contexts = [(h.payload.get("text") or "").strip() for h in top5]
        user_prompt = build_user_prompt(question, top5, include_expanded=False)
        gen = llm._live.generate(prompt=user_prompt, system=system_prompt,
                                 max_tokens=MAX_OUTPUT_TOKENS, temperature=0.0)
        verification = verify_citations(gen.text, retrieval_context={h.chunk_id for h in top5})
        answer = verification.annotated_text

        outputs.append({
            "qid": qid,
            "query_type": entry["query_type"],
            "question": question,
            "gold_chunks": entry.get("gold_chunks", []),
            "retrieved_chunks": retrieved_chunks,
            "contexts": contexts,
            "answer": answer,
            "ground_truth": entry.get("gold_answer", ""),
            "has_corpus_limit_declaration": entry.get("has_corpus_limit_declaration", False),
            "use_case": entry.get("use_case", ""),
            "detect_norms": norms,
            "path": path,
            "rescue_ratio": rescue,
            "n_gold": n_gold,
            "gold_in_top20": sorted(gold_set & set(ranked_ids[:TOP_K_RESCUE])),
            "gold_missing_top20": sorted(gold_set - set(ranked_ids[:TOP_K_RESCUE])),
        })

    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "provider": llm.provider_name, "model": llm.model_name,
        "top_k_gen": TOP_K_GEN, "top_k_rescue": TOP_K_RESCUE,
        "subquery_calls": llm.subquery_calls,
        "n_queries": len(outputs),
    }
    OUTPUTS_PATH.write_text(
        json.dumps({"metadata": meta, "outputs": outputs}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    log.info("Outputs scritti: %s (sub-query calls: %d)",
             OUTPUTS_PATH.name, len(llm.subquery_calls))
    return outputs


def step_judge(outputs: list[dict]) -> dict[str, dict]:
    """RAGAS faith/ar sui 12 outputs. Ritorna {qid: {faithfulness, answer_relevancy}}."""
    sys.path.insert(0, str(ROOT / "spike"))
    import run_ragas_eval_v2 as R
    from langchain_huggingface import HuggingFaceEmbeddings

    R._load_env()
    client, tracker = R.build_tracked_client(enable_caching=False)
    judge = R.build_judge(client)
    embeddings = HuggingFaceEmbeddings(model_name=R.EMBEDDINGS_MODEL)

    log.info("RAGAS judge su %d query (model=%s)...", len(outputs), R.JUDGE_MODEL)
    rows = R._evaluate_batch(outputs, judge, embeddings)
    by_qid: dict[str, dict] = {}
    for o, row in zip(outputs, rows, strict=True):
        by_qid[o["qid"]] = {
            "faithfulness": float(row["faithfulness"]) if row.get("faithfulness") is not None else None,
            "answer_relevancy": float(row["answer_relevancy"]) if row.get("answer_relevancy") is not None else None,
        }
    cost = R.cost_from_tracker(tracker)
    log.info("Judge done. n_calls=%d cost≈$%.3f", tracker["n_calls"], cost)
    by_qid["__cost__"] = {"usd": cost, "n_calls": tracker["n_calls"]}
    return by_qid


def write_report(outputs: list[dict], judged: dict[str, dict]) -> None:
    TARGET = ["Q9", "Q25", "Q68", "Q69", "Q70", "Q71"]
    SENTINEL = ["Q6", "Q7", "Q63", "Q87"]
    CORPUS_LIMIT = ["Q43", "Q94"]
    by_qid = {o["qid"]: o for o in outputs}

    L: list[str] = []
    L.append("# Subset cross-norma v1.1 — misurazione end-to-end")
    L.append("")
    L.append(f"**Data (UTC)**: {datetime.now(timezone.utc).isoformat()}")
    cost = judged.get("__cost__", {})
    L.append(f"**Judge cost**: ≈${cost.get('usd', 0):.3f} ({cost.get('n_calls', 0)} judge calls)")
    L.append("**Config**: enable_cross_norm=True, reranker MPS attivo, "
             "gen Sonnet 4.6 top_k=5, judge Sonnet 4.6, sub-query cassette V2 (Q68/Q69) + live.")
    L.append("")

    # verifica falsi positivi trigger
    L.append("## Verifica trigger (sentinelle + corpus_limit)")
    L.append("")
    L.append("| qid | gruppo | detect_norms | path | atteso |")
    L.append("|---|---|---|---|---|")
    fp = []
    for qid in SENTINEL + CORPUS_LIMIT:
        o = by_qid[qid]
        grp = "sentinella" if qid in SENTINEL else "corpus_limit"
        ok = len(o["detect_norms"]) < 2
        flag = "✓ fallback" if ok else "⚠ FALSO POSITIVO"
        if not ok:
            fp.append(qid)
        L.append(f"| {qid} | {grp} | {o['detect_norms']} | {o['path']} | {flag} |")
    L.append("")
    if fp:
        L.append(f"**⚠ FALSI POSITIVI TRIGGER: {fp}** — il trigger è scattato su query non multi-norma.")
    else:
        L.append("**Zero falsi positivi**: tutte le sentinelle e corpus_limit → path fallback.")
    L.append("")

    # per-query dettaglio
    def section(title: str, qids: list[str]):
        L.append(f"## {title}")
        L.append("")
        L.append("| qid | type | detect_norms | path | rescue | faith | ar |")
        L.append("|---|---|---|---|---|---|---|")
        for qid in qids:
            o = by_qid[qid]
            j = judged.get(qid, {})
            rescue = o["rescue_ratio"]
            rescue_s = "n/a" if rescue is None else f"{len(o['gold_in_top20'])}/{o['n_gold']} ({rescue:.2f})"
            fa = j.get("faithfulness")
            ar = j.get("answer_relevancy")
            fa_s = "n/a" if fa is None else f"{fa:.3f}"
            ar_s = "n/a" if ar is None else f"{ar:.3f}"
            norms_s = ",".join(o["detect_norms"]) if o["detect_norms"] else "—"
            L.append(f"| {qid} | {o['query_type']} | {norms_s} | {o['path']} | {rescue_s} | {fa_s} | {ar_s} |")
        L.append("")

    section("Target cross-norma (6)", TARGET)
    section("Sentinelle mainstream (4)", SENTINEL)
    section("Corpus_limit (2)", CORPUS_LIMIT)

    # gold missing dettaglio target
    L.append("## Gold mancanti in top-20 (target cross-norma)")
    L.append("")
    for qid in TARGET:
        o = by_qid[qid]
        if o["gold_missing_top20"]:
            L.append(f"- **{qid}**: {o['gold_missing_top20']}")
        else:
            L.append(f"- **{qid}**: nessuno (rescue completo)")
    L.append("")

    # tabella sintetica finale
    def med(qids, key_metric):
        return _median([judged.get(q, {}).get(key_metric) for q in qids])

    def med_rescue(qids):
        return _median([by_qid[q]["rescue_ratio"] for q in qids])

    L.append("## Tabella sintetica")
    L.append("")
    L.append("| gruppo | n | rescue med | faith med | ar med |")
    L.append("|---|---|---|---|---|")
    for label, qids in [("target cross-norma", TARGET),
                        ("sentinelle", SENTINEL),
                        ("corpus_limit", CORPUS_LIMIT)]:
        r = med_rescue(qids)
        f = med(qids, "faithfulness")
        a = med(qids, "answer_relevancy")
        r_s = "n/a" if r is None else f"{r:.3f}"
        f_s = "n/a" if f is None else f"{f:.3f}"
        a_s = "n/a" if a is None else f"{a:.3f}"
        L.append(f"| {label} | {len(qids)} | {r_s} | {f_s} | {a_s} |")
    L.append("")
    L.append("_Non-regressione: confronta sentinelle/corpus_limit vs F.2 v3 archived "
             "(data/benchmark/ragas_aggregates_v2.json / BENCHMARK_RAGAS_W7_v2.md)._")
    L.append("")
    L.append("## Note di lettura")
    L.append("")
    L.append("_(da compilare manualmente)_")
    L.append("")

    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    log.info("Report scritto: %s", REPORT_PATH)


def main() -> int:
    outputs = step_retrieve_generate()
    judged = step_judge(outputs)
    # persisti faith/ar dentro outputs json
    payload = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    for o in payload["outputs"]:
        j = judged.get(o["qid"], {})
        o["faithfulness"] = j.get("faithfulness")
        o["answer_relevancy"] = j.get("answer_relevancy")
    payload["metadata"]["judge_cost"] = judged.get("__cost__", {})
    OUTPUTS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    write_report(outputs, judged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
