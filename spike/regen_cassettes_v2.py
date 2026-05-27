"""Rigenera le cassette sub-query Sonnet 4.6 (prompt template V2 con clausola
nominazione esplicita) per Q68 + Q69.

Cancella le vecchie chiavi q68:*/q69:* e le riscrive con output live.
Costo atteso: ~$0.025 (6 chiamate Sonnet 4.6).

    spike/.venv/bin/python spike/regen_cassettes_v2.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASSETTE = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"

Q68 = (
    "Un'azienda ospedaliera intende mettere in produzione un chatbot AI "
    "per supportare il triage telefonico dei pazienti: quali adempimenti "
    "integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima "
    "dell'avvio?"
)
Q69 = (
    "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale "
    "NIS2 per il settore sanitario, intende impiegare un sistema di IA per "
    "supportare le attività di farmacovigilanza con dati provenienti da "
    "operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai "
    "sensi di AI Act, GDPR e NIS2?"
)

JOBS = [
    ("q68", Q68, ["gdpr", "ai_act", "l_132_2025"]),
    ("q69", Q69, ["gdpr", "ai_act", "nis2"]),
]


def main() -> int:
    from core.cross_norm.subquery_generator import generate_subquery
    from core.llm_provider.config import load_provider_from_env

    llm = load_provider_from_env()
    print(f"provider={llm.provider_name} model={llm.model_name}")

    cassette = json.loads(CASSETTE.read_text(encoding="utf-8"))
    # preserva _meta, droppa le vecchie chiavi q68:*/q69:*
    new_cassette = {"_meta": cassette.get("_meta", {})}
    new_cassette["_meta"].update({
        "model": llm.model_name,
        "temperature": 0.0,
        "regenerated": str(date.today()),
        "prompt_template_version": "v2 (clausola nominazione esplicita istituti)",
        "source": "spike/regen_cassettes_v2.py (live)",
        "key_format": "<query_label>:<norm_id>",
    })

    for label, query, norms in JOBS:
        for nid in norms:
            print(f"\n[{label}:{nid}] live generate...")
            text = generate_subquery(query, nid, llm, max_tokens=200)
            print(f"  → {text}")
            new_cassette[f"{label}:{nid}"] = text

    CASSETTE.write_text(
        json.dumps(new_cassette, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nCassette riscritta: {CASSETTE}")
    print(f"Chiavi: {sorted(k for k in new_cassette if not k.startswith('_'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
