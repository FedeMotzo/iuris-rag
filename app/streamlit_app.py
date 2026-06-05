"""Cross-Norm Presentation Viewer — render-only sui 12 artefatti congelati."""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st

from core.citation_renderer import norm_label, render_cites_default

_PRES_DIR = pathlib.Path(__file__).parent.parent / "spike" / "runs" / "paid_subset_v1"
_BENCHMARK = pathlib.Path(__file__).parent.parent / "data" / "benchmark" / "gold_answers_v2.json"


@st.cache_data
def _load_questions() -> dict[str, str]:
    """Mappa qid → testo domanda originale."""
    items = json.loads(_BENCHMARK.read_text(encoding="utf-8"))
    return {item["qid"]: item["question"] for item in items}


@st.cache_data
def _load_all() -> dict[str, tuple[dict, dict]]:
    """Carica presentation + raw JSON per ogni query."""
    result: dict[str, tuple[dict, dict]] = {}
    for pres_path in sorted(_PRES_DIR.glob("*.presentation.json")):
        name = pres_path.stem.replace(".presentation", "")
        pres = json.loads(pres_path.read_text(encoding="utf-8"))
        raw_path = _PRES_DIR / f"{name}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
        result[name] = (pres, raw)
    return result


def _sub_queries_for_article(art: dict, norm_id: str, groups: list[dict]) -> list[str]:
    art_cites = set(art["cites"])
    seen: set[str] = set()
    out: list[str] = []
    for g in groups:
        if g["source"] == norm_id and art_cites & set(g["cited_chunk_ids"]):
            sq = g["sub_query"]
            if sq not in seen:
                seen.add(sq)
                out.append(sq)
    return out


def _render_article(art: dict, sub_queries: list[str]) -> None:
    st.markdown(f"**{art['article']} — {art['rubric']}**")
    if sub_queries:
        for sq in sub_queries:
            st.caption(f"🔍 {sq}")
    st.markdown(render_cites_default(art["body"]))
    badges: list[str] = []
    if art["verified"]:
        badges.append(":green[✓ verificato]")
    else:
        badges.append(":red[⚠ non verificato]")
    if art["truncated"]:
        badges.append(":orange[⚠ troncato]")
    st.markdown("  ".join(badges))


def main() -> None:
    st.set_page_config(page_title="Cross-Norm Viewer", layout="wide")
    st.title("Cross-Norm Presentation Viewer")

    all_data = _load_all()
    questions = _load_questions()
    query_names = sorted(all_data.keys(), key=lambda q: int(q[1:]))

    selected = st.selectbox(
        "Query",
        query_names,
        format_func=lambda q: f"{q} — {questions.get(q, q)}",
    )

    pres, raw = all_data[selected]
    groups: list[dict] = raw.get("groups", [])

    st.markdown(pres["orientation"])

    for norm in pres["norms"]:
        articles = norm["articles"]
        label = f"{norm_label(norm['short_name'])} · {len(articles)} articoli"
        with st.expander(label, expanded=False):
            for art in articles:
                sub_queries = _sub_queries_for_article(art, norm["norm_id"], groups)
                _render_article(art, sub_queries)
                st.divider()


if __name__ == "__main__":
    main()
