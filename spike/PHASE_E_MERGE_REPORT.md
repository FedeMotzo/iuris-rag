# Phase E merge report — gold_answers_v2.json

Data: 2026-05-20.
Sorgenti: `data/benchmark/gold_answers_v1.json` (Q1-Q50) + `data/benchmark/candidates_v2_curated.json` (Q51-Q100).
Output: `data/benchmark/gold_answers_v2.json` (100 entry).

## Step 1 — Validazione input
✅ OK. 50+50 entry, schema identico (10 campi), qid Q1-Q50 + Q51-Q100 non sovrapposti.

## Step 2 — Lookup Qdrant (popolamento hierarchy + text v2)
- chunk_id unici richiesti: **63**
- chunk_id popolati: **63**
- chunk_id missing: **0**
- gold_chunks dict popolati end-to-end: **86**

## Step 3 — Schema consistency

| Check | pass | fail |
|---|---:|---:|
| schema 10 campi | 100 | 0 |
| qid uniqueness | 100 | 0 |
| query_type valido | 100 | 0 |
| positive con gold_chunks | 100 | 0 |
| chunk text popolato | 100 | 0 |
| pattern canonico corpus_limit | 23 | 0 |
| pattern citazione | 100 | 0 |

Nessun errore o warning.

## Step 4 — Statistiche aggregate

### query_type
| dataset | positive | negative | edge | totale |
|---|---:|---:|---:|---:|
| v1 | 38 | 10 | 2 | 50 |
| v2 | 39 | 10 | 1 | 50 |
| cumulato | 77 | 20 | 3 | 100 |

### has_corpus_limit_declaration
| dataset | true | false |
|---|---:|---:|
| v1 | 11 | 39 |
| v2 | 12 | 38 |
| cumulato | 23 | 77 |

### query_type × has_corpus_limit_declaration
| dataset | positive_limit=F | positive_limit=T | negative_limit=F | edge_limit=F | edge_limit=T |
|---|---:|---:|---:|---:|---:|
| v1 | 27 | 11 | 10 | 2 | 0 |
| v2 | 31 | 8 | 6 | 1 | 0 |
| cumulato | 58 | 19 | 16 | 3 | 0 |

### Norme toccate (count query, cross-norma somma >100%)
| Norma | v1 | v2 | cumulato |
|---|---:|---:|---:|
| AI Act | 19 | 10 | 29 |
| Codice Privacy | 1 | 5 | 6 |
| D.Lgs 231/2001 | 6 | 6 | 12 |
| GDPR | 12 | 21 | 33 |
| L. 132/2025 | 2 | 8 | 10 |
| NIS2 | 3 | 13 | 16 |

### Paired queries intenzionali (design v2)
| Tema | qid coppia |
|---|---|
| art_38__paras_1_11 | Q55 (essenziali), Q83 (importanti) |
| GDPR_art_25_NIS2 | Q54 (destinatari servizio), Q57 (autorità doppia notifica) |
| L132_art_9_GDPR | Q64 (trattamento dati sanitario), Q67 (trattamento dati sviluppo IA) |

