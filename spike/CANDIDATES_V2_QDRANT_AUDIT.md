# Candidates v2 — Qdrant audit (fase A curatela)

Data: 2026-05-20
Fase: pivot W7→W10 step 4 — verifica meccanica candidate v2 prima della
curatela giuridica.
Input: [`data/benchmark/candidates_v2.json`](../data/benchmark/candidates_v2.json) (82 candidate).
Collection: `italian_legal_v1_hybrid` (Qdrant localhost:6333, 865 chunk).
Script: [`spike/audit_candidates.py`](audit_candidates.py).

**Obiettivo:** verificare meccanicamente che i `gold_chunks_proposed`
delle 82 candidate puntino a chunk_id esistenti in Qdrant. Read-only.

---

## Step 1 — Inventario dei chunk_id proposti

- 82 candidate totali (62 positive + 17 negative + 3 edge).
- **88 chunk_id unici** nei `gold_chunks_proposed` (un chunk può comparire in più candidate).
- 17 candidate hanno `gold_chunks_proposed=[]` (16 negative + 0 edge + 1 negative su cluster "art abrogato" che già implementa il pattern atteso). Skippate dalla verifica esistenza per design.

## Step 2 — Verifica esistenza in Qdrant

- 865 chunk scrolled dalla collection.
- **87 / 88 chunk_id unici esistenti.** 1 chunk_id missing.
- Il chunk_id missing è `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38` ed è referenziato da 3 candidate distinte (errore sistemico, vedi Step 5).

## Step 3 — Audit per candidate

**79 / 82 audit pass** (gap=0). 3 candidate con gap=1.

Solo le 3 candidate con gap > 0:

| qid | cluster | confidence | n_proposed | n_existing | gap | missing_chunks |
|---|---|---|---:|---:|---:|---|
| C008 | NIS2 mono-norma | bassa | 1 | 0 | 1 | `…138__art_38` |
| C009 | NIS2 mono-norma | bassa | 2 | 1 | 1 | `…138__art_38` |
| C050 | Sanzionatorio puro | bassa | 1 | 0 | 1 | `…138__art_38` |

Le restanti 79 candidate hanno gap=0 (o n_proposed=0 atteso per negative). Output completo nello script + `spike/_audit_candidates_debug.json`.

---

## Step 4 — Aggregati per cluster

| Cluster | n candidate | gap=0 | gap>0 | % audit pass |
|---|---:|---:|---:|---:|
| 231 fattispecie oltre 24-bis           |  5 |  5 | 0 | 100.0% |
| Codice Privacy mono-norma              |  8 |  8 | 0 | 100.0% |
| Cross-norma 3+ norme                   |  8 |  8 | 0 | 100.0% |
| Cross-norma scenario 2 norme           |  5 |  5 | 0 | 100.0% |
| Diritti dell'interessato GDPR          |  6 |  6 | 0 | 100.0% |
| Edge: vaghe / mix                      |  3 |  3 | 0 | 100.0% |
| L. 132/2025                            |  7 |  7 | 0 | 100.0% |
| NIS2 cross GDPR                        |  3 |  3 | 0 | 100.0% |
| **NIS2 mono-norma**                    | 12 | 10 | **2** | **83.3%** |
| Negative: Garante UC4                  |  3 |  3 | 0 | 100.0% |
| Negative: art abrogato Codice Privacy  |  5 |  5 | 0 | 100.0% |
| Negative: art inesistente              |  3 |  3 | 0 | 100.0% |
| Negative: corpus mancante              |  3 |  3 | 0 | 100.0% |
| Negative: omonimia numerazione         |  3 |  3 | 0 | 100.0% |
| Procedurali 'come si fa X'             |  3 |  3 | 0 | 100.0% |
| **Sanzionatorio puro**                 |  5 |  4 | **1** | **80.0%** |

**Nessun cluster sotto soglia 70%.** Entrambe le due % <100 sono cluster con singolo errore sistemico riparabile (vedi Step 5).

---

## Step 5 — Diagnosi pattern errori

Codici di classificazione: **a**=articolo inesistente · **b**=abrogato · **c**=prefisso URN errato · **d**=suffisso/formato errato · **e**=non ingerito (es. annex AI Act ≠ III) · **f**=sconosciuto.

Sommario: `{d: 3}` — tutti gli errori sono dello stesso tipo.

### NIS2 mono-norma + Sanzionatorio puro

3 candidate (C008, C009, C050) propongono `…138__art_38` come chunk
intero. In Qdrant l'articolo **esiste ma è splittato in 2
article_fragment** per oversize del testo:

- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_1_11`
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_12_16`

Causa **(d) suffisso/formato errato — sotto-caso "articolo splittato per oversize"**. NIS2 art. 38 è l'articolo sulle sanzioni amministrative pecuniarie, lungo (16 commi) → la chunking lo ha splittato in due frammenti. La candidate generation v2 non ha tenuto conto del fragment-split.

**Errore non distribuito**: tutti e 3 i missing si concentrano sullo stesso chunk_id NIS2 art_38. Nessun altro articolo splittato in Qdrant è referenziato dalle candidate.

Lezione operativa per la curatela: 5 chunk in totale sono article_fragment in Qdrant (NIS2 art_31, art_38, AI Act art_57 — verificare). Verificare manualmente che eventuali altre query NIS2/AI Act su articoli lunghi puntino al fragment_id corretto.

---

## Step 6 — Raccomandazione per candidate

Tutte e 3 le candidate con gap > 0 sono **RIPARABILI**: il chunk
esiste, va solo riferito come pair di fragment_id.

| qid | gap | missing_chunks | azione | proposta alternativa |
|---|---:|---|---|---|
| C008 | 1 | `…138__art_38` | **RIPARABILE** | sostituire con `…138__art_38__paras_1_11` + `…138__art_38__paras_12_16` |
| C009 | 1 | `…138__art_38` | **RIPARABILE** | idem (il chunk `…138__art_3` proposto in coppia esiste, è solo art_38 da riparare) |
| C050 | 1 | `…138__art_38` | **RIPARABILE** | idem |

Distribuzione azioni complessiva: `{RIPARABILE: 3, SOSTITUIBILE: 0, DA SCARTARE: 0}`.

---

## Step 7 — Sintesi finale

| Metrica | Valore |
|---|---:|
| Audit pass (gap=0) | **79 / 82** (96.3%) |
| Audit fail (gap>0) | 3 |
| → riparabili | 3 |
| → sostituibili | 0 |
| → da scartare | 0 |
| **Pool survivor per fase B** | **82 / 82** (100%) |

### Ratio survivor / target per cluster

Target derivati da `BENCHMARK_DISTRIBUTION_ANALYSIS.md` step 7 (50
query finali). Per i 5 sub-cluster Negative target distribuito
proporzionalmente al pool (somma=8).

| Cluster | survivor | target | ratio | alert |
|---|---:|---:|---:|---|
| NIS2 mono-norma                       | 12 | 6 | 2.00× |  |
| NIS2 cross GDPR                       |  3 | 2 | 1.50× |  |
| Codice Privacy mono-norma             |  8 | 5 | 1.60× |  |
| L. 132/2025                           |  7 | 4 | 1.75× |  |
| Cross-norma 3+ norme                  |  8 | 5 | 1.60× |  |
| **Cross-norma scenario 2 norme**      |  5 | 4 | **1.25×** | ⚠ a rischio (<1.5×) |
| Diritti dell'interessato GDPR         |  6 | 4 | 1.50× |  |
| **Sanzionatorio puro**                |  5 | 4 | **1.25×** | ⚠ a rischio (<1.5×) |
| 231 fattispecie oltre 24-bis          |  5 | 3 | 1.67× |  |
| Procedurali 'come si fa X'            |  3 | 2 | 1.50× |  |
| Negative: Garante UC4                 |  3 | 1 | 3.00× |  |
| Negative: art abrogato Codice Privacy |  5 | 2 | 2.50× |  |
| Negative: art inesistente             |  3 | 2 | 1.50× |  |
| Negative: corpus mancante             |  3 | 2 | 1.50× |  |
| Negative: omonimia numerazione        |  3 | 1 | 3.00× |  |
| **Edge: vaghe / mix**                 |  3 | 3 | **1.00×** | ⚠ a rischio (=1.0×) |

**ALERT critici (ratio < 1.0×): 0** — tutti i cluster raggiungono il
target con il pool survivor attuale.

**ALERT a rischio (ratio < 1.5×): 3 cluster** dove un singolo scarto
in fase B (curatela giuridica) può portare sotto-target:

- **Cross-norma scenario 2 norme** (5 → target 4): margine 1. Cluster
  tematicamente delicato (richiede integrazione di norme con vocabolari
  diversi); se la curatela scarta 2 candidate il cluster va sotto-target.
- **Sanzionatorio puro** (5 → target 4): margine 1. Già 1 candidate
  (C050) richiede riparazione del fragment-split.
- **Edge: vaghe / mix** (3 → target 3): **margine zero**. Qualsiasi
  scarto in fase B porta sotto-target. Cluster ad alto rischio.

### Errori sistemici

| chunk_id | n candidate impattate |
|---|---:|
| `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38` | **3** (C008, C009, C050) |

L'unico errore sistemico è il fragment-split di NIS2 art. 38 — pattern
unico, fix banale a 3 righe nel JSON candidate v2 in fase B.

---

## Raccomandazione operativa per fase B (curatela giuridica)

1. **Apertura della fase B**: applicare il fix RIPARABILE a C008, C009,
   C050 sostituendo `…138__art_38` con i 2 fragment. Audit
   meccanico chiude al 100%.
2. **Attenzione ai 3 cluster a rischio (Cross-norma scenario 2 norme,
   Sanzionatorio puro, Edge: vaghe / mix)**: la curatela deve scartare
   il minimo indispensabile per non andare sotto-target. Edge ha
   margine zero — un singolo scarto richiede rigenerazione.
3. **Verifica preventiva fragment-split**: prima di curare le 12 NIS2
   mono-norma e 3 Sanzionatorio puro, controllare nel payload Qdrant
   che ogni `art_N` referenziato esista come chunk singolo, altrimenti
   sostituire con la coppia di fragment. Stessa cautela su AI Act
   art_57 (probabile fragment).
4. **Nessun candidate è DA SCARTARE per assenza chunk**. Il dataset
   passa cleanly la verifica meccanica → la fase B può concentrarsi
   sulla qualità giuridica delle gold_answer, non su debug strutturale
   del retrieval mapping.
