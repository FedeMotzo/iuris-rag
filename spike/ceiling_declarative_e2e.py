"""Ceiling end-to-end con sub-query dichiarative per-istituto.

STEP 0: rigenera sub-query con prompt dichiarativo (Sonnet, ~$0.06 totale).
STEP 1 (free): per ogni (qid, source, sub-query) hybrid retrieve + rerank.
STEP 2 (free): RRF cross-source v1.1, top-5, recall@5 vs baseline.

NIENTE generation, NIENTE RAGAS.

    spike/.venv/bin/python spike/ceiling_declarative_e2e.py [--stop-after-step0]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_SUBQ = ROOT / "spike/data/declarative_subqueries.json"
OUT_RESULTS = ROOT / "spike/data/ceiling_declarative_results.json"

QUERIES = {
    "Q68": ("q68",
            "Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?",
            ["gdpr", "ai_act", "l_132_2025"]),
    "Q69": ("q69",
            "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare un sistema di IA per supportare le attività di farmacovigilanza con dati provenienti da operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai sensi di AI Act, GDPR e NIS2?",
            ["gdpr", "ai_act", "nis2"]),
    "Q70": ("q70",
            "Una banca italiana intende affidare in outsourcing a un fornitore extra-UE la gestione di un sistema di IA per il rilevamento di operazioni sospette di riciclaggio: quali profili AI Act, GDPR, NIS2 e 231 deve considerare in fase di selezione del fornitore?",
            ["gdpr", "ai_act", "dlgs_231", "nis2"]),
    "Q71": ("q71",
            "Una regione italiana intende mettere in produzione un sistema di IA per supportare l'attribuzione di punteggi nelle graduatorie di accesso ai servizi residenziali per anziani: quali sono i principali profili giuridici da considerare integrando GDPR, AI Act, L. 132/2025 e NIS2?",
            ["gdpr", "ai_act", "nis2", "l_132_2025"]),
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

NORM_TO_DOC_URN = {
    "gdpr": "eli/reg/2016/679/oj",
    "ai_act": "eli/reg/2024/1689/oj",
    "dlgs_231": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
    "nis2": "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    "codice_privacy": "akn/it/act/decreto_legislativo/stato/2003-06-30/196",
    "l_132_2025": "akn/it/act/legge/stato/2025-09-23/132",
}

PROMPT = """Per la norma {short_name}, identifica gli istituti GENUINAMENTE attivati dallo scenario qui sotto e produci UNA sub-query DICHIARATIVA per ognuno.

Scenario:
"{query}"

Vocabolario tecnico della norma {short_name}:
{vocab}

REGOLA DI OUTPUT (TASSATIVA):
- Forma DICHIARATIVA, NON interrogativa. NON "Quali obblighi...", NON "Quando...", NON "In che modo...".
- Struttura fissa per ogni sub-query:
  <rubrica/oggetto dell'istituto> ex art. <N> <sigla norma>: <3-4 keyword di rubrica>
- NON includere il contesto applicativo dello scenario. VIETATI questi e simili termini:
  "ospedaliero", "ospedale", "bancario", "banca", "chatbot", "azienda", "regione", "farmacovigilanza", "extra-UE", "anziani", "triage", "pazienti".
- Includi sempre numero di articolo esplicito ("ex art. N") e sigla della norma.
- Sii selettivo: solo istituti DIRETTAMENTE invocati dallo scenario; non enumerare tutti gli articoli della norma.

ESEMPI DI OUTPUT CORRETTO:
"Trattamento di categorie particolari di dati personali ex art. 9 GDPR: divieto, deroghe, dati sanitari."
"Classificazione dei sistemi di IA ad alto rischio ex art. 6 e Allegato III AI Act: criteri, categorie."
"Trasferimento di dati personali verso paesi terzi ex art. 44 GDPR: principio generale, garanzie adeguate."
"Reati di riciclaggio e autoriciclaggio ex art. 25-octies D.Lgs 231/2001: responsabilità dell'ente."

Output: SOLO un JSON array di stringhe, una per istituto attivato. Niente preamboli, niente code fence.
"""


def _load_glossary():
    import yaml
    g = yaml.safe_load((ROOT / "core/cross_norm/norm_glossary.yaml").read_text())
    return g


def step0_generate_subqueries():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from core.llm_provider.config import load_provider_from_env
    from core.cross_norm.subquery_generator import _parse_subquery_list

    g = _load_glossary()
    llm = load_provider_from_env()
    print(f"provider={llm.provider_name} model={llm.model_name}\n")

    out = {}
    n_calls = 0
    for qid, (_label, question, norms) in QUERIES.items():
        out[qid] = {"question": question, "subqueries_by_norm": {}}
        for nid in norms:
            entry = g[nid]
            short_name = entry.get("short_name") or nid
            vocab = "\n".join(f"- {v}" for v in entry.get("vocabolario", []))
            prompt = PROMPT.format(short_name=short_name, query=question, vocab=vocab)
            print(f"[{qid}:{nid}] generate...")
            res = llm.generate(prompt=prompt, system=None, max_tokens=500, temperature=0.0)
            text = res.text
            try:
                sqs = _parse_subquery_list(text)
            except ValueError as e:
                print(f"  PARSE FAIL: {e}. Raw: {text!r}")
                sqs = []
            for i, sq in enumerate(sqs):
                print(f"   [{i}] {sq}")
            out[qid]["subqueries_by_norm"][nid] = sqs
            n_calls += 1
    OUT_SUBQ.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUBQ.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved → {OUT_SUBQ} (calls={n_calls})")
    return out


def _gate_check(subqueries: dict) -> list[str]:
    """Verifica forma dichiarativa, presenza 'ex art.', assenza contesto applicativo."""
    forbidden = ["ospedalier", "ospedale", "bancar", "banca", "chatbot",
                 "azienda", "regione", "farmacovigilanza", "extra-UE",
                 "extra-ue", "anziani", "triage", "pazient", "settore sanitario"]
    interrogatives = ["quali ", "quando ", "come ", "in che modo",
                      "in quali", "qual è", "che cosa", "perché"]
    issues = []
    for qid, qd in subqueries.items():
        for nid, sqs in qd["subqueries_by_norm"].items():
            for i, sq in enumerate(sqs):
                sl = sq.lower()
                for kw in interrogatives:
                    if sl.startswith(kw) or sl.lstrip('"').startswith(kw):
                        issues.append(f"{qid}:{nid}[{i}] INTERROGATIVA: {sq[:80]}")
                        break
                for f in forbidden:
                    if f.lower() in sl:
                        issues.append(f"{qid}:{nid}[{i}] CONTESTO SCENARIO ('{f}'): {sq[:80]}")
                if not re.search(r"ex\s+art(?:icolo|\.)?\s*\d", sq, re.IGNORECASE) and \
                   "allegato" not in sl:
                    issues.append(f"{qid}:{nid}[{i}] manca 'ex art. N': {sq[:80]}")
    return issues


def step1_retrieve_rerank_rrf(subqueries: dict):
    """Per ogni (qid, source, sub_q): hybrid retrieve + rerank top-5.
       Per global: query originale.
       RRF cross-source: chunk -> Σ 1/(60+rank) sui ranking di tutte le (source,sub_q)+global.
       Output: top-5 fuso + per-gold rank.
    """
    import logging; logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever

    print("\nLoading models (bge-m3 + bm25 + reranker)...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    cli = QdrantClient(host="localhost", port=6333, timeout=60)
    hybrid = HybridRetriever(cli, enc, bm, "italian_legal_v1_hybrid", reranker=rr)

    RRF_K = 60
    TOP_K_PER_RANK = 5
    TOP_K_FINAL = 5

    results = {}
    for qid, qd in subqueries.items():
        question = qd["question"]
        print(f"\n[{qid}] running pipeline...")
        rankings = []  # list of (label, [(chunk_id, rank), ...])
        candidates_payload = {}  # chunk_id -> payload (for debug)

        for nid, sqs in qd["subqueries_by_norm"].items():
            doc_urn = NORM_TO_DOC_URN[nid]
            for sq_idx, sq in enumerate(sqs):
                hits = hybrid.retrieve(query=sq, top_k=TOP_K_PER_RANK,
                                       mode="hybrid", rerank_top_k=20,
                                       filter_doc_urn=doc_urn)
                ranking = [(h.chunk_id, h.rank, float(h.score)) for h in hits]
                label = f"filtered:{nid}#{sq_idx}"
                rankings.append((label, sq, ranking))
                for cid, _r, _s in ranking:
                    candidates_payload.setdefault(cid, {})
                print(f"  {label}  '{sq[:70]}...'  top-{len(ranking)}")
        # Global ranking
        ghits = hybrid.retrieve(query=question, top_k=TOP_K_PER_RANK,
                                mode="hybrid", rerank_top_k=20, filter_doc_urn=None)
        g_ranking = [(h.chunk_id, h.rank, float(h.score)) for h in ghits]
        rankings.append(("global", question, g_ranking))
        for cid, _r, _s in g_ranking:
            candidates_payload.setdefault(cid, {})
        print(f"  global  top-{len(g_ranking)}")

        # RRF
        rrf_score = defaultdict(float)
        contribs = defaultdict(list)
        for label, sq, ranking in rankings:
            for cid, rank, score in ranking:
                rrf_score[cid] += 1.0 / (RRF_K + rank)
                contribs[cid].append((label, rank, score))
        fused = sorted(rrf_score.items(), key=lambda kv: (-kv[1], kv[0]))
        top_final = fused[:TOP_K_FINAL]
        ranked_all = [c for c, _ in fused]

        # gold ranks
        gold_ranks = {}
        for g, label in GOLDS[qid]:
            gold_ranks[g] = ranked_all.index(g) + 1 if g in ranked_all else None

        results[qid] = {
            "top5": [{"chunk_id": c, "rrf": s,
                      "sources": [{"label": lb, "rank": r, "score": sc}
                                  for lb, r, sc in contribs[c]]}
                     for c, s in top_final],
            "gold_ranks": gold_ranks,
            "n_rankings": len(rankings),
            "n_candidates": len(rrf_score),
        }

        # print
        print(f"  Top-5 fused:")
        for i, (c, s) in enumerate(top_final, 1):
            src_str = ",".join(lb.split(":")[1] if ":" in lb else lb
                               for lb, _r, _sc in contribs[c])
            is_gold = " ★ GOLD" if any(g == c for g, _ in GOLDS[qid]) else ""
            print(f"    {i}. {c.split('__',2)[-1]:<22} rrf={s:.4f}  src=[{src_str}]{is_gold}")
        for g, lab in GOLDS[qid]:
            r = gold_ranks.get(g)
            print(f"    GOLD {lab:<22}  fusion rank: {r if r else '>pool'}")

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stop-after-step0", action="store_true")
    ap.add_argument("--reuse-subqueries", action="store_true",
                    help="riusa subqueries esistenti, no LLM call")
    args = ap.parse_args()

    # STEP 0
    if args.reuse_subqueries and OUT_SUBQ.exists():
        print("Reusing existing subqueries from", OUT_SUBQ)
        subqueries = json.loads(OUT_SUBQ.read_text())
    else:
        print("=" * 80)
        print("STEP 0 — Genero sub-query dichiarative (~$0.06 paid)")
        print("=" * 80)
        subqueries = step0_generate_subqueries()

    # GATE CHECK
    print("\n" + "=" * 80)
    print("GATE CHECK — forma dichiarativa, ex art., no contesto scenario")
    print("=" * 80)
    issues = _gate_check(subqueries)
    if issues:
        print("\nPROBLEMI rilevati:")
        for it in issues:
            print(f"  - {it}")
        print(f"\nTotale problemi: {len(issues)}")
    else:
        print("OK — nessun problema sintattico.")

    if args.stop_after_step0:
        print("\n--stop-after-step0 → STOP qui per ispezione manuale.")
        return 0

    # STEP 1+2
    print("\n" + "=" * 80)
    print("STEP 1+2 — Hybrid retrieve + rerank + RRF cross-source v1.1 (FREE)")
    print("=" * 80)
    results = step1_retrieve_rerank_rrf(subqueries)

    # recall@5
    print("\n" + "=" * 80)
    print("STEP 2 — recall@5 per query")
    print("=" * 80)
    baseline_v11 = {"Q68": 0.4, "Q69": 0.4, "Q70": 0.2, "Q71": 0.4}
    baseline_5e = {"Q68": 0.2, "Q69": 0.2, "Q70": 0.2, "Q71": 0.0}
    rows = []
    for qid in ["Q68", "Q69", "Q70", "Q71"]:
        golds = GOLDS[qid]
        ranks = results[qid]["gold_ranks"]
        top5 = {c["chunk_id"] for c in results[qid]["top5"]}
        n_hit = sum(1 for g, _ in golds if g in top5)
        recall = n_hit / len(golds)
        rows.append((qid, len(golds), recall, baseline_v11.get(qid),
                     baseline_5e.get(qid)))
    print(f"\n{'qid':<5}{'#gold':>6}{'r@5 new':>10}{'v1.1':>8}{'5e':>6}")
    for qid, n, r, b, e in rows:
        print(f"{qid:<5}{n:>6}{r:>10.3f}{b:>8.2f}{e:>6.2f}")
    med_new = statistics.median(r for _, _, r, _, _ in rows)
    med_v11 = statistics.median(b for _, _, _, b, _ in rows)
    med_5e = statistics.median(e for _, _, _, _, e in rows)
    print(f"{'MEDIAN':<5}{'':<6}{med_new:>10.3f}{med_v11:>8.2f}{med_5e:>6.2f}")

    OUT_RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved results → {OUT_RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
