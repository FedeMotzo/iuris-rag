"""Smoke test coabitazione MPS — W5.

Verifica se bge-m3 (encoder MPS), bge-reranker-v2-m3 e Qwen2.5-14B-Q4_K_M
(via Ollama) possono coabitare sui 24 GB di unified memory di un Mac M4
Pro, e in quale configurazione la latenza end-to-end del flusso
retrieval → rerank → generate resta entro 5 s.

Non modifica core/; usa HybridRetriever e BgeM3Encoder così come sono.

Esegui:
    spike/.venv/bin/python spike/smoke_mps_coabitation.py
"""

from __future__ import annotations

import gc
import json
import logging
import os
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOG_PATH = ROOT / "spike" / "smoke_mps_coabitation.log"
RESULTS_PATH = ROOT / "spike" / "MPS_COABITATION_RESULTS.md"
GOLD_PATH = ROOT / "data" / "benchmark" / "gold_validated_v2.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("smoke_mps")

# --- Costanti -----------------------------------------------------------------

COLLECTION = "italian_legal_v1_hybrid"
BM25_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_MAX_LENGTH = 512
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "qwen2.5:14b"

TARGET_QIDS = ["Q6", "Q7", "Q1"]
N_RUNS = 3  # primo è warmup, mediano sui 2 restanti
RERANK_TOP_K = 20
RAG_TOP_K = 5  # quanti chunk passare al prompt
MAX_OUTPUT_TOKENS = 500

# Soglie pass/fail
LAT_P50_THRESHOLD_MS = 5000
TOK_PER_SEC_WARN = 10.0

SAMPLE_INTERVAL_S = 0.5

# --- Sampler --------------------------------------------------------------------


@dataclass
class MemorySample:
    t: float
    rss_python_mb: float
    rss_ollama_mb: float
    mps_current_mb: float
    mps_driver_mb: float
    vm_total_mb: float
    vm_used_mb: float
    vm_available_mb: float
    swap_used_mb: float


class MemorySampler:
    """Campiona metriche di memoria in un thread di background."""

    def __init__(self, interval_s: float = SAMPLE_INTERVAL_S) -> None:
        self._interval = interval_s
        self._samples: list[MemorySample] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._py = psutil.Process(os.getpid())
        self._torch_mps = None

    def _init_torch(self) -> None:
        try:
            import torch
            if torch.backends.mps.is_available():
                self._torch_mps = torch.mps
        except Exception:
            self._torch_mps = None

    def _find_ollama_rss(self) -> float:
        total = 0.0
        for p in psutil.process_iter(["name"]):
            try:
                name = (p.info.get("name") or "").lower()
                if "ollama" in name:
                    total += p.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return total

    def _take_sample(self) -> MemorySample:
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        mps_cur = 0.0
        mps_drv = 0.0
        if self._torch_mps is not None:
            try:
                mps_cur = self._torch_mps.current_allocated_memory() / (1024 * 1024)
                mps_drv = self._torch_mps.driver_allocated_memory() / (1024 * 1024)
            except Exception:
                pass
        return MemorySample(
            t=time.time(),
            rss_python_mb=self._py.memory_info().rss / (1024 * 1024),
            rss_ollama_mb=self._find_ollama_rss(),
            mps_current_mb=mps_cur,
            mps_driver_mb=mps_drv,
            vm_total_mb=vm.total / (1024 * 1024),
            vm_used_mb=vm.used / (1024 * 1024),
            vm_available_mb=vm.available / (1024 * 1024),
            swap_used_mb=sw.used / (1024 * 1024),
        )

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._samples.append(self._take_sample())
            except Exception as exc:
                log.warning("sampler error: %s", exc)
            self._stop.wait(self._interval)

    def start(self) -> None:
        self._init_torch()
        self._samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> list[MemorySample]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return list(self._samples)


# --- Memory pressure ------------------------------------------------------------


def memory_pressure() -> str:
    """Approssima la pressione memoria via `memory_pressure` (macOS) o vm_stat.

    Ritorna "normal", "warn", "critical" oppure "unknown".
    """
    # memory_pressure -Q non esiste su tutte le macchine; usiamo vm_stat e
    # confrontiamo free+inactive vs total.
    try:
        out = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=2,
        ).stdout
    except Exception:
        return "unknown"

    page_size = 16384  # M-series usa 16 KiB di default
    free = inactive = active = wired = compressor = 0
    for line in out.splitlines():
        if "page size of" in line:
            parts = line.strip().rstrip(".").split()
            try:
                page_size = int(parts[-2])
            except (ValueError, IndexError):
                pass
        elif line.startswith("Pages free:"):
            free = int(line.split(":")[1].strip().rstrip("."))
        elif line.startswith("Pages inactive:"):
            inactive = int(line.split(":")[1].strip().rstrip("."))
        elif line.startswith("Pages active:"):
            active = int(line.split(":")[1].strip().rstrip("."))
        elif line.startswith("Pages wired down:"):
            wired = int(line.split(":")[1].strip().rstrip("."))
        elif line.startswith("Pages occupied by compressor:"):
            compressor = int(line.split(":")[1].strip().rstrip("."))

    total_pages = free + inactive + active + wired + compressor
    if total_pages == 0:
        return "unknown"
    free_ratio = (free + inactive) / total_pages
    # Macos memory_pressure normal ~ >20% free+inactive; warn 10-20%; critical <10%
    if free_ratio > 0.20:
        return "normal"
    if free_ratio > 0.10:
        return "warn"
    return "critical"


# --- Caricamento risorse --------------------------------------------------------


def load_queries() -> list[dict[str, str]]:
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    by_qid = {q["qid"]: q for q in data["queries"]}
    out = []
    for qid in TARGET_QIDS:
        if qid not in by_qid:
            raise RuntimeError(f"qid {qid} non in {GOLD_PATH}")
        out.append({"qid": qid, "query": by_qid[qid]["query"]})
    return out


def check_ollama_model() -> None:
    log.info("Verifico modello Ollama %s su %s", OLLAMA_MODEL, OLLAMA_HOST)
    r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
    r.raise_for_status()
    names = {m["name"] for m in r.json().get("models", [])}
    if OLLAMA_MODEL not in names:
        raise RuntimeError(f"{OLLAMA_MODEL} non installato. Disponibili: {names}")


def build_retriever(reranker):
    """Costruisce HybridRetriever riusando il singleton bge-m3 (MPS)."""
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name=BM25_MODEL)
    client = QdrantClient(host="localhost", port=6333)
    return HybridRetriever(
        client=client,
        encoder=encoder,
        bm25=bm25,
        collection=COLLECTION,
        reranker=reranker,
    )


def load_reranker(device: str):
    from sentence_transformers import CrossEncoder
    log.info("Carico reranker %s su device=%s", RERANKER_MODEL, device)
    rk = CrossEncoder(RERANKER_MODEL, device=device, max_length=RERANK_MAX_LENGTH)
    # warmup
    rk.predict([("warmup", "warmup")], show_progress_bar=False)
    return rk


def unload_reranker(reranker) -> float:
    """Scarica il reranker e libera memoria MPS. Ritorna tempo in ms."""
    t0 = time.perf_counter()
    try:
        # forziamo deallocazione esplicita dei tensori sul device
        if hasattr(reranker, "model"):
            del reranker.model
    except Exception:
        pass
    del reranker
    gc.collect()
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            torch.mps.synchronize()
    except Exception:
        pass
    return (time.perf_counter() - t0) * 1000


# --- Prompt RAG -----------------------------------------------------------------


def build_rag_prompt(query: str, hits) -> str:
    parts = []
    for h in hits[:RAG_TOP_K]:
        chunk_id = h.chunk_id
        hierarchy = " > ".join(h.payload.get("hierarchy_path") or [])
        text = (h.payload.get("text") or "").strip()
        parts.append(f"[{chunk_id}] {hierarchy}\n{text}\n---\n")
    context = "\n".join(parts)
    return (
        "Rispondi in italiano alla domanda usando solo i passaggi normativi qui sotto. "
        "Cita gli identificativi tra parentesi quadre.\n\n"
        f"--- PASSAGGI ---\n{context}\n--- DOMANDA ---\n{query}\n"
    )


# --- Chiamata Ollama in streaming ----------------------------------------------


@dataclass
class GenResult:
    t_first_token_ms: float
    t_total_ms: float
    n_tokens: int
    text: str


def ollama_generate_stream(prompt: str) -> GenResult:
    """Stream da /api/generate, misura TTFT e tempo totale."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        # num_ctx=8192: il default Ollama (2048) provoca context shift quando
        # prompt + output > 2048, invalidando la KV cache del prefisso. Per
        # Q1 (prompt ~3k tok + 500 output) questo si traduce in TTFT 21s
        # ricorrenti invece dei ~150ms attesi su cache hit. 8192 entra
        # ampiamente nei budget memoria di Qwen Q4_K_M.
        "options": {"num_predict": MAX_OUTPUT_TOKENS, "num_ctx": 8192},
    }
    t0 = time.perf_counter()
    t_first: float | None = None
    chunks: list[str] = []
    n_tokens = 0
    with httpx.stream(
        "POST",
        f"{OLLAMA_HOST}/api/generate",
        json=payload,
        timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
    ) as r:
        r.raise_for_status()
        for raw in r.iter_lines():
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "response" in obj and obj["response"]:
                if t_first is None:
                    t_first = time.perf_counter()
                chunks.append(obj["response"])
                # ogni chunk in /api/generate è ~1 token; ma il valore vero
                # arriva nel done finale come eval_count.
            if obj.get("done"):
                if "eval_count" in obj:
                    n_tokens = int(obj["eval_count"])
                break
    t_end = time.perf_counter()
    if t_first is None:
        t_first = t_end
    if n_tokens == 0:
        # fallback: stima per chunk count
        n_tokens = len(chunks)
    return GenResult(
        t_first_token_ms=(t_first - t0) * 1000,
        t_total_ms=(t_end - t0) * 1000,
        n_tokens=n_tokens,
        text="".join(chunks),
    )


# --- Misurazione di una singola query ------------------------------------------


@dataclass
class QueryRun:
    qid: str
    t_retrieval_ms: float
    t_rerank_ms: float
    t_gen_ttft_ms: float
    t_gen_total_ms: float
    n_output_tokens: int
    tok_per_sec: float
    t_end_to_end_ms: float


def run_one_query(retriever, query: str, qid: str) -> QueryRun:
    # Retrieval con rerank_top_k=20: HybridRetriever fa retrieve + rerank
    # in una sola call. Per separare le due fasi, facciamo retrieve raw e
    # poi rerank manuale, replicando la logica interna.
    t_r0 = time.perf_counter()
    raw_hits = list(retriever.retrieve(
        query=query, top_k=RERANK_TOP_K, mode="hybrid", rerank_top_k=None,
    ))
    t_r1 = time.perf_counter()

    t_rk0 = time.perf_counter()
    reranked = retriever._rerank(query, raw_hits, top_k=RAG_TOP_K)
    t_rk1 = time.perf_counter()

    prompt = build_rag_prompt(query, reranked)
    gen = ollama_generate_stream(prompt)

    t_retr_ms = (t_r1 - t_r0) * 1000
    t_rerank_ms = (t_rk1 - t_rk0) * 1000
    elapsed_gen = max(gen.t_total_ms - gen.t_first_token_ms, 1.0)
    tok_per_sec = gen.n_tokens / (elapsed_gen / 1000.0)
    e2e = t_retr_ms + t_rerank_ms + gen.t_total_ms

    log.info(
        "[%s] retr=%.0fms rerank=%.0fms TTFT=%.0fms gen=%.0fms tok=%d tok/s=%.1f e2e=%.0fms",
        qid, t_retr_ms, t_rerank_ms, gen.t_first_token_ms, gen.t_total_ms,
        gen.n_tokens, tok_per_sec, e2e,
    )

    return QueryRun(
        qid=qid,
        t_retrieval_ms=t_retr_ms,
        t_rerank_ms=t_rerank_ms,
        t_gen_ttft_ms=gen.t_first_token_ms,
        t_gen_total_ms=gen.t_total_ms,
        n_output_tokens=gen.n_tokens,
        tok_per_sec=tok_per_sec,
        t_end_to_end_ms=e2e,
    )


# --- Scenario -------------------------------------------------------------------


@dataclass
class ScenarioResult:
    name: str
    description: str
    runs: dict[str, list[QueryRun]] = field(default_factory=dict)  # qid -> runs (escluso warmup)
    peak_rss_python_mb: float = 0.0
    peak_rss_ollama_mb: float = 0.0
    peak_mps_current_mb: float = 0.0
    peak_mps_driver_mb: float = 0.0
    peak_vm_used_mb: float = 0.0
    swap_delta_mb: float = 0.0
    memory_pressure_observed: str = "normal"
    extra: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def median_e2e_ms(self) -> float:
        all_runs = [r for runs in self.runs.values() for r in runs]
        if not all_runs:
            return float("nan")
        return statistics.median(r.t_end_to_end_ms for r in all_runs)

    def median_tok_per_sec(self) -> float:
        all_runs = [r for runs in self.runs.values() for r in runs]
        if not all_runs:
            return float("nan")
        return statistics.median(r.tok_per_sec for r in all_runs)

    def verdict(self) -> dict[str, str]:
        v = {}
        v["swap"] = "FAIL" if self.swap_delta_mb > 0 else "PASS"
        v["pressure"] = (
            "PASS" if self.memory_pressure_observed == "normal" else "FAIL"
        )
        e2e = self.median_e2e_ms()
        v["latency"] = "FAIL" if (e2e != e2e or e2e > LAT_P50_THRESHOLD_MS) else "PASS"
        v["throughput"] = (
            "WARN" if self.median_tok_per_sec() < TOK_PER_SEC_WARN else "PASS"
        )
        v["overall"] = (
            "PASS" if all(x == "PASS" for x in (v["swap"], v["pressure"], v["latency"]))
            else "FAIL"
        )
        return v


def _summarize_peaks(samples: list[MemorySample], baseline_swap_mb: float, sr: ScenarioResult) -> None:
    if not samples:
        return
    sr.peak_rss_python_mb = max(s.rss_python_mb for s in samples)
    sr.peak_rss_ollama_mb = max(s.rss_ollama_mb for s in samples)
    sr.peak_mps_current_mb = max(s.mps_current_mb for s in samples)
    sr.peak_mps_driver_mb = max(s.mps_driver_mb for s in samples)
    sr.peak_vm_used_mb = max(s.vm_used_mb for s in samples)
    sr.swap_delta_mb = max(s.swap_used_mb for s in samples) - baseline_swap_mb
    pressures = {memory_pressure() for _ in range(1)}
    sr.memory_pressure_observed = pressures.pop()


def _flush_mps() -> None:
    gc.collect()
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
            torch.mps.synchronize()
    except Exception:
        pass


def warmup_ollama() -> None:
    log.info("Warmup Ollama (carica %s in memoria)", OLLAMA_MODEL)
    httpx.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": "Rispondi solo: ok.",
            "stream": False,
            "options": {"num_predict": 4},
        },
        timeout=180,
    ).raise_for_status()


def run_scenario(
    name: str,
    description: str,
    reranker_device: str,
    unload_after_rerank: bool,
    queries: list[dict[str, str]],
) -> ScenarioResult:
    log.info("=" * 70)
    log.info("SCENARIO %s — %s", name, description)
    log.info("=" * 70)

    sr = ScenarioResult(name=name, description=description)
    sampler = MemorySampler()
    baseline_swap_mb = psutil.swap_memory().used / (1024 * 1024)

    try:
        reranker = load_reranker(reranker_device)
        retriever = build_retriever(reranker if not unload_after_rerank else reranker)

        # warmup query (scartata)
        log.info("Warmup query Q6 (scartata)")
        warm_q = next(q for q in queries if q["qid"] == "Q6")
        if unload_after_rerank:
            # Per S3, simuliamo la dinamica: usa la stessa retriever, ma
            # il reranker dovrà essere ricaricato per ogni run. Per il
            # warmup teniamo il reranker, scaricheremo solo nelle run di misura.
            run_one_query(retriever, warm_q["query"], warm_q["qid"])
        else:
            run_one_query(retriever, warm_q["query"], warm_q["qid"])

        sampler.start()

        for q in queries:
            qid = q["qid"]
            runs_for_q: list[QueryRun] = []
            for i in range(N_RUNS):
                if unload_after_rerank and i > 0:
                    # in S3 misuriamo anche t_unload + t_reload
                    pass
                run = run_one_query(retriever, q["query"], qid)
                # primo run di ogni qid è warmup → scarta
                if i > 0:
                    runs_for_q.append(run)

                if unload_after_rerank:
                    # Scarica reranker dopo l'uso, simula coabitazione
                    t_unload = unload_reranker(retriever._reranker)
                    retriever._reranker = None
                    sr.extra.setdefault("t_unload_ms", []).append(t_unload)
                    # Ricarica per la prossima query (fuori dall'ultimo loop)
                    is_last = (qid == queries[-1]["qid"] and i == N_RUNS - 1)
                    if not is_last:
                        t_load0 = time.perf_counter()
                        retriever._reranker = load_reranker(reranker_device)
                        sr.extra.setdefault("t_reload_ms", []).append(
                            (time.perf_counter() - t_load0) * 1000
                        )

            sr.runs[qid] = runs_for_q

        samples = sampler.stop()
        _summarize_peaks(samples, baseline_swap_mb, sr)

    except Exception as exc:
        sampler.stop()
        log.exception("Errore in scenario %s", name)
        sr.error = f"{type(exc).__name__}: {exc}"
    finally:
        # cleanup
        try:
            if "retriever" in locals() and retriever._reranker is not None:
                unload_reranker(retriever._reranker)
                retriever._reranker = None
        except Exception:
            pass
        _flush_mps()

    return sr


# --- Output ---------------------------------------------------------------------


def _fmt_ms(x: float) -> str:
    if x != x:
        return "n/a"
    return f"{x:.0f}"


def _fmt_mb(x: float) -> str:
    if x != x:
        return "n/a"
    return f"{x:.0f}"


def render_results(setup: dict, scenarios: list[ScenarioResult]) -> str:
    out = ["# MPS coabitation smoke — risultati", ""]
    out.append("## Setup")
    for k, v in setup.items():
        out.append(f"- **{k}**: {v}")
    out.append("")

    for sr in scenarios:
        out.append(f"## Risultati {sr.name} — {sr.description}")
        if sr.error:
            out.append(f"\n**ERRORE**: `{sr.error}`\n")
            continue
        out.append("")
        out.append("| qid | t_retrieval ms | t_rerank ms | TTFT ms | t_gen ms | tok/s | t_e2e ms |")
        out.append("|---|---|---|---|---|---|---|")
        for qid, runs in sr.runs.items():
            if not runs:
                continue
            # mediana sui run validi (≥2 per qid)
            tr = statistics.median(r.t_retrieval_ms for r in runs)
            trk = statistics.median(r.t_rerank_ms for r in runs)
            tt = statistics.median(r.t_gen_ttft_ms for r in runs)
            tg = statistics.median(r.t_gen_total_ms for r in runs)
            tps = statistics.median(r.tok_per_sec for r in runs)
            e2e = statistics.median(r.t_end_to_end_ms for r in runs)
            out.append(
                f"| {qid} | {_fmt_ms(tr)} | {_fmt_ms(trk)} | {_fmt_ms(tt)} "
                f"| {_fmt_ms(tg)} | {tps:.1f} | {_fmt_ms(e2e)} |"
            )
        out.append("")
        out.append("**Picchi memoria**")
        out.append("")
        out.append(
            "| peak Python RSS MB | peak Ollama RSS MB | peak MPS current MB "
            "| peak MPS driver MB | peak VM used MB | swap Δ MB | mem pressure |"
        )
        out.append("|---|---|---|---|---|---|---|")
        out.append(
            f"| {_fmt_mb(sr.peak_rss_python_mb)} | {_fmt_mb(sr.peak_rss_ollama_mb)} "
            f"| {_fmt_mb(sr.peak_mps_current_mb)} | {_fmt_mb(sr.peak_mps_driver_mb)} "
            f"| {_fmt_mb(sr.peak_vm_used_mb)} | {sr.swap_delta_mb:+.0f} "
            f"| {sr.memory_pressure_observed} |"
        )
        if sr.extra.get("t_unload_ms"):
            out.append(
                f"\n- t_unload_reranker mediana: {statistics.median(sr.extra['t_unload_ms']):.0f} ms"
            )
        if sr.extra.get("t_reload_ms"):
            out.append(
                f"- t_reload_reranker mediana: {statistics.median(sr.extra['t_reload_ms']):.0f} ms"
            )
        out.append("")

    out.append("## Confronto scenari")
    out.append("")
    out.append(
        "| scenario | p50 e2e ms | tok/s | swap | mem pressure | latenza | overall |"
    )
    out.append("|---|---|---|---|---|---|---|")
    for sr in scenarios:
        if sr.error:
            out.append(f"| {sr.name} | ERROR | - | - | - | - | FAIL ({sr.error}) |")
            continue
        v = sr.verdict()
        out.append(
            f"| {sr.name} | {_fmt_ms(sr.median_e2e_ms())} "
            f"| {sr.median_tok_per_sec():.1f} | {v['swap']} | {v['pressure']} "
            f"| {v['latency']} | **{v['overall']}** |"
        )
    out.append("")

    # raccomandazione
    out.append("## Raccomandazione")
    out.append("")
    chosen = next(
        (sr for sr in scenarios if not sr.error and sr.verdict()["overall"] == "PASS"),
        None,
    )
    if chosen is not None:
        out.append(
            f"Adottare **{chosen.name}** ({chosen.description}) per la pipeline serving "
            f"W5: p50 end-to-end {_fmt_ms(chosen.median_e2e_ms())} ms sotto la soglia "
            f"di {LAT_P50_THRESHOLD_MS} ms, nessuno swap osservato, memory pressure "
            f"`{chosen.memory_pressure_observed}`. Throughput Qwen "
            f"{chosen.median_tok_per_sec():.1f} tok/s "
            f"({'≥' if chosen.median_tok_per_sec() >= TOK_PER_SEC_WARN else '<'} "
            f"{TOK_PER_SEC_WARN} tok/s di guardia)."
        )
    else:
        out.append(
            "Nessuno degli scenari testati passa tutte le soglie. Prossimi step:"
        )
        out.append("- valutare reranker più leggero (`bge-reranker-base`, ~280MB)")
        out.append("- provare bge-m3 in FP16 su MPS (verificare prima compatibilità op)")
        out.append("- valutare offload Qwen su MLX (vs Ollama Q4_K_M)")
        out.append("- ridurre `rerank_top_k` da 20 a 10")
    out.append("")
    return "\n".join(out)


# --- Main -----------------------------------------------------------------------


def main() -> int:
    t_start = time.time()
    log.info("Smoke MPS coabitation — start")

    check_ollama_model()

    queries = load_queries()
    log.info("Query target: %s", [q["qid"] for q in queries])

    # warmup Ollama: carichiamo Qwen in memoria PRIMA di iniziare la misura,
    # così non contaminiamo il primo scenario col cold start del modello.
    warmup_ollama()

    setup = {
        "host": subprocess.run(["uname", "-a"], capture_output=True, text=True).stdout.strip(),
        "python": sys.version.split()[0],
        "ollama_model": OLLAMA_MODEL,
        "reranker_model": RERANKER_MODEL,
        "collection": COLLECTION,
        "rerank_top_k": RERANK_TOP_K,
        "rag_top_k": RAG_TOP_K,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "sample_interval_s": SAMPLE_INTERVAL_S,
        "baseline_vm_used_mb": f"{psutil.virtual_memory().used / (1024 * 1024):.0f}",
        "baseline_swap_used_mb": f"{psutil.swap_memory().used / (1024 * 1024):.0f}",
        "baseline_mem_pressure": memory_pressure(),
    }
    try:
        import torch
        setup["torch"] = torch.__version__
        setup["mps_available"] = torch.backends.mps.is_available()
    except Exception:
        pass

    scenarios: list[ScenarioResult] = []

    # S1: tutto su MPS
    s1 = run_scenario(
        name="S1",
        description="bge-m3 MPS + reranker MPS + Ollama attivo (tutto residente)",
        reranker_device="mps",
        unload_after_rerank=False,
        queries=queries,
    )
    scenarios.append(s1)

    s1_pass = (not s1.error) and s1.verdict()["overall"] == "PASS"
    if not s1_pass:
        log.info("S1 non passa — proseguo con S2")
        s2 = run_scenario(
            name="S2",
            description="bge-m3 MPS + reranker CPU + Ollama attivo",
            reranker_device="cpu",
            unload_after_rerank=False,
            queries=queries,
        )
        scenarios.append(s2)
        s2_pass = (not s2.error) and s2.verdict()["overall"] == "PASS"
        if not s2_pass:
            log.info("S2 non passa — proseguo con S3")
            s3 = run_scenario(
                name="S3",
                description="bge-m3 MPS + reranker MPS load/unload + Ollama attivo",
                reranker_device="mps",
                unload_after_rerank=True,
                queries=queries,
            )
            scenarios.append(s3)
    else:
        log.info("S1 passa — S2 e S3 non necessari")

    md = render_results(setup, scenarios)
    RESULTS_PATH.write_text(md, encoding="utf-8")
    log.info("Risultati scritti su %s", RESULTS_PATH)
    log.info("Smoke completato in %.0f s", time.time() - t_start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
