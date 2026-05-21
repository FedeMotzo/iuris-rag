# EUR-Lex findings — Mini-spike D7

> Data: 2026-05-16. Tempo speso: ~30 min su 60 budget.
> Obiettivo: capire come accedere a GDPR e AI Act su EUR-Lex per popolare il corpus.

---

## Sintesi esiti per endpoint

Test condotti su due CELEX di riferimento:
- **GDPR**: `CELEX:32016R0679` (Reg. UE 2016/679)
- **AI Act**: `CELEX:32024R1689` (Reg. UE 2024/1689)

| Tentativo | URL pattern | GDPR | AI Act | Note |
|---|---|---|---|---|
| AKN suffix ELI | `/eli/reg/YYYY/N/oj.akn` | 404 | 404 | Endpoint non esiste |
| AKN content-negotiation | `Accept: application/akn+xml` | 200 ma HTML | n/a | Header ignorato, ti dà l'HTML |
| AKN legal-content | `/legal-content/IT/TXT/AKN/?uri=CELEX:...` | **500** | **500** | Endpoint esiste ma rotto |
| AKN legal-content alt | `/legal-content/IT/AKN/?uri=CELEX:...` | 404 | n/a | |
| XML ELI suffix | `/eli/reg/YYYY/N/oj.xml` | 404 | n/a | |
| XML legal-content | `/legal-content/IT/TXT/XML/?uri=CELEX:...` | 200 (1.85 MB) | 200 (1.35 MB) | **Solo metadata Cellar**, NON il testo |
| Cellar notice=object | `Accept: application/xml; notice=object` + `Accept-Language: ita` | 200 (7 KB) | 200 (5.7 KB) | Anche qui: solo metadata Cellar |
| **HTML rendering** | `/legal-content/IT/TXT/HTML/?uri=CELEX:...` | **200 (826 KB)** | **200 (1.3 MB)** | ✅ contiene il testo strutturato con ELI subdivision |

**Conclusioni dirette:**

- ❌ **AKN su EUR-Lex non è disponibile pubblicamente** per GDPR né per AI Act. Né suffix ELI, né content-negotiation, né endpoint dedicato funzionano (404/500/HTML).
- ⚠️ **L'endpoint "XML" che si pensava fosse Formex restituisce solo metadati Cellar** (root `<NOTICE type="branch">` con `WORK`, `EXPRESSION`, `URI`, `EUROVOC concepts`, ecc.). 26.787 elementi nel GDPR Cellar package, ma tag dominanti sono `IDENTIFIER`, `VALUE`, `TYPE`, `URI`, `PREFLABEL` — niente articoli, niente commi, niente testo dell'atto.
- 🔒 **Il Formex 4 del testo dell'atto è dentro Cellar** ma raggiungibile solo enumerando le manifestation della Expression (UUID `*.0013/xml/object` ecc.), richiede SPARQL su `publications.europa.eu/webapi/rdf/sparql` o conoscenza degli URL Cellar per manifestation. Strada lunga, fuori dal vincolo "1 ora" dello spike.
- ✅ **L'HTML rendering è strutturato e parsabile**.

## Struttura dell'HTML EUR-Lex (utile per il parser)

Analisi rapida con `lxml.html` su entrambi i documenti:

| Marker | GDPR | AI Act | Significato |
|---|---|---|---|
| `<p class="ti-art">` | 198 | 226 | Titolo di articolo (es. "Articolo 5") |
| `<div class="eli-subdivision">` | 281 | 303 | Subdivision strutturata ELI (articolo, capitolo, sezione, considerando) |
| `id="d1e*"` o `id="art_*"` | 324 | 401 | ID granulari sui nodi |
| Esempi di id | `tit_1`, `d1e40-1-1`, `pbl_1`, `cit_1`, `cit_2`, `ntc1-L_2016119IT.01000101-E0001` | Stessi pattern | Pattern ELI standardizzato: `tit_*` = titoli, `cit_*` = citazioni, `ntc*` = note, `d1e*` = subdivisioni del testo |

Gli `id="d1e*"` non sono URN parlanti come `art_5` dell'AKN Normattiva, ma sono **stabili** (riferiscono offset DOM standardizzati). Sufficienti per costruire citazioni dirette (URL `#d1e40-1-1`).

## Decisione tra le tre opzioni del piano

**(a) estendere `italian_legal_parser` come adapter EUR-Lex AKN** → **scartata**: AKN non esiste su EUR-Lex (404/500). Non c'è niente da adaptare.

**(b) creare `eur_lex_parser` separato per Formex** → **scartata nella forma originale**, riformulata: il Formex 4 del testo è tecnicamente accessibile via Cellar SPARQL o enumerazione manifestation, ma il costo di scoperta degli URL corretti non è giustificato quando l'HTML rendering è strutturato bene e copre lo stesso bisogno.

**(c) fallback Docling+PDF** → **scartata**: l'HTML è già strutturato con classi ELI semantiche. Usare PDF + OCR/layout sarebbe sovradimensionato e perderebbe gli `id` granulari.

### Raccomandazione: **(b) riformulata — `eur_lex_parser` separato che parsa HTML rendering** (non Formex)

Motivazione:
- HTML rendering è disponibile, gratuito, senza autenticazione, supporta tutte le lingue UE
- Le classi ELI (`eli-subdivision`, `ti-art`) e gli id (`d1e*`, `tit_*`) sono **standard sui regolamenti EU** → un parser unico copre GDPR, AI Act, NIS2 EU, eIDAS, DSA, DMA, ecc.
- L'API interna del parser produce lo stesso AST di `italian_legal_parser` (Normattiva AKN): `{numero, rubrica, urn/eli, gerarchia, commi[], lettere[]}` → uniforme per il retrieval downstream
- Costo stimato: **6-8 ore** (vs ~4h del parser AKN Normattiva). Più costoso perché:
  - HTML è meno semantico di AKN (serve mappare classi/id su tipi)
  - Gestione considerando vs articoli (in AKN c'è `<recital>` esplicito, in HTML è una classe)
  - Pulizia di markup di rendering (note a piè di pagina, riferimenti incrociati)
- Tener da parte Cellar SPARQL come opzione futura se servisse Formex (es. per analisi di varianti linguistiche o cross-reference automatici)

## Caveat scoperti

1. **Sessione/cookie EUR-Lex**: ELX_SESSIONID viene impostato ma non sembra obbligatorio per accedere all'HTML (la richiesta è andata 200 al primo colpo senza dance di sessione). Verificare se sotto carico o con header diversi serva pre-warming.
2. **HTML può differire per versione consolidata vs versione iniziale**: il CELEX `32016R0679` punta alla versione iniziale; per la consolidata serve un CELEX diverso (`02016R0679-YYYYMMDD`). Da capire se l'HTML consolidato ha la stessa struttura.
3. **Notes/footnotes**: gli id `ntc*` indicano note. Il parser deve decidere se inglobarle nel testo dell'articolo o estrarle separatamente.
4. **Considerando**: per il GDPR ce ne sono 173 e contengono interpretazione importante. Vanno gestiti come chunk separati con un loro tipo (recital, non article).
5. **AI Act struttura**: 226 `<p class="ti-art">` su un totale di ~113 articoli effettivi del regolamento → probabilmente ogni articolo ha 2 marker (titolo + riferimento). Da verificare empiricamente.

## Artefatti

- [data/gdpr_eurlex.html](data/gdpr_eurlex.html) — 826 KB, HTML rendering GDPR italiano
- [data/ai_act_eurlex.html](data/ai_act_eurlex.html) — 1.3 MB, HTML rendering AI Act italiano
- [data/gdpr_formex.xml](data/gdpr_formex.xml) — 1.85 MB, Cellar metadata package GDPR (NON il testo)
- [data/ai_act_formex.xml](data/ai_act_formex.xml) — 1.35 MB, idem AI Act
- [data/gdpr_cellar_object.xml](data/gdpr_cellar_object.xml), [data/ai_act_cellar_object.xml](data/ai_act_cellar_object.xml) — 7 KB / 5.7 KB, Cellar object notice (anche questi solo metadata)

## Impatto su SCOPE.md e roadmap

- Nessuna modifica strutturale a `SCOPE.md`. La voce "Reg. UE 2016/679 (GDPR) — testo italiano consolidato" e "Reg. UE 2024/1689 (AI Act) — via EUR-Lex" restano valide; cambia solo il **transport**: HTML rendering invece di Formex/AKN immaginato.
- Settimana 2 del piano: "Ingestion AI Act + Garante" — confermato fattibile entro la settimana, parser EUR-Lex HTML costa 6-8h.
- Aggiunge un piccolo rischio architetturale: se EUR-Lex cambia il rendering HTML (template Bootstrap?), il parser si rompe. Mitigare con test di non-regressione su un campione fisso.
