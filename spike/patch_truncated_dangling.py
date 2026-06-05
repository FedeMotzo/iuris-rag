"""One-off: ricalcola truncated OR has_dangling_cite su tutti gli artefatti.

Uso: python spike/patch_truncated_dangling.py
Riscrive i file in place; riporta le sezioni flippate.
"""
from __future__ import annotations

import json
import pathlib

from core.citation_marker import has_dangling_cite

PRES_DIR = pathlib.Path(__file__).parent / "runs" / "paid_subset_v1"


def main() -> None:
    total_flipped: list[str] = []
    for path in sorted(PRES_DIR.glob("*.presentation.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        flipped: list[str] = []
        for norm in data["norms"]:
            for art in norm["articles"]:
                if not art["truncated"] and has_dangling_cite(art["body"]):
                    art["truncated"] = True
                    flipped.append(f"{norm['norm_id']}/{art['article']}")
        if flipped:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"{path.name}: flipped → {flipped}")
            total_flipped.extend(f"{path.name}::{s}" for s in flipped)
        else:
            print(f"{path.name}: nessun cambio")
    print(f"\nTotale sezioni flippate: {len(total_flipped)}")
    for s in total_flipped:
        print(f"  {s}")


if __name__ == "__main__":
    main()
