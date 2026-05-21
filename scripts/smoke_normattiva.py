"""Manual smoke test against the live Normattiva endpoint.

Run this once by hand to confirm the dance still works end-to-end:

    python scripts/smoke_normattiva.py

Downloads the Codice Privacy AKN XML, compares its byte length against the
spike fixture and reports a verdict. NOT part of the automated test suite.
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from core.normattiva_client import NormattivaClient  # noqa: E402

URN = "urn:nir:stato:decreto.legislativo:2003-06-30;196"
FIXTURE = REPO_ROOT / "spike" / "data" / "codice_privacy_akn.xml"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with tempfile.TemporaryDirectory() as tmp:
        client = NormattivaClient(cache_dir=Path(tmp))
        live = client.fetch_akn(URN)

    fixture = FIXTURE.read_bytes()
    delta = len(live) - len(fixture)
    pct = abs(delta) / len(fixture) * 100 if fixture else 0.0

    print(f"live bytes   : {len(live):,}")
    print(f"fixture bytes: {len(fixture):,}")
    print(f"delta        : {delta:+,} ({pct:.2f}%)")

    head = live[:120].decode("utf-8", errors="replace")
    print(f"head         : {head!r}")

    looks_xml = head.lstrip().startswith("<?xml") and "akomaNtoso" in live[:1024].decode(
        "utf-8", errors="replace"
    )
    if not looks_xml:
        print("VERDICT: FAIL — response does not look like AKN XML")
        return 1

    if pct < 5.0:
        print("VERDICT: OK — size matches the spike fixture within 5%")
        return 0
    print(f"VERDICT: OK (XML), but size drifted by {pct:.2f}% from the spike fixture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
