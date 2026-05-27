"""Fixture condivise per i test cross_norm.

Cassette LLM:
- `tests/cross_norm/cassettes/subquery_responses.json` mappa
  `"<query_label>:<norm_id>"` → testo di risposta canonico Sonnet.
- `StubLLMClient` espone `.generate()` compatibile con `LLMProvider.generate`
  ma lookup deterministico via etichetta query (NON via prompt hash —
  l'etichetta è esplicita per leggibilità).

Pattern: i test passano sia `query_label` (es. "q68") sia il testo reale al
stub; lo stub usa `query_label` per il lookup ma valida che il prompt
contenga la query reale (sanity check sull'integrazione).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

CASSETTES_DIR = Path(__file__).resolve().parent / "cassettes"


@dataclass
class _StubResult:
    text: str


class StubLLMClient:
    """LLM stub: ritorna risposte canoniche da cassette JSON.

    Compatibile con `core.llm_provider.LLMProvider.generate`:
    `generate(prompt, system, max_tokens, temperature) -> obj.text`.
    """

    def __init__(self, cassette_path: Path, query_label: str) -> None:
        self._cassette = json.loads(cassette_path.read_text(encoding="utf-8"))
        self._query_label = query_label
        self._calls: list[dict] = []

    def generate(self, prompt: str, system=None, max_tokens=200, temperature=0.0):
        # Inferisce norm_id dal prompt: "Norma target: <short_name>"
        # Più robusto: il prompt contiene il vocabolario, deduco dal short_name.
        # In pratica: il caller (test) sa quale norm_id sta richiedendo, ma il
        # cassette è keyed su norma. Estrazione via marker "Norma target: ".
        norm_id = self._infer_norm_id_from_prompt(prompt)
        key = f"{self._query_label}:{norm_id}"
        self._calls.append({"key": key, "prompt_len": len(prompt)})
        if key not in self._cassette:
            raise KeyError(
                f"Cassette miss: chiave {key!r} non presente in {CASSETTES_DIR}. "
                f"Chiavi disponibili: {sorted(k for k in self._cassette if not k.startswith('_'))}"
            )
        return _StubResult(text=self._cassette[key])

    @property
    def calls(self) -> list[dict]:
        return list(self._calls)

    @staticmethod
    def _infer_norm_id_from_prompt(prompt: str) -> str:
        # Mappa short_name (in `Norma target: <short_name>`) → norm_id.
        # Tieni allineata con norm_glossary.yaml/short_name.
        SHORT_TO_ID = {
            "GDPR": "gdpr",
            "AI Act": "ai_act",
            "D.Lgs 231/2001": "dlgs_231",
            "NIS2": "nis2",
            "Codice Privacy": "codice_privacy",
            "L. 132/2025": "l_132_2025",
        }
        # Estrai la riga "Norma target: ..."
        for line in prompt.splitlines():
            if line.startswith("Norma target:"):
                tail = line[len("Norma target:"):].strip()
                # tail può essere "GDPR / Regolamento UE 2016/679" — splitta sul "/"
                for short, nid in SHORT_TO_ID.items():
                    if tail.startswith(short):
                        return nid
                raise ValueError(f"Norma non riconosciuta dal prompt: {tail!r}")
        raise ValueError("Prompt non contiene 'Norma target:'")


@pytest.fixture
def subquery_cassette_path() -> Path:
    return CASSETTES_DIR / "subquery_responses.json"


@pytest.fixture
def q68_stub_llm(subquery_cassette_path: Path) -> StubLLMClient:
    return StubLLMClient(subquery_cassette_path, query_label="q68")


@pytest.fixture
def q69_stub_llm(subquery_cassette_path: Path) -> StubLLMClient:
    return StubLLMClient(subquery_cassette_path, query_label="q69")
