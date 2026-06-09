"""UC1 — FE Streamlit: classificazione AI Act live + adempimenti progressivi.

Entry SEPARATO dall'app render-only cross-norma (app/streamlit_app.py), che
resta intatta. Nessuna logica di classificazione qui: solo chiamate a
`pipeline.classify()` e `pipeline.get_obligations()`.

Avvio:
    streamlit run app/uc1_classification_app.py
Prerequisiti: Qdrant su localhost:6333 (collection italian_legal_v1_hybrid) e
ANTHROPIC_API_KEY nel .env.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import streamlit as st  # noqa: E402

COLLECTION = "italian_legal_v1_hybrid"

ROLE_LABELS = {
    "deployer": "Lo uso (deployer)",
    "provider": "L'ho costruito / lo vendo (provider)",
}


# --------------------------------------------------------------------------- #
# Pipeline (init UNA volta sola: il path UC1 usa fetch_by_chunk_ids + LLM, niente
# embedding/rerank → retriever leggero con encoder/bm25/reranker = None).
# --------------------------------------------------------------------------- #

def build_uc1_pipeline():
    """Costruisce la pipeline UC1 (no streamlit → riusabile dallo smoke)."""
    from qdrant_client import QdrantClient

    from core.hybrid_retriever import HybridRetriever
    from core.serving import build_default_pipeline

    client = QdrantClient(host="localhost", port=6333)
    retriever = HybridRetriever(
        client=client, encoder=None, bm25=None,
        collection=COLLECTION, reranker=None,
    )
    return build_default_pipeline(retriever)


@st.cache_resource(show_spinner=False)
def get_pipeline():
    return build_uc1_pipeline()


# --------------------------------------------------------------------------- #
# Rendering (dai dati strutturati; nessuna logica di classificazione)
# --------------------------------------------------------------------------- #

def _esito(res) -> tuple[str, str]:
    """(label, livello streamlit) per lo stato — vietata ha priorità su tutto."""
    if res.card.prohibited_flag:
        return "⛔ Pratica vietata (art. 5)", "error"
    if res.high_risk_annex:
        return "🔴 Alto rischio via Allegato III", "error"
    if res.judgment.art6_1_safety_component.plausible:
        return ("🟠 Possibile alto rischio via art. 6(1) (componente di "
                "sicurezza, non verificabile nel corpus)", "warning")
    return "🟢 Non risulta alto rischio", "success"


def render_card(res) -> None:
    card = res.card
    label, level = _esito(res)
    getattr(st, level)(f"**Esito**: {label}")

    st.subheader("1. Verdetto")
    if card.prohibited_flag:
        st.error(card.verdict)
    else:
        st.markdown(card.verdict)

    st.subheader("2. Categoria Allegato III")
    st.markdown(card.annex_iii_category or "— nessuna area Allegato III —")

    st.subheader("3. Eccezione art. 6(3)")
    st.markdown(card.art6_3_exception or "— non applicabile (nessuna area flaggata) —")

    st.subheader("6. Limiti dichiarati")
    if card.declared_limits:
        for lim in card.declared_limits:
            st.markdown(f"- {lim}")
    else:
        st.markdown("— nessun limite dichiarato —")

    st.subheader("7. Disclaimer")
    st.caption(card.disclaimer)

    with st.expander("Dettaglio giudizio (sez. 0 — per-candidato)", expanded=False):
        j = res.judgment
        st.markdown("**Allegato III (8 punti):**")
        for a in j.annex_iii:
            mark = "✅ **APPLIES**" if a.applies else "—"
            cite = f"  (`{a.cite}`)" if a.cite else ""
            st.markdown(f"- punto {a.point}: {mark} — {a.reason}{cite}")
        st.markdown("**Art. 5 — pratiche vietate (8 candidati):**")
        for p in j.prohibited_practices:
            mark = "⛔ **APPLIES**" if p.applies else "—"
            cite = f"  (`{p.cite}`)" if p.cite else ""
            st.markdown(f"- {p.practice}) {p.label}: {mark} — {p.reason}{cite}")
        st.markdown(
            f"- **art. 6(1) componente di sicurezza**: "
            f"{'plausibile' if j.art6_1_safety_component.plausible else 'no'} "
            f"— {j.art6_1_safety_component.reason}"
        )
        st.markdown(
            f"- **art. 6(3) eccezione**: "
            f"{'plausibile' if j.art6_3_exception.plausible else 'no'} "
            f"— {j.art6_3_exception.reason}"
        )


def _obligations_table_md(obs) -> str:
    lines = ["| voce | titolo | descrizione | condizione | note | GDPR |",
             "|---|---|---|---|---|---|"]
    for o in obs:
        gdpr = "cfr. art. 35 GDPR" if o.gdpr_link else ""
        cond = o.condition or "sempre"
        note = (o.note or "").replace("|", "/")
        lines.append(
            f"| {o.label} | {o.title} | {o.description} | {cond} | {note} | {gdpr} |"
        )
    return "\n".join(lines)


def render_obligations(obs, role: str, high_risk_annex: bool) -> None:
    st.markdown(
        f"**Ruolo**: {ROLE_LABELS.get(role, role)} — **{len(obs)} voci**. "
        "Le condizioni NON sono risolte: tutte le voci sono mostrate con il tag, "
        "la valutazione spetta al DPO."
    )
    if not high_risk_annex:
        st.info(
            "Il sistema non risulta alto rischio via Allegato III: questa lista è "
            "mostrata a titolo di riferimento per il ruolo selezionato."
        )
    st.markdown(_obligations_table_md(obs))

    st.markdown("**Testo-fonte per voce** (id lookup sul corpus):")
    for o in obs:
        with st.expander(f"{o.label} — {o.title}  ·  {o.source_chunk_id}"):
            st.markdown(o.source_text or "_testo-fonte non disponibile_")
            if o.gdpr_link:
                st.markdown(f"**cfr. art. 35 GDPR** (puntatore statico · `{o.gdpr_link}`):")
                st.markdown(o.gdpr_source_text or "_testo GDPR non disponibile_")


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

def main() -> None:
    st.set_page_config(page_title="UC1 — Classificazione AI Act", layout="wide")
    st.title("UC1 — Classificazione di un sistema AI (AI Act)")
    st.caption("Evidenza a supporto della classificazione del DPO — non un verdetto vincolante.")

    desc = st.text_area(
        "Descrivi il sistema AI",
        height=150,
        placeholder="Es. Un comune usa un sistema AI per calcolare il punteggio di "
                    "accesso agli alloggi di edilizia popolare…",
        key="uc1_desc_input",
    )

    if st.button("Classifica", type="primary"):
        if not desc.strip():
            st.warning("Inserisci una descrizione del sistema.")
        else:
            try:
                pipeline = get_pipeline()
                with st.spinner("Classificazione in corso (giudizio LLM)…"):
                    res = pipeline.classify(desc.strip())
                st.session_state["uc1_result"] = res
                st.session_state["uc1_desc"] = desc.strip()
                # reset della rivelazione adempimenti al nuovo classify
                for k in ("uc1_show_selector", "uc1_obligations", "uc1_obl_role"):
                    st.session_state.pop(k, None)
            except Exception as exc:  # noqa: BLE001
                st.session_state.pop("uc1_result", None)
                st.error(
                    f"Errore durante la classificazione: {exc}\n\n"
                    "Verifica che Qdrant sia attivo su localhost:6333 e che "
                    "ANTHROPIC_API_KEY sia impostata nel .env."
                )

    res = st.session_state.get("uc1_result")
    if res is None:
        return

    st.divider()
    st.caption(f"Sistema valutato: _{st.session_state.get('uc1_desc', '')}_")
    render_card(res)

    # ---- Adempimenti: rivelazione progressiva (NON ri-esegue classify) ----
    st.divider()
    st.header("Adempimenti")

    if res.card.prohibited_flag:
        st.error("Adempimenti non pertinenti: la pratica è vietata dall'art. 5.")
        return
    if not res.high_risk_annex:
        st.info("Adempimenti Capo III non dovuti su questa base (non alto rischio "
                "via Allegato III).")
        return

    if st.button("Mostra adempimenti"):
        st.session_state["uc1_show_selector"] = True

    if st.session_state.get("uc1_show_selector"):
        role = st.radio(
            "Qual è il tuo ruolo rispetto al sistema?",
            options=("deployer", "provider"),
            format_func=lambda r: ROLE_LABELS[r],
            horizontal=True,
            key="uc1_role_radio",
        )
        if st.button("Mostra", key="uc1_show_obl"):
            try:
                pipeline = get_pipeline()
                with st.spinner("Carico gli adempimenti…"):
                    obs = pipeline.get_obligations(role)
                st.session_state["uc1_obligations"] = obs
                st.session_state["uc1_obl_role"] = role
            except Exception as exc:  # noqa: BLE001
                st.error(f"Errore nel caricamento degli adempimenti: {exc}")

        obs = st.session_state.get("uc1_obligations")
        shown_role = st.session_state.get("uc1_obl_role")
        if obs is not None:
            if shown_role != role:
                st.info("Ruolo cambiato: clicca «Mostra» per aggiornare la lista.")
            render_obligations(obs, shown_role, res.high_risk_annex)


if __name__ == "__main__":
    main()
