# Corpus Italian Legal RAG — Overview per generazione benchmark

Il corpus v1 contiene **6 norme primarie** indicizzate in Qdrant come chunk individuali (article, recital, annex). Tutti i `chunk_id` seguono convenzioni URN deterministiche.

## Norme nel corpus

### 1. GDPR — Reg. UE 2016/679 (testo italiano consolidato)

**Prefisso URN**: `eli/reg/2016/679/oj__`

**Pattern chunk_id**:
- `eli/reg/2016/679/oj__art_N` per articoli 1-99 (es. `eli/reg/2016/679/oj__art_35` per DPIA)
- `eli/reg/2016/679/oj__recital_N` per considerando 1-173

**Copertura**: completa (99/99 articoli + tutti i considerando).

### 2. AI Act — Reg. UE 2024/1689 (testo italiano)

**Prefisso URN**: `eli/reg/2024/1689/oj__`

**Pattern chunk_id**:
- `eli/reg/2024/1689/oj__art_N` per articoli 1-113
- `eli/reg/2024/1689/oj__recital_N` per considerando 1-180
- `eli/reg/2024/1689/oj__annex_III__point_M` per Allegato III, punto M (M ∈ 1-8). Es. `eli/reg/2024/1689/oj__annex_III__point_4` per occupazione/HR.

**Copertura**: 113/113 articoli, considerando completi, **ma SOLO Allegato III è ingerito**. Allegati I, II, IV-XIII NON sono nel corpus. Non generare query gold sugli Allegati ≠ III.

### 3. Codice Privacy — D.Lgs 196/2003 (testo italiano consolidato Normattiva)

**Prefisso URN**: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__`

**Pattern chunk_id**:
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_N` per articoli vigenti
- Sotto-articoli con suffisso latino: `__art_2-bis`, `__art_2-octies`, `__art_2-sex-decies`, ecc.

**Copertura**: **107 articoli vigenti** (di 221 nel sorgente AKN, 114 abrogati esclusi giustamente). Articoli abrogati NON sono in Qdrant — usali come `gold_chunks=[]` per le query negative "articolo abrogato".

**Articoli importanti per il benchmark**:
- `art_1` (Oggetto), `art_2-octies` (condanne penali), `art_2-ter` (basi giuridiche italiane), `art_154-160` (Garante), `art_167` (trattamento illecito), `art_175` (forze polizia), `art_58` (intelligence)

### 4. D.Lgs 231/2001 — Responsabilità amministrativa enti

**Prefisso URN**: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__`

**Pattern chunk_id**: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_N`

**Copertura**: 109/109 articoli. Include articoli reati-presupposto con suffisso bis/ter/ecc.:
- `art_24-bis` (delitti informatici, rilevante per privacy/AI)
- `art_25-septies` (sicurezza sul lavoro)
- `art_25-octies` (riciclaggio)
- `art_25` e `art_25-ter` (corruzione)
- `art_9` (sanzioni interdittive)

**Limite noto**: gli articoli del codice penale richiamati come reati-presupposto (es. 615-ter, 635-bis, 24-bis del c.p.) **NON sono nel corpus v1**. Una query che richiede dispositivo del c.p. va con `has_corpus_limit_declaration=true` + dichiarazione esplicita.

### 5. D.Lgs 138/2024 — NIS2 (Direttiva NIS2 recepita)

**Prefisso URN**: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__` (nota: data XML AKN scaricato è 2024-09-04, NON 2024-09-12 come spesso citato)

**Pattern chunk_id**: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_N`

**Copertura**: 50/50 articoli circa. **Atto fragile per retrieval**: solo 3 query benchmark v1 lo toccano, vocabolario tecnico (soggetti essenziali/importanti, supply chain ICT, notifica incidenti). Attenzione a query troppo astratte.

### 6. L. 132/2025 — Disposizioni AI italiane

**Prefisso URN**: `akn/it/act/legge/stato/2025-09-23/132__`

**Pattern chunk_id**: `akn/it/act/legge/stato/2025-09-23/132__art_N`

**Copertura**: 28 articoli totali. Include sezioni specifiche per settori (sanità, lavoro, giustizia, sport, ricerca).

**Articoli rilevanti**:
- `art_3` (principi generali)
- `art_4` (informazione e riservatezza)
- `art_11` (lavoro)
- `art_22` (giovani e sport, contiene riferimenti AI ricerca)
- `art_27` (clausola di invarianza finanziaria — usato come negative omonimia in Q35 v1)

## Articoli splittati come fragment (per oversize)

Gli articoli con testo molto lungo (soglia operativa ~2000 token, verificata
empiricamente) sono splittati in più `article_fragment` durante l'ingestione,
per non saturare la finestra di prompt del LLM. Il `chunk_id` mantiene il
prefisso URN dell'articolo + suffisso `__paras_<first>_<last>`. **Non
esiste un point con `chunk_id` senza il suffisso `__paras_X_Y`** per
questi articoli — referenziarli senza il suffisso produce gap di gold.

Inventario corrente (9 fragment su 6 articoli, scoperti via Qdrant
`italian_legal_v1_hybrid` scroll 2026-05-20):

### D.Lgs 231/2001 — 2 fragment su 1 articolo

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6` — Capo I > Sezione III > art. 25-undecies (Reati ambientali), commi 1-6, 1873 token
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` — idem, commi 7-8, 363 token

### D.Lgs 138/2024 NIS2 — 3 fragment su 2 articoli

- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_2__paras_1_1` — Capo I > art. 2 (Definizioni), comma 1 unico, 3546 token (intero articolo definitorio monoblocco)
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_1_11` — Capo V > art. 38 (Sanzioni amministrative), commi 1-11 (massimali per essenziali/importanti, criteri determinazione), 1971 token
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_12_16` — idem, commi 12-16 (reiterazione, registrazione mancata, sospensione dirigenti come misura aggiuntiva), 775 token

### AI Act (Reg UE 2024/1689) — 4 fragment su 2 articoli

- `eli/reg/2024/1689/oj__art_5__paras_1_3` — Capo II > art. 5 (Pratiche di IA vietate), commi 1-3 (elenco pratiche vietate + eccezioni law enforcement), 1960 token
- `eli/reg/2024/1689/oj__art_5__paras_4_8` — idem, commi 4-8 (autorizzazione, notifica, sanzioni), 616 token
- `eli/reg/2024/1689/oj__art_57__paras_1_15` — Capo VI > art. 57 (Spazi di sperimentazione normativa per l'IA — sandbox), commi 1-15 (istituzione, scopo, partecipazione), 1852 token
- `eli/reg/2024/1689/oj__art_57__paras_16_17` — idem, commi 16-17 (eccezioni PMI, atto esecutivo), 362 token

### Implicazioni per generazione gold_chunks

Quando una candidate richiede l'intero articolo X di una norma in cui X è
splittato come fragment:

- Se la query è sulla **materia complessiva dell'articolo**:
  `gold_chunks=[fragment_1, fragment_2, ...]` (tutti i fragment).
- Se la query è su **uno specifico sottotema** coperto da un singolo
  fragment (es. solo i massimali NIS2 commi 1-11 vs solo la sospensione
  dirigenti commi 12-16): `gold_chunks=[fragment_pertinente]`.
- **NON usare `chunk_id` senza suffisso `__paras_X_Y`**, perché non
  esiste come point in Qdrant. L'audit meccanico (`spike/audit_candidates.py`)
  flagga il gap come errore di tipo (d) "suffisso/formato errato —
  articolo splittato per oversize".

Lezione operativa W7 (vedi `spike/CANDIDATES_V2_QDRANT_AUDIT.md` step
5): le 3 candidate C008/C009/C050 generate da chat fresh-context
puntavano a `…138__art_38` senza suffisso fragment → tutte 3 RIPARATE
in fase B come dimostrazione del pattern.

## Norme NON nel corpus v1 (sentinelle per negative)

Se una query richiede contenuto da queste fonti, usa `has_corpus_limit_declaration=true` o `query_type=negative`:

- **Codice penale italiano** (richiamato da 231 art. 24-bis...25-undecies): le singole fattispecie penali non sono nel corpus
- **D.Lgs 81/2008** (sicurezza sul lavoro), **D.Lgs 152/2006** (ambiente), altri decreti settoriali italiani
- **Standard ISO** (9001, 27001, 27701, 42001): esclusi per copyright
- **Direttive UE non recepite** o **Regolamenti UE diversi** dai 2 nel corpus (es. ePrivacy, Data Act, DSA, DMA, DORA, MDR)
- **Linee guida EDPB / WP29** (sono soft law, fuori scope v1)
- **Provvedimenti Garante Privacy** (UC4, rinviato a v1.1)
- **Costituzione italiana, Codice civile** (fuori scope per design)

## Convenzioni di citazione (devono essere rispettate)

Nelle `gold_answer`, ogni claim sostantiva è seguita da `[cite:chunk_id]` PRIMA della punteggiatura. Esempi:
- Singola: `...soggetti a sanzione pecuniaria fino a settecento quote [cite:akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis].`
- Multipla: `...la disciplina si integra con il GDPR [cite:eli/reg/2016/679/oj__art_35] [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies].`
- **MAI** senza spazio: `[cite:X][cite:Y]` è errore.

## Dichiarazione di limite corpus (pattern canonico)

Quando la `gold_answer` deve dichiarare un limite, usa il pattern esatto: `"...non incluso nel corpus normativo di riferimento"` (con concordanza incluso/inclusi/inclusa/incluse). NON usare varianti come "non disponibile nel contesto" o "non presente nei chunk forniti".

Esempio:
> Il dettaglio delle fattispecie penali richiamate dall'art. 24-bis richiede il codice penale, **non incluso nel corpus normativo di riferimento**.