"""PARTE 2 — de-risk del tiebreaker reranker sul path mono (retrieval, $0).

Per ogni sentinella confronta il top-k del retrieval mono con tiebreaker ON
(key=(-score, chunk_id)) vs OFF (sort stabile per solo score, comportamento
storico) e verifica se c'è un tie di score al confine del top-k. gold-in-top-k.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spike.validate_decomposer_v1_2 import parse_gold_chunk  # noqa: E402
from spike.validate_map_assemble import _build_retriever  # noqa: E402

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
SENTINELS = {"Q34": "gdpr", "Q11": "ai_act", "Q40": "nis2",
             "Q25": "dlgs_231", "Q62": "codice_privacy"}
TOP_K, POOL = 5, 20


def main() -> int:
    gold = {it["qid"]: it for it in json.loads(GOLD.read_text())}
    retr = _build_retriever()

    # monkeypatch _rerank per catturare (hit, score) grezzi del pool pre-sort
    captured = {}
    orig = type(retr)._rerank

    def patched(self, query, hits, top_k):
        rk = self._ensure_reranker_available()
        pairs = list(zip(hits, rk.predict(
            [(query, h.payload.get("text", "")) for h in hits],
            show_progress_bar=False), strict=True))
        captured["pairs"] = [(h, float(s)) for h, s in pairs]
        return orig(self, query, hits, top_k)

    type(retr)._rerank = patched

    print("qid  | norm        | top-k diff ON vs OFF | tie@confine | gold-in-topk ON/OFF")
    print("-" * 78)
    all_ok = True
    for qid, nid in SENTINELS.items():
        it = gold[qid]
        res_on = retr.retrieve(query=it["question"], top_k=TOP_K, mode="hybrid",
                               rerank_top_k=POOL)
        on_ids = [h.chunk_id for h in res_on]
        pairs = captured["pairs"]
        # OFF: sort stabile per solo score desc (storico)
        off = sorted(pairs, key=lambda p: -p[1])   # Python sort è stabile
        off_ids = [h.chunk_id for h, _ in off[:TOP_K]]
        # tie al confine del top-k: score[k-1] == score[k]?
        scores_sorted = sorted((s for _, s in pairs), reverse=True)
        tie = (len(scores_sorted) > TOP_K
               and scores_sorted[TOP_K - 1] == scores_sorted[TOP_K])
        diff = set(on_ids) != set(off_ids)

        gold_arts = {c["chunk_id"] for c in it["gold_chunks"]
                     if parse_gold_chunk(c["chunk_id"])[1] in ("article", "annex_point")}
        gold_on = bool(gold_arts & set(on_ids))
        gold_off = bool(gold_arts & set(off_ids))
        if diff or (gold_on != gold_off):
            all_ok = False
        print(f"{qid:4} | {nid:11} | {'DIFF' if diff else 'identico':^20} | "
              f"{'sì' if tie else 'no':^11} | {gold_on}/{gold_off}")

    type(retr)._rerank = orig
    print("\nVERDETTO PARTE 2:",
          "membership top-k INVARIATA su tutte e 5" if all_ok
          else "ATTENZIONE: differenza rilevata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
