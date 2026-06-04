"""Rigenera le cassette sub-query con prompt V3 mono-concetto (v1.2).

Genera per Q9, Q68, Q69, Q70, Q71 — Q25 esclusa (path fallback, no sub-q).
Output: list[str] per ogni (qid, norm_id). Costo atteso: ~$0.08 (16 chiamate
Sonnet 4.6 con max_tokens=400).

    spike/.venv/bin/python spike/regen_cassettes_v3.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASSETTE = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"

QUERIES = {
    "q9": "Quali sono i reati presupposto in materia di trattamento illecito di dati personali ai sensi del D.Lgs 231/2001 e del Codice Privacy?",
    "q68": "Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?",
    "q69": "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare un sistema di IA per supportare le attività di farmacovigilanza con dati provenienti da operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai sensi di AI Act, GDPR e NIS2?",
    "q70": "Una banca italiana intende affidare in outsourcing a un fornitore extra-UE la gestione di un sistema di IA per il rilevamento di operazioni sospette di riciclaggio: quali profili AI Act, GDPR, NIS2 e 231 deve considerare in fase di selezione del fornitore?",
    "q71": "Una regione italiana intende mettere in produzione un sistema di IA per supportare l'attribuzione di punteggi nelle graduatorie di accesso ai servizi residenziali per anziani: quali sono i principali profili giuridici da considerare integrando GDPR, AI Act, L. 132/2025 e NIS2?",
}


def _q_for(qid_lower: str) -> str:
    return QUERIES[qid_lower]


def main() -> int:
    from core.cross_norm.multi_norm_trigger import detect_norms
    from core.cross_norm.subquery_generator import generate_subquery
    from core.llm_provider.config import load_provider_from_env

    jobs: list[tuple[str, list[str]]] = []
    for label in QUERIES:
        norms = detect_norms(_q_for(label))
        if len(norms) < 2:
            print(f"[{label}] {len(norms)} norma → fallback path, skip")
            continue
        jobs.append((label, norms))
    print(f"Jobs: {jobs}")

    llm = load_provider_from_env()
    print(f"provider={llm.provider_name} model={llm.model_name}\n")

    cassette = json.loads(CASSETTE.read_text(encoding="utf-8"))
    cassette.setdefault("_meta", {})
    cassette["_meta"]["v3_regen_date"] = str(date.today())
    cassette["_meta"]["v3_prompt"] = "mono-concept (JSON array di sub-query)"
    cassette["_meta"]["v3_format"] = "list[str]"

    n_calls = 0
    for label, norms in jobs:
        for nid in norms:
            print(f"[{label}:{nid}] live generate...")
            sub_qs = generate_subquery(_q_for(label), nid, llm, max_tokens=400)
            print(f"  → {len(sub_qs)} sub-query mono-concetto:")
            for i, sq in enumerate(sub_qs):
                print(f"     [{i}] {sq}")
            cassette[f"{label}:{nid}"] = sub_qs  # list[str]
            n_calls += 1

    CASSETTE.write_text(
        json.dumps(cassette, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nCassette V3 scritta: {CASSETTE}  (n_calls={n_calls})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
