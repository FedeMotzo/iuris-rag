# Stats dataset `gold_answers_v1.json`

Stato chiusura W7-prep, 2026-05-19.

## Composizione

| campo | valore |
|---|---:|
| Totale entry | **50** |
| `query_type=positive` | **38** |
| `query_type=negative` | **10** |
| `query_type=edge` | **2** (Q5, Q46) |
| `review_status=reviewed` | **50** |
| `review_status=todo` | 0 |
| `review_status=blocked` | 0 |

Distribuzione `review_status` 100% `reviewed` → dataset pronto per Ragas eval.

## Lunghezza `gold_answer` (solo positive, n=38)

| metrica | min | mediana | max |
|---|---:|---:|---:|
| Parole (whitespace split) | 62 | 127 | 169 |
| Frasi (approx, regex split su `.!?`) | 2 | 6 | 15 |
| Citazioni `[cite:CHUNK_ID]` | 2 | 3 | 6 |

Frasi `max=15` è dominato da Q43 (gold con elenchi a punti che il regex
spezza come frasi). La mediana di 6 frasi è una proxy più rappresentativa
della lunghezza tipica.

## Qualità citazioni

| check | risultato |
|---|---|
| Citazioni con `chunk_id` non in `gold_chunks` della stessa entry | **0** |
| Citazioni adiacenti senza spazio (`][cite:`) | **0** |
| Formato canonico `[cite:X] [cite:Y]` (spazio singolo per multi-cite) | rispettato (vedi `core/rag_prompt/system_prompt.it.md`) |

## "Dichiarazione di limite corpus"

Pattern stabile applicato in **11 query positive** (rispetto alle 10
inizialmente stimate — Q9 va inclusa con il proprio scenario C):

| qid | corpus mancante dichiarato |
|---|---|
| Q9 | codice penale italiano (articoli richiamati da 231 art. 24-bis) |
| Q12 | art. 5 AI Act |
| Q13 | dettaglio Capo III AI Act per fornitori e deployer |
| Q15 | art. 5 AI Act |
| Q24 | codice penale + D.Lgs 81/2008 (sicurezza lavoro) |
| Q25 | codice penale italiano |
| Q26 | codice penale italiano |
| Q27 | codice penale + D.Lgs 152/2006 + altri decreti settoriali |
| Q43 | articoli specifici GDPR + Codice Privacy (basi giuridiche, diritti, sicurezza, DPIA, sanzioni) |
| Q45 | altri articoli L. 132/2025 |
| Q49 | norma ISO 9001 (standard tecnico privato) |

**Linguaggio canonico user-facing**: `"...non incluso nel corpus normativo
di riferimento"` (e varianti di concordanza: incluso/inclusi/incluse).
NON usare `"gold_chunks forniti"` o altro lessico tecnico interno.

**Tipi di corpus mancante** raggruppati:
- Norme penali (4 query: Q9, Q25, Q26, Q27, Q24 parziale) → estensione
  v1.1 "codice penale articoli richiamati da 231"
- Articoli AI Act non ingeriti (3 query: Q12, Q13, Q15) → rivalutare se
  re-ingestione completa AI Act è giustificata
- Decreti settoriali italiani (Q24 → D.Lgs 81/2008; Q27 → D.Lgs 152/2006)
  → estensione corpus settoriale v1.1
- Standard ISO (Q49) → fuori scope (copyright)
- Limiti interni al corpus già presente (Q43, Q45) → coperti dalle norme
  primarie già ingerite, sono dichiarazioni di selettività di risposta

## Audit annotazione benchmark eseguito in parallelo

- **6 query 231-related** ispezionate (vedi `spike/ANNOTATION_SAMPLING_231.md`)
- **2 fix di annotazione** applicati: Q5 → edge case, Q9 → gold ridotto
  a `art_24-bis` con scenario C (vedi `PROJECT_CONTEXT.md` voci 30-31)
- Pattern allucinazione LLM-hint su `art_25-undecies` (reati ambientali)
  isolato a Q5 + Q9, **non sistemico**

## File correlati

- `data/benchmark/gold_answers_v1.json` — il dataset
- `data/benchmark/gold_validated_v2.json` — benchmark retrieval (50 query,
  38 positive + 10 negative + 2 edge dopo audit)
- `data/benchmark/BENCHMARK_W3.md` — metriche retrieval aggregate
  (sezioni "Re-aggregazione post-riclassificazione Q5 → edge" e
  "Re-aggregazione post-fix Q9")
- `spike/ANNOTATION_SAMPLING_231.md` — audit annotazione 231
- `spike/Q5_RETRIEVAL_DIAG.md` + `spike/CORPUS_231_DIAG.md` — diagnostica Q5
- `PROJECT_CONTEXT.md` registro decisioni voci 30-32 — chiusura W7-prep
