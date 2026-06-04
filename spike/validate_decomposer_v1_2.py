"""STEP 2 v1.2 — Rigenera sub-query col nuovo prompt decomposer e ispeziona.

NO modifiche alla pipeline: solo generate_subquery live su tutte le query
cross-norma (detect_norms >= 2) del benchmark gold_answers_v3.json.

Output:
- lista qid cross-norma
- sub-query raggruppate per (qid, norma)
- tabelle di controllo A (forma) / B (copertura gold articolo) / C (allegati)

    spike/.venv/bin/python spike/validate_decomposer_v1_2.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GOLD = ROOT / "data/benchmark/gold_answers_v3.json"
# Checkpoint: sub-query già generate, per non ripagare in caso di re-run.
CHECKPOINT = Path(__file__).resolve().parent / "validate_decomposer_v1_2_cache.json"

# chunk_id prefix → norm_id (chiave norm_glossary / detect_norms)
PREFIX_TO_NORM = {
    "eli/reg/2016/679/oj": "gdpr",
    "eli/reg/2024/1689/oj": "ai_act",
    "akn/it/act/decreto_legislativo/stato/2024-09-04/138": "nis2",
    "akn/it/act/decreto_legislativo/stato/2001-06-08/231": "dlgs_231",
    "akn/it/act/legge/stato/2025-09-23/132": "l_132_2025",
    "akn/it/act/decreto_legislativo/stato/2003-06-30/196": "codice_privacy",
}

ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}

# Termini di contesto applicativo vietati (settori/strumenti/soggetti).
CONTEXT_TERMS = [
    "sanitar", "bancari", "ospedalier", "farmaceutic", "farmacovigilanza",
    "residenzial", "anzian", "pazient", "candidat", "riciclaggio", "antiricicl",
    "chatbot", "triage", "screening", "outsourcing", "graduatori",
    "azienda", "regione", "banca", "fornitore", "extra-ue", "extra ue",
]

INTERROG_START = re.compile(
    r"^\s*(quali|quando|come|in che modo|perch[eé]|chi|cosa|quale|dove|"
    r"\bè\b|sono\b)", re.IGNORECASE
)


def parse_gold_chunk(chunk_id: str):
    """→ (norm_id, kind, ref) dove kind in {article, annex_point, recital}."""
    norm_id = None
    for pre, nid in PREFIX_TO_NORM.items():
        if chunk_id.startswith(pre + "__"):
            norm_id = nid
            suffix = chunk_id[len(pre) + 2 :]
            break
    else:
        return (None, "unknown", chunk_id)

    if suffix.startswith("annex_"):
        m = re.match(r"annex_([IVX]+|\d+)__point_(\d+)", suffix)
        if m:
            return (norm_id, "annex_point", (m.group(1), int(m.group(2))))
        return (norm_id, "annex_point", suffix)
    if suffix.startswith("recital_"):
        return (norm_id, "recital", suffix.replace("recital_", ""))
    if suffix.startswith("art_"):
        m = re.match(r"art_(\d+(?:-[a-z]+)?)", suffix)
        ref = m.group(1) if m else suffix.replace("art_", "")
        return (norm_id, "article", ref)
    return (norm_id, "other", suffix)


def article_mentioned(subqs: list[str], art_ref: str) -> bool:
    """Una sub-query nomina 'art. N' (con eventuale suffisso -bis/-ter)?"""
    base = art_ref.split("-")[0]
    suffix = art_ref.split("-")[1] if "-" in art_ref else None
    for sq in subqs:
        low = sq.lower()
        # 'art' ... numero come token (no 'art. 5' che matcha 'art. 56')
        for m in re.finditer(r"art\.?\s*0*" + re.escape(base) + r"\b", low):
            if suffix is None:
                return True
            # richiede il suffisso nelle ~10 char successive
            tail = low[m.end() : m.end() + 12]
            if suffix in tail:
                return True
    return False


def annex_point_mentioned(subqs: list[str], roman: str, point: int) -> bool:
    for sq in subqs:
        low = sq.lower()
        has_roman = re.search(
            r"\b(allegato|annex)\s+" + roman.lower() + r"\b", low
        )
        has_point = re.search(r"punto\s*0*" + str(point) + r"\b", low)
        if has_roman and has_point:
            return True
    return False


def check_forma(sq: str):
    """→ dict di violazioni per la singola sub-query."""
    low = sq.lower()
    interrogativa = bool(sq.strip().endswith("?")) or bool(INTERROG_START.match(sq))
    has_art = bool(re.search(r"art\.?\s*\d", low))
    has_allegato = ("allegato" in low) or ("annex" in low)
    no_art_ref = not (has_art or has_allegato)
    ctx_hits = sorted({t for t in CONTEXT_TERMS if t in low})
    return {
        "interrogativa": interrogativa,
        "no_art_ref": no_art_ref,
        "ctx_terms": ctx_hits,
    }


def main() -> int:
    from core.cross_norm.multi_norm_trigger import detect_norms
    from core.cross_norm.subquery_generator import SUBQUERY_MAX_TOKENS, generate_subquery
    from core.llm_provider.config import load_provider_from_env

    gold = json.loads(GOLD.read_text(encoding="utf-8"))

    cross = []
    for it in gold:
        norms = detect_norms(it["question"])
        if len(norms) >= 2:
            cross.append((it["qid"], norms, it))

    print("=" * 78)
    print(f"QUERY CROSS-NORMA (detect_norms >= 2): {len(cross)} su {len(gold)}")
    print("qid     | norme rilevate")
    print("-" * 78)
    for qid, norms, _ in cross:
        print(f"{qid:7} | {', '.join(norms)}")

    llm = load_provider_from_env()
    print(f"\nprovider={llm.provider_name} model={llm.model_name}")

    # Checkpoint: ricarica sub-query già generate (re-run gratis).
    cache: dict[str, list[str]] = {}
    if CHECKPOINT.is_file():
        cache = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        print(f"checkpoint: {len(cache)} (qid,norma) già in cache")

    def _gen_retry(question: str, nid: str, attempts: int = 5) -> list[str]:
        for k in range(attempts):
            try:
                return generate_subquery(question, nid, llm, max_tokens=SUBQUERY_MAX_TOKENS)
            except Exception as exc:  # noqa: BLE001
                if k == attempts - 1:
                    raise
                wait = 2 ** k
                print(f"    retry {k + 1}/{attempts - 1} fra {wait}s ({exc})")
                time.sleep(wait)
        return []  # unreachable

    n_calls = 0
    generated: dict[tuple[str, str], list[str]] = {}
    for qid, norms, it in cross:
        for nid in norms:
            ck = f"{qid}:{nid}"
            if ck in cache:
                generated[(qid, nid)] = cache[ck]
                continue
            sub_qs = _gen_retry(it["question"], nid)
            generated[(qid, nid)] = sub_qs
            cache[ck] = sub_qs
            n_calls += 1
            CHECKPOINT.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    print(f"chiamate LLM nuove: {n_calls} (totale (qid,norma): {len(generated)})\n")

    # ---- Sub-query raggruppate per (qid, norma) ----
    print("=" * 78)
    print("SUB-QUERY PER (qid, norma)")
    print("=" * 78)
    for qid, norms, it in cross:
        print(f"\n### {qid}")
        print(f"Q: {it['question']}")
        for nid in norms:
            print(f"  [{nid}]")
            for i, sq in enumerate(generated[(qid, nid)]):
                print(f"     {i}. {sq}")

    # ---- TABELLA A: forma ----
    print("\n" + "=" * 78)
    print("TABELLA A — FORMA (violazioni per qid)")
    print("qid     | #subq | interrog | no_art_ref | ctx_terms (sub-query offending)")
    print("-" * 78)
    for qid, norms, _ in cross:
        all_sq = [(nid, sq) for nid in norms for sq in generated[(qid, nid)]]
        n = len(all_sq)
        interrog = []
        no_ref = []
        ctx = []
        for nid, sq in all_sq:
            f = check_forma(sq)
            tag = f"{nid}:{all_sq.index((nid, sq))}"
            if f["interrogativa"]:
                interrog.append(sq[:40])
            if f["no_art_ref"]:
                no_ref.append(sq[:40])
            if f["ctx_terms"]:
                ctx.append(f"{','.join(f['ctx_terms'])}→«{sq[:50]}»")
        i_s = "OK" if not interrog else f"{len(interrog)}: " + " | ".join(interrog)
        r_s = "OK" if not no_ref else f"{len(no_ref)}: " + " | ".join(no_ref)
        c_s = "OK" if not ctx else f"{len(ctx)}: " + " ;; ".join(ctx)
        print(f"{qid:7} | {n:5} | {i_s}")
        if no_ref:
            print(f"        |       | no_art_ref → {r_s}")
        if ctx:
            print(f"        |       | ctx → {c_s}")

    # ---- TABELLA B: copertura gold articolo ----
    print("\n" + "=" * 78)
    print("TABELLA B — COPERTURA GOLD A LIVELLO ARTICOLO")
    print("qid     | norm        | gold art        | sub-query dedicata?")
    print("-" * 78)
    for qid, norms, it in cross:
        norm_set = set(norms)
        for c in it["gold_chunks"]:
            nid, kind, ref = parse_gold_chunk(c["chunk_id"])
            if kind != "article":
                continue
            subqs = generated.get((qid, nid), [])
            in_scope = nid in norm_set
            covered = article_mentioned(subqs, ref) if in_scope else False
            scope_note = "" if in_scope else " (norma non in detect_norms!)"
            flag = "SI" if covered else "NO"
            print(f"{qid:7} | {str(nid):11} | art. {str(ref):10} | {flag}{scope_note}")

    # ---- TABELLA C: allegati ----
    print("\n" + "=" * 78)
    print("TABELLA C — ALLEGATI (gold = punto d'allegato)")
    print("qid     | norm        | gold allegato       | sub-query dedicata?")
    print("-" * 78)
    any_annex = False
    for qid, norms, it in cross:
        norm_set = set(norms)
        for c in it["gold_chunks"]:
            nid, kind, ref = parse_gold_chunk(c["chunk_id"])
            if kind != "annex_point":
                continue
            any_annex = True
            subqs = generated.get((qid, nid), [])
            label = f"Allegato {ref[0]} punto {ref[1]}" if isinstance(ref, tuple) else str(ref)
            in_scope = nid in norm_set
            covered = (
                annex_point_mentioned(subqs, ref[0], ref[1])
                if (in_scope and isinstance(ref, tuple))
                else False
            )
            scope_note = "" if in_scope else " (norma non in detect_norms!)"
            flag = "SI" if covered else "NO"
            print(f"{qid:7} | {str(nid):11} | {label:19} | {flag}{scope_note}")
    if not any_annex:
        print("(nessun gold a livello di punto d'allegato nelle query cross-norma)")

    print("\n" + "=" * 78)
    print(f"FATTO. chiamate LLM={n_calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
