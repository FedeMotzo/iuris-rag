# UC1 — Eval classificazione AI Act (run diagnostico)

Gold: `data/benchmark/gold_uc1_classification.json` (2026-06-09). Modello classify(): vedi .env (Anthropic Sonnet). Corpus read-only (fetch-by-id sul set fisso).

**Lettura.** I `positive`/`negative` sono gold netto → strict pass/fail. Gli `edge` (incl. i 6 ri-tipizzati, ora positive) dipendono dalla bozza Orientamenti art. 6: per gli edge ANCORA edge si affianca la lettura difendibile del gold senza pass/fail. Candidate-match = recall dei candidati attesi (punto Allegato III / lettera art. 5 / flag 6(1)). Riporta, non decide.

## Tabella per-scenario

| id | tipo | settore | gold verdict | predicted | gold cand | pred cand | verdict ✓ | cand ✓ |
|---|---|---|---|---|---|---|:--:|:--:|
| S01 | positive | PA | vietato | vietato | art5:h | AIII:1,6 art5:h | ✅ | Y |
| S02 | negative | banking | non-HR | non-HR | — | — | ✅ | — |
| S03 | edge | insurance | AIII | AIII | AIII:1 | AIII:1 | ✅ | Y |
| S04 | edge | PA | AIII | AIII | AIII:2 | AIII:2 | ✅ | Y |
| S05 | edge | PA | non-HR | non-HR | — | — | ✅ | — |
| S06 | positive | PA | AIII | AIII | AIII:3 | AIII:3 | ✅ | Y |
| S07 | positive | PA | AIII | AIII | AIII:3 | AIII:3 | ✅ | Y |
| S08 | edge | PA | non-HR | non-HR | — | — | ✅ | — |
| S09 | positive | insurance | AIII | AIII | AIII:4 | AIII:4 | ✅ | Y |
| S10 ⚑6(3) | edge | insurance | non-HR | non-HR | — | — | ✅ | — |
| S11 | edge | banking | AIII | AIII | AIII:4 | AIII:4 | ✅ | Y |
| S12 | positive | PA | AIII | AIII | AIII:5 | AIII:5 | ✅ | Y |
| S13 ⚑6(3) | edge | PA | non-HR | non-HR | — | — | ✅ | — |
| S14 | positive | banking | AIII | AIII | AIII:5 | AIII:5 | ✅ | Y |
| S15 | edge | banking | non-HR | non-HR | — | — | ✅ | — |
| S16 | positive | insurance | AIII | AIII | AIII:5 | AIII:5 | ✅ | Y |
| S17 ⚑multi | positive | healthcare | AIII | AIII | AIII:5 | AIII:5 6(1) | ✅ | Y |
| S18 | positive | PA | AIII | AIII | AIII:6 | AIII:6 | ✅ | Y |
| S19 | positive | PA | AIII | AIII | AIII:6 | AIII:6 | ✅ | Y |
| S20 | positive | PA | AIII | AIII | AIII:6 | AIII:6 | ✅ | Y |
| S21 | positive | PA | AIII | AIII | AIII:7 | AIII:7 | ✅ | Y |
| S22 ⚑6(3) | edge | PA | non-HR | non-HR | — | — | ✅ | — |
| S23 | positive | PA | AIII | AIII | AIII:8 | AIII:8 | ✅ | Y |
| S24 ⚑6(3) | edge | PA | non-HR | non-HR | — | — | ✅ | — |
| S25 | positive | PA | AIII | vietato | AIII:8 | AIII:8 art5:a | ❌ | Y |
| S26 | positive | banking | vietato | vietato | art5:a | art5:a,b | ✅ | Y |
| S27 | positive | banking | vietato | vietato | art5:b | AIII:5 art5:b | ✅ | Y |
| S28 | positive | PA | vietato | vietato | art5:c | art5:c | ✅ | Y |
| S29 | positive | PA | vietato | vietato | art5:d | AIII:6 art5:d | ✅ | Y |
| S30 | positive | PA | vietato | vietato | art5:e | AIII:1,6 art5:e | ✅ | Y |
| S31 | positive | banking | vietato | vietato | art5:f | AIII:1,4 art5:f | ✅ | Y |
| S32 | positive | insurance | vietato | vietato | art5:g | AIII:1,5 art5:g | ✅ | Y |
| S33 | positive | PA | vietato | vietato | art5:h | AIII:1,6 art5:h | ✅ | Y |
| S34 | positive | healthcare | 6(1) | 6(1) | 6(1) | 6(1) | ✅ | Y |
| S35 | negative | healthcare | non-HR | non-HR | — | — | ✅ | — |
| S36 | edge | altro | 6(1) | 6(1) | 6(1) | 6(1) | ✅ | Y |
| S37 ⚑6(3) | edge | insurance | non-HR | non-HR | — | — | ✅ | — |
| S38 ⚑6(3) | edge | PA | non-HR | non-HR | — | — | ✅ | — |
| S39 ⚑6(3) | edge | banking | non-HR | non-HR | — | — | ✅ | — |
| S40 ⚑6(3) | edge | banking | non-HR | non-HR | — | — | ✅ | — |
| S41 | positive | insurance | AIII | AIII | AIII:5 | AIII:5 | ✅ | Y |
| S42 | negative | banking | non-HR | non-HR | — | — | ✅ | — |
| S43 | negative | insurance | non-HR | non-HR | — | — | ✅ | — |
| S44 | negative | banking | non-HR | non-HR | — | — | ✅ | — |
| S45 | negative | healthcare | non-HR | non-HR | — | — | ✅ | — |
| S46 | negative | PA | non-HR | non-HR | — | — | ✅ | — |
| S47 | edge | insurance | non-HR | non-HR | — | — | ✅ | — |
| S48 | edge | healthcare | non-HR | 6(1) | — | 6(1) | ❌ | — |
| S49 | edge | banking | non-HR | non-HR | — | — | ✅ | — |
| S50 ⚑multi | positive | PA | AIII | AIII | AIII:5 | AIII:5 6(1) | ✅ | Y |

## Confusion matrix verdetto (righe=gold, colonne=predetto)

| gold ↓ \ pred → | vietato | AIII | 6(1) | non-HR | tot |
|---|--:|--:|--:|--:|--:|
| **vietato** | 9 | 0 | 0 | 0 | 9 |
| **AIII** | 1 | 17 | 0 | 0 | 18 |
| **6(1)** | 0 | 0 | 2 | 0 | 2 |
| **non-HR** | 0 | 0 | 1 | 20 | 21 |

## Accuratezza per tipo

| tipo | n | verdict accuracy | candidate accuracy (su scorabili) |
|---|--:|--:|--:|
| positive | 25 | 0.96 | 1.00 |
| negative | 7 | 1.00 | — |
| edge | 18 | 0.94  *(edge: NON pass/fail — vedi sotto)* | 1.00 |

**Strict accuracy positive+negative (gold stabile): 31/32 = 0.97.**

## Edge — gold-vs-predetto (NON pass/fail; divergenze marcate)

Gli `edge` restano edge: si affianca la lettura difendibile del gold alla risposta del classificatore. ⚠ = divergenza.

| id | gold (difendibile) | predicted | divergenza |
|---|---|---|:--:|
| S03 | AIII | AIII |  |
| S04 | AIII | AIII |  |
| S05 | non-HR | non-HR |  |
| S08 | non-HR | non-HR |  |
| S10 | non-HR | non-HR |  |
| S11 | AIII | AIII |  |
| S13 | non-HR | non-HR |  |
| S15 | non-HR | non-HR |  |
| S22 | non-HR | non-HR |  |
| S24 | non-HR | non-HR |  |
| S36 | 6(1) | 6(1) |  |
| S37 | non-HR | non-HR |  |
| S38 | non-HR | non-HR |  |
| S39 | non-HR | non-HR |  |
| S40 | non-HR | non-HR |  |
| S47 | non-HR | non-HR |  |
| S48 | non-HR | 6(1) | ⚠ |
| S49 | non-HR | non-HR |  |

## Isolamento esenzione art. 6(3) (S10, S13, S22, S24, S37–S40)

classify() non ha un filtro 6(3) che retroceda un alto-rischio: predice `non alto rischio` SOLO se il giudice marca tutti i punti Allegato III `applies=false`. Qui si vede se ci riesce e cosa fa il flag informativo `art6_3_exception.plausible`.

| id | gold | predicted | punti AIII predetti | 6(3).plausible | esito |
|---|---|---|---|:--:|---|
| S10 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S13 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S22 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S24 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S37 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S38 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S39 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |
| S40 | non-HR | non-HR | — | sì | predetto non-HR (atteso) |

**8/8 scenari 6(3) predetti `non alto rischio` (allineati alla lettura difendibile del gold).**

## Multi-categoria (S17, S50)

Entrambi gli scenari sono 5(a)+5(d): **stesso punto 5**. Il classificatore opera a granularità di PUNTO (`annex_iii` 1-8, senza sotto-lettere) → non può rappresentare due sotto-categorie dello stesso punto. Il check 'entrambi i punti' è N/A a questa granularità (collassa su punto 5).

| id | sotto-lettere gold | punti gold | punti predetti |
|---|---|---|---|
| S17 | 5d,5a | 5 | 5 |
| S50 | 5a,5d | 5 | 5 |
