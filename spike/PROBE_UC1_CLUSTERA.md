# PROBE UC1 Cluster A — retrieval per la classificazione AI Act

Spike read-only. Misura se, per 3 query single-norm (solo AI Act), i chunk portanti della classificazione (`__art_6` + punto Allegato III atteso) emergono nel retrieval e sotto quale **forma** di query. Nessun layer intake costruito: i 3 ARM sono simulati a mano.

## Setup

- **Retriever**: BASE `HybridRetriever` single-norm (stesso pattern di `spike/smoke_rag_pipeline.py`), **nessun** `CrossNormRetriever`, **nessun** filtro `doc_urn` → retrieval sull'intero corpus.
- **Collection**: `italian_legal_v1_hybrid`
- **Mode**: hybrid (RRF dense+bm25) + rerank cross-encoder `BAAI/bge-reranker-v2-m3` (MPS).
- **Profondità**: lista post-rerank `top_k=20`, pool pre-rerank `rerank_top_k=50`.
- **LLM (ARM2)**: `anthropic` / `claude-sonnet-4-6` via `generate_subquery(scenario, "ai_act", llm)`.
- **Match target**: per **suffisso** del `chunk_id` (`endswith`). Rank 1..20 o "non in top-20".
- **Soglia decisione pre-dichiarata**: top-5 (top_k produttivo).

## Q101 — banca / screening CV

**Target** (match per suffisso): `__art_6`, `__annex_III__point_4`

**ARM1 (scenario grezzo)**: Una banca utilizza un sistema AI per analizzare e filtrare automaticamente i CV dei candidati e valutarli in fase di selezione del personale: è classificato ad alto rischio ai sensi dell'Allegato III dell'AI Act?

**ARM3 (dichiarativa ideale)**: Sistema di IA ad alto rischio per il reclutamento e la selezione del personale ex Allegato III punto 4 AI Act / Regolamento UE 2024/1689: analisi e filtraggio delle candidature, valutazione dei candidati.

**ARM2 — sub-query generate verbatim da `generate_subquery` (25)**:

1. Classificazione sistema di IA ad alto rischio ex art. 6 AI Act / Regolamento UE 2024/1689: criteri di classificazione, ambito di applicazione, Allegato III.
2. Allegato III punto 4 lettera a) AI Act / Regolamento UE 2024/1689: sistemi di IA per reclutamento e selezione del personale, filtraggio CV, valutazione candidati.
3. Sistema di gestione dei rischi ex art. 9 AI Act / Regolamento UE 2024/1689: processo iterativo, misure di gestione, rischi residui.
4. Governance dei dati di addestramento ex art. 10 AI Act / Regolamento UE 2024/1689: pratiche di gestione dati, pertinenza, bias, qualità dei dataset.
5. Documentazione tecnica ex art. 11 AI Act / Regolamento UE 2024/1689: redazione prima della commercializzazione, contenuto, aggiornamento.
6. Registrazione automatica degli eventi ex art. 12 AI Act / Regolamento UE 2024/1689: capacità di logging, tracciabilità, periodo di conservazione.
7. Trasparenza e fornitura di informazioni ai deployer ex art. 13 AI Act / Regolamento UE 2024/1689: istruzioni per l'uso, informazioni obbligatorie, chiarezza.
8. Sorveglianza umana ex art. 14 AI Act / Regolamento UE 2024/1689: misure integrate, supervisione durante utilizzo, intervento umano.
9. Accuratezza, robustezza e cybersicurezza ex art. 15 AI Act / Regolamento UE 2024/1689: livelli di accuratezza, resilienza, misure di sicurezza informatica.
10. Obblighi del fornitore di sistemi ad alto rischio ex art. 16 AI Act / Regolamento UE 2024/1689: conformità Capo III, sistema di qualità, registrazione.
11. Sistema di gestione della qualità ex art. 17 AI Act / Regolamento UE 2024/1689: politiche, procedure, responsabilità, documentazione.
12. Conservazione della documentazione ex art. 18 AI Act / Regolamento UE 2024/1689: periodo di conservazione, obblighi del fornitore, accessibilità.
13. Registrazione automatica degli eventi e obblighi di conservazione dei log ex art. 19 AI Act / Regolamento UE 2024/1689: conservazione da parte del fornitore, durata.
14. Azioni correttive e obblighi di informazione ex art. 20 AI Act / Regolamento UE 2024/1689: non conformità, misure correttive, notifica alle autorità.
15. Cooperazione con le autorità competenti ex art. 21 AI Act / Regolamento UE 2024/1689: accesso alla documentazione, obblighi di collaborazione.
16. Responsabilità lungo la catena del valore ex art. 25 AI Act / Regolamento UE 2024/1689: distributore, importatore, deployer considerato fornitore, modifiche sostanziali, ridenominazione.
17. Obblighi del deployer di sistemi ad alto rischio ex art. 26 AI Act / Regolamento UE 2024/1689: conformità istruzioni d'uso, sorveglianza umana, monitoraggio, conservazione log, informativa ai lavoratori.
18. Valutazione d'impatto sui diritti fondamentali ex art. 27 AI Act / Regolamento UE 2024/1689: organismi di diritto pubblico, servizi essenziali, obbligatorietà, procedura.
19. Valutazione di conformità ex art. 43 AI Act / Regolamento UE 2024/1689: procedure applicabili ai sistemi ad alto rischio, controllo interno, terza parte.
20. Dichiarazione di conformità UE ex art. 47 AI Act / Regolamento UE 2024/1689: contenuto, redazione, responsabilità del fornitore.
21. Marcatura CE ex art. 48 AI Act / Regolamento UE 2024/1689: apposizione, regole, visibilità.
22. Registrazione nella banca dati UE dei sistemi ad alto rischio ex art. 49 AI Act / Regolamento UE 2024/1689: obbligo di registrazione, informazioni richieste, banca dati EU.
23. Monitoraggio post-commercializzazione ex art. 72 AI Act / Regolamento UE 2024/1689: piano di monitoraggio, raccolta dati, obblighi del fornitore.
24. Segnalazione di incidenti gravi ex art. 73 AI Act / Regolamento UE 2024/1689: obbligo di notifica, termini, autorità competente.
25. Sanzioni ex art. 99 AI Act / Regolamento UE 2024/1689: violazioni obblighi sistemi ad alto rischio, massimali, fatturato globale.

### Tabella rank

| Target | rank ARM1 | rank ARM2 (best) | rank ARM3 |
|---|---|---|---|
| `__art_6` | 1 | 1 | 4 |
| `__annex_III__point_4` | 11 | 1 | 1 |

### ARM2 — dettaglio rank per sub-query

| # | sub-query (troncata) | __art_6 | __annex_III__point_4 |
|---|---|---|---|
| 1 | Classificazione sistema di IA ad alto rischio ex art. 6 AI Act / Regol… | 1 | non in top-20 |
| 2 | Allegato III punto 4 lettera a) AI Act / Regolamento UE 2024/1689: sis… | 12 | 1 |
| 3 | Sistema di gestione dei rischi ex art. 9 AI Act / Regolamento UE 2024/… | 20 | non in top-20 |
| 4 | Governance dei dati di addestramento ex art. 10 AI Act / Regolamento U… | non in top-20 | non in top-20 |
| 5 | Documentazione tecnica ex art. 11 AI Act / Regolamento UE 2024/1689: r… | non in top-20 | non in top-20 |
| 6 | Registrazione automatica degli eventi ex art. 12 AI Act / Regolamento … | non in top-20 | non in top-20 |
| 7 | Trasparenza e fornitura di informazioni ai deployer ex art. 13 AI Act … | non in top-20 | non in top-20 |
| 8 | Sorveglianza umana ex art. 14 AI Act / Regolamento UE 2024/1689: misur… | non in top-20 | non in top-20 |
| 9 | Accuratezza, robustezza e cybersicurezza ex art. 15 AI Act / Regolamen… | non in top-20 | non in top-20 |
| 10 | Obblighi del fornitore di sistemi ad alto rischio ex art. 16 AI Act / … | non in top-20 | non in top-20 |
| 11 | Sistema di gestione della qualità ex art. 17 AI Act / Regolamento UE 2… | non in top-20 | non in top-20 |
| 12 | Conservazione della documentazione ex art. 18 AI Act / Regolamento UE … | non in top-20 | non in top-20 |
| 13 | Registrazione automatica degli eventi e obblighi di conservazione dei … | non in top-20 | non in top-20 |
| 14 | Azioni correttive e obblighi di informazione ex art. 20 AI Act / Regol… | non in top-20 | non in top-20 |
| 15 | Cooperazione con le autorità competenti ex art. 21 AI Act / Regolament… | non in top-20 | non in top-20 |
| 16 | Responsabilità lungo la catena del valore ex art. 25 AI Act / Regolame… | non in top-20 | non in top-20 |
| 17 | Obblighi del deployer di sistemi ad alto rischio ex art. 26 AI Act / R… | non in top-20 | non in top-20 |
| 18 | Valutazione d'impatto sui diritti fondamentali ex art. 27 AI Act / Reg… | non in top-20 | non in top-20 |
| 19 | Valutazione di conformità ex art. 43 AI Act / Regolamento UE 2024/1689… | 19 | non in top-20 |
| 20 | Dichiarazione di conformità UE ex art. 47 AI Act / Regolamento UE 2024… | non in top-20 | non in top-20 |
| 21 | Marcatura CE ex art. 48 AI Act / Regolamento UE 2024/1689: apposizione… | non in top-20 | non in top-20 |
| 22 | Registrazione nella banca dati UE dei sistemi ad alto rischio ex art. … | non in top-20 | non in top-20 |
| 23 | Monitoraggio post-commercializzazione ex art. 72 AI Act / Regolamento … | non in top-20 | non in top-20 |
| 24 | Segnalazione di incidenti gravi ex art. 73 AI Act / Regolamento UE 202… | non in top-20 | non in top-20 |
| 25 | Sanzioni ex art. 99 AI Act / Regolamento UE 2024/1689: violazioni obbl… | 19 | non in top-20 |

### Top-5 post-rerank per ARM

**ARM1**:
```
   1. art_6  (score=0.9688)
   2. art_7  (score=0.9298)
   3. art_49  (score=0.8762)
   4. recital_57  (score=0.8387)
   5. art_80  (score=0.8035)
```
**ARM3**:
```
   1. annex_III__point_4  (score=0.9955)
   2. recital_57  (score=0.9860)
   3. art_43  (score=0.9790)
   4. art_6  (score=0.9730)
   5. art_7  (score=0.9484)
```

### VERDETTO

**GO** — ARM2 (macchina esistente) mette art_6 E il punto Allegato III atteso in top-5.

## Q102 — comune / edilizia popolare

**Target** (match per suffisso): `__art_6`, `__annex_III__point_5`

**ARM1 (scenario grezzo)**: Un comune italiano usa un sistema AI per calcolare automaticamente il punteggio di accesso agli alloggi di edilizia popolare: è classificato ad alto rischio ai sensi dell'Allegato III?

**ARM3 (dichiarativa ideale)**: Sistema di IA ad alto rischio usato da un'autorità pubblica per valutare l'ammissibilità a prestazioni e servizi pubblici essenziali ex Allegato III punto 5 AI Act / Regolamento UE 2024/1689: assegnazione di alloggi di edilizia residenziale pubblica.

**ARM2 — sub-query generate verbatim da `generate_subquery` (19)**:

1. Classificazione sistema di IA ad alto rischio ex art. 6 AI Act / Regolamento UE 2024/1689: criteri, ambito, applicabilità Allegato III.
2. Allegato III punto 5 lettera b) AI Act / Regolamento UE 2024/1689: accesso a servizi pubblici essenziali, prestazioni sociali, valutazione ammissibilità.
3. Sistema di gestione dei rischi ex art. 9 AI Act / Regolamento UE 2024/1689: processo iterativo, misure di controllo, rischi residui.
4. Governance dei dati di addestramento ex art. 10 AI Act / Regolamento UE 2024/1689: pratiche di gestione dati, pertinenza, bias, qualità dataset.
5. Documentazione tecnica ex art. 11 AI Act / Regolamento UE 2024/1689: redazione, contenuto, aggiornamento, Allegato IV.
6. Registrazione automatica degli eventi ex art. 12 AI Act / Regolamento UE 2024/1689: log, tracciabilità, periodo di conservazione.
7. Trasparenza e fornitura di informazioni al deployer ex art. 13 AI Act / Regolamento UE 2024/1689: istruzioni per l'uso, obblighi informativi.
8. Sorveglianza umana ex art. 14 AI Act / Regolamento UE 2024/1689: misure integrate, supervisione, intervento umano, override.
9. Accuratezza, robustezza e cybersicurezza ex art. 15 AI Act / Regolamento UE 2024/1689: livelli di accuratezza, resilienza, protezione attacchi.
10. Obblighi del deployer ex art. 26 AI Act / Regolamento UE 2024/1689: conformità istruzioni d'uso, sorveglianza umana, conservazione log, informativa lavoratori.
11. Responsabilità lungo la catena del valore ex art. 25 AI Act / Regolamento UE 2024/1689: distributore, importatore, terzo considerato fornitore, modifiche sostanziali, obblighi fornitore originario.
12. Valutazione d'impatto sui diritti fondamentali ex art. 27 AI Act / Regolamento UE 2024/1689: organismi di diritto pubblico, servizi pubblici essenziali, obbligatorietà, procedura.
13. Valutazione di conformità ex art. 43 AI Act / Regolamento UE 2024/1689: procedura, controllo interno, organismo notificato, sistemi ad alto rischio.
14. Dichiarazione di conformità UE ex art. 47 AI Act / Regolamento UE 2024/1689: contenuto, redazione, responsabilità del fornitore.
15. Marcatura CE ex art. 48 AI Act / Regolamento UE 2024/1689: apposizione, condizioni, visibilità, responsabilità.
16. Registrazione nella banca dati UE dei sistemi ad alto rischio ex art. 49 AI Act / Regolamento UE 2024/1689: obbligo di registrazione, soggetti obbligati, informazioni richieste.
17. Monitoraggio post-commercializzazione ex art. 72 AI Act / Regolamento UE 2024/1689: piano, raccolta dati, obblighi del fornitore.
18. Segnalazione di incidenti gravi ex art. 73 AI Act / Regolamento UE 2024/1689: obbligo di notifica, autorità competente, termini, soglie.
19. Sanzioni ex art. 99 AI Act / Regolamento UE 2024/1689: violazioni obblighi sistemi ad alto rischio, massimali, fatturato globale.

### Tabella rank

| Target | rank ARM1 | rank ARM2 (best) | rank ARM3 |
|---|---|---|---|
| `__art_6` | 1 | 1 | 9 |
| `__annex_III__point_5` | non in top-20 | 1 | 1 |

### ARM2 — dettaglio rank per sub-query

| # | sub-query (troncata) | __art_6 | __annex_III__point_5 |
|---|---|---|---|
| 1 | Classificazione sistema di IA ad alto rischio ex art. 6 AI Act / Regol… | 1 | non in top-20 |
| 2 | Allegato III punto 5 lettera b) AI Act / Regolamento UE 2024/1689: acc… | 4 | 1 |
| 3 | Sistema di gestione dei rischi ex art. 9 AI Act / Regolamento UE 2024/… | non in top-20 | non in top-20 |
| 4 | Governance dei dati di addestramento ex art. 10 AI Act / Regolamento U… | non in top-20 | non in top-20 |
| 5 | Documentazione tecnica ex art. 11 AI Act / Regolamento UE 2024/1689: r… | non in top-20 | non in top-20 |
| 6 | Registrazione automatica degli eventi ex art. 12 AI Act / Regolamento … | non in top-20 | non in top-20 |
| 7 | Trasparenza e fornitura di informazioni al deployer ex art. 13 AI Act … | non in top-20 | non in top-20 |
| 8 | Sorveglianza umana ex art. 14 AI Act / Regolamento UE 2024/1689: misur… | non in top-20 | non in top-20 |
| 9 | Accuratezza, robustezza e cybersicurezza ex art. 15 AI Act / Regolamen… | non in top-20 | non in top-20 |
| 10 | Obblighi del deployer ex art. 26 AI Act / Regolamento UE 2024/1689: co… | non in top-20 | non in top-20 |
| 11 | Responsabilità lungo la catena del valore ex art. 25 AI Act / Regolame… | non in top-20 | non in top-20 |
| 12 | Valutazione d'impatto sui diritti fondamentali ex art. 27 AI Act / Reg… | non in top-20 | 19 |
| 13 | Valutazione di conformità ex art. 43 AI Act / Regolamento UE 2024/1689… | 15 | non in top-20 |
| 14 | Dichiarazione di conformità UE ex art. 47 AI Act / Regolamento UE 2024… | non in top-20 | non in top-20 |
| 15 | Marcatura CE ex art. 48 AI Act / Regolamento UE 2024/1689: apposizione… | non in top-20 | non in top-20 |
| 16 | Registrazione nella banca dati UE dei sistemi ad alto rischio ex art. … | non in top-20 | non in top-20 |
| 17 | Monitoraggio post-commercializzazione ex art. 72 AI Act / Regolamento … | non in top-20 | non in top-20 |
| 18 | Segnalazione di incidenti gravi ex art. 73 AI Act / Regolamento UE 202… | non in top-20 | non in top-20 |
| 19 | Sanzioni ex art. 99 AI Act / Regolamento UE 2024/1689: violazioni obbl… | 19 | non in top-20 |

### Top-5 post-rerank per ARM

**ARM1**:
```
   1. art_6  (score=0.9216)
   2. art_7  (score=0.7980)
   3. art_80  (score=0.7910)
   4. art_43  (score=0.7113)
   5. art_49  (score=0.6436)
```
**ARM3**:
```
   1. annex_III__point_5  (score=0.9966)
   2. recital_58  (score=0.9958)
   3. recital_96  (score=0.9623)
   4. annex_III__point_7  (score=0.9603)
   5. art_7  (score=0.9420)
```

### VERDETTO

**GO** — ARM2 (macchina esistente) mette art_6 E il punto Allegato III atteso in top-5.

## Q103 — radiografie / diagnosi

**Target** (match per suffisso): `__art_6`

**ARM1 (scenario grezzo)**: Un sistema AI che analizza immagini radiografiche per supportare la diagnosi di patologie polmonari è ad alto rischio ai sensi dell'AI Act? Chi è il fornitore e chi è il deployer in un contesto ospedaliero?

**ARM3 (dichiarativa ideale)**: Sistema di IA quale componente di sicurezza di un dispositivo medico ex art. 6(1) AI Act / Regolamento UE 2024/1689: classificazione ad alto rischio per rinvio alla normativa di armonizzazione settoriale.

**ARM2 — sub-query generate verbatim da `generate_subquery` (20)**:

1. Classificazione sistema di IA ad alto rischio ex art. 6 AI Act / Regolamento UE 2024/1689: criteri di classificazione, ambito di applicazione, condizioni.
2. Allegato III punto 5 lettera a) AI Act / Regolamento UE 2024/1689: sistemi di IA destinati a essere utilizzati come dispositivi medici, classificazione ad alto rischio.
3. Obblighi del fornitore — sistema di gestione dei rischi ex art. 9 AI Act / Regolamento UE 2024/1689: identificazione, valutazione, mitigazione rischi, ciclo continuo.
4. Obblighi del fornitore — governance dei dati di addestramento ex art. 10 AI Act / Regolamento UE 2024/1689: qualità dati, pratiche di gestione, bias, pertinenza.
5. Obblighi del fornitore — documentazione tecnica ex art. 11 AI Act / Regolamento UE 2024/1689: contenuto, redazione, aggiornamento, allegato IV.
6. Obblighi del fornitore — registrazione automatica eventi ex art. 12 AI Act / Regolamento UE 2024/1689: log, capacità di registrazione, conservazione.
7. Obblighi del fornitore — trasparenza e informazioni al deployer ex art. 13 AI Act / Regolamento UE 2024/1689: istruzioni per l'uso, informazioni obbligatorie, leggibilità.
8. Obblighi del fornitore — sorveglianza umana ex art. 14 AI Act / Regolamento UE 2024/1689: misure integrate, supervisione, intervento umano, override.
9. Obblighi del fornitore — accuratezza, robustezza e cybersicurezza ex art. 15 AI Act / Regolamento UE 2024/1689: livelli di accuratezza, resilienza, protezione attacchi.
10. Responsabilità lungo la catena del valore dell'IA ex art. 25 AI Act / Regolamento UE 2024/1689: distributore, importatore, deployer considerato fornitore, modifiche sostanziali, obblighi fornitore originario.
11. Obblighi del deployer ex art. 26 AI Act / Regolamento UE 2024/1689: conformità istruzioni d'uso, sorveglianza umana, monitoraggio funzionamento, conservazione log, informativa lavoratori.
12. Valutazione d'impatto sui diritti fondamentali ex art. 27 AI Act / Regolamento UE 2024/1689: organismi diritto pubblico, servizi pubblici essenziali, obbligatorietà, procedura.
13. Valutazione di conformità ex art. 43 AI Act / Regolamento UE 2024/1689: procedure applicabili, coinvolgimento organismo notificato, sistemi ad alto rischio.
14. Dichiarazione di conformità UE ex art. 47 AI Act / Regolamento UE 2024/1689: contenuto, redazione, responsabilità del fornitore.
15. Marcatura CE ex art. 48 AI Act / Regolamento UE 2024/1689: apposizione, condizioni, visibilità, sistemi ad alto rischio.
16. Registrazione nella banca dati UE dei sistemi ad alto rischio ex art. 49 AI Act / Regolamento UE 2024/1689: obbligo di registrazione, soggetti obbligati, informazioni richieste.
17. Modifiche sostanziali al sistema di IA ex art. 83 AI Act / Regolamento UE 2024/1689: definizione modifica sostanziale, conseguenze sulla conformità, nuova valutazione.
18. Monitoraggio post-commercializzazione ex art. 72 AI Act / Regolamento UE 2024/1689: piano di monitoraggio, raccolta dati, obblighi del fornitore.
19. Segnalazione di incidenti gravi ex art. 73 AI Act / Regolamento UE 2024/1689: definizione incidente grave, termini di notifica, autorità competente, obblighi del deployer.
20. Sanzioni ex art. 99 AI Act / Regolamento UE 2024/1689: violazioni obblighi fornitore e deployer, massimali, fatturato globale.

### Tabella rank

| Target | rank ARM1 | rank ARM2 (best) | rank ARM3 |
|---|---|---|---|
| `__art_6` | non in top-20 | 1 | 2 |

### ARM2 — dettaglio rank per sub-query

| # | sub-query (troncata) | __art_6 |
|---|---|---|
| 1 | Classificazione sistema di IA ad alto rischio ex art. 6 AI Act / Regol… | 1 |
| 2 | Allegato III punto 5 lettera a) AI Act / Regolamento UE 2024/1689: sis… | 4 |
| 3 | Obblighi del fornitore — sistema di gestione dei rischi ex art. 9 AI A… | non in top-20 |
| 4 | Obblighi del fornitore — governance dei dati di addestramento ex art. … | non in top-20 |
| 5 | Obblighi del fornitore — documentazione tecnica ex art. 11 AI Act / Re… | non in top-20 |
| 6 | Obblighi del fornitore — registrazione automatica eventi ex art. 12 AI… | non in top-20 |
| 7 | Obblighi del fornitore — trasparenza e informazioni al deployer ex art… | non in top-20 |
| 8 | Obblighi del fornitore — sorveglianza umana ex art. 14 AI Act / Regola… | non in top-20 |
| 9 | Obblighi del fornitore — accuratezza, robustezza e cybersicurezza ex a… | non in top-20 |
| 10 | Responsabilità lungo la catena del valore dell'IA ex art. 25 AI Act / … | non in top-20 |
| 11 | Obblighi del deployer ex art. 26 AI Act / Regolamento UE 2024/1689: co… | non in top-20 |
| 12 | Valutazione d'impatto sui diritti fondamentali ex art. 27 AI Act / Reg… | non in top-20 |
| 13 | Valutazione di conformità ex art. 43 AI Act / Regolamento UE 2024/1689… | 17 |
| 14 | Dichiarazione di conformità UE ex art. 47 AI Act / Regolamento UE 2024… | non in top-20 |
| 15 | Marcatura CE ex art. 48 AI Act / Regolamento UE 2024/1689: apposizione… | 11 |
| 16 | Registrazione nella banca dati UE dei sistemi ad alto rischio ex art. … | non in top-20 |
| 17 | Modifiche sostanziali al sistema di IA ex art. 83 AI Act / Regolamento… | non in top-20 |
| 18 | Monitoraggio post-commercializzazione ex art. 72 AI Act / Regolamento … | non in top-20 |
| 19 | Segnalazione di incidenti gravi ex art. 73 AI Act / Regolamento UE 202… | non in top-20 |
| 20 | Sanzioni ex art. 99 AI Act / Regolamento UE 2024/1689: violazioni obbl… | non in top-20 |

### Top-5 post-rerank per ARM

**ARM1**:
```
   1. recital_84  (score=0.9902)
   2. recital_93  (score=0.9883)
   3. recital_155  (score=0.9872)
   4. art_25  (score=0.9830)
   5. art_20  (score=0.9807)
```
**ARM3**:
```
   1. recital_50  (score=0.9969)
   2. art_6  (score=0.9954)
   3. recital_64  (score=0.9933)
   4. recital_52  (score=0.9884)
   5. recital_47  (score=0.9867)
```

### Verifica Q103 — nessun punto Allegato III forzato

- Punti Allegato III nei top-5 **ARM3**: NESSUNO
- Punti Allegato III nei top-5 di **una qualsiasi sub-query ARM2**: NESSUNO

**Conferma assenza contenuto MDR / Allegato I MDR dal corpus** (scroll read-only su `italian_legal_v1_hybrid`, 865 chunk):

- Regolamento MDR **2017/745 NON ingerito come norma autonoma**: la stringa `2017/745` compare in **5 chunk, tutti `doc_urn=eli/reg/2024/1689/oj`** (AI Act: `recital_147`, `art_73`, `recital_46`, `recital_51`, `recital_84`) — solo come **rinvio** nel testo dell'AI Act, mai come testo dispositivo proprio dell'MDR.
- `"dispositivo medico"` compare in 7 chunk, tutti come menzione dentro AI Act/GDPR/NIS2 (`recital_147`, `recital_64`, `art_11`, `art_9`, …), nessun chunk MDR.
- **Nessun chunk di Allegato I** di alcuna norma è presente in corpus (`__annex_I` / `annex_I_` → NESSUNO). ⇒ l'Allegato I MDR (e l'Allegato I AI Act) sono **assenti**.

Conclusione: il rinvio settoriale (art. 6(1) → normativa di armonizzazione MDR) **non è risolvibile dal retrieval** perché il corpus non contiene l'MDR; coerente col verdetto "art. 6 + dichiarazione limite MDR".

### VERDETTO

**GO** — art_6 in top-5 (ARM2=1, ARM3=2); nessun punto Allegato III atteso. Output corretto = art. 6 + dichiarazione limite MDR.

## Sintesi verdetti

| Query | Verdetto |
|---|---|
| Q101 | GO |
| Q102 | GO |
| Q103 | GO |
