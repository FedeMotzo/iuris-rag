"""Rigenera SOLO Q71 ai_act con regola di granularità sugli Allegati.
Costo ~$0.005 (1 chiamata Sonnet). Funnel locale free.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TARGET_ID = "eli/reg/2024/1689/oj__annex_III__point_5"
TARGET_DOC_URN = "eli/reg/2024/1689/oj"

Q71_QUESTION = (
    "Una regione italiana intende mettere in produzione un sistema di IA per "
    "supportare l'attribuzione di punteggi nelle graduatorie di accesso ai "
    "servizi residenziali per anziani: quali sono i principali profili "
    "giuridici da considerare integrando GDPR, AI Act, L. 132/2025 e NIS2?"
)

PROMPT = """Per la norma AI Act / Regolamento UE 2024/1689, identifica gli istituti GENUINAMENTE attivati dallo scenario qui sotto e produci UNA sub-query DICHIARATIVA per ognuno.

Scenario:
"{query}"

Vocabolario tecnico tipico dell'AI Act:
- sistema di IA ad alto rischio (art. 6, Allegato III)
- Allegato III punto 5 (servizi pubblici essenziali, credit scoring)
- Allegato III punto 4 (occupazione, HR)
- Allegato III punto 1 (biometria)
- gestione dei rischi (art. 9)
- governance dei dati di addestramento (art. 10)
- documentazione tecnica (art. 11)
- registrazione automatica eventi/log (art. 12)
- trasparenza (art. 13)
- sorveglianza umana (art. 14)
- accuratezza, robustezza, cybersicurezza (art. 15)
- obblighi del fornitore (artt. 16-22)
- obblighi del deployer (art. 26)
- FRIA - valutazione d'impatto diritti fondamentali (art. 27)
- valutazione di conformità e marcatura CE (artt. 43-49)
- registrazione nella banca dati UE (art. 71)
- monitoraggio post-commercializzazione e incidenti gravi (artt. 72-73)
- divieto di social scoring e pratiche vietate (art. 5)

REGOLA DI OUTPUT (TASSATIVA):
- Forma DICHIARATIVA, NON interrogativa.
- Struttura fissa per ogni sub-query:
  <rubrica/oggetto dell'istituto> ex art. <N> AI Act: <3-4 keyword di rubrica>
- NON includere contesto applicativo dello scenario. VIETATI: "anziani", "regione", "graduatorie", "servizi residenziali", "PA", "punteggi".
- Includi sempre numero di articolo esplicito ("ex art. N") e sigla "AI Act".
- Sii selettivo: solo istituti DIRETTAMENTE invocati dallo scenario.

GRANULARITÀ: ogni punto specifico di un Allegato (es. Allegato III punto 5) o sotto-voce dispositiva implicata dallo scenario riceve una sub-query DEDICATA mono-concetto che lo nomina esplicitamente (es. "Allegato III punto 5 AI Act: accesso a servizi pubblici essenziali e prestazioni"). NON accorparlo in una sub-query generale di classificazione/alto rischio.

ESEMPI DI OUTPUT CORRETTO:
"Classificazione dei sistemi di IA ad alto rischio ex art. 6 AI Act: criteri."
"Allegato III punto 5 AI Act: accesso a servizi pubblici essenziali e prestazioni."
"Valutazione d'impatto sui diritti fondamentali (FRIA) ex art. 27 AI Act: organismi di diritto pubblico."

Output: SOLO un JSON array di stringhe. Niente preamboli, niente code fence.
"""

SIGLA_PATTERNS = [
    ("gdpr", re.compile(r"\bGDPR\b", re.IGNORECASE)),
    ("ai_act", re.compile(r"\bAI\s*Act\b", re.IGNORECASE)),
    ("l_132_2025", re.compile(r"\bL\.?\s*132/2025\b", re.IGNORECASE)),
    ("dlgs_231", re.compile(r"\bD\.?\s*Lgs\.?\s*231/2001\b", re.IGNORECASE)),
    ("nis2", re.compile(r"\bNIS2\b|\bD\.?\s*Lgs\.?\s*138/2024\b", re.IGNORECASE)),
]


def _norm_of(text):
    earliest = None
    for nid, pat in SIGLA_PATTERNS:
        m = pat.search(text)
        if m and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), nid)
    return earliest[1] if earliest else None


def _parse(text):
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s).strip()
    try:
        arr = json.loads(s)
        if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
            return [x.strip() for x in arr if x.strip()]
    except Exception:
        pass
    # fallback regex
    return [m.strip() for m in re.findall(r'"((?:[^"\\]|\\.)*?)"', s)
            if m.strip() and len(m.strip()) > 10]


def main():
    import logging; logging.basicConfig(level=logging.ERROR)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from anthropic import Anthropic
    from qdrant_client import QdrantClient, models
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.terminology import expand_query
    from core.vector_store import (
        DENSE_VECTOR_NAME, HYBRID_COLLECTION_NAME, SPARSE_VECTOR_NAME,
    )

    print("STEP 2 — rigenera Q71 ai_act col prompt + regola granularità")
    print("=" * 80)
    ant = Anthropic()
    msg = ant.messages.create(
        model="claude-sonnet-4-6", max_tokens=600, temperature=0.0,
        messages=[{"role": "user", "content": PROMPT.format(query=Q71_QUESTION)}],
    )
    raw = msg.content[0].text if msg.content else ""
    cost = (msg.usage.input_tokens / 1_000_000) * 3.0 + \
           (msg.usage.output_tokens / 1_000_000) * 15.0
    sqs = _parse(raw)
    sqs_filt = [sq for sq in sqs if _norm_of(sq) == "ai_act"]
    dropped = [sq for sq in sqs if _norm_of(sq) != "ai_act"]
    print(f"in_tok={msg.usage.input_tokens} out_tok={msg.usage.output_tokens}  cost≈${cost:.4f}")
    print(f"sub-query totali emesse: {len(sqs)}  (post-filtro ai_act: {len(sqs_filt)})")
    if dropped:
        for d in dropped:
            print(f"  DROPPED (non ai_act): {d[:80]}")
    print()
    has_point5_dedicated = False
    for i, sq in enumerate(sqs_filt):
        is_point5 = bool(re.search(r"allegato\s+iii\s+punto\s*5", sq, re.IGNORECASE)) or \
                    bool(re.search(r"servizi\s+pubblici\s+essenziali", sq, re.IGNORECASE)) or \
                    bool(re.search(r"servizi\s+essenziali", sq, re.IGNORECASE) and "punto" in sq.lower())
        if is_point5:
            has_point5_dedicated = True
        mk = "  ★ DEDICATA point_5" if is_point5 else ""
        print(f"  [{i}] {sq}{mk}")
    print()
    print(f"VERIFICA: sub-query dedicata a 'Allegato III punto 5' / 'servizi pubblici essenziali' presente? "
          f"→ {'SI' if has_point5_dedicated else 'NO'}")

    # STEP 3 — funnel locale
    print("\n" + "=" * 80)
    print("STEP 3 — funnel per point_5 sulle nuove sub-query")
    print("=" * 80)
    cli = QdrantClient(host="localhost", port=6333, timeout=60)
    print("Loading models...")
    enc = BgeM3Encoder.get(device="mps")
    bm = SparseTextEmbedding(model_name="Qdrant/bm25")
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("w", "w")], show_progress_bar=False)
    flt_ai = models.Filter(must=[models.FieldCondition(
        key="doc_urn", match=models.MatchValue(value=TARGET_DOC_URN))])

    def find_rank(points, cid):
        for i, pp in enumerate(points, 1):
            if pp.payload.get("chunk_id") == cid:
                return i, float(pp.score)
        return None, None

    print(f"\n{'tag':<18}{'sub_query (snippet)':<70}{'dense':>8}{'sparse':>8}{'hybrid':>8}{'rerank':>15}{'top-3?':>10}")
    in_top3_any = False
    for i, sq in enumerate(sqs_filt):
        q_exp = expand_query(sq)
        dvec = enc.encode([q_exp], batch_size=1)[0]
        emb = next(bm.query_embed(q_exp))
        svec = models.SparseVector(indices=emb.indices.tolist(),
                                   values=emb.values.tolist())
        dpts = cli.query_points(
            collection_name=HYBRID_COLLECTION_NAME, query=dvec, using=DENSE_VECTOR_NAME,
            limit=20, with_payload=["chunk_id"], query_filter=flt_ai,
        ).points
        spts = cli.query_points(
            collection_name=HYBRID_COLLECTION_NAME, query=svec, using=SPARSE_VECTOR_NAME,
            limit=20, with_payload=["chunk_id"], query_filter=flt_ai,
        ).points
        hpts = cli.query_points(
            collection_name=HYBRID_COLLECTION_NAME,
            prefetch=[
                models.Prefetch(query=dvec, using=DENSE_VECTOR_NAME, limit=40, filter=flt_ai),
                models.Prefetch(query=svec, using=SPARSE_VECTOR_NAME, limit=40, filter=flt_ai),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=20, with_payload=True,
        ).points
        d_rank, _ = find_rank(dpts, TARGET_ID)
        s_rank, _ = find_rank(spts, TARGET_ID)
        h_rank, _ = find_rank(hpts, TARGET_ID)
        if h_rank is not None:
            pairs = [(q_exp, pp.payload.get("text", "")) for pp in hpts]
            scores = rr.predict(pairs, show_progress_bar=False)
            ranked = sorted(zip(hpts, scores), key=lambda x: -float(x[1]))
            ranked_ids = [pp.payload.get("chunk_id") for pp, _ in ranked]
            if TARGET_ID in ranked_ids:
                r_rank = ranked_ids.index(TARGET_ID) + 1
                r_score = float([s for pp, s in ranked if pp.payload.get("chunk_id") == TARGET_ID][0])
            else:
                r_rank, r_score = None, None
        else:
            r_rank, r_score = None, None
        d_s = f"r{d_rank}" if d_rank else "—"
        s_s = f"r{s_rank}" if s_rank else "—"
        h_s = f"r{h_rank}" if h_rank else "—"
        r_s = f"r{r_rank}@{r_score:.3f}" if r_rank else "—"
        in_top3 = "YES" if r_rank and r_rank <= 3 else "no"
        if r_rank and r_rank <= 3: in_top3_any = True
        snip = sq[:65] + "..." if len(sq) > 65 else sq
        tag = f"v3g_#{i}"
        print(f"{tag:<18}{snip:<70}{d_s:>8}{s_s:>8}{h_s:>8}{r_s:>15}{in_top3:>10}")

    print()
    best_rank = min((r for r in [None] +
                     [r_rank for r_rank in []]
                     if r is not None), default=None)
    print(f"VERIFICA point_5 entra in top-3 di ALMENO una nuova sub-query: "
          f"{'YES' if in_top3_any else 'NO'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
