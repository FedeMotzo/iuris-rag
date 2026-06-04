"""Pulisce le cassette V3 generate con parser buggato (rimuove garbage fence
items, ricostruisce il JSON dalle stringhe quoted, applica nuovo parser).

Costo zero (nessuna chiamata LLM). Idempotente.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASSETTE = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"

GARBAGE_PREFIXES = ("```", "[", "]", "{", "}")


def clean_item(s: str) -> str | None:
    """Rimuove trailing comma JSON, surrounding quotes, e filtra garbage."""
    s = s.strip()
    # strip trailing JSON syntax leftovers
    while s.endswith((",", '"', "'", " ")):
        s = s[:-1].strip()
    # strip leading quote
    while s.startswith(('"', "'", " ")):
        s = s[1:].strip()
    if not s or len(s) < 20:
        return None
    if any(s.startswith(p) for p in GARBAGE_PREFIXES):
        return None
    if s.lower().startswith("json"):
        return None
    return s


def main() -> int:
    cass = json.loads(CASSETTE.read_text(encoding="utf-8"))
    n_cleaned = 0
    n_dropped_total = 0
    for k, v in list(cass.items()):
        if k.startswith("_"):
            continue
        if not isinstance(v, list):
            continue
        before = len(v)
        cleaned = []
        for item in v:
            if not isinstance(item, str):
                continue
            c = clean_item(item)
            if c is not None:
                cleaned.append(c)
        n_dropped = before - len(cleaned)
        n_dropped_total += n_dropped
        if cleaned != v:
            cass[k] = cleaned
            n_cleaned += 1
            print(f"  {k}: {before} → {len(cleaned)} (dropped {n_dropped})")
        if not cleaned:
            print(f"  WARNING: {k} è vuota dopo pulizia!")

    cass.setdefault("_meta", {})["v3_cleaned"] = "spike/cleanup_cassettes_v3.py"
    CASSETTE.write_text(
        json.dumps(cass, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n{n_cleaned} entries pulite, {n_dropped_total} items spuri rimossi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
