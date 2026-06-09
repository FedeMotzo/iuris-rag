"""Giudizio di classificazione a INSIEME CHIUSO (single-norm AI Act).

Step di giudizio per-candidato su un set FISSO di norme di classificazione
(Allegato III punti 1-8, art. 5, art. 6), caricato per chunk_id da Qdrant — non
recuperato semanticamente. Un solo prompt all'LLM principale (Sonnet), output
JSON, poi validazione deterministica per appartenenza al set fisso (nessun
riferimento inventato).

Questo SOSTITUISCE l'inferenza del verdetto dalle citazioni del dossier (che
forzava punti Allegato III per scenari non pertinenti, vedi Step 3).
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from .models import (
    AnnexJudgment,
    ClassificationJudgment,
    PlausibilityJudgment,
    ProhibitedPracticeJudgment,
)

if TYPE_CHECKING:
    from core.hybrid_retriever.types import RetrievalResult

logger = logging.getLogger(__name__)

# Set fisso delle norme di classificazione AI Act (chunk_id confermati in Qdrant,
# vedi spike/CORPUS_INGESTION_AUDIT.md). Punto unico di verità per l'intake.
_AI_ACT_URN = "eli/reg/2024/1689/oj"
ANNEX_III_POINT_IDS = [f"{_AI_ACT_URN}__annex_III__point_{n}" for n in range(1, 9)]
ART5_IDS = [
    f"{_AI_ACT_URN}__art_5__paras_1_3",
    f"{_AI_ACT_URN}__art_5__paras_4_8",
]
ART6_ID = f"{_AI_ACT_URN}__art_6"
FIXED_SET_CHUNK_IDS = ANNEX_III_POINT_IDS + ART5_IDS + [ART6_ID]

_CHUNK_TEXT_CAP = 1800
_NUM_ANNEX_POINTS = 8

# Pratiche vietate dell'art. 5, decomposte in candidati per-pratica (come gli 8
# punti dell'Allegato III). Etichette verificate sul testo dell'art. 5 nel set
# fisso. La lettera è il riferimento all'art. 5(1)(a..h).
PROHIBITED_PRACTICES: list[tuple[str, str]] = [
    ("a", "Tecniche subliminali/manipolative/ingannevoli che distorcono "
          "materialmente il comportamento causando danno significativo"),
    ("b", "Sfruttamento di vulnerabilità (età, disabilità, situazione "
          "socio-economica) per distorcere il comportamento causando danno"),
    ("c", "Social scoring che porta a trattamento pregiudizievole/sfavorevole"),
    ("d", "Valutazione del rischio di reato basata unicamente su "
          "profilazione/tratti di personalità (polizia predittiva individuale)"),
    ("e", "Creazione/ampliamento di banche dati di riconoscimento facciale "
          "tramite scraping non mirato di immagini"),
    ("f", "Inferenza delle emozioni sul luogo di lavoro e negli istituti di "
          "istruzione (salvo motivi medici/sicurezza)"),
    ("g", "Categorizzazione biometrica per inferire attributi sensibili (razza, "
          "opinioni politiche, appartenenza sindacale, convinzioni "
          "religiose/filosofiche, vita sessuale, orientamento)"),
    ("h", "Identificazione biometrica remota in tempo reale in spazi pubblici a "
          "fini di contrasto (salvo eccezioni)"),
]
_PRACTICE_LABELS = {k: v for k, v in PROHIBITED_PRACTICES}
_NUM_PRACTICES = len(PROHIBITED_PRACTICES)
_PRACTICES_BULLETS = "\n".join(f"  {k}) {v}" for k, v in PROHIBITED_PRACTICES)

JUDGE_PROMPT = """Sei un assistente che supporta la classificazione di un sistema di IA ai sensi del Regolamento UE 2024/1689 (AI Act). Ti vengono forniti la descrizione di un sistema e i testi normativi rilevanti per la classificazione (ciascuno preceduto dal suo identificativo fra parentesi quadre). Esprimi, candidato per candidato, una decisione motivata.

Descrizione del sistema:
{system_description}

Testi normativi (ognuno preceduto dal suo identificativo [ID]):
{chunks}

Compito:
- Per CIASCUNO degli 8 punti dell'Allegato III: indica applies true/false con un motivo breve. Sii CONSERVATIVO: "false" è la risposta corretta e attesa quando il sistema non rientra chiaramente in quel punto. NON forzare un punto solo perché tematicamente vicino o perché il testo è disponibile. "Nessun punto applicabile" è un esito pienamente valido e frequente.
- Per CIASCUNA delle 8 pratiche vietate dell'art. 5 (elencate sotto, a..h): indica applies true/false con un motivo breve. Valuta OGNI pratica singolarmente — non fermarti alle più note (manipolazione, biometria): considera anche social scoring, polizia predittiva, scraping facciale, e in particolare l'INFERENZA DELLE EMOZIONI sul luogo di lavoro o negli istituti di istruzione (pratica f). Sii conservativo: applies true solo se il sistema integra CHIARAMENTE quella specifica pratica.
  Pratiche vietate (art. 5):
{practices}
- art6_1_safety_component: plausible true se il sistema potrebbe essere ad alto rischio come componente di sicurezza di un prodotto regolato da normativa di armonizzazione settoriale (es. dispositivo medico), anche se quella normativa non è tra i testi forniti.
- art6_3_exception: plausible true se è ipotizzabile la deroga dell'art. 6(3) (compito procedurale ristretto; non sostituisce né influenza materialmente una decisione umana; meramente preparatorio).
- Quando applies=true, "cite" DEVE essere l'identificativo [ID] esatto del testo che fonda la decisione, copiato dai testi forniti. Quando applies=false, "cite" = null.

Rispondi SOLO con un oggetto JSON valido (nessun testo prima o dopo), con questo schema ESATTO: tutti gli 8 punti Allegato III (1-8) e tutte le 8 pratiche vietate (a-h).
{{
  "annex_iii": [
    {{"point": 1, "applies": false, "reason": "...", "cite": null}},
    {{"point": 2, "applies": false, "reason": "...", "cite": null}},
    {{"point": 3, "applies": false, "reason": "...", "cite": null}},
    {{"point": 4, "applies": false, "reason": "...", "cite": null}},
    {{"point": 5, "applies": false, "reason": "...", "cite": null}},
    {{"point": 6, "applies": false, "reason": "...", "cite": null}},
    {{"point": 7, "applies": false, "reason": "...", "cite": null}},
    {{"point": 8, "applies": false, "reason": "...", "cite": null}}
  ],
  "prohibited_practices": [
    {{"practice": "a", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "b", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "c", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "d", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "e", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "f", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "g", "applies": false, "reason": "...", "cite": null}},
    {{"practice": "h", "applies": false, "reason": "...", "cite": null}}
  ],
  "art6_1_safety_component": {{"plausible": false, "reason": "..."}},
  "art6_3_exception": {{"plausible": false, "reason": "..."}}
}}"""

JUDGE_MAX_TOKENS = 2000


def _chunk_block(fixed_chunks: "RetrievalResult") -> str:
    blocks: list[str] = []
    for h in fixed_chunks:
        txt = (h.payload or {}).get("text", "") or ""
        if len(txt) > _CHUNK_TEXT_CAP:
            txt = txt[:_CHUNK_TEXT_CAP] + "…"
        blocks.append(f"[{h.chunk_id}]\n{txt}")
    return "\n\n".join(blocks)


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s)
    return s.strip()


def _extract_json_object(text: str) -> str:
    """Isola il primo oggetto JSON bilanciato (tollera testo prima/dopo)."""
    s = _strip_fences(text)
    start = s.find("{")
    if start == -1:
        return s
    depth = 0
    for i in range(start, len(s)):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return s[start:]


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "sì", "si")
    return bool(v)


def _as_str(v: Any) -> str:
    return v if isinstance(v, str) else ("" if v is None else str(v))


def _clean_cite(v: Any) -> str | None:
    if not isinstance(v, str):
        return None
    c = v.strip().strip("[]").strip()
    return c or None


def parse_judgment(raw_text: str) -> ClassificationJudgment:
    """Parsa l'output LLM (JSON, anche sporco) in ClassificationJudgment.

    Robusto: rimuove code fence, isola il primo oggetto JSON bilanciato,
    normalizza gli 8 punti Allegato III (riempie i mancanti con applies=false).
    NON valida l'appartenenza dei cite: vedi `validate_judgment`.
    """
    obj = json.loads(_extract_json_object(raw_text))
    if not isinstance(obj, dict):
        raise ValueError(f"giudizio: atteso oggetto JSON, trovato {type(obj).__name__}")

    by_point: dict[int, AnnexJudgment] = {}
    for item in obj.get("annex_iii") or []:
        if not isinstance(item, dict):
            continue
        try:
            point = int(item.get("point"))
        except (TypeError, ValueError):
            continue
        if 1 <= point <= _NUM_ANNEX_POINTS:
            by_point[point] = AnnexJudgment(
                point=point,
                applies=_as_bool(item.get("applies")),
                reason=_as_str(item.get("reason")),
                cite=_clean_cite(item.get("cite")),
            )
    annex = [
        by_point.get(n, AnnexJudgment(point=n, applies=False, reason="", cite=None))
        for n in range(1, _NUM_ANNEX_POINTS + 1)
    ]

    by_practice: dict[str, ProhibitedPracticeJudgment] = {}
    for item in obj.get("prohibited_practices") or []:
        if not isinstance(item, dict):
            continue
        key = _as_str(item.get("practice")).strip().lower()
        if key in _PRACTICE_LABELS:
            by_practice[key] = ProhibitedPracticeJudgment(
                practice=key,
                label=_PRACTICE_LABELS[key],
                applies=_as_bool(item.get("applies")),
                reason=_as_str(item.get("reason")),
                cite=_clean_cite(item.get("cite")),
            )
    practices = [
        by_practice.get(k, ProhibitedPracticeJudgment(
            practice=k, label=v, applies=False, reason="", cite=None))
        for k, v in PROHIBITED_PRACTICES
    ]

    def _plaus(key: str) -> PlausibilityJudgment:
        raw = obj.get(key) or {}
        return PlausibilityJudgment(
            plausible=_as_bool(raw.get("plausible")),
            reason=_as_str(raw.get("reason")),
        )

    return ClassificationJudgment(
        annex_iii=annex,
        prohibited_practices=practices,
        art6_1_safety_component=_plaus("art6_1_safety_component"),
        art6_3_exception=_plaus("art6_3_exception"),
    )


def validate_judgment(
    judgment: ClassificationJudgment, valid_ids: set[str],
) -> ClassificationJudgment:
    """Verifica deterministica per APPARTENENZA: ogni applies=true con cite non
    appartenente al set fisso viene declassato a applies=false (nessun
    riferimento inventato). Muta in place e ritorna lo stesso oggetto.
    """
    for a in judgment.annex_iii:
        if a.applies and (a.cite is None or a.cite not in valid_ids):
            logger.info("giudizio: annex point %d scartato (cite invalido: %r)",
                        a.point, a.cite)
            a.applies = False
    for p in judgment.prohibited_practices:
        if p.applies and (p.cite is None or p.cite not in valid_ids):
            logger.info("giudizio: pratica vietata %s scartata (cite invalido: %r)",
                        p.practice, p.cite)
            p.applies = False
    return judgment


def judge_classification(
    system_description: str,
    fixed_chunks: "RetrievalResult",
    llm: Any,
    max_tokens: int = JUDGE_MAX_TOKENS,
) -> ClassificationJudgment:
    """Un solo prompt di giudizio (LLM principale) + parse + validazione."""
    prompt = JUDGE_PROMPT.format(
        system_description=system_description,
        chunks=_chunk_block(fixed_chunks),
        practices=_PRACTICES_BULLETS,
    )
    res = llm.generate(prompt=prompt, system=None, max_tokens=max_tokens, temperature=0.0)
    text = getattr(res, "text", None)
    if text is None:
        raise ValueError(f"giudizio: llm senza attributo `text`: {res!r}")
    judgment = parse_judgment(text)
    valid_ids = {h.chunk_id for h in fixed_chunks}
    return validate_judgment(judgment, valid_ids)
