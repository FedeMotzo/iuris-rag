"""Probe: due chiamate identiche, misura TTFT in 4 condizioni.

Q1 e Q6 con num_ctx default vs num_ctx=8192 esplicito. Se Q1 mostra cache
hit solo con num_ctx esplicito → conferma truncation. Altrimenti l'anomalia
è altrove.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = "http://localhost:11434"
MODEL = "qwen2.5:14b"


def one_call(prompt: str, num_ctx: int | None, n_predict: int = 30) -> tuple[float, float, int]:
    options = {"num_predict": n_predict}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    t0 = time.perf_counter()
    t_first = None
    n_tok = 0
    with httpx.stream(
        "POST", f"{OLLAMA}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": True, "options": options},
        timeout=120,
    ) as r:
        for raw in r.iter_lines():
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("response"):
                if t_first is None:
                    t_first = time.perf_counter()
            if obj.get("done"):
                n_tok = obj.get("eval_count", 0)
                break
    t_end = time.perf_counter()
    return (t_first - t0) * 1000, (t_end - t0) * 1000, n_tok


def probe(label: str, prompt: str, num_ctx: int | None, n_predict: int = 30) -> None:
    print(f"\n=== {label} (num_ctx={num_ctx}, n_predict={n_predict}, prompt_chars={len(prompt)}) ===")
    for i in range(3):
        ttft, total, n = one_call(prompt, num_ctx, n_predict)
        print(f"  run {i}: TTFT={ttft:7.0f} ms  total={total:7.0f} ms  out_tok={n}")


def main() -> int:
    p_q6 = (ROOT / "spike/_prompt_Q6.txt").read_text(encoding="utf-8")
    p_q1 = (ROOT / "spike/_prompt_Q1.txt").read_text(encoding="utf-8")

    # baseline Ollama: assicuro il modello caldo
    httpx.post(f"{OLLAMA}/api/generate",
               json={"model": MODEL, "prompt": "ok.", "stream": False,
                     "options": {"num_predict": 4}}, timeout=120).raise_for_status()

    probe("Q1 default ctx, n_predict=500 (smoke real)", p_q1, None, n_predict=500)
    probe("Q1 num_ctx=8192, n_predict=500", p_q1, 8192, n_predict=500)
    probe("Q6 default ctx, n_predict=500", p_q6, None, n_predict=500)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
