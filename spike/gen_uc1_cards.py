"""Genera le card UC1 per la revisione qualità (DoD d). Spike, LIVE.

Post-split: classify() dà SOLO classificazione (sez. 1-3 + limiti + high_risk);
gli adempimenti sono get_obligations(role). Output in spike/UC1_CARDS/:
- {slug}.{json,md} per i 6 scenari (con adempimenti deployer se high_risk);
- obligations_provider.md / obligations_deployer.md (liste canoniche grounded).
NON auto-valida il merito giuridico.

    spike/.venv/bin/python spike/gen_uc1_cards.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("gen_uc1")
log.setLevel(logging.INFO)

OUT = ROOT / "spike" / "UC1_CARDS"
COLLECTION = "italian_legal_v1_hybrid"

SCENARIOS = [
    ("q101_banca_cv", "positivo", "deployer", (
        "Una banca utilizza un sistema AI per analizzare e filtrare "
        "automaticamente i CV dei candidati e valutarli in fase di selezione "
        "del personale: è classificato ad alto rischio ai sensi dell'Allegato "
        "III dell'AI Act?"
    )),
    ("q102_edilizia_popolare", "positivo", "deployer", (
        "Un comune italiano usa un sistema AI per calcolare automaticamente il "
        "punteggio di accesso agli alloggi di edilizia popolare: è classificato "
        "ad alto rischio ai sensi dell'Allegato III?"
    )),
    ("q103_radiografie", "positivo", "deployer", (
        "Un sistema AI che analizza immagini radiografiche per supportare la "
        "diagnosi di patologie polmonari è ad alto rischio ai sensi dell'AI "
        "Act? Chi è il fornitore e chi è il deployer in un contesto ospedaliero?"
    )),
    ("neg_scorte_magazzino", "negativo", "deployer", (
        "Un'azienda manifatturiera usa un sistema AI per prevedere il "
        "fabbisogno di scorte di magazzino e ottimizzare gli ordini ai "
        "fornitori in base allo storico delle vendite."
    )),
    ("neg_antispam_interno", "negativo", "deployer", (
        "Un'azienda usa un sistema AI per filtrare le email di spam in arrivo "
        "sulle caselle di posta interne dei dipendenti."
    )),
    ("nearmiss_chatbot_cs", "near-miss", "deployer", (
        "Un'azienda usa un chatbot basato su AI per rispondere alle domande "
        "dei clienti sul servizio di assistenza e fornire informazioni sui "
        "prodotti."
    )),
    ("vietata_emozioni_lavoro", "vietata", "deployer", (
        "Un'azienda installa un sistema AI che analizza il tono della voce e "
        "le espressioni facciali dei dipendenti durante le riunioni e le "
        "telefonate per inferirne lo stato emotivo (stress, frustrazione, "
        "entusiasmo) e produrre report sul coinvolgimento del personale."
    )),
]


def build_pipeline():
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder

    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.serving import build_default_pipeline

    encoder = BgeM3Encoder.get(device="mps")
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    client = QdrantClient(host="localhost", port=6333)
    retriever = HybridRetriever(
        client=client, encoder=encoder, bm25=bm25,
        collection=COLLECTION, reranker=reranker,
    )
    return build_default_pipeline(retriever)


def _obligation_lines(obs) -> list[str]:
    L = ["| voce | titolo | descrizione | condizione | note | fonte | GDPR |",
         "|---|---|---|---|---|---|---|"]
    for o in obs:
        cond = o.condition or "sempre"
        note = o.note or ""
        gdpr = f"cfr. art. 35 GDPR ({'risolto' if o.gdpr_source_text else 'n/d'})" if o.gdpr_link else ""
        fonte = "sì" if o.source_text else "no"
        L.append(f"| {o.label} | {o.title} | {o.description} | {cond} | {note} | {fonte} | {gdpr} |")
    return L


def _esito_label(res) -> str:
    if res.card.prohibited_flag:
        return "⛔ pratica vietata (art. 5)"
    if res.high_risk_annex:
        return "alto rischio via Allegato III"
    if res.judgment.art6_1_safety_component.plausible:
        return "possibile alto rischio via art. 6(1) (componente di sicurezza, non verificabile nel corpus)"
    return "non risulta alto rischio"


def render_card_md(slug, kind, role, res, obs) -> str:
    card = res.card
    j = res.judgment
    L: list[str] = []
    L.append(f"# Card UC1 — {slug} ({kind})")
    L.append("")
    L.append(f"**Scenario**: {res.system_description}")
    L.append("")
    L.append(f"**Esito**: {_esito_label(res)} (high_risk_annex={res.high_risk_annex})")
    L.append("")
    L.append("## 0. Giudizio per-candidato (insieme chiuso)")
    L.append("")
    L.append("**Allegato III (8 punti):**")
    for a in j.annex_iii:
        mark = "**APPLIES**" if a.applies else "no"
        L.append(f"- punto {a.point}: {mark} — {a.reason} (cite: {a.cite})")
    L.append("**Art. 5 — pratiche vietate (8 candidati):**")
    for p in j.prohibited_practices:
        mark = "**APPLIES**" if p.applies else "no"
        L.append(f"- {p.practice}) {p.label}: {mark} — {p.reason} (cite: {p.cite})")
    L.append(f"- art. 6(1) componente di sicurezza: "
             f"{'plausibile' if j.art6_1_safety_component.plausible else 'no'} "
             f"— {j.art6_1_safety_component.reason}")
    L.append(f"- art. 6(3) eccezione: "
             f"{'plausibile' if j.art6_3_exception.plausible else 'no'} "
             f"— {j.art6_3_exception.reason}")
    L.append("")
    L.append("## 1. Verdetto")
    L.append("")
    L.append(card.verdict)
    L.append("")
    L.append(f"- pratica vietata (art. 5): **{card.prohibited_flag}**")
    L.append("")
    L.append("## 2. Categoria Allegato III")
    L.append("")
    L.append(card.annex_iii_category or "— nessuna area Allegato III —")
    L.append("")
    L.append("## 3. Eccezione art. 6(3)")
    L.append("")
    L.append(card.art6_3_exception or "— non applicabile (nessuna area flaggata) —")
    L.append("")
    L.append(f"## 4. Adempimenti (ruolo: {role} (predefinito) — cambia se l'hai "
             f"costruito/lo vendi)")
    L.append("")
    if res.card.prohibited_flag:
        L.append("— Adempimenti non pertinenti: la pratica è vietata dall'art. 5. —")
    elif not res.high_risk_annex:
        L.append("— non alto rischio via Allegato III: adempimenti Capo III non dovuti "
                 "su questa base —")
    else:
        L.append(f"Lista canonica del ruolo **{role}** ({len(obs)} voci), tutte mostrate "
                 f"con il tag di condizione (il DPO valuta; le condizioni non sono risolte):")
        L.append("")
        L += _obligation_lines(obs)
    L.append("")
    L.append("## 6. Limiti dichiarati")
    L.append("")
    if card.declared_limits:
        for lim in card.declared_limits:
            L.append(f"- {lim}")
    else:
        L.append("— nessun limite dichiarato —")
    L.append("")
    L.append("## 7. Disclaimer")
    L.append("")
    L.append(card.disclaimer)
    return "\n".join(L)


def render_obligations_md(role, obs) -> str:
    L = [f"# Adempimenti AI Act — ruolo {role} ({len(obs)} voci)", "",
         "Dato statico curato (verificato su EUR-Lex), grounded sul corpus via "
         "fetch_by_chunk_ids. Le condizioni NON sono risolte.", ""]
    L += _obligation_lines(obs)
    L.append("")
    L.append("## Testo-fonte (estratto) per voce")
    L.append("")
    for o in obs:
        src = (o.source_text or "")[:200].replace("\n", " ")
        L.append(f"### {o.label} — {o.title}  (`{o.source_chunk_id}`)")
        L.append(f"{src}…")
        if o.gdpr_link:
            g = (o.gdpr_source_text or "")[:200].replace("\n", " ")
            L.append(f"- **cfr. art. 35 GDPR** (`{o.gdpr_link}`): {g}…")
        L.append("")
    return "\n".join(L)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    log.info("Costruzione pipeline (reranker MPS)...")
    pipeline = build_pipeline()

    # liste canoniche per ruolo (scenario-indipendenti, grounded)
    deployer_obs = pipeline.get_obligations("deployer")
    provider_obs = pipeline.get_obligations("provider")
    (OUT / "obligations_deployer.md").write_text(
        render_obligations_md("deployer", deployer_obs), encoding="utf-8")
    (OUT / "obligations_provider.md").write_text(
        render_obligations_md("provider", provider_obs), encoding="utf-8")
    log.info("liste canoniche: deployer=%d provider=%d", len(deployer_obs), len(provider_obs))

    summary = []
    cards_by_slug = {}
    for slug, kind, role, scenario in SCENARIOS:
        log.info("=== %s (%s)", slug, kind)
        res = pipeline.classify(scenario)
        obs = pipeline.get_obligations(role) if res.obligations_applicable else []
        (OUT / f"{slug}.json").write_text(
            json.dumps({"kind": kind, "role": role,
                        "obligations": [o.to_dict() for o in obs], **res.to_dict()},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        (OUT / f"{slug}.md").write_text(
            render_card_md(slug, kind, role, res, obs), encoding="utf-8")
        c = res.card
        log.info("[%s] high_risk_annex=%s art6_1=%s allegato_iii=%s vietata=%s n_adempimenti=%d",
                 slug, res.high_risk_annex, res.judgment.art6_1_safety_component.plausible,
                 c.annex_iii_category is not None, c.prohibited_flag, len(obs))
        summary.append((slug, kind, res, len(obs)))
        cards_by_slug[slug] = obs

    # prova: q101 e q102 (entrambi deployer high_risk) → liste IDENTICHE
    def _sig(obs):
        return [(o.label, o.condition) for o in obs]
    q101, q102 = cards_by_slug.get("q101_banca_cv", []), cards_by_slug.get("q102_edilizia_popolare", [])
    identical = _sig(q101) == _sig(q102) and len(q101) == 12
    log.info("q101==q102 adempimenti deployer identici (12 voci): %s", identical)

    idx = ["# UC1_CARDS — indice revisione qualità", "",
           f"q101==q102 adempimenti deployer identici: **{identical}** "
           f"(Art. 10 NON tra i deployer: "
           f"{'Art. 10' not in {o.label for o in deployer_obs}})", "",
           "| slug | tipo | esito | high_risk_annex | Allegato III | vietata | n_adempimenti |",
           "|---|---|---|---|---|---|---|"]
    for slug, kind, res, nob in summary:
        cat = "sì" if res.card.annex_iii_category else "no"
        idx.append(f"| {slug} | {kind} | {_esito_label(res)} | {res.high_risk_annex} | "
                   f"{cat} | {res.card.prohibited_flag} | {nob} |")
    idx += ["", "Liste canoniche: [obligations_provider.md](obligations_provider.md) "
            "(20 voci) · [obligations_deployer.md](obligations_deployer.md) (12 voci)."]
    (OUT / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    log.info("Card scritte in %s", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
