"""Map → assembly strutturato per cross-norma v1.2 (step 3).

Map: per ogni `SubQueryGroup` una mini-risposta LLM (Haiku) sui suoi top-k hit,
focalizzata e citata. Map SEQUENZIALE (la concorrenza è il passo successivo).

Assembly: concatenazione DETERMINISTICA (zero LLM) delle mini raggruppate per
norma (source) e, dentro ogni norma, per numero d'articolo crescente. Niente
dedup-per-articolo, niente executive summary: i marker [cite:CHUNK_ID] testuali
sono preservati così `verify_citations` li aggancia.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from core.citation_marker import has_dangling_cite
from core.hybrid_retriever.types import RetrievalHit, RetrievalResult

from .retriever import CrossNormResult, SubQueryGroup
from .subquery_generator import DEFAULT_GLOSSARY_PATH

logger = logging.getLogger(__name__)

MAP_PROMPT = """Sub-query:
{sub_query}

Chunk disponibili:
{chunks}

Regole (tassative):
- Rispondi SOLO usando i chunk forniti. NON riferire né citare articoli o norme non presenti nel contesto fornito — se ritieni manchi qualcosa, non inventarlo. Se i chunk non coprono la sub-query, dillo in una riga e basta.
- Cita con UN SOLO [cite:CHUNK_ID] nudo per affermazione; CHUNK_ID copiato esatto e completo dai chunk forniti; niente paragrafi/virgole/id multipli/abbreviazioni dentro le parentesi.
- Solo prosa, nessun header markdown (#, ##, ###): la struttura la dà l'assembly."""

MAP_MAX_TOKENS = 1200
MAP_LENGTH_RETRY_TOKENS = 2000  # 2° tentativo se la mini è troncata (finish=length)
MAP_CONCURRENCY_DEFAULT = 6
MAP_RETRIES = 3  # tentativi totali sulla chiamata map (429 / transienti)
MAP_FAIL_PREFIX = "⚠️ MINI NON GENERATA"  # marker esplicito in caso di fallimento
MAP_MODEL_DEFAULT = "claude-haiku-4-5"
_CHUNK_TEXT_CAP = 1600  # caratteri per chunk nel prompt mini

_CITE_RE = re.compile(r"\[cite:([^\]]+)\]")
_ALLEGATO_RE = re.compile(r"[Aa]llegato\s+([IVXLC]+)\s+punto\s+(\d+)")
# Range/elenco di articoli: "artt. 44-49", "artt. 44, 49", "artt. 13-14".
_ARTT_RANGE_RE = re.compile(
    r"\bartt\.?\s*(\d+)\s*[-,]\s*(\d+)", re.IGNORECASE,
)
_ART_RE = re.compile(
    r"\bart\.?\s*(\d+)(?:[-\s]?(bis|ter|quater|quinquies|sexies|septies|"
    r"octies|nonies|decies|undecies))?",
    re.IGNORECASE,
)
_SUFFIX_ORDER = {
    None: 0, "bis": 1, "ter": 2, "quater": 3, "quinquies": 4, "sexies": 5,
    "septies": 6, "octies": 7, "nonies": 8, "decies": 9, "undecies": 10,
}
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


@dataclass
class MiniResult:
    """Esito di UNA mini-risposta su un SubQueryGroup."""

    source: str                 # norm_id (gdpr/ai_act/...)
    sub_query: str
    text: str
    cited_chunk_ids: list[str]
    group_chunk_ids: list[str]  # universo del gruppo (per il check di faith)
    article_label: str          # "Art. 27" | "Allegato III punto 5" | "—"
    rubric: str                 # oggetto/rubrica (parte della sub-query)
    sort_key: tuple[int, int, int]
    finish_reason: str
    n_input_tokens: int
    n_output_tokens: int
    truncated: bool = False     # True se ancora finish=length dopo il retry esteso


def _chunk_text(h: RetrievalHit) -> str:
    txt = (h.payload or {}).get("text", "")
    if len(txt) > _CHUNK_TEXT_CAP:
        txt = txt[:_CHUNK_TEXT_CAP] + "…"
    return txt


def _parse_article(sub_query: str) -> tuple[str, str, tuple[int, int, int]]:
    """→ (article_label, rubric, sort_key) parsato dalla sub-query."""
    m_all = _ALLEGATO_RE.search(sub_query)
    if m_all:
        roman, point = m_all.group(1), int(m_all.group(2))
        label = f"Allegato {roman} punto {point}"
        rubric = sub_query.split(label, 1)[0].strip(" .:—-") or label
        # allegati DOPO gli articoli (prefisso 1)
        return label, rubric, (1, _ROMAN.get(roman, 99), point)
    m_range = _ARTT_RANGE_RE.search(sub_query)
    if m_range:
        n1, n2 = int(m_range.group(1)), int(m_range.group(2))
        label = f"Artt. {n1}-{n2}"
        head = re.split(r"\bex\s+artt?\.?|\bartt?\.?", sub_query, maxsplit=1)[0]
        rubric = head.strip(" .:—-")
        return label, rubric, (0, n1, 0)
    m_art = _ART_RE.search(sub_query)
    if m_art:
        num = int(m_art.group(1))
        suffix = (m_art.group(2) or "").lower() or None
        label = f"Art. {num}" + (f"-{suffix}" if suffix else "")
        # rubrica = testo prima di "ex art." (o prima di "art.")
        head = re.split(r"\bex\s+art\.?|\bart\.?", sub_query, maxsplit=1)[0]
        rubric = head.strip(" .:—-")
        return label, rubric, (0, num, _SUFFIX_ORDER.get(suffix, 0))
    return "—", sub_query.strip()[:80], (2, 0, 0)


def _extract_cites(text: str) -> list[str]:
    seen: list[str] = []
    for cid in _CITE_RE.findall(text):
        c = cid.strip()
        if c and c not in seen:
            seen.append(c)
    return seen


def load_norm_short_names(glossary_path: Path = DEFAULT_GLOSSARY_PATH) -> dict[str, str]:
    with glossary_path.open(encoding="utf-8") as fh:
        glossary = yaml.safe_load(fh)
    return {
        nid: (entry or {}).get("short_name", nid)
        for nid, entry in (glossary or {}).items()
    }


def load_norm_doc_urns(glossary_path: Path = DEFAULT_GLOSSARY_PATH) -> dict[str, str]:
    with glossary_path.open(encoding="utf-8") as fh:
        glossary = yaml.safe_load(fh)
    return {
        nid: (entry or {}).get("doc_urn", "")
        for nid, entry in (glossary or {}).items()
    }


# Bracket cite con coda tollerata (come il verifier): inizia non-spazio.
_CITE_BRACKET_RE = re.compile(r"\[cite:([^\]\s][^\]]*)\]")
# Suffisso articolo/allegato/considerando dentro un id (per l'espansione).
_ART_SUFFIX_RE = re.compile(r"(art|annex|recital)_[0-9A-Za-z_\-]+")


def _split_bracket_tokens(content: str) -> list[str]:
    """Spezza il contenuto di un bracket: split su ';'/',' + strip 'cite:'."""
    out: list[str] = []
    for raw in re.split(r"[;,]", content):
        t = raw.strip()
        if t.lower().startswith("cite:"):
            t = t[len("cite:"):].strip()
        if t:
            out.append(t)
    return out


def _normalize_token(token: str, doc_urn: str, universe: set[str]) -> str | None:
    """Riscrive la FORMA di un token-cite a id pieno (non fabbrica).

    - già id pieno noto → tieni;
    - prefisso di un id noto (coda descrittiva) → l'id noto;
    - già URN pieno (con '/') ma estraneo → tieni (fallirà la verifica);
    - abbreviato (art_N…, NNN__art_N…) → doc_urn del gruppo + suffisso articolo
      (anche se non nell'universo: si espande e poi fallisce correttamente);
    - non-id (es. "paragrafo 1") → None (scartato).
    """
    t = token.strip().rstrip(" .,;:")
    if not t:
        return None
    if t in universe:
        return t
    for k in universe:
        if t.startswith(k) and (len(t) == len(k) or t[len(k)] in " ,;:"):
            return k
    if "/" in t:
        return t
    m = _ART_SUFFIX_RE.search(t)
    if m and doc_urn:
        return f"{doc_urn}__{m.group(0)}"
    return None


_CITE_OPEN_RE = re.compile(r"\[cite:[A-Za-z0-9/_.\-]+")


def close_unclosed_cites(text: str) -> str:
    """Auto-chiude un `[cite:ID` privo di `]` prima del confine (newline / '###'
    / fine testo). Deterministico. Un bracket che HA già una `]` prima del
    confine (anche con coda descrittiva) è lasciato intatto: lo gestisce la
    normalizzazione dei token."""
    inserts: list[int] = []
    for m in _CITE_OPEN_RE.finditer(text):
        e = m.end()
        if text[e:e + 1] == "]":
            continue  # già chiuso subito dopo l'id
        nxt_close = text.find("]", e)
        nl = text.find("\n", e)
        hdr = text.find("###", e)
        bounds = [b for b in (nl, hdr) if b != -1]
        boundary = min(bounds) if bounds else len(text)
        if nxt_close != -1 and nxt_close < boundary:
            continue  # c'è una `]` prima del confine → bracket chiuso (coda)
        inserts.append(e)
    if not inserts:
        return text
    out: list[str] = []
    prev = 0
    for p in inserts:
        out.append(text[prev:p])
        out.append("]")
        prev = p
    out.append(text[prev:])
    return "".join(out)


def normalize_mini_text(text: str, doc_urn: str, universe: set[str]) -> str:
    """Normalizza tutti i [cite:...] del testo: bracket non chiusi auto-chiusi,
    id pieni, code strippate, multi-cite splittati. Deterministico, zero LLM."""
    text = close_unclosed_cites(text)

    def _repl(m: "re.Match[str]") -> str:
        norm: list[str] = []
        for tok in _split_bracket_tokens(m.group(1)):
            full = _normalize_token(tok, doc_urn, universe)
            if full and full not in norm:
                norm.append(full)
        if not norm:
            return m.group(0)
        return " ".join(f"[cite:{x}]" for x in norm)

    return _CITE_BRACKET_RE.sub(_repl, text)


def normalize_minis(
    minis: list[MiniResult],
    norm_doc_urns: dict[str, str],
    universe_ids: set[str],
) -> list[MiniResult]:
    """Ritorna le mini con testo+cite normalizzati usando il doc_urn del gruppo."""
    out: list[MiniResult] = []
    for m in minis:
        doc_urn = norm_doc_urns.get(m.source, "")
        new_text = normalize_mini_text(m.text, doc_urn, universe_ids)
        out.append(replace(
            m, text=new_text, cited_chunk_ids=_extract_cites(new_text),
        ))
    return out


def _generate_with_retry(map_llm, prompt: str, max_tokens: int):
    """Chiama map_llm.generate con backoff esponenziale (429/transienti).

    Returns (res, error): res=None se tutti i tentativi falliscono.
    """
    last_exc: Exception | None = None
    for attempt in range(MAP_RETRIES):
        try:
            return map_llm.generate(
                prompt=prompt, system=None, max_tokens=max_tokens,
                temperature=0.0,
            ), None
        except Exception as exc:  # noqa: BLE001 — qualsiasi errore del provider è ritentabile
            last_exc = exc
            if attempt < MAP_RETRIES - 1:
                wait = (2 ** attempt) + random.uniform(0.0, 0.25)
                logger.warning(
                    "map generate fallita (tentativo %d/%d): %s — retry fra %.1fs",
                    attempt + 1, MAP_RETRIES, exc, wait,
                )
                time.sleep(wait)
    return None, last_exc


def _map_one(
    g: SubQueryGroup, map_llm, top_k_hits: int, max_tokens: int,
) -> MiniResult:
    """Una mini su un singolo gruppo. Pura rispetto allo stato condiviso.

    Una mini non può fallire in silenzio: dopo i retry, se ancora fallisce, la
    sezione riporta un marker esplicito (MAP_FAIL_PREFIX) e finish_reason=error.
    """
    hits = g.hits[:top_k_hits]
    group_cids = [h.chunk_id for h in hits]
    chunks_block = "\n\n".join(
        f"[{h.chunk_id}]\n{_chunk_text(h)}" for h in hits
    )
    prompt = MAP_PROMPT.format(sub_query=g.sub_query, chunks=chunks_block)
    label, rubric, sort_key = _parse_article(g.sub_query)

    res, err = _generate_with_retry(map_llm, prompt, max_tokens)
    if err is not None:
        logger.error(
            "map mini FALLITA dopo %d tentativi source=%s %s: %s",
            MAP_RETRIES, g.source, label, err,
        )
        return MiniResult(
            source=g.source, sub_query=g.sub_query,
            text=f"{MAP_FAIL_PREFIX} (errore map dopo {MAP_RETRIES} tentativi: {err})",
            cited_chunk_ids=[], group_chunk_ids=group_cids,
            article_label=label, rubric=rubric, sort_key=sort_key,
            finish_reason="error", n_input_tokens=0, n_output_tokens=0,
        )

    # Troncamento: se finish=length, riprova UNA volta con cap esteso.
    truncated = False
    if getattr(res, "finish_reason", None) == "length":
        res2, err2 = _generate_with_retry(map_llm, prompt, MAP_LENGTH_RETRY_TOKENS)
        if err2 is None and res2 is not None:
            res = res2
        if getattr(res, "finish_reason", None) == "length":
            truncated = True
            logger.warning(
                "map mini ANCORA troncata dopo cap %d: source=%s %s",
                MAP_LENGTH_RETRY_TOKENS, g.source, label,
            )

    text = (getattr(res, "text", "") or "").strip()
    if has_dangling_cite(text):
        truncated = True
        logger.warning(
            "map mini con [cite: dangling (troncamento silenzioso): source=%s %s",
            g.source, label,
        )
    return MiniResult(
        source=g.source,
        sub_query=g.sub_query,
        text=text,
        cited_chunk_ids=_extract_cites(text),
        group_chunk_ids=group_cids,
        article_label=label,
        rubric=rubric,
        sort_key=sort_key,
        finish_reason=getattr(res, "finish_reason", "stop"),
        n_input_tokens=getattr(res, "n_input_tokens", 0),
        n_output_tokens=getattr(res, "n_output_tokens", 0),
        truncated=truncated,
    )


def map_groups(
    groups: list[SubQueryGroup],
    map_llm,
    top_k_hits: int = 5,
    max_tokens: int = MAP_MAX_TOKENS,
    concurrency: int = MAP_CONCURRENCY_DEFAULT,
) -> list[MiniResult]:
    """Map per-gruppo, concorrente e bounded da `concurrency` (default ~6).

    Il risultato è SEMPRE in ordine di gruppo (posizionale), mai di
    completamento: `minis[i]` corrisponde a `groups[i]`. `concurrency=1`
    equivale al sequenziale. L'ordinamento finale (source/articolo) è
    responsabilità di `assemble_report`.
    """
    n = len(groups)
    if concurrency <= 1 or n <= 1:
        return [_map_one(g, map_llm, top_k_hits, max_tokens) for g in groups]

    results: list[MiniResult | None] = [None] * n
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        fut_to_idx = {
            ex.submit(_map_one, g, map_llm, top_k_hits, max_tokens): i
            for i, g in enumerate(groups)
        }
        for fut in as_completed(fut_to_idx):
            results[fut_to_idx[fut]] = fut.result()
    return [m for m in results if m is not None]


def assemble_report(
    minis: list[MiniResult],
    norm_short_names: dict[str, str],
) -> tuple[str, int]:
    """Assembly deterministico → (testo markdown, n_sezioni). Zero LLM, no dedup."""
    by_source: "OrderedDict[str, list[MiniResult]]" = OrderedDict()
    for m in minis:
        by_source.setdefault(m.source, []).append(m)

    parts: list[str] = []
    n_sections = 0
    for source, group in by_source.items():
        parts.append(f"## {norm_short_names.get(source, source)}")
        for m in sorted(group, key=lambda x: x.sort_key):
            if m.article_label.startswith(("Art.", "Allegato")) and m.rubric:
                header = f"{m.article_label} — {m.rubric}"
            else:
                header = m.article_label
            parts.append(f"### {header}")
            parts.append(m.text)
            n_sections += 1
    return "\n\n".join(parts), n_sections


def collect_universe(
    groups: list[SubQueryGroup], top_k_hits: int = 5,
) -> RetrievalResult:
    """Universo chunk per il verifier: unione dedup di tutti i hit dei gruppi."""
    best: dict[str, RetrievalHit] = {}
    order: list[str] = []
    for g in groups:
        for h in g.hits[:top_k_hits]:
            cur = best.get(h.chunk_id)
            if cur is None:
                best[h.chunk_id] = h
                order.append(h.chunk_id)
            elif h.score > cur.score:
                best[h.chunk_id] = h
    hits = [
        RetrievalHit(
            chunk_id=best[c].chunk_id, score=best[c].score,
            payload=best[c].payload, rank=i + 1,
        )
        for i, c in enumerate(order)
    ]
    return RetrievalResult(hits)


def map_and_assemble(
    cn_result: CrossNormResult,
    map_llm,
    top_k_hits: int = 5,
    glossary_path: Path = DEFAULT_GLOSSARY_PATH,
    concurrency: int = MAP_CONCURRENCY_DEFAULT,
) -> tuple[str, RetrievalResult, list[MiniResult], int]:
    """Map (LLM, concorrente bounded) + assembly (deterministico) + universo.

    Returns: (testo_assemblato, universo_chunk, minis, n_sezioni).
    """
    short_names = load_norm_short_names(glossary_path)
    minis = map_groups(
        cn_result.groups, map_llm, top_k_hits=top_k_hits, concurrency=concurrency,
    )
    universe = collect_universe(cn_result.groups, top_k_hits=top_k_hits)
    # Normalizzazione marker deterministica (id pieni via doc_urn del gruppo).
    minis = normalize_minis(
        minis, load_norm_doc_urns(glossary_path), {h.chunk_id for h in universe},
    )
    text, n_sections = assemble_report(minis, short_names)
    return text, universe, minis, n_sections


def build_run_artifact(
    qid: str,
    cn_result: CrossNormResult,
    minis: list[MiniResult],
    assembled_text: str,
    universe: RetrievalResult,
    top_k_hits: int = 5,
) -> dict:
    """Artefatto stabile per il re-check gratuito del verifier (indipendente
    dal non-determinismo del retrieval). `minis[i]` ↔ `cn_result.groups[i]`."""
    sub_queries: "OrderedDict[str, list[str]]" = OrderedDict()
    groups_out = []
    for g, m in zip(cn_result.groups, minis):
        sub_queries.setdefault(g.source, []).append(g.sub_query)
        groups_out.append({
            "source": g.source,
            "sub_query": g.sub_query,
            "hit_chunk_ids": [h.chunk_id for h in g.hits[:top_k_hits]],
            "top_score": float(g.hits[0].score) if g.hits else 0.0,
            "mini": m.text,
            "cited_chunk_ids": m.cited_chunk_ids,
            "truncated": m.truncated,
        })
    return {
        "qid": qid,
        "detected_norms": list(cn_result.detected_norms),
        "sub_queries": sub_queries,
        "groups": groups_out,
        "assembled_text": assembled_text,
        "universe": [h.chunk_id for h in universe],
    }


def write_run_artifact(
    out_dir: Path,
    run_id: str,
    qid: str,
    cn_result: CrossNormResult,
    minis: list[MiniResult],
    assembled_text: str,
    universe: RetrievalResult,
    top_k_hits: int = 5,
) -> Path:
    """Scrive `out_dir/<run_id>/<qid>.json`. Ritorna il path scritto."""
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{qid}.json"
    artifact = build_run_artifact(
        qid, cn_result, minis, assembled_text, universe, top_k_hits=top_k_hits,
    )
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return path
