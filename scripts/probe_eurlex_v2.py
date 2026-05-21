"""Probe manuale EUR-Lex su 3 ipotesi aperte prima di scrivere il parser.

    python scripts/probe_eurlex_v2.py

Esegue 3 verifiche, output formattato umano:
  1. Versione iniziale GDPR vs consolidata: stessa struttura DOM o diversa?
  2. AI Act: i 226 <p class="ti-art"> sono articoli distinti o duplicati?
  3. GDPR: dove vivono i 173 considerando nel DOM?

Cache HTML scaricati in data/cache/eurlex/ (no re-download). Riusa i fixture
dello spike #1 (spike/data/) per i dati già disponibili.
"""

from __future__ import annotations

import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests
from lxml import html

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "cache" / "eurlex"
SPIKE_DATA = REPO_ROOT / "spike" / "data"

USER_AGENT = "iuris-rag-spike/0.2 (research)"
TIMEOUT_S = 30

# Fixture già scaricate dallo spike #1
FIXTURE_GDPR = SPIKE_DATA / "gdpr_eurlex.html"
FIXTURE_AI_ACT = SPIKE_DATA / "ai_act_eurlex.html"

# URL base EUR-Lex per HTML rendering italiano
EURLEX_HTML = "https://eur-lex.europa.eu/legal-content/IT/TXT/HTML/?uri=CELEX:{celex}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_cached(celex: str) -> tuple[Path, int]:
    """Scarica l'HTML rendering del CELEX (cache hit/miss). Ritorna (path, http_status)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{celex.replace(':', '_')}.html"
    if cache_path.exists() and cache_path.stat().st_size > 1000:
        print(f"  [cache hit] {cache_path.name} ({cache_path.stat().st_size} bytes)")
        return cache_path, 200
    print(f"  [cache miss] scarico {celex}...")
    r = requests.get(
        EURLEX_HTML.format(celex=celex),
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_S,
        allow_redirects=True,
    )
    if r.status_code == 200 and len(r.content) > 1000:
        cache_path.write_bytes(r.content)
    return cache_path, r.status_code


def _parse(path: Path):
    return html.parse(str(path)).getroot()


def _classes_in(doc) -> Counter:
    """Conta tutte le classi CSS univoche nel documento."""
    c = Counter()
    for el in doc.xpath("//*[@class]"):
        for cls in el.get("class").split():
            c[cls] += 1
    return c


def _id_prefix(doc, prefix: str) -> int:
    return len(doc.xpath(f"//*[starts-with(@id, '{prefix}')]"))


def _short(s: str | None, n: int = 80) -> str:
    if not s:
        return ""
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _parent_descr(node) -> str:
    p = node.getparent()
    if p is None:
        return "(root)"
    tag = p.tag if isinstance(p.tag, str) else str(p.tag)
    cls = p.get("class", "")
    pid = p.get("id", "")
    parts = [tag]
    if cls:
        parts.append(f'class="{cls}"')
    if pid:
        parts.append(f'id="{pid}"')
    return f"<{' '.join(parts)}>"


# ---------------------------------------------------------------------------
# Punto 1 — versione iniziale vs consolidata GDPR
# ---------------------------------------------------------------------------

CONSOLIDATA_CANDIDATES = [
    "02016R0679-20160504",  # suggerimento dal task
    "02016R0679-20180504",
    "02016R0679-20180525",  # data effettiva di applicazione GDPR
]


def _find_consolidated_via_initial(initial_doc) -> str | None:
    """Cerca nell'HTML iniziale un link a 'Versione consolidata'."""
    # Tentativo: link che porta a CELEX 02016R0679-*
    for a in initial_doc.xpath("//a[@href]"):
        href = a.get("href", "")
        m = re.search(r"CELEX[:=](02016R0679-\d{8})", href)
        if m:
            return m.group(1)
    # Tentativo: testo "Versione consolidata"
    for a in initial_doc.xpath("//a[contains(text(), 'consolidat') or contains(text(), 'Consolidat')]"):
        href = a.get("href", "")
        m = re.search(r"(02016R0679-\d{8})", href)
        if m:
            return m.group(1)
    return None


def punto1_versione_consolidata():
    print("\n" + "=" * 78)
    print("PUNTO 1 — Versione consolidata GDPR vs iniziale")
    print("=" * 78)

    # Iniziale (fixture)
    print(f"\n• Iniziale (fixture): {FIXTURE_GDPR.relative_to(REPO_ROOT)}")
    if not FIXTURE_GDPR.exists():
        print(f"  ✗ Fixture mancante. Esegui prima lo spike #1.")
        return
    initial_doc = _parse(FIXTURE_GDPR)
    initial_size = FIXTURE_GDPR.stat().st_size

    # Consolidata: provo i candidati in ordine
    consolidata_celex = None
    consolidata_path = None
    consolidata_status = None
    for celex in CONSOLIDATA_CANDIDATES:
        print(f"\n• Provo CELEX consolidato {celex}")
        path, status = _fetch_cached(celex)
        if status == 200 and path.exists() and path.stat().st_size > 100_000:
            consolidata_celex = celex
            consolidata_path = path
            consolidata_status = status
            print(f"  ✓ trovata ({path.stat().st_size} bytes)")
            break
        else:
            print(f"  ✗ status={status} size={path.stat().st_size if path.exists() else 0}")
        time.sleep(1.0)  # rate limit cortese

    # Fallback finale: estraggo link "Versione consolidata" dall'iniziale
    if not consolidata_celex:
        print("\n• Fallback: cerco link 'Versione consolidata' nell'HTML iniziale")
        suggested = _find_consolidated_via_initial(initial_doc)
        if suggested:
            print(f"  Trovato CELEX: {suggested}")
            path, status = _fetch_cached(suggested)
            if status == 200 and path.exists() and path.stat().st_size > 100_000:
                consolidata_celex = suggested
                consolidata_path = path
                consolidata_status = status
                print(f"  ✓ trovata ({path.stat().st_size} bytes)")
        else:
            print("  Nessun link consolidata trovato nell'HTML iniziale")

    if not consolidata_path:
        print("\n  ✗ Impossibile ottenere la versione consolidata. Stop Punto 1.")
        return

    # Confronto strutturale
    cons_doc = _parse(consolidata_path)
    cons_size = consolidata_path.stat().st_size

    metrics = []
    for label, doc, size in [("INIZIALE", initial_doc, initial_size),
                              ("CONSOLIDATA", cons_doc, cons_size)]:
        m = {
            "bytes": size,
            "p.ti-art": len(doc.xpath('//p[contains(@class, "ti-art")]')),
            "div.eli-subdivision": len(doc.xpath('//div[contains(@class, "eli-subdivision")]')),
            "id=d1e*": _id_prefix(doc, "d1e"),
            "id=tit_*": _id_prefix(doc, "tit_"),
            "id=cit_*": _id_prefix(doc, "cit_"),
            "id=ntc*": _id_prefix(doc, "ntc"),
        }
        metrics.append((label, m))

    print("\n  Confronto strutturale:")
    keys = list(metrics[0][1].keys())
    print(f"    {'Metrica':<22} {'INIZIALE':>14} {'CONSOLIDATA':>14}")
    for k in keys:
        a = metrics[0][1][k]
        b = metrics[1][1][k]
        diff = "" if a == b else ("  Δ=" + str(b - a))
        print(f"    {k:<22} {a:>14} {b:>14}{diff}")

    # Classi nuove nella consolidata
    cls_init = set(_classes_in(initial_doc).keys())
    cls_cons = set(_classes_in(cons_doc).keys())
    new_in_consolidata = sorted(cls_cons - cls_init)
    removed_from_initial = sorted(cls_init - cls_cons)
    print(f"\n  Classi CSS univoche — iniziale: {len(cls_init)}, consolidata: {len(cls_cons)}")
    print(f"  Classi NUOVE nella consolidata ({len(new_in_consolidata)}):")
    for c in new_in_consolidata[:30]:
        print(f"    + {c}")
    if len(new_in_consolidata) > 30:
        print(f"    ... e altre {len(new_in_consolidata) - 30}")
    print(f"  Classi PRESENTI SOLO nell'iniziale ({len(removed_from_initial)}):")
    for c in removed_from_initial[:15]:
        print(f"    - {c}")

    # Verdetto
    same_struct = (
        metrics[0][1]["p.ti-art"] == metrics[1][1]["p.ti-art"]
        and metrics[0][1]["div.eli-subdivision"] == metrics[1][1]["div.eli-subdivision"]
        and not new_in_consolidata
    )
    if same_struct:
        verdetto = "STESSA STRUTTURA — parser funzionerà senza modifiche"
    else:
        verdetto = "STRUTTURA DIVERSA — il parser deve gestire entrambe le varianti"
    print(f"\n  Verdetto: {verdetto}")
    print(f"  CELEX consolidato usato: {consolidata_celex}")


# ---------------------------------------------------------------------------
# Punto 2 — i 226 ti-art dell'AI Act
# ---------------------------------------------------------------------------

def punto2_ai_act_ti_art():
    print("\n" + "=" * 78)
    print("PUNTO 2 — I 226 <p class='ti-art'> dell'AI Act")
    print("=" * 78)

    if not FIXTURE_AI_ACT.exists():
        print(f"  ✗ Fixture mancante: {FIXTURE_AI_ACT}")
        return
    doc = _parse(FIXTURE_AI_ACT)
    elements = doc.xpath('//p[contains(@class, "ti-art")]')
    print(f"\n  Totale elementi <p class='ti-art'>: {len(elements)}")

    def show(label: str, indices: list[int]):
        print(f"\n  --- {label} ---")
        for i in indices:
            if i >= len(elements):
                continue
            el = elements[i]
            text = el.text_content().strip()
            classes = el.get("class", "")
            pid = el.get("id", "")
            print(f"    [{i:>3}] id={pid!r:<20} class={classes!r:<25}")
            print(f"          parent: {_parent_descr(el)}")
            print(f"          text  : {_short(text, 100)}")

    show("Primi 20", list(range(0, 20)))
    mid = len(elements) // 2
    show(f"5 a metà (indici {mid}-{mid + 4})", list(range(mid, mid + 5)))
    show("Ultimi 10", list(range(max(0, len(elements) - 10), len(elements))))

    # Analisi: pattern empirico
    print("\n  Pattern empirico:")
    # 1. Conta quanti elementi hanno testo che matchA "Articolo N"
    art_label = re.compile(r"^\s*Articolo\s+\d+\s*$", re.IGNORECASE)
    art_label_alt = re.compile(r"^\s*Articolo\s+\d+\b", re.IGNORECASE)
    rubric_only = []  # testi che NON sono "Articolo N" (sono rubriche)
    label_only = []   # testi tipo "Articolo 5"
    for el in elements:
        t = el.text_content().strip()
        if art_label.match(t):
            label_only.append(t)
        elif art_label_alt.match(t):
            label_only.append(t)
        else:
            rubric_only.append(t)
    print(f"    Elementi con testo 'Articolo N' (label puro): {len(label_only)}")
    print(f"    Elementi con altro testo (rubriche o altro): {len(rubric_only)}")

    # 2. Verifica se sono in alternanza (label + rubrica per articolo)
    if len(label_only) > 0 and len(rubric_only) > 0:
        ratio = len(elements) / max(1, len(label_only))
        print(f"    Rapporto totale/label: {ratio:.2f} (≈2.0 = ogni articolo ha label + rubrica)")

    # 3. Conta articoli "veri" (unici per numero)
    nums = set()
    for el in elements:
        t = el.text_content().strip()
        m = re.search(r"Articolo\s+(\d+)", t, re.IGNORECASE)
        if m:
            nums.add(int(m.group(1)))
    print(f"    Numeri di articolo univoci rilevati: {len(nums)} (range: "
          f"{min(nums) if nums else '-'}-{max(nums) if nums else '-'})")

    # 4. Esamina id dei ti-art: ce ne sono di duplicati?
    ids = [el.get("id") or "(none)" for el in elements]
    id_counts = Counter(ids)
    duplicates = [(k, v) for k, v in id_counts.items() if v > 1 and k != "(none)"]
    no_id = id_counts.get("(none)", 0)
    print(f"    Elementi senza id: {no_id}")
    print(f"    Id duplicati: {len(duplicates)} (esempi: {duplicates[:5]})")

    # Verdetto provvisorio
    print(f"\n  Verdetto provvisorio: articoli veri ≈ {len(nums)} "
          f"(vs {len(elements)} elementi 'ti-art' totali)")


# ---------------------------------------------------------------------------
# Punto 3 — considerando del GDPR
# ---------------------------------------------------------------------------

def punto3_considerando_gdpr():
    print("\n" + "=" * 78)
    print("PUNTO 3 — Considerando del GDPR (attesi: 173)")
    print("=" * 78)

    if not FIXTURE_GDPR.exists():
        print(f"  ✗ Fixture mancante: {FIXTURE_GDPR}")
        return
    doc = _parse(FIXTURE_GDPR)

    # Strategia 1: classi con 'recital'/'consider'
    recital_classes = []
    for cls, n in _classes_in(doc).items():
        if "recital" in cls.lower() or "consider" in cls.lower():
            recital_classes.append((cls, n))
    print(f"\n  Strategia 1 — classi con 'recital'/'consider': {len(recital_classes)}")
    for c, n in recital_classes[:15]:
        print(f"    {c}: {n}")

    # Strategia 2: id con prefisso candidato
    print("\n  Strategia 2 — id con prefisso candidato:")
    rct_count = 0
    for prefix in ["rct_", "rec_", "considerando_", "cnsd_", "recital_"]:
        els = doc.xpath(f"//*[starts-with(@id, '{prefix}')]")
        if els:
            print(f"    '{prefix}': {len(els)} elementi")
            if prefix == "rct_":
                rct_count = len(els)

    # Strategia 3: <p class~="normal"> con testo che inizia con "(N) ..."
    p_normal = doc.xpath('//p[contains(@class, "normal")]')
    recital_pattern = re.compile(r"^\(\s*(\d+)\s*\)\s+")
    recital_text_candidates = []
    for el in p_normal:
        t = (el.text_content() or "").strip()
        m = recital_pattern.match(t)
        if m:
            recital_text_candidates.append((int(m.group(1)), el, t))
    print(f"\n  Strategia 3 — <p class~='normal'> con testo '(N) ...': "
          f"{len(recital_text_candidates)} (nota: nell'iniziale 'normal' non esiste, usato per consolidata)")

    # Strategia 2-bis: esempi dettagliati dai rct_*
    if rct_count > 0:
        rct_elements = doc.xpath("//*[starts-with(@id, 'rct_')]")
        print(f"\n  Esempi dei primi 3 elementi con id='rct_*':")
        for el in rct_elements[:3]:
            pid = el.get("id")
            cls = el.get("class", "")
            tag = el.tag if isinstance(el.tag, str) else str(el.tag)
            txt = (el.text_content() or "").strip()
            # Numero del considerando dall'id (es. rct_5 → 5)
            m = re.search(r"rct_(\d+)", pid)
            num = m.group(1) if m else "?"
            print(f"    Considerando ({num})")
            print(f"      eId          : {pid!r}")
            print(f"      tag          : <{tag}>")
            print(f"      class        : {cls!r}")
            print(f"      parent       : {_parent_descr(el)}")
            print(f"      text (80 ch.): {_short(txt, 80)}")

        # Verifica range numerico
        nums = []
        for el in rct_elements:
            m = re.search(r"rct_(\d+)", el.get("id", ""))
            if m:
                nums.append(int(m.group(1)))
        if nums:
            nums_set = set(nums)
            missing = sorted(set(range(min(nums), max(nums) + 1)) - nums_set)
            print(f"\n    Range numerico: {min(nums)}-{max(nums)}, univoci: {len(nums_set)}")
            if missing:
                print(f"    Numeri MANCANTI nel range: {missing[:10]}"
                      f"{'...' if len(missing) > 10 else ''}")
            else:
                print(f"    Sequenza completa, nessun considerando mancante.")

    # Verdetto finale
    print(f"\n  Verifica copertura: GDPR ha 173 considerando attesi.")
    print(f"  → Trovati via id 'rct_*': {rct_count}")
    print(f"  → Trovati via testo '(N)' su p.normal: {len(recital_text_candidates)}")

    print("\n  Pattern di detection consigliato per il parser EUR-Lex (template Official Journal):")
    if rct_count >= 150:
        print('    XPath: //*[starts-with(@id, "rct_")]')
        print('    eId nativo: l\'attributo id="rct_N" dà direttamente il numero del considerando')
        print('    Costruzione URI: <doc_eli>#rct_N')
    else:
        print("    Strategia 2 non basta. Riguardare DOM dei 173 considerando reali.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 78)
    print("PROBE EUR-LEX v2 — 3 ipotesi aperte prima del parser")
    print("=" * 78)
    print(f"REPO_ROOT  : {REPO_ROOT}")
    print(f"Cache HTML : {CACHE_DIR}")
    print(f"Fixture    : {SPIKE_DATA}")

    punto1_versione_consolidata()
    punto2_ai_act_ti_art()
    punto3_considerando_gdpr()

    print("\n" + "=" * 78)
    print("Fine probe. Output usabile per dimensionare il parser EUR-Lex HTML.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
