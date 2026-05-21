"""Ispezione strutturale della versione consolidata GDPR (template codifica).

    python scripts/probe_eurlex_v3.py

Lavora sul fixture cached `data/cache/eurlex/02016R0679-20160504.html`. Se
mancante, lo scarica una volta. Solo lettura, niente parser.

Sezioni:
  1. Subdivision inventory (tipi delle 101 <div class="eli-subdivision">)
  2. Articoli (atteso: 99)
  3. Considerando (atteso: 173)
  4. Gerarchia: title-division-1 / title-division-2
  5. Rettifiche/modifiche: modref e footnote

Ogni sezione termina con un "DETECTION PATTERN PROPOSTO" da usare nel parser.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import requests
from lxml import html

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "cache" / "eurlex"
CELEX_CONS = "02016R0679-20160504"
FIXTURE = CACHE_DIR / f"{CELEX_CONS}.html"
URL = f"https://eur-lex.europa.eu/legal-content/IT/TXT/HTML/?uri=CELEX:{CELEX_CONS}"


def _short(s: str | None, n: int = 60) -> str:
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


def _first_child_element(node):
    for c in node.iterchildren():
        if isinstance(c.tag, str):
            return c
    return None


def _ensure_fixture():
    if FIXTURE.exists() and FIXTURE.stat().st_size > 100_000:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  [download] {URL}")
    r = requests.get(URL, headers={"User-Agent": "iuris-rag-probe/0.3"}, timeout=30)
    if r.status_code == 200 and len(r.content) > 100_000:
        FIXTURE.write_bytes(r.content)
    else:
        raise RuntimeError(f"Download fallito: {r.status_code} size={len(r.content)}")


# ---------------------------------------------------------------------------
# 1. Subdivision inventory
# ---------------------------------------------------------------------------

def sez1_subdivision_inventory(doc):
    print("\n" + "=" * 78)
    print("1. SUBDIVISION INVENTORY")
    print("=" * 78)

    subs = doc.xpath('//div[contains(@class, "eli-subdivision")]')
    print(f"Totale <div class~='eli-subdivision'>: {len(subs)}\n")

    by_first_child_class = defaultdict(list)
    no_first_child = []
    for s in subs:
        fc = _first_child_element(s)
        if fc is None:
            no_first_child.append(s)
            continue
        fc_cls = fc.get("class") or "(nessuna classe)"
        by_first_child_class[fc_cls].append((s, fc))

    print(f"{'classe primo figlio':<32} {'conteggio':>9}")
    print("-" * 78)
    for cls, items in sorted(by_first_child_class.items(), key=lambda x: -len(x[1])):
        print(f"{cls:<32} {len(items):>9}")
    if no_first_child:
        print(f"{'(nessun figlio elemento)':<32} {len(no_first_child):>9}")

    # 3 esempi per ciascuna classe del primo figlio
    print()
    for cls, items in sorted(by_first_child_class.items(), key=lambda x: -len(x[1])):
        print(f"  ── classe primo figlio = '{cls}' (esempi):")
        for sub, fc in items[:3]:
            sid = sub.get("id") or "(no id)"
            txt = _short((fc.text_content() or "").strip(), 60)
            print(f"     [id={sid!r:<25}] {txt!r}")
        print()

    print("DETECTION PATTERN PROPOSTO:")
    print("  - Mappare classe-del-primo-figlio → tipo di subdivision (vedi tabella sopra)")
    print("  - Pattern XPath: //div[contains(@class,'eli-subdivision')]/*[1][@class]")


# ---------------------------------------------------------------------------
# 2. Articoli
# ---------------------------------------------------------------------------

def sez2_articoli(doc):
    print("\n" + "=" * 78)
    print("2. ARTICOLI (atteso: 99)")
    print("=" * 78)

    # Ipotesi: articolo = subdivision con primo figlio class~='title-article-norm'
    subs = doc.xpath('//div[contains(@class, "eli-subdivision")]')
    articoli = []
    for s in subs:
        fc = _first_child_element(s)
        if fc is None:
            continue
        if "title-article-norm" in (fc.get("class") or ""):
            articoli.append((s, fc))

    print(f"Subdivision con primo figlio class~='title-article-norm': {len(articoli)}")
    if not articoli:
        print("  Nessun articolo trovato con questo pattern.")
        print("\nDETECTION PATTERN PROPOSTO:")
        print("  ✗ pattern fallisce, riconsiderare")
        return

    # Hanno id?
    with_id = sum(1 for s, _ in articoli if s.get("id"))
    print(f"Articoli con id sulla subdivision: {with_id} / {len(articoli)}")
    if with_id:
        print(f"  Esempi id: {[s.get('id') for s, _ in articoli[:5]]}")

    # Numero estraibile?
    num_re = re.compile(r"Articolo\s+(\d+)", re.IGNORECASE)
    nums = []
    for s, fc in articoli:
        m = num_re.search(fc.text_content() or "")
        if m:
            nums.append(int(m.group(1)))
    print(f"Articoli con numero estraibile dal testo: {len(nums)}")
    if nums:
        print(f"  Range: {min(nums)}-{max(nums)} | univoci: {len(set(nums))}")

    # Esempi: primi 3 + rubrica (secondo figlio)
    print("\nPrimi 3 articoli — struttura:")
    for s, fc in articoli[:3]:
        sid = s.get("id") or "(no id)"
        children = [c for c in s.iterchildren() if isinstance(c.tag, str)]
        print(f"  subdivision id={sid!r}, n_children={len(children)}")
        for i, c in enumerate(children[:4]):
            cls = c.get("class") or ""
            txt = _short((c.text_content() or "").strip(), 70)
            print(f"    [{i}] <{c.tag} class={cls!r}> {txt!r}")
        print()

    print("DETECTION PATTERN PROPOSTO:")
    print('  XPath: //div[contains(@class,"eli-subdivision")][./*[1][contains(@class,"title-article-norm")]]')
    print('  Numero: regex r"Articolo\\s+(\\d+)" sul testo del primo figlio')
    print('  Rubrica: testo del figlio class~="stitle-article-norm" (se presente)')


# ---------------------------------------------------------------------------
# 3. Considerando
# ---------------------------------------------------------------------------

def sez3_considerando(doc):
    print("\n" + "=" * 78)
    print("3. CONSIDERANDO (atteso: 173)")
    print("=" * 78)

    # Strategia A: subdivision con testo "(N) ..."
    subs = doc.xpath('//div[contains(@class, "eli-subdivision")]')
    rct_pattern = re.compile(r"^\(\s*(\d+)\s*\)\s+")
    sub_recital_candidates = []
    for s in subs:
        t = (s.text_content() or "").strip()
        m = rct_pattern.match(t)
        if m:
            sub_recital_candidates.append((int(m.group(1)), s, t))
    print(f"  A — subdivision con testo '(N) ...': {len(sub_recital_candidates)}")

    # Strategia B: cerco classi 'recital'
    rec_class = doc.xpath('//*[contains(@class, "recital")]')
    print(f"  B — elementi con class~='recital': {len(rec_class)}")

    # Strategia C: id con prefisso
    for prefix in ["rct_", "rec_", "considerando_"]:
        n = len(doc.xpath(f"//*[starts-with(@id, '{prefix}')]"))
        if n > 0:
            print(f"  C — id con prefisso '{prefix}': {n}")
        else:
            print(f"  C — id con prefisso '{prefix}': 0")

    # Strategia D: <p> con class~='normal' e testo "(N) ..."
    p_normal = doc.xpath('//p[contains(@class, "normal")]')
    p_recital = [el for el in p_normal if rct_pattern.match((el.text_content() or "").strip())]
    print(f"  D — <p class~='normal'> con testo '(N) ...': {len(p_recital)}")
    if p_recital:
        # Estraggo i numeri trovati
        nums = []
        for el in p_recital:
            m = rct_pattern.match((el.text_content() or "").strip())
            if m:
                nums.append(int(m.group(1)))
        if nums:
            print(f"    Range: {min(nums)}-{max(nums)} | univoci: {len(set(nums))}")
            missing = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
            print(f"    Buchi nel range: {len(missing)} {missing[:10]}")

    # Esempi: primi 3 da strategia D (la più promettente vista la struttura)
    if p_recital:
        print("\n  Esempi (primi 3 considerando via strategia D):")
        for el in p_recital[:3]:
            t = (el.text_content() or "").strip()
            m = rct_pattern.match(t)
            n = m.group(1) if m else "?"
            cls = el.get("class") or ""
            pid = el.get("id") or "(no id)"
            print(f"    Considerando ({n}):")
            print(f"      tag    : <p class={cls!r} id={pid!r}>")
            print(f"      parent : {_parent_descr(el)}")
            print(f"      text   : {_short(t, 80)!r}")

    print("\nDETECTION PATTERN PROPOSTO:")
    if len(p_recital) >= 150:
        print('  XPath: //p[contains(@class,"normal") and re:match(text(), "^\\\\(\\\\d+\\\\)\\\\s")]')
        print('  Numero: regex r"^\\\\((\\\\d+)\\\\)" sul testo del <p>')
        print('  URI: non c\'è id nativo → costruire f"{doc_eli}#rct_{N}" sintetico')
    elif len(sub_recital_candidates) >= 150:
        print('  XPath: //div[contains(@class,"eli-subdivision") and re:match(., "^\\\\(\\\\d+\\\\)")]')
    else:
        print('  ✗ nessuna strategia copre i 173 considerando attesi — analisi manuale richiesta')


# ---------------------------------------------------------------------------
# 4. Gerarchia
# ---------------------------------------------------------------------------

def sez4_gerarchia(doc):
    print("\n" + "=" * 78)
    print("4. GERARCHIA: title-division-1 / title-division-2")
    print("=" * 78)

    div1 = doc.xpath('//*[contains(@class, "title-division-1")]')
    div2 = doc.xpath('//*[contains(@class, "title-division-2")]')
    print(f"Elementi title-division-1 (probabile Capo):    {len(div1)}")
    print(f"Elementi title-division-2 (probabile Sezione): {len(div2)}")

    def show(label, els):
        print(f"\n  Primi 3 {label}:")
        for el in els[:3]:
            cls = el.get("class") or ""
            pid = el.get("id") or "(no id)"
            # eventuali attributi data-*
            data_attrs = {k: v for k, v in el.attrib.items() if k.startswith("data-")}
            txt = _short((el.text_content() or "").strip(), 70)
            print(f"    <{el.tag} class={cls!r} id={pid!r} {data_attrs or ''}>")
            print(f"      text   : {txt!r}")
            print(f"      parent : {_parent_descr(el)}")

    if div1:
        show("title-division-1", div1)
    if div2:
        show("title-division-2", div2)

    # Verifica annidamento: un title-division-2 è dentro una subdivision che a sua
    # volta è dentro una subdivision con title-division-1?
    nested = 0
    for d2 in div2:
        ancestor_subs = d2.xpath('./ancestor::div[contains(@class,"eli-subdivision")]')
        if any(a.xpath('./*[contains(@class,"title-division-1")]') for a in ancestor_subs):
            nested += 1
    print(f"\n  Annidamento: {nested}/{len(div2)} title-division-2 sono "
          f"dentro una subdivision il cui figlio diretto è title-division-1")
    if nested == len(div2) and div2:
        print("  → struttura ANNIDATA (Capo > Sezione)")
    elif nested == 0:
        print("  → struttura PIATTA (livelli su pari livello)")
    else:
        print("  → struttura MISTA")

    print("\nDETECTION PATTERN PROPOSTO:")
    print('  Capo:    //div[contains(@class,"eli-subdivision")][./*[1][contains(@class,"title-division-1")]]')
    print('  Sezione: //div[contains(@class,"eli-subdivision")][./*[1][contains(@class,"title-division-2")]]')
    print('  Verifica relazione padre-figlio via ./ancestor::')


# ---------------------------------------------------------------------------
# 5. Rettifiche / modifiche
# ---------------------------------------------------------------------------

def sez5_modref(doc):
    print("\n" + "=" * 78)
    print("5. RETTIFICHE / MODIFICHE — classi 'modref' e 'footnote'")
    print("=" * 78)

    modrefs = doc.xpath('//*[contains(@class, "modref")]')
    footnotes = doc.xpath('//*[contains(@class, "footnote")]')
    print(f"Elementi class~='modref':   {len(modrefs)}")
    print(f"Elementi class~='footnote': {len(footnotes)}")

    print("\n  Primi 5 modref:")
    for el in modrefs[:5]:
        tag = el.tag if isinstance(el.tag, str) else str(el.tag)
        cls = el.get("class") or ""
        href = el.get("href") or ""
        n_links = len(el.xpath('.//a'))
        txt = _short((el.text_content() or "").strip(), 80)
        print(f"    <{tag} class={cls!r} {'href=' + repr(href) if href else ''}>")
        print(f"      n_links_interni: {n_links}")
        print(f"      text   : {txt!r}")
        print(f"      parent : {_parent_descr(el)}")

    print("\n  Primi 3 footnote:")
    for el in footnotes[:3]:
        tag = el.tag if isinstance(el.tag, str) else str(el.tag)
        cls = el.get("class") or ""
        n_links = len(el.xpath('.//a'))
        txt = _short((el.text_content() or "").strip(), 80)
        print(f"    <{tag} class={cls!r}>")
        print(f"      n_links: {n_links}")
        print(f"      text   : {txt!r}")
        print(f"      parent : {_parent_descr(el)}")

    # Heuristica: modref sono inline (dentro paragrafi) o block (separati)?
    if modrefs:
        inline = sum(
            1 for el in modrefs
            if el.getparent() is not None
            and el.getparent().tag == "p"
        )
        print(f"\n  Modref dentro un <p> (inline): {inline}/{len(modrefs)}")

    print("\nDETECTION PATTERN PROPOSTO:")
    print('  Modref: //*[contains(@class,"modref")] — di norma inline nel testo,')
    print('          contengono link a rettifiche/modifiche. Decisione: mantenerli')
    print('          come testo inline nel chunk (sono informativi, non strutturali).')
    print('  Footnote: //*[contains(@class,"footnote")] — note a piè di pagina.')
    print('            Estrarre separatamente o filtrare a seconda dell\'uso (RAG: filtrare).')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 78)
    print("PROBE EUR-LEX v3 — versione CONSOLIDATA GDPR (template codifica)")
    print("=" * 78)
    print(f"Fixture: {FIXTURE.relative_to(REPO_ROOT)}")
    _ensure_fixture()
    doc = html.parse(str(FIXTURE)).getroot()

    sez1_subdivision_inventory(doc)
    sez2_articoli(doc)
    sez3_considerando(doc)
    sez4_gerarchia(doc)
    sez5_modref(doc)

    print("\n" + "=" * 78)
    print("Fine ispezione. Pattern documentati. Pronto per dimensionare il parser.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
