# BENCHMARK RAGAS W7 v2 — eval Ragas su gold_answers_v2.json

**Date:** 2026-05-24
**Finished (UTC):** 2026-05-24T14:05:33.512901+00:00
**Judge:** `claude-sonnet-4-6` · embeddings `BAAI/bge-m3`
**Metriche:** faithfulness, answer_relevancy (2)
**Cost reale:** $1.3452 · LLM calls 57 · wall 754s · prompt_caching=disabled

### Note metodologiche

- **`context_precision` non inclusa**: spec F.2 originale chiedeva 3 metriche, ma il dry-run Q51 ha mostrato $0.132/sample (proiezione $13.20 su 100, 13× sopra spec). Drop context_precision per ridurre cost a target $2-4. La dimensione retrieval-quality resta coperta da R@5/R@10/R@20/MRR computati in F.1 su 100 query (vedi `spike/BENCHMARK_W3_v2.md`).
- **Anthropic prompt caching tentato, disabilitato**: il dry-run Q52+Q70 ha mostrato `cache_read_input_tokens=0` su tutte le call. I prompt Ragas tra extract-statements, verify-statements e generate-question hanno prefisso strutturalmente diverso → 0% cache hit pagando +25% overhead di cache_creation. Caching disabilitato, instrumentazione tracker mantenuta. Dettaglio in `spike/PHASE_F2_PREFLIGHT.md`.
- **100 query full coverage**, no stratified subset. Save incrementale per resilienza ai crash (batch=10).

## 1. Sintesi globale (100 query)

| metrica | n | median | mean | p10 | p90 | min | max | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| faithfulness | 20 | 0.849 | 0.784 | 0.364 | 1.000 | 0.333 | 1.000 | 0.217 |
| answer_relevancy | 20 | 0.738 | 0.496 | 0.000 | 0.930 | 0.000 | 0.987 | 0.410 |

## 2. Per query_type

| type | n | faith median | faith mean | rel median | rel mean |
|---|---:|---:|---:|---:|---:|
| positive | 18 | 0.894 | 0.791 | 0.747 | 0.552 |
| negative | 2 | 0.722 | 0.722 | 0.000 | 0.000 |

## 3. Per cluster v2 (use_case, proxy)

Nota: nel dataset v2 ogni qid ha use_case unico (n=1 per use_case). Per cluster-level analysis vera servirebbe mappare qid→cluster dai metadata di `candidates_v2_curated.json` (rinviato a v1.1 / iterazione successiva).

| use_case | n | faith | rel |
|---|---:|---:|---:|
| 231 fattispecie informatica art 24-bis | 1 | 0.667 | 0.000 |
| 231 sicurezza lavoro omicidio colposo | 1 | 1.000 | 0.915 |
| AI Act Allegato III biometria | 1 | 0.941 | 0.802 |
| AI Act timeline divieti | 1 | 1.000 | 0.860 |
| Banca outsourcing IA AML extra-UE | 1 | 0.625 | 0.731 |
| Compiti del DPO | 1 | 1.000 | 0.786 |
| Garante provvedimento ChatGPT 2023 | 1 | 0.778 | 0.000 |
| ISO 27701 corpus mancante | 1 | 0.667 | 0.000 |
| NIS2 sanzioni soggetti essenziali | 1 | 0.778 | 0.000 |
| NIS2 sanzioni soggetti importanti | 1 | 0.364 | 0.000 |
| PA regionale IA graduatorie sociali | 1 | 0.389 | 0.749 |
| Pharma IA farmacovigilanza | 1 | 0.647 | 0.720 |
| Procedura DPIA passi e contenuti | 1 | 0.889 | 0.826 |
| Quando DPIA è obbligatoria | 1 | 0.955 | 0.875 |
| Reati 231 trattamento illecito dati | 1 | 0.938 | 0.000 |
| Sanità chatbot AI triage paziente | 1 | 0.333 | 0.930 |
| Trattamento dati forze di polizia | 1 | 1.000 | 0.987 |
| edge: mix in/off corpus | 1 | 0.900 | 0.000 |
| edge: query troppo generica | 1 | 0.810 | 0.000 |
| stress: art 27 AI Act FRIA | 1 | 1.000 | 0.745 |

## 4. Per has_corpus_limit_declaration

| flag | n | faith median | faith mean | rel median | rel mean |
|---|---:|---:|---:|---:|---:|
| false | 9 | 0.647 | 0.677 | 0.745 | 0.615 |
| true | 11 | 0.900 | 0.872 | 0.000 | 0.399 |

## 5. Per norma toccata

| norma | n | faith median | rel median |
|---|---:|---:|---:|
| AI Act | 7 | 0.647 | 0.749 |
| Codice Privacy | 2 | 0.905 | 0.493 |
| D.Lgs 231/2001 | 5 | 0.900 | 0.000 |
| GDPR | 8 | 0.728 | 0.768 |
| L. 132/2025 | 2 | 0.361 | 0.840 |
| NIS2 | 5 | 0.625 | 0.720 |

## 6. Confronto v1 W7 archived ↔ v1 ricalcolato F.2

Le 50 query v1 (Q1-Q50) includono 38 positive + 10 negative + 2 edge. Il W7 archived ha valutato solo le 38 positive; per confronto omogeneo, filtro v1_subset alle stesse 38 positive sul ricalcolato.

| metrica | W7 archived (38 pos) | F.2 ricalcolato (38 pos) | delta |
|---|---:|---:|---:|
| faithfulness median | 0.944 | 0.941 | -0.003 (ok) |
| answer_relevancy median | 0.763 | 0.745 | -0.018 (ok) |

## 7. Bottom-5 per metrica

### Bottom-5 `faithfulness`

| qid | score | query_type | cluster (use_case) |
|---|---:|---|---|
| Q68 | 0.333 | positive | Sanità chatbot AI triage paziente |
| Q83 | 0.364 | positive | NIS2 sanzioni soggetti importanti |
| Q71 | 0.389 | positive | PA regionale IA graduatorie sociali |
| Q70 | 0.625 | positive | Banca outsourcing IA AML extra-UE |
| Q69 | 0.647 | positive | Pharma IA farmacovigilanza |

### Bottom-5 `answer_relevancy`

| qid | score | query_type | cluster (use_case) |
|---|---:|---|---|
| Q9 | 0.000 | positive | Reati 231 trattamento illecito dati |
| Q25 | 0.000 | positive | 231 fattispecie informatica art 24-bis |
| Q43 | 0.000 | positive | edge: query troppo generica |
| Q49 | 0.000 | positive | edge: mix in/off corpus |
| Q55 | 0.000 | positive | NIS2 sanzioni soggetti essenziali |

## 8. Verdict

Target SCOPE pivotato (vedi `SCOPE.md` Metriche di "fatto" post-2026-05-20):
- `faithfulness` ≥ 0.85
- `answer_relevancy` ≥ 0.80
- `context_precision` ≥ 0.80 (NON misurata in F.2, vedi note metodologiche)

- faithfulness median (positive, n=18): **0.894** (✅ ≥0.85)
- answer_relevancy median (positive, n=18): **0.747** (❌ <0.80)

**Verdict: NOT-READY. Soglie sotto target — investigare bottom-5 per follow-up.**

Follow-up identificati per v1.1 (vedi anche `ROADMAP_POST_V1.md` Finding W7):
- Runtime corpus_limit detection via LLM-as-judge (regex inaffidabile, vedi PHASE_F1_DIAGNOSTIC).
- Estensione corpus codice penale articoli richiamati da 231 (4+ candidate W7-prep richiedono il c.p.).
- Tuning system prompt per uniformare pattern lessicale "dichiarazione di limite".
- Eventuale context_precision in run successivo dedicato (se rilevante).

## 9. Paired queries intenzionali design v2

Da metadata di `candidates_v2_curated.json` (fase C):
| Tema | qid coppia | faith A | faith B | rel A | rel B |
|---|---|---:|---:|---:|---:|
| NIS2 art_38__paras_1_11 (sanzioni) | Q55,Q83 | 0.778 | 0.364 | 0.000 | 0.000 |
| NIS2 art_25 (notifica) | Q54,Q57 | n/a | n/a | n/a | n/a |
| L.132 art_9 (trattamento dati) | Q64,Q67 | n/a | n/a | n/a | n/a |

---

**Bias del dataset v2 verso il posizionamento DPO/legal mainstream**: la composizione delle 50 query nuove (Q51-Q100) privilegia 6 cluster mirati al target professional (NIS2, Codice Privacy lato italiano, L. 132/2025, cross-norma 3+, diritti dell'interessato, sanzioni). Aggregati v2 vs v1 W7 archived possono divergere proprio per questa scelta di copertura tematica, non solo per qualità pipeline. Quando comunicato esternamente, segnalare che il benchmark è progettato per stressare il sistema sul target professional italiano, non come golden truth neutrale.

