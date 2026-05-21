# Corpus ingestion audit — read-only

Data: 2026-05-20
Fase: post-W7, pivot W7→W10 step 2 (vedi `SCOPE.md` registro 2026-05-20).
Collection: `italian_legal_v1_hybrid` (Qdrant localhost:6333).
Script: [`spike/audit_corpus.py`](audit_corpus.py).

**Obiettivo:** quantificare la completezza dell'ingestione del corpus v1
in Qdrant prima della fase 3 (estensione corpus + curatela 50 query
addizionali). Diagnostica read-only: nessuna modifica a Qdrant, niente
re-ingest.

---

## Step 1 — Inventario chunk in Qdrant

Totale chunk scrolled: **865**.

| Norma | article | art_frag | recital | annex | annex_pt | other | totale |
|---|---:|---:|---:|---:|---:|---:|---:|
| GDPR (Reg UE 2016/679)              | 99  | 0 | 173 | 0 | 0 | 0 | **272** |
| AI Act (Reg UE 2024/1689)           | 111 | 4 | 180 | 0 | 8 | 0 | **303** |
| Codice Privacy (D.Lgs 196/2003)     | 107 | 0 |   0 | 0 | 0 | 0 | **107** |
| D.Lgs 231/2001                      | 108 | 2 |   0 | 0 | 0 | 0 | **110** |
| D.Lgs 138/2024 (NIS2)               |  42 | 3 |   0 | 0 | 0 | 0 |  **45** |
| L. 132/2025                         |  28 | 0 |   0 | 0 | 0 | 0 |  **28** |

Note di lettura:
- `article` = chunk `__art_N` intero.
- `article_fragment` = chunk `__art_N__paras_M_K` (articolo splittato per oversize).
- `annex_pt` = chunk `__annex_X__point_N` (split del solo Annex III AI Act).
- Codice Privacy / 231 / NIS2 / L.132 sono norme nazionali AKN, niente recital né annex parsati in v1.

---

## Step 2 — Confronto con atteso (per norma)

Sorgenti usati come ground truth:
- GDPR articoli ← `data/cache/eurlex/IT/02016R0679-20160504.html` (consolidata) via `core.eur_lex_parser.parse_articles`.
- GDPR recital ← `data/cache/eurlex/IT/32016R0679.html` (iniziale) via `parse_recitals`.
- AI Act articoli + recital ← `data/cache/eurlex/IT/32024R1689.html` (iniziale, consolidata IT inesistente) via gli stessi parser.
- AI Act annex ← regex `id="anx_[IVX]+"` sull'HTML iniziale (parser dedicato esiste solo per Annex III).
- Norme italiane ← XML AKN in `data/cache/normattiva/` via `core.italian_legal_parser.parse_akn`.

### GDPR (Reg UE 2016/679)

- Attesi: art=99 · rec=173 · ann=0
- Effettivi: art=99 · rec=173 · ann=0
- **Gap: ∅**

### AI Act (Reg UE 2024/1689)

- Attesi: art=113 · rec=180 · ann=**13**
- Effettivi: art=113 · rec=180 · ann=**1** (Annex III splittato in 8 point chunks)
- **Gap articoli (0)**: ∅
- **Gap recital (0)**: ∅
- **Gap annex (12)**: `I, II, IV, V, VI, VII, VIII, IX, X, XI, XII, XIII`

### Codice Privacy (D.Lgs 196/2003)

- Attesi (eId nel XML AKN): art=221
- Effettivi in Qdrant: art=107
- Abrogati nel sorgente AKN: **114** (taggati `is_abrogated=True` dal parser, esclusi dall'ingestione)
- **Gap reale = 0**: 221 − 114 abrogati = 107 (quadra esattamente con Qdrant)
- I 114 articoli "mancanti" sono tutti articoli abrogati presenti nel testo AKN come placeholder ma senza testo dispositivo (causa (b)).

### D.Lgs 231/2001

- Attesi: art=109 · Effettivi: art=109 (includono i 2 article_fragment). **Gap: ∅**

### D.Lgs 138/2024 (NIS2)

- Attesi: art=44 · Effettivi: art=44 (includono i 3 article_fragment). **Gap: ∅**
- Nota: il prefisso URN reale in Qdrant è `2024-09-04/138` (data dell'XML AKN scaricato), non `2024-09-12` come riportato nel prompt di audit.

### L. 132/2025

- Attesi: art=28 · Effettivi: art=28. **Gap: ∅**

---

## Step 3 — Verifica Allegati AI Act

| Annex | atteso in HTML | chunk in Qdrant | gap |
|---|---|---:|---|
| I     | sì | 0 | **MANCA** |
| II    | sì | 0 | **MANCA** |
| III   | sì | 8 (split per 8 macro-punti) | OK |
| IV    | sì | 0 | **MANCA** |
| V     | sì | 0 | **MANCA** |
| VI    | sì | 0 | **MANCA** |
| VII   | sì | 0 | **MANCA** |
| VIII  | sì | 0 | **MANCA** |
| IX    | sì | 0 | **MANCA** |
| X     | sì | 0 | **MANCA** |
| XI    | sì | 0 | **MANCA** |
| XII   | sì | 0 | **MANCA** |
| XIII  | sì | 0 | **MANCA** |

12 allegati su 13 non ingeriti.

Riferimento qualitativo dei contenuti mancanti (dal testo dell'AI Act):
- **Annex I**: lista di norme di armonizzazione UE richiamate per high-risk
- **Annex II**: reati gravi per cui è ammesso identificazione biometrica remota live
- **Annex IV**: documentazione tecnica obbligatoria per high-risk
- **Annex V-VII**: dichiarazione UE di conformità + procedure di valutazione
- **Annex VIII**: informazioni per registrazione in banca dati UE
- **Annex IX-X**: deroghe e contenuti tecnici aggiuntivi
- **Annex XI-XIII**: documentazione GPAI (general-purpose AI models)

---

## Step 4 — Diagnosi gap

Per ogni gap, la causa più probabile tra le 5 categorie del prompt:

### AI Act — 12 annex mancanti

Tutti **(d) configurazione di ingestione**: il parser
`core.eur_lex_parser.parser` espone solo `parse_annex_iii_aiact()` (8
macro-punti). Gli altri 12 allegati non hanno parser dedicato e non
sono mai stati ingeriti. La struttura HTML degli altri allegati è
analoga a Annex III (id `anx_N`, sezioni numerate o lettere), quindi
un parser generico è tecnicamente fattibile — è una scelta di scope v1
non un bug isolato. Riferimento decisione: PROJECT_CONTEXT voce 14
(considerando + articoli inclusi, annex non discussi esplicitamente in
v1).

### Codice Privacy — 114 articoli "mancanti"

Tutti **(b) articolo abrogato**: il parser AKN marca correttamente
ognuno di essi `is_abrogated=True` e l'ingestion li esclude. Il sorgente
AKN li elenca come eId nel manifest ma il testo dispositivo è vuoto. Non
è un gap reale — è scope giuridico corretto del D.Lgs 196/2003
post-armonizzazione GDPR.

### Altri (231, NIS2, L.132, GDPR)

Nessun gap.

---

## Step 5 — Impatto benchmark + priorità

Cross-reference con `data/benchmark/gold_answers_v1.json` (38 query
positive): per ogni `chunk_id` referenziato come `gold_chunks` verifico
se è presente in Qdrant.

**Risultato: 0 query del benchmark v1 impattate.** Tutti i
`gold_chunks` delle 38 positive cadono su articoli/recital/annex
effettivamente in Qdrant. I gap (annex AI Act + abrogati Codice Privacy)
non bloccano nessuna query attualmente valutata.

| Norma | gap | % su attesi | query benchmark v1 impattate | priorità fix | stima costo |
|---|---:|---:|---|---|---|
| GDPR (Reg UE 2016/679)             |   0 |   0.0% | — | — | — |
| **AI Act (Reg UE 2024/1689)**      |  12 |   3.9% | nessuna su v1 — alta probabile su benchmark esteso (≥100 query, fase 3 pivot) | **MEDIA** | medio (parser generico annex riusa la logica di `parse_annex_iii_aiact`, 0.5-1 gg) |
| Codice Privacy (D.Lgs 196/2003)    | 114 |  51.6% | nessuna — sono tutti abrogati, scope giuridico corretto | **BASSA** (non-fix) | nullo (no-op, scelta giuridicamente corretta) |
| D.Lgs 231/2001                     |   0 |   0.0% | — | — | — |
| D.Lgs 138/2024 (NIS2)              |   0 |   0.0% | — | — | — |
| L. 132/2025                        |   0 |   0.0% | — | — | — |

**Priorità di fix consolidata:**

1. **MEDIA — AI Act annex I, II, IV-XIII**: nessuna query benchmark v1 li referenzia, ma il benchmark esteso (fase 3) introdurrà 50 nuove query e la copertura procedurale/documentale (annex IV per documentazione tecnica, annex V-VII per conformità, annex XI-XIII per GPAI) è plausibile target. Da rivalutare a valle della curatela query estese: se nessuna delle 50 nuove query li tocca, declassare a BASSA / rimandare a v1.1.
2. **BASSA / non-fix — Codice Privacy abrogati**: gap apparente ma giuridicamente coerente. Nessun fix necessario. Eventuale azione: aggiungere chunk-stub per ogni abrogato con metadata `"abrogated": true` e testo "[articolo abrogato — vedi <riferimento sostitutivo>]" per supportare query del tipo "cosa diceva l'art. X del Codice Privacy prima dell'abrogazione" — fuori scope v1, valutare in v1.1 con il pattern dichiarazione di limite.

---

## Sintesi

**Corpus v1 sostanzialmente completo per il benchmark attuale.** Nessun
gap impatta le 38 query positive di `gold_answers_v1.json`. Le due
anomalie identificate sono entrambe scope-driven, non bug:

- 12 allegati AI Act non ingeriti per scelta di parser limitato a
  Annex III in v1 (PROJECT_CONTEXT voce 14 silente sugli altri annex).
- 114 articoli Codice Privacy correttamente esclusi perché abrogati nel
  sorgente AKN (`is_abrogated=True`).

**Raccomandazione per fase 3 del pivot** (curatela 50 query addizionali
per benchmark esteso): redigere le 50 nuove query **prima** di decidere
l'estensione del parser annex AI Act. Se ≥1 delle 50 nuove query
referenzia un annex diverso da III, la priorità sale da MEDIA ad ALTA e
giustifica l'investimento (~0.5-1 gg) di un parser generico annex.
Altrimenti rimandare a v1.1 senza perdita di valore.

**Nessun altro intervento di ingestione richiesto prima del re-run W3 +
Ragas sul benchmark esteso.**
