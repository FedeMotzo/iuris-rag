"""Test map→assembly cross-norma v1.2 step 3 — concorrenza + persistenza.

Zero LLM: stub `_StubMapLLM` ritorna una mini canned per sub-query (cita il
primo chunk del prompt). Verifica:
(a) concorrenza ≡ sequenziale (mapping gruppo→mini posizionale);
(b) ordine assembly per source/articolo, indipendente dall'ordine di completamento;
(c) artefatto di persistenza scritto come da schema;
(d) il bound limita la concorrenza.
"""

from __future__ import annotations

import json
import re
import threading
import time

from core.cross_norm.map_assemble import (
    assemble_report,
    build_run_artifact,
    close_unclosed_cites,
    collect_universe,
    map_groups,
    normalize_mini_text,
    write_run_artifact,
)
from core.cross_norm.retriever import CrossNormResult, SubQueryGroup
from core.hybrid_retriever.types import RetrievalHit

_FIRST_BRACKET = re.compile(r"\[([^\]\n]+)\]")


class _Res:
    def __init__(self, text: str) -> None:
        self.text = text
        self.n_input_tokens = 10
        self.n_output_tokens = 5
        self.finish_reason = "stop"


class _StubMapLLM:
    """Stub deterministico: la mini cita il PRIMO chunk_id del prompt.

    Traccia la concorrenza di picco (con `delay` per forzare overlap).
    """

    provider_name = "stub"
    model_name = "stub-map"

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self._lock = threading.Lock()
        self._concurrent = 0
        self.peak = 0
        self.n_calls = 0

    def generate(self, prompt, system=None, max_tokens=600, temperature=0.0):
        with self._lock:
            self._concurrent += 1
            self.peak = max(self.peak, self._concurrent)
            self.n_calls += 1
        try:
            if self.delay:
                time.sleep(self.delay)
            cid = _FIRST_BRACKET.search(prompt).group(1)
            return _Res(f"Mini canned. [cite:{cid}]")
        finally:
            with self._lock:
                self._concurrent -= 1


# ----------------------------------------------------------- helpers

def _hit(cid: str, score: float) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=cid, score=score,
        payload={"chunk_id": cid, "text": f"testo di {cid}"}, rank=1,
    )


def _group(source: str, sub_query: str, cids: list[str]) -> SubQueryGroup:
    return SubQueryGroup(
        sub_query=sub_query, source=source,
        hits=[_hit(c, 1.0 - i * 0.1) for i, c in enumerate(cids)],
    )


def _sample_groups() -> list[SubQueryGroup]:
    # Ordine VOLUTAMENTE non per source/articolo, per testare il riordino.
    return [
        _group("ai_act", "FRIA ex art. 27 AI Act: obblighi.", ["ai__art_27"]),
        _group("gdpr", "Categorie particolari ex art. 9 GDPR: deroghe.", ["gdpr__art_9"]),
        _group("ai_act", "Classificazione ex art. 6 AI Act: criteri.", ["ai__art_6"]),
        _group("gdpr", "DPIA ex art. 35 GDPR: obbligatorietà.", ["gdpr__art_35"]),
        _group("gdpr", "Sicurezza ex art. 32 GDPR: misure.", ["gdpr__art_32"]),
        _group("ai_act", "Deployer ex art. 26 AI Act: obblighi.", ["ai__art_26"]),
    ]


_SHORT = {"gdpr": "GDPR", "ai_act": "AI Act"}


# ----------------------------------------------------------- (a) concorrenza ≡ seq

def test_concurrent_equals_sequential_mapping() -> None:
    groups = _sample_groups()
    minis_seq = map_groups(groups, _StubMapLLM(), concurrency=1)
    minis_con = map_groups(groups, _StubMapLLM(delay=0.01), concurrency=6)

    assert len(minis_seq) == len(minis_con) == len(groups)
    # mapping posizionale gruppo→mini preservato in entrambi
    for i, g in enumerate(groups):
        assert minis_seq[i].sub_query == g.sub_query
        assert minis_con[i].sub_query == g.sub_query
    # stesso identico mapping (testo, source, cite, sort_key)
    for a, b in zip(minis_seq, minis_con):
        assert (a.source, a.text, a.cited_chunk_ids, a.sort_key) == (
            b.source, b.text, b.cited_chunk_ids, b.sort_key
        )


# ----------------------------------------------------------- (b) ordine assembly

def test_assembly_order_by_source_then_article() -> None:
    groups = _sample_groups()
    # delay alto + bound alto → ordine di completamento ≠ ordine di gruppo
    minis = map_groups(groups, _StubMapLLM(delay=0.01), concurrency=6)
    text, n_sections = assemble_report(minis, _SHORT)

    assert n_sections == 6
    headers = [ln for ln in text.splitlines() if ln.startswith(("## ", "### "))]
    assert headers == [
        "## AI Act",          # ai_act è la prima source incontrata
        "### Art. 6 — Classificazione",
        "### Art. 26 — Deployer",
        "### Art. 27 — FRIA",
        "## GDPR",
        "### Art. 9 — Categorie particolari",
        "### Art. 32 — Sicurezza",
        "### Art. 35 — DPIA",
    ]


def test_assembly_deterministic_across_runs() -> None:
    groups = _sample_groups()
    t1, _ = assemble_report(map_groups(groups, _StubMapLLM(delay=0.005), concurrency=6), _SHORT)
    t2, _ = assemble_report(map_groups(groups, _StubMapLLM(delay=0.005), concurrency=6), _SHORT)
    assert t1 == t2


# ----------------------------------------------------------- (c) persistenza

def test_persistence_artifact_schema(tmp_path) -> None:
    groups = _sample_groups()
    cn = CrossNormResult(query="Q", detected_norms=["gdpr", "ai_act"], groups=groups)
    minis = map_groups(groups, _StubMapLLM(), concurrency=1)
    text, _ = assemble_report(minis, _SHORT)
    universe = collect_universe(groups)

    path = write_run_artifact(tmp_path, "run42", "Q70", cn, minis, text, universe)
    assert path == tmp_path / "run42" / "Q70.json"
    assert path.is_file()

    art = json.loads(path.read_text(encoding="utf-8"))
    assert art["qid"] == "Q70"
    assert art["detected_norms"] == ["gdpr", "ai_act"]
    assert set(art["sub_queries"].keys()) == {"gdpr", "ai_act"}
    assert len(art["groups"]) == len(groups)
    for go, g in zip(art["groups"], groups):
        assert set(go.keys()) == {
            "source", "sub_query", "hit_chunk_ids", "top_score", "mini",
            "cited_chunk_ids", "truncated",
        }
        assert go["source"] == g.source
        assert go["hit_chunk_ids"] == [h.chunk_id for h in g.hits]
    assert art["assembled_text"] == text
    assert set(art["universe"]) == {h.chunk_id for g in groups for h in g.hits}


def test_build_run_artifact_matches_write(tmp_path) -> None:
    groups = _sample_groups()
    cn = CrossNormResult(query="Q", detected_norms=["gdpr", "ai_act"], groups=groups)
    minis = map_groups(groups, _StubMapLLM(), concurrency=1)
    text, _ = assemble_report(minis, _SHORT)
    universe = collect_universe(groups)
    art = build_run_artifact("Q70", cn, minis, text, universe)
    assert art["groups"][0]["mini"].startswith("Mini canned.")


# ----------------------------------------------------------- (d) bound concorrenza

def test_semaphore_bounds_concurrency() -> None:
    groups = _sample_groups() * 3  # 18 gruppi
    stub = _StubMapLLM(delay=0.02)
    map_groups(groups, stub, concurrency=3)
    assert stub.n_calls == len(groups)
    assert stub.peak <= 3
    assert stub.peak >= 2  # con 18 gruppi e delay, il pool satura il bound


def test_bound_one_is_sequential() -> None:
    groups = _sample_groups()
    stub = _StubMapLLM(delay=0.01)
    map_groups(groups, stub, concurrency=1)
    assert stub.peak == 1


# ----------------------------------------------------------- (PARTE 1) retry/fail

class _FlakyLLM:
    """Fallisce `fail_times` volte poi riesce (test del retry)."""

    provider_name = "stub"
    model_name = "flaky"

    def __init__(self, fail_times: int, always: bool = False) -> None:
        self.fail_times = fail_times
        self.always = always
        self.calls = 0
        self._lock = threading.Lock()

    def generate(self, prompt, system=None, max_tokens=600, temperature=0.0):
        with self._lock:
            self.calls += 1
            n = self.calls
        if self.always or n <= self.fail_times:
            raise RuntimeError("429 simulated overloaded")
        cid = _FIRST_BRACKET.search(prompt).group(1)
        return _Res(f"Recuperata. [cite:{cid}]")


def test_retry_recovers_after_transient(monkeypatch) -> None:
    monkeypatch.setattr("core.cross_norm.map_assemble.time.sleep", lambda *_: None)
    groups = [_group("gdpr", "DPIA ex art. 35 GDPR: x.", ["gdpr__art_35"])]
    llm = _FlakyLLM(fail_times=2)  # 2 fail, 3° tentativo ok
    minis = map_groups(groups, llm, concurrency=1)
    assert llm.calls == 3
    assert minis[0].finish_reason == "stop"
    assert minis[0].cited_chunk_ids == ["gdpr__art_35"]


def test_persistent_failure_marked_not_silent(monkeypatch) -> None:
    monkeypatch.setattr("core.cross_norm.map_assemble.time.sleep", lambda *_: None)
    from core.cross_norm.map_assemble import MAP_FAIL_PREFIX
    groups = [_group("gdpr", "DPIA ex art. 35 GDPR: x.", ["gdpr__art_35"])]
    llm = _FlakyLLM(fail_times=0, always=True)
    minis = map_groups(groups, llm, concurrency=1)
    assert minis[0].finish_reason == "error"
    assert minis[0].text.startswith(MAP_FAIL_PREFIX)
    assert minis[0].cited_chunk_ids == []


# ----------------------------------------------------------- (PARTE 1) normalizzazione marker

_AI = "eli/reg/2024/1689/oj"


def test_normalize_abbreviated_to_full() -> None:
    uni = {f"{_AI}__art_6", f"{_AI}__art_27"}
    out = normalize_mini_text("Classificazione [cite:art_6] e FRIA [cite:art_27].", _AI, uni)
    assert out == f"Classificazione [cite:{_AI}__art_6] e FRIA [cite:{_AI}__art_27]."


def test_normalize_strips_descriptive_tail() -> None:
    uni = {f"{_AI}__art_12"}
    out = normalize_mini_text("Log [cite:eli/reg/2024/1689/oj__art_12, paragrafo 1].", _AI, uni)
    assert out == f"Log [cite:{_AI}__art_12]."


def test_normalize_splits_multicite() -> None:
    uni = {f"{_AI}__art_12", f"{_AI}__art_19"}
    out = normalize_mini_text(
        f"Vedi [cite:{_AI}__art_12; cite:{_AI}__art_19].", _AI, uni)
    assert out == f"Vedi [cite:{_AI}__art_12] [cite:{_AI}__art_19]."


def test_normalize_partial_actnum_form() -> None:
    d231 = "akn/it/act/decreto_legislativo/stato/2001-06-08/231"
    uni = {f"{d231}__art_25-octies"}
    out = normalize_mini_text("Sanzioni [cite:231__art_25-octies].", d231, uni)
    assert out == f"Sanzioni [cite:{d231}__art_25-octies]."


def test_normalize_abbrev_not_in_universe_stays_unverified() -> None:
    """Espande la forma ma NON fabbrica: l'id non in universo resta unverified."""
    from core.citation_verifier import verify_citations
    uni = {f"{_AI}__art_6"}
    out = normalize_mini_text("Vedi [cite:art_99].", _AI, uni)
    assert out == f"Vedi [cite:{_AI}__art_99]."   # espanso
    vr = verify_citations(out, uni)
    assert vr.all_verified is False                # ma non verificato
    assert vr.n_total == 1


# ----------------------------------------------------------- (PARTE 1) bracket-fix

def test_bracketfix_unclosed_before_newline() -> None:
    out = close_unclosed_cites(f"…specifiche [cite:{_AI}__art_25\n\n### Art. 26")
    assert out == f"…specifiche [cite:{_AI}__art_25]\n\n### Art. 26"


def test_bracketfix_unclosed_before_section_header() -> None:
    out = close_unclosed_cites(f"deployer [cite:{_AI}__art_13### Art. 14")
    assert out == f"deployer [cite:{_AI}__art_13]### Art. 14"


def test_bracketfix_unclosed_at_end_of_text() -> None:
    out = close_unclosed_cites(f"chiude qui [cite:{_AI}__art_99")
    assert out == f"chiude qui [cite:{_AI}__art_99]"


def test_bracketfix_unclosed_before_space_prose_no_close() -> None:
    # nessuna `]` da nessuna parte → chiude subito dopo l'id (prima della prosa)
    out = close_unclosed_cites(f"vedi [cite:{_AI}__art_25 e poi prosegue senza chiusura")
    assert out == f"vedi [cite:{_AI}__art_25] e poi prosegue senza chiusura"


def test_bracketfix_closed_with_trailing_prose_left_untouched() -> None:
    # esiste una `]` prima del confine → trattato come chiuso, non tocca
    s = f"vedi [cite:{_AI}__art_25 e poi prosegue]"
    assert close_unclosed_cites(s) == s


def test_bracketfix_unclosed_abbreviated_then_normalized() -> None:
    uni = {f"{_AI}__art_7"}
    fixed = close_unclosed_cites("notifica [cite:art_7\nprosegue")
    assert fixed == "notifica [cite:art_7]\nprosegue"
    # composizione con normalizzazione: id pieno + verificabile
    norm = normalize_mini_text("notifica [cite:art_7\nprosegue", _AI, uni)
    assert f"[cite:{_AI}__art_7]" in norm


def test_bracketfix_leaves_closed_brackets_untouched() -> None:
    s = f"ok [cite:{_AI}__art_6] e [cite:{_AI}__art_9]."
    assert close_unclosed_cites(s) == s


def test_bracketfix_leaves_closed_with_tail_untouched() -> None:
    # bracket chiuso con coda: la `]` esiste prima del newline → non lo tocca
    s = f"log [cite:{_AI}__art_12, paragrafo 1]\n"
    assert close_unclosed_cites(s) == s
