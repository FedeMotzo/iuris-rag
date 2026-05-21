"""Build gold-candidate lists for benchmark queries.

Strategies (deliberately ricche per coprire ciò che il retriever potrebbe
trovare, lasciando al revisore umano la scelta del gold):
  A) Direct hints: (doc_short_name, suffix) → match per chunk_id (art_N inclusi
     gli split __paras_X_Y, oltre a recital_N e annex_X).
  B) Textual search: literal case-insensitive substring match in chunk.text,
     ranked by `count(term) / n_words` and capped at top 10 per term.
  C) Hybrid retrieval (solo in modalità --v2, opzionale): query API
     dense+sparse RRF su `italian_legal_v1_hybrid`, top-20.

Default: emette `data/benchmark/gold_candidates.json` per le 10 query baseline.
Con `--v2`: emette `data/benchmark/gold_candidates_v2.json` con 50 query —
le 10 baseline copiate verbatim da `gold_validated.json` (candidati + is_gold
preservati), le 40 nuove costruite fresh con A+B+C.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from ingest_corpus import load_all_chunks  # noqa: E402 — reuse the canonical pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("build_gold_candidates")


# Short-name → doc_urn produced by chunking pipeline (verified by assertions below).
DOC_URN_MAP = {
    "aiact": "eli/reg/2024/1689/oj",
    "gdpr": "eli/reg/2016/679/oj",
    "231": "akn/it/act/decreto_legislativo/stato/2001-06-08/231",
    "196": "akn/it/act/decreto_legislativo/stato/2003-06-30/196",
    "nis2": "akn/it/act/decreto_legislativo/stato/2024-09-04/138",
    "l132": "akn/it/act/legge/stato/2025-09-23/132",
}


QUERIES = [
    {
        "qid": "Q1",
        "use_case": "AI Act high-risk HR screening",
        "query": "Un sistema che fa screening automatico dei CV in fase di selezione del personale ricade tra i sistemi ad alto rischio dell'AI Act?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("aiact", "art_6"),
            ("aiact", "art_26"),
        ],
        # Q1 HR screening — i terms originali ("alto rischio", "screening",
        # "selezione del personale", "allegato III") non pescavano considerando 57
        # che usa "occupazione" e "assunzione". Estesi per coprire quel vocabolario.
        "search_terms": [
            "allegato III", "selezione del personale", "alto rischio", "screening",
            "occupazione", "assunzione",
        ],
    },
    {
        "qid": "Q2",
        "use_case": "Timeline AI Act credit scoring",
        "query": "Quando entrano in vigore gli obblighi dell'AI Act per un sistema di credit scoring già operativo?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("aiact", "art_113"),
            ("aiact", "art_111"),
        ],
        "search_terms": ["entrata in vigore", "valutazione del merito di credito", "credit scoring", "agosto 2026"],
    },
    {
        "qid": "Q3",
        "use_case": "DPIA vs FRIA",
        "query": "In che casi devo fare una valutazione d'impatto sui diritti fondamentali ai sensi dell'AI Act in aggiunta alla DPIA prevista dal GDPR?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("aiact", "art_27"),
            ("gdpr", "art_35"),
        ],
        "search_terms": ["valutazione d'impatto", "diritti fondamentali", "DPIA", "considerando 84"],
    },
    {
        "qid": "Q4",
        "use_case": "Garante riconoscimento facciale lavoro (negative)",
        "query": "Il Garante si è già pronunciato sull'uso di sistemi di riconoscimento facciale per il controllo accessi dei dipendenti?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["riconoscimento facciale", "biometrici", "lavoratori"],
        "note": "Garante NON in corpus v1. Lista candidati come sanity check di falsi positivi.",
    },
    {
        "qid": "Q5",
        "use_case": "231 + AI decisioni HR",
        "query": "L'uso di sistemi AI per decisioni che riguardano i lavoratori può attivare responsabilità ai sensi del D.Lgs 231/2001?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("231", "art_25-undecies"),
            ("231", "art_24-bis"),
            ("gdpr", "art_22"),
        ],
        "search_terms": ["decisioni automatizzate", "trattamento illecito di dati", "responsabilità amministrativa"],
    },
    {
        "qid": "Q6",
        "use_case": "Compiti del DPO",
        "query": "Quali sono i compiti del responsabile della protezione dei dati?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("gdpr", "art_39"),
            ("gdpr", "art_37"),
            ("gdpr", "art_38"),
        ],
        "search_terms": ["responsabile della protezione dei dati", "compiti", "RPD", "DPO"],
    },
    {
        "qid": "Q7",
        "use_case": "Quando DPIA è obbligatoria",
        "query": "Quando è obbligatoria la valutazione d'impatto sulla protezione dei dati?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("gdpr", "art_35"),
        ],
        "search_terms": ["valutazione d'impatto sulla protezione dei dati", "rischio elevato", "trattamento sistematico"],
    },
    {
        "qid": "Q8",
        "use_case": "Cos'è FRIA e quando si fa",
        "query": "Cos'è la valutazione d'impatto sui diritti fondamentali e quando va condotta?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("aiact", "art_27"),
        ],
        "search_terms": ["valutazione d'impatto sui diritti fondamentali", "FRIA", "diritti fondamentali"],
    },
    {
        "qid": "Q9",
        "use_case": "Reati 231 trattamento illecito dati",
        "query": "Quali sono i reati presupposto in materia di trattamento illecito di dati personali ai sensi del 231?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("231", "art_25-undecies"),
            ("231", "art_24-bis"),
        ],
        "search_terms": ["trattamento illecito", "delitti contro la riservatezza", "delitti informatici"],
    },
    {
        "qid": "Q10",
        "use_case": "NIS2 soggetti essenziali/importanti",
        "query": "La mia azienda è considerata soggetto essenziale o importante ai sensi del decreto NIS2?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("nis2", "art_3"),
        ],
        "search_terms": ["soggetti essenziali", "soggetti importanti", "ambito di applicazione", "dimensione"],
    },
]


TEXTUAL_TOPN_PER_TERM = 10
HYBRID_TOP_K = 20
ALLOWED_EXPECTED_KINDS = {"positive", "negative", "edge"}


# ---------------------------------------------------------------------------
# 40 query nuove (Q11–Q50) per benchmark settimana 3
# ---------------------------------------------------------------------------
NEW_QUERIES: list[dict] = [
    # ---- UC1: high-risk AI Act --------------------------------------------
    {
        "qid": "Q11",
        "use_case": "AI Act high-risk credit scoring",
        "query": "Un sistema di credit scoring usato da una banca per valutare la concessione di mutui è classificato come ad alto rischio dall'AI Act?",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_6"), ("aiact", "art_111"), ("aiact", "annex_III")],
        "search_terms": ["credit scoring", "alto rischio", "valutazione del merito di credito"],
    },
    {
        "qid": "Q12",
        "use_case": "AI Act high-risk emotion recognition scuole",
        "query": "I sistemi di riconoscimento delle emozioni utilizzati in contesti educativi sono considerati ad alto rischio?",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_6"), ("aiact", "annex_III"), ("aiact", "recital_57")],
        "search_terms": ["riconoscimento delle emozioni", "istruzione", "alto rischio"],
    },
    {
        "qid": "Q13",
        "use_case": "AI Act Allegato III biometria",
        "query": "Allegato III AI Act sistemi alto rischio biometria",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "annex_III"), ("aiact", "art_6"), ("aiact", "recital_54")],
        "search_terms": ["Allegato III", "biometria"],
    },
    {
        "qid": "Q14",
        "use_case": "AI Act GPAI vs high-risk obblighi",
        "query": "Un fornitore di modelli AI per finalità generali ha obblighi specifici diversi rispetto ai fornitori di sistemi ad alto rischio?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("aiact", "art_51"),
            ("aiact", "art_53"),
            ("aiact", "art_55"),
            ("aiact", "recital_99"),
            ("aiact", "recital_100"),
        ],
        "search_terms": ["modelli di IA per finalità generali", "GPAI", "finalità generali"],
    },
    # ---- UC2: timeline AI Act ---------------------------------------------
    {
        "qid": "Q15",
        "use_case": "AI Act timeline divieti",
        "query": "Quando scattano i divieti dell'AI Act sui sistemi a rischio inaccettabile?",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_113"), ("aiact", "art_5"), ("aiact", "recital_179")],
        "search_terms": ["rischio inaccettabile", "divieti", "2 febbraio 2025"],
    },
    {
        "qid": "Q16",
        "use_case": "AI Act timeline GPAI già immessi",
        "query": "Entro quando devo adeguare un sistema di IA per finalità generali immesso sul mercato prima del 2 agosto 2025?",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_111"), ("aiact", "recital_179")],
        "search_terms": ["2 agosto 2025", "GPAI", "finalità generali"],
    },
    {
        "qid": "Q17",
        "use_case": "AI Act art 113 stress",
        "query": "art 113 entrata in vigore AI Act",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_113")],
        "search_terms": ["art 113", "entrata in vigore"],
    },
    {
        "qid": "Q18",
        "use_case": "AI Act timeline sanzioni",
        "query": "Le sanzioni dell'AI Act sono già applicabili oppure è previsto un periodo transitorio?",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_99"), ("aiact", "art_113")],
        "search_terms": ["sanzioni", "entrata in vigore", "transitorio"],
    },
    # ---- UC3: DPIA + FRIA -------------------------------------------------
    {
        "qid": "Q19",
        "use_case": "DPIA + FRIA scoring bancario",
        "query": "Una banca che usa AI per scoring creditizio deve condurre la FRIA oltre alla DPIA?",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_27"), ("gdpr", "art_35"), ("aiact", "annex_III")],
        "search_terms": ["valutazione d'impatto", "FRIA", "DPIA", "scoring"],
    },
    # ---- UC4: Garante (negative — corpus non li contiene) -----------------
    {
        "qid": "Q20",
        "use_case": "Garante sanzioni biometria dipendenti",
        "query": "Quali sono le sanzioni del Garante per uso non autorizzato di dati biometrici dei dipendenti?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["biometrici", "dipendenti", "sanzioni"],
        "note": "NEGATIVE — Garante non in corpus v1, ci si aspetta is_gold=false su tutti.",
    },
    {
        "qid": "Q21",
        "use_case": "Garante riconoscimento facciale aeroporti",
        "query": "Il Garante ha autorizzato il riconoscimento facciale negli aeroporti italiani?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["riconoscimento facciale", "aeroporti"],
        "note": "NEGATIVE — Garante non in corpus v1, ci si aspetta is_gold=false su tutti.",
    },
    {
        "qid": "Q22",
        "use_case": "Garante riconoscimento facciale presenze",
        "query": "Esiste un provvedimento del Garante che vieta l'uso del riconoscimento facciale per le presenze in azienda?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["Garante", "riconoscimento facciale", "presenze"],
        "note": "NEGATIVE — Garante non in corpus v1, ci si aspetta is_gold=false su tutti.",
    },
    # ---- UC5: multi-normativa 231 -----------------------------------------
    {
        "qid": "Q23",
        "use_case": "231 + GDPR + AI selezione fornitori",
        "query": "Un'azienda che usa un sistema AI per la selezione automatizzata dei fornitori espone l'ente a responsabilità ex 231 in caso di violazione GDPR?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("231", "art_24-bis"),
            ("gdpr", "art_22"),
            ("231", "art_5"),
            ("231", "art_6"),
        ],
        "search_terms": ["responsabilità ente", "trattamento illecito", "automatizzata"],
    },
    {
        "qid": "Q24",
        "use_case": "231 modello organizzativo + AI HR",
        "query": "Il modello organizzativo 231 deve essere aggiornato per coprire i rischi connessi all'uso di sistemi AI per decisioni HR?",
        "expected_kind": "positive",
        "candidate_hints": [
            ("231", "art_6"),
            ("231", "art_7"),
            ("aiact", "art_26"),
            ("aiact", "recital_57"),
        ],
        "search_terms": ["modello organizzativo", "ente", "rischi"],
    },
    {
        "qid": "Q25",
        "use_case": "231 fattispecie informatica art 24-bis",
        "query": "Un dipendente accede abusivamente al sistema informatico di un concorrente per favorire l'azienda: l'ente risponde ai sensi del 231?",
        "expected_kind": "positive",
        "candidate_hints": [("231", "art_24-bis"), ("231", "art_5")],
        "search_terms": ["accesso abusivo", "delitti informatici", "ente"],
    },
    # ---- Stress lessicali (Q26–Q40) ---------------------------------------
    {
        "qid": "Q26",
        "use_case": "stress: art 24-bis 231",
        "query": "art 24-bis 231 delitti informatici",
        "expected_kind": "positive",
        "candidate_hints": [("231", "art_24-bis")],
        "search_terms": ["art 24-bis", "delitti informatici"],
    },
    {
        "qid": "Q27",
        "use_case": "stress: art 25-undecies",
        "query": "art 25-undecies reati ambientali",
        "expected_kind": "positive",
        "candidate_hints": [("231", "art_25-undecies")],
        "search_terms": ["art 25-undecies", "reati ambientali"],
    },
    {
        "qid": "Q28",
        "use_case": "stress: art 5 GDPR",
        "query": "art 5 GDPR principi trattamento",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "art_5")],
        "search_terms": ["art 5", "principi"],
    },
    {
        "qid": "Q29",
        "use_case": "stress: considerando 84 GDPR",
        "query": "considerando 84 GDPR DPIA",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "recital_84")],
        "search_terms": ["considerando 84", "valutazione d'impatto"],
    },
    {
        "qid": "Q30",
        "use_case": "stress: Allegato III punto 4 AI Act",
        "query": "Allegato III punto 4 lettera a AI Act",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "annex_III")],
        "search_terms": ["Allegato III", "punto 4"],
    },
    {
        "qid": "Q31",
        "use_case": "stress: art 22 GDPR",
        "query": "art 22 GDPR processo decisionale automatizzato",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "art_22")],
        "search_terms": ["art 22", "decisionale automatizzato"],
    },
    {
        "qid": "Q32",
        "use_case": "stress: art 6 NIS2",
        "query": "art 6 NIS2 soggetti essenziali importanti",
        "expected_kind": "positive",
        "candidate_hints": [("nis2", "art_6")],
        "search_terms": ["art 6", "soggetti essenziali", "soggetti importanti"],
    },
    {
        "qid": "Q33",
        "use_case": "stress: art 35 disambiguation",
        "query": "art 35 valutazione impatto",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "art_35"), ("aiact", "art_27")],
        "search_terms": ["art 35", "valutazione d'impatto"],
        "note": "DISAMBIGUATION — gold atteso: gdpr/art_35 + aiact/art_27. Articoli 35 omonimi in 231, NIS2, AI Act (autorità di notifica) NON sono gold.",
    },
    {
        "qid": "Q34",
        "use_case": "stress: art 9 GDPR",
        "query": "art 9 GDPR categorie particolari",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "art_9")],
        "search_terms": ["art 9", "categorie particolari"],
    },
    {
        "qid": "Q35",
        "use_case": "stress: art 27 AI Act FRIA",
        "query": "art 27 AI Act FRIA",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_27")],
        "search_terms": ["art 27", "FRIA", "diritti fondamentali"],
    },
    {
        "qid": "Q36",
        "use_case": "stress: art 111 AI Act",
        "query": "art 111 AI Act sistemi già immessi",
        "expected_kind": "positive",
        "candidate_hints": [("aiact", "art_111")],
        "search_terms": ["art 111", "già immessi"],
    },
    {
        "qid": "Q37",
        "use_case": "stress: considerando 71 vs art 22 GDPR",
        "query": "considerando 71 GDPR profilazione vieta o consente",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "recital_71"), ("gdpr", "art_22")],
        "search_terms": ["considerando 71", "profilazione"],
        "note": "Gold atteso include sia recital_71 sia art_22 — testa se il sistema preferisce recital o articolato.",
    },
    {
        "qid": "Q38",
        "use_case": "stress: L. 132/2025 art 11",
        "query": "L. 132/2025 art 11 lavoro intelligenza artificiale",
        "expected_kind": "positive",
        "candidate_hints": [("l132", "art_11")],
        "search_terms": ["art 11", "lavoro"],
    },
    {
        "qid": "Q39",
        "use_case": "stress: art 6 GDPR base giuridica",
        "query": "art 6 GDPR base giuridica del trattamento",
        "expected_kind": "positive",
        "candidate_hints": [("gdpr", "art_6")],
        "search_terms": ["art 6", "base giuridica", "liceità"],
    },
    {
        "qid": "Q40",
        "use_case": "stress: NIS2 obblighi notifica naturale",
        "query": "Quali sono gli obblighi di notifica degli incidenti per i soggetti essenziali ai sensi della NIS2?",
        "expected_kind": "positive",
        "candidate_hints": [("nis2", "art_25"), ("nis2", "art_26")],
        "search_terms": ["obblighi notifica", "incidenti", "soggetti essenziali"],
    },
    # ---- Edge / negative (Q41–Q50) ---------------------------------------
    {
        "qid": "Q41",
        "use_case": "edge: Data Act off-corpus",
        "query": "Cosa prevede il Data Act sui dati industriali?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["Data Act", "dati industriali"],
        "note": "NEGATIVE — Data Act non in corpus v1.",
    },
    {
        "qid": "Q42",
        "use_case": "edge: ISO 27001 off-scope",
        "query": "Quali requisiti impone la ISO 27001 per i sistemi AI?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["ISO 27001"],
        "note": "NEGATIVE — ISO 27001 fuori corpus per copyright.",
    },
    {
        "qid": "Q43",
        "use_case": "edge: query troppo generica",
        "query": "Cosa dice la legge sulla privacy?",
        "expected_kind": "edge",
        "candidate_hints": [("gdpr", "art_1"), ("196", "art_1")],
        "search_terms": ["legge privacy"],
        "note": "EDGE — gold criterio: primo chunk informativo del corpus su quale norma regola la privacy in Italia.",
    },
    {
        "qid": "Q44",
        "use_case": "edge: EDPB off-corpus",
        "query": "Quali sono le linee guida EDPB sulla pseudonimizzazione?",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["EDPB", "pseudonimizzazione"],
        "note": "NEGATIVE — EDPB non in corpus v1.",
    },
    {
        "qid": "Q45",
        "use_case": "edge: query vaga multi-doc",
        "query": "normativa AI Italia 2025",
        "expected_kind": "edge",
        "candidate_hints": [("l132", "art_1")],
        "search_terms": ["intelligenza artificiale", "2025"],
    },
    {
        "qid": "Q46",
        "use_case": "edge: operativa ChatGPT",
        "query": "Posso usare ChatGPT per analizzare documenti aziendali confidenziali?",
        "expected_kind": "edge",
        "candidate_hints": [],
        "search_terms": ["documenti aziendali", "confidenziali"],
        "note": "EDGE — nessun chunk risponde direttamente. Gold vuoto accettabile; aspettarsi principi GDPR/AI Act in top-k.",
    },
    {
        "qid": "Q47",
        "use_case": "edge: art inesistente",
        "query": "art 999 GDPR",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["art 999"],
        "note": "NEGATIVE — articolo inesistente. Score bassi attesi.",
    },
    {
        "qid": "Q48",
        "use_case": "edge: ePrivacy off-corpus",
        "query": "regolamento EU sui cookie",
        "expected_kind": "negative",
        "candidate_hints": [],
        "search_terms": ["cookie", "ePrivacy"],
        "note": "NEGATIVE — ePrivacy non in corpus v1.",
    },
    {
        "qid": "Q49",
        "use_case": "edge: mix in/off corpus",
        "query": "Posso integrare il modello 231 con il sistema di gestione qualità ISO 9001?",
        "expected_kind": "edge",
        "candidate_hints": [("231", "art_6"), ("231", "art_7")],
        "search_terms": ["modello organizzativo", "qualità"],
        "note": "EDGE — parte 231 in corpus, ISO 9001 no. Gold atteso: chunk 231 sul modello organizzativo.",
    },
    {
        "qid": "Q50",
        "use_case": "edge: vaga ma con anchor lessicale",
        "query": "sanzioni AI Act multe massime",
        "expected_kind": "edge",
        "candidate_hints": [("aiact", "art_99")],
        "search_terms": ["sanzioni", "multe"],
    },
]


def _verify_doc_urns(chunks: list, doc_map: dict[str, str]) -> None:
    """Assert that each short-name URN actually exists in the loaded corpus."""
    seen = {c.doc_urn for c in chunks}
    for short, urn in doc_map.items():
        if urn not in seen:
            log.warning("doc_urn for %r not present in corpus: %s", short, urn)


def _match_hint(chunks: list, urn: str, suffix: str) -> list:
    """Match chunks via hint (urn, suffix). Suffix is `art_N`, `recital_N`, `annex_X`.

    For `art_N`: also matches split chunks `{urn}__art_N__paras_X_Y` (Q5/Q9 etc).
    """
    target = f"{urn}__{suffix}"
    if suffix.startswith("art_"):
        return [
            c for c in chunks
            if c.doc_urn == urn and (
                c.chunk_id == target or c.chunk_id.startswith(target + "__")
            )
        ]
    return [c for c in chunks if c.chunk_id == target]


def _rank_textual_matches(chunks: list, term: str, topn: int) -> list:
    """Return top-N chunks by frequency-normalized term count."""
    term_lower = term.lower()
    scored: list[tuple[float, int, object]] = []
    for c in chunks:
        text_lower = c.text.lower()
        n = text_lower.count(term_lower)
        if n == 0:
            continue
        n_words = max(1, len(c.text.split()))
        score = n / n_words
        scored.append((score, n, c))
    # Sort: higher score first; break ties by raw count, then chunk_id for determinism.
    scored.sort(key=lambda x: (-x[0], -x[1], x[2].chunk_id))
    return [s[2] for s in scored[:topn]]


def _candidate_dict(chunk, found_via: list[str], notes: str,
                    *, default_is_gold=None) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "doc_urn": chunk.doc_urn,
        "article_eid": chunk.article_eid,
        "chunk_type": chunk.chunk_type,
        "hierarchy_path": chunk.hierarchy_path,
        "text_excerpt": chunk.text[:250],
        "found_via": found_via,
        "is_gold": default_is_gold,
        "notes": notes,
    }


def build_candidates_for_query(
    query: dict,
    chunks: list,
    *,
    retriever=None,
    default_is_gold=None,
) -> list[dict]:
    """Return ordered candidate dicts (hint matches first, then textual, then hybrid).

    If `retriever` is provided, also adds Strategy C: hybrid retrieval (top-20).
    `default_is_gold` controls the seed value (None per baseline, False per v2 new).
    """
    found_via_by_id: dict[str, list[str]] = {}
    chunk_by_id: dict[str, object] = {}

    def _register(chunk, source: str) -> None:
        if chunk.chunk_id not in chunk_by_id:
            chunk_by_id[chunk.chunk_id] = chunk
            found_via_by_id[chunk.chunk_id] = []
        if source not in found_via_by_id[chunk.chunk_id]:
            found_via_by_id[chunk.chunk_id].append(source)

    # Strategy A — hints.
    for short, suffix in query.get("candidate_hints", []):
        urn = DOC_URN_MAP.get(short)
        if urn is None:
            log.warning("[%s] unknown short-name in hint: %r", query["qid"], short)
            continue
        matched = _match_hint(chunks, urn, suffix)
        if not matched:
            log.warning("[%s] hint (%s, %s) matched 0 chunks (URN=%s)",
                        query["qid"], short, suffix, urn)
        for c in matched:
            _register(c, f"hint:{short}/{suffix}")

    # Strategy B — textual.
    for term in query.get("search_terms", []):
        top = _rank_textual_matches(chunks, term, TEXTUAL_TOPN_PER_TERM)
        for c in top:
            _register(c, f"term:{term}")

    # Strategy C — hybrid retrieval (RRF dense+sparse) — solo se attivata.
    if retriever is not None:
        try:
            hits = retriever.retrieve(query["query"], top_k=HYBRID_TOP_K, mode="hybrid")
            by_id = {c.chunk_id: c for c in chunks}
            for h in hits:
                chunk = by_id.get(h.chunk_id)
                if chunk is None:
                    log.warning("[%s] hybrid hit chunk_id %s not in loaded corpus",
                                query["qid"], h.chunk_id)
                    continue
                _register(chunk, f"hybrid:rank={h.rank}")
        except Exception as e:  # noqa: BLE001 — degrade graceful per qualunque errore
            log.warning("[%s] hybrid retrieval failed (%s); proseguo senza Strategy C",
                        query["qid"], e)

    # Build dicts. Default note: query["note"] se presente, fallback per Q4.
    default_note = query.get("note", "")
    if not default_note and query["qid"] == "Q4":
        default_note = "NEGATIVE — Garante non in corpus v1, ci si aspetta is_gold=false su tutti."

    candidates = [
        _candidate_dict(chunk_by_id[cid], found_via_by_id[cid], default_note,
                        default_is_gold=default_is_gold)
        for cid in chunk_by_id
    ]
    # Order: hint-backed first, then textual; secondary key chunk_id for stability.
    candidates.sort(key=lambda c: (
        not any(fv.startswith("hint:") for fv in c["found_via"]),
        c["chunk_id"],
    ))
    return candidates


def _print_summary(qid: str, expected_kind: str, candidates: list[dict]) -> None:
    n_total = len(candidates)
    n_hint = sum(1 for c in candidates if any(fv.startswith("hint:") for fv in c["found_via"]))
    n_term = sum(1 for c in candidates if any(fv.startswith("term:") for fv in c["found_via"]))
    n_hybrid = sum(1 for c in candidates if any(fv.startswith("hybrid:") for fv in c["found_via"]))
    warn = ""
    if expected_kind == "positive" and n_total == 0:
        warn = "  ⚠ ZERO CANDIDATES — hint matches missing, investigate"
    print(f"{qid}: {n_total} candidati [hint={n_hint}, term={n_term}, hybrid={n_hybrid}]{warn}")


def _validate_expected_kinds(queries: list[dict]) -> None:
    for q in queries:
        kind = q.get("expected_kind")
        if kind not in ALLOWED_EXPECTED_KINDS:
            raise ValueError(
                f"[{q['qid']}] expected_kind={kind!r} non valido; "
                f"valori ammessi: {sorted(ALLOWED_EXPECTED_KINDS)}"
            )


def _build_hybrid_retriever():
    """Costruisce un HybridRetriever su `italian_legal_v1_hybrid`. None se Qdrant down."""
    try:
        from fastembed import SparseTextEmbedding
        from core.embedding import BgeM3Encoder
        from core.hybrid_retriever import HybridRetriever
        from core.vector_store import HYBRID_COLLECTION_NAME, get_client

        client = get_client()
        if not client.collection_exists(HYBRID_COLLECTION_NAME):
            log.warning("Collection %s assente: Strategy C disattivata",
                        HYBRID_COLLECTION_NAME)
            return None
        encoder = BgeM3Encoder.get()
        bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
        return HybridRetriever(client, encoder, bm25, HYBRID_COLLECTION_NAME)
    except Exception as e:  # noqa: BLE001
        log.warning("Hybrid retriever non disponibile (%s): Strategy C disattivata", e)
        return None


def _load_baseline_queries_from_gold_validated(path: Path) -> list[dict]:
    """Carica le query baseline (Q1..Q10) da `gold_validated.json`, verbatim.

    Preserva candidati e is_gold già annotato.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Atteso file baseline {path} (necessario in modalità --v2). "
            "Eseguire prima `build_gold_validated.py` per generarlo."
        )
    data = json.loads(path.read_text())
    return data["queries"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--v2", action="store_true",
        help="Genera gold_candidates_v2.json con 50 query: Q1-Q10 verbatim "
             "da gold_validated.json, Q11-Q50 fresh con A+B+C (hybrid).",
    )
    args = parser.parse_args()

    print("Loading corpus chunks (parse + chunk pipeline)...", file=sys.stderr)
    chunks = load_all_chunks()
    print(f"Loaded {len(chunks)} chunks", file=sys.stderr)

    _verify_doc_urns(chunks, DOC_URN_MAP)

    if args.v2:
        return _main_v2(chunks)

    # ----- modalità baseline (invariata) ---------------------------------
    _validate_expected_kinds(QUERIES)
    output = {"queries": []}
    print()
    print(f"{'QID':4s} | candidates")
    print("-" * 70)
    for q in QUERIES:
        candidates = build_candidates_for_query(q, chunks)
        output["queries"].append({
            "qid": q["qid"],
            "query": q["query"],
            "use_case": q["use_case"],
            "expected_kind": q["expected_kind"],
            "candidates": candidates,
        })
        _print_summary(q["qid"], q["expected_kind"], candidates)

    out_path = ROOT / "data" / "benchmark" / "gold_candidates.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\nWrote {out_path.relative_to(ROOT)}", file=sys.stderr)
    return 0


def _main_v2(chunks: list) -> int:
    """Modalità v2: 50 query, baseline frozen + nuove fresh con hybrid."""
    _validate_expected_kinds(QUERIES)
    _validate_expected_kinds(NEW_QUERIES)

    baseline_path = ROOT / "data" / "benchmark" / "gold_validated.json"
    baseline_qs = _load_baseline_queries_from_gold_validated(baseline_path)
    baseline_qids = {q["qid"] for q in baseline_qs}
    expected_baseline = {q["qid"] for q in QUERIES}
    if baseline_qids != expected_baseline:
        log.warning("Baseline qid set differente: validato=%s, atteso=%s",
                    sorted(baseline_qids), sorted(expected_baseline))

    print("Building HybridRetriever per Strategy C...", file=sys.stderr)
    retriever = _build_hybrid_retriever()
    if retriever is None:
        print("⚠ Strategy C (hybrid) disattivata — solo A (hints) + B (terms)",
              file=sys.stderr)

    output = {"queries": []}
    print()
    print(f"{'QID':4s} | candidates")
    print("-" * 70)

    # Baseline Q1-Q10: copia verbatim (candidati + is_gold preservati)
    for bq in baseline_qs:
        output["queries"].append(bq)
        n = len(bq["candidates"])
        n_gold = sum(1 for c in bq["candidates"] if c.get("is_gold") is True)
        print(f"{bq['qid']}: {n} candidati (baseline preservata, gold={n_gold})")

    # Q11-Q50: fresh con A+B+C, is_gold=False default per indicare "non annotato".
    for q in NEW_QUERIES:
        candidates = build_candidates_for_query(
            q, chunks, retriever=retriever, default_is_gold=False,
        )
        output["queries"].append({
            "qid": q["qid"],
            "query": q["query"],
            "use_case": q["use_case"],
            "expected_kind": q["expected_kind"],
            "candidates": candidates,
        })
        _print_summary(q["qid"], q["expected_kind"], candidates)

    out_path = ROOT / "data" / "benchmark" / "gold_candidates_v2.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    # Summary finale
    n_queries = len(output["queries"])
    n_baseline = len(baseline_qs)
    n_new = len(NEW_QUERIES)
    print()
    print("=" * 70)
    print(f"Wrote {out_path.relative_to(ROOT)}")
    print(f"  Totale query: {n_queries} (baseline {n_baseline} + new {n_new})")
    print(f"  Strategy C hybrid: {'ON' if retriever else 'OFF (degraded)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
