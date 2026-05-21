"""Manual smoke test against live EUR-Lex.

    python scripts/smoke_eurlex.py

Downloads two CELEX (GDPR iniziale + GDPR consolidata 2016-05-04) via
`EurLexClient` into a temp cache and compares byte length with the fixtures
shipped in the repository. Not part of the automated test suite.
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from core.eur_lex_client import EurLexClient  # noqa: E402

CASES = [
    (
        "GDPR iniziale",
        "32016R0679",
        REPO_ROOT / "spike" / "data" / "gdpr_eurlex.html",
    ),
    (
        "GDPR consolidata 2016-05-04",
        "02016R0679-20160504",
        REPO_ROOT / "data" / "cache" / "eurlex" / "02016R0679-20160504.html",
    ),
]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    overall = 0
    with tempfile.TemporaryDirectory() as tmp:
        client = EurLexClient(cache_dir=Path(tmp))
        for label, celex, fixture in CASES:
            print(f"\n--- {label} (CELEX:{celex}) ---")
            live = client.fetch_html(celex)
            print(f"  live bytes    : {len(live):,}")

            if not fixture.exists():
                print(f"  fixture       : MISSING at {fixture}")
                overall = 1
                continue

            ref = fixture.read_bytes()
            delta = len(live) - len(ref)
            pct = abs(delta) / len(ref) * 100 if ref else 0.0
            print(f"  fixture bytes : {len(ref):,}")
            print(f"  delta         : {delta:+,} ({pct:.2f}%)")

            head = live[:120].decode("utf-8", errors="replace").replace("\n", " ")
            print(f"  head          : {head!r}")
            looks_html = b"<html" in live[:2048].lower() or b"<!doctype html" in live[:200].lower()
            if not looks_html:
                print("  VERDICT       : FAIL — does not look like HTML")
                overall = 1
                continue
            if pct < 5.0:
                print("  VERDICT       : OK — size matches fixture within 5%")
            else:
                print(f"  VERDICT       : OK (HTML) — size drifted by {pct:.2f}%")

    return overall


if __name__ == "__main__":
    sys.exit(main())
