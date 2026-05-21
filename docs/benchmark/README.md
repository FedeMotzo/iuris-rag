# Benchmark — overview metodologico

Porta d'ingresso al blocco benchmark in `docs/`. Documento di
sintesi per chi vuole capire come è valutato il sistema, dopo aver
letto l'architettura in [`docs/architecture/`](../architecture/) e
prima di scendere ai report di dettaglio.

Le fonti autoritative vivono in
[`data/benchmark/`](../../data/benchmark/). Questo README non
duplica: linka.

Il benchmark è il deliverable centrale del rilascio v1 — vedi
pivot 2026-05-20 in [`SCOPE.md`](../../SCOPE.md) registro modifiche
+ [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) voce 34.

---

## Cosa è il benchmark

Il benchmark Italian Legal RAG è **duale per design**:

- **Retrieval**: misura `R@5`, `R@10`, `MRR`, `NDCG@10` su
  `gold_chunks` annotati manualmente per query.
- **Generation**: misura `faithfulness` (groundedness della
  risposta nei chunk recuperati) e `answer_relevancy` (pertinenza
  della risposta alla domanda) via [Ragas](https://docs.ragas.io)
  con LLM-as-judge.

Le due dimensioni rispondono a domande diverse: "il retrieval porta
chunk utili?" vs "la risposta è fedele al contesto e pertinente
alla domanda?". W3 risponde alla prima, W7 e F.2 alla seconda. Il
verdict "pipeline ready per rilascio v1" si decide su entrambe.

Audience del benchmark: ricercatori e practitioner RAG legal
italiano interessati a metodologia riproducibile e numeri
contestualizzati, non un punto di riferimento universale. Vedi
"Limiti del benchmark" sotto.

---

## Versioni del benchmark

| Versione | Query | Composizione | Uso | Documento autoritativo |
|---|---:|---|---|---|
| v1 | 50 | 38 positive + 10 negative + 2 edge | Retrieval W3+W4, Ragas W7 | [`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md), [`BENCHMARK_RAGAS_W7.md`](../../data/benchmark/BENCHMARK_RAGAS_W7.md) |
| v2 | 100 | 77 positive + 20 negative + 3 edge | Ragas F.2 (verdict v1) | [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md) |

Note:

- **v2 estende v1** con 50 query nuove (Q51-Q100), curate sulla
  base delle lezioni W7-prep. Il brief operativo della curatela è
  in [`BENCHMARK_V2_CURATION_BRIEF.md`](../../data/benchmark/BENCHMARK_V2_CURATION_BRIEF.md)
  (spec scritta a monte, vincolo metodologico). Le 50 nuove sono
  stratificate per cluster: NIS2 mono-norma (6), Codice Privacy
  (5), L. 132/2025 (4), cross-norma 3+ (5), GDPR diritti
  interessato (4), sanzionatorio puro (4), 231 oltre 24-bis (3),
  procedurali "come si fa X" (2), e altri.
- **Q5 e Q46 sono le 2 edge di v1**: vocabolari disgiunti
  cross-norma (Q5) e operativa ChatGPT (Q46). v2 aggiunge 1 edge
  (Q100).
- **Le 38 positive Q1-Q50 sono comuni a v1 e v2**: permettono
  controllo drift judge/pipeline fra W7 (2026-05-20) e F.2
  (2026-05-21). Sul subset comune F.2 misura `faithfulness` median
  -0.042 e `answer_relevancy` median -0.007, entrambi sotto soglia
  metodologica 0.05 → judge e pipeline confermati stabili. Vedi
  [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md)
  § "Drift v1 W7 archived vs F.2 ricalcolato".

Le statistiche dettagliate del dataset v1 (composizione, lunghezze
gold_answer, qualità citazioni, 11 query con dichiarazione di
limite corpus) sono in [`STATS.md`](../../data/benchmark/STATS.md).

---

## Metriche e soglie

### Retrieval (su `gold_chunks` annotati)

Metriche calcolate per ogni query positive ed edge con gold non
vuoto.

| Metrica | Definizione | Setup confrontati |
|---|---|---|
| `Recall@5` | quota di gold nei top-5 retrieval | dense puro · hybrid (BM25+dense+RRF) · hybrid+reranker top-20 · hybrid+reranker top-50 |
| `Recall@10` | quota di gold nei top-10 | (stessi) |
| `MRR` | mean reciprocal rank del primo gold | (stessi) |
| `NDCG@10` | normalized discounted cumulative gain | (stessi) |

**Default produttivo**: `rerank_top_k=20` (hybrid + reranker
top-20). È strict-dominant su dense puro e hybrid puro (+17pp R@10
con hybrid, +6pp ulteriori con reranker top-20, zero regressioni
puntuali). Top-50 sale di altri +10pp medi ma introduce regressioni
isolate → esposto come parametro, non default. Vedi
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) voce 18 +
[`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md).

**Numeri W3+W4 cumulativi** (`hybrid_rrk`, 39 positive
post-riannotazione gold orfani): `R@10=0.712`, `MRR=0.677`,
`NDCG@10=0.634`. Delta vs baseline chiusura W3 (`+11.3 pp` R@10).
Vedi [`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md)
sezione "Re-run post-riannotazione gold orfani" + le successive
re-aggregazioni amministrative (Q5→edge, fix Q9). Pipeline outputs
su gold v2 (100 query) in
[`spike/BENCHMARK_W3_v2.md`](../../spike/BENCHMARK_W3_v2.md).

Baseline W2 dense puro + istruzioni di riproduzione in
[`BENCHMARK_BASELINE.md`](../../data/benchmark/BENCHMARK_BASELINE.md).

### Generation (Ragas + LLM-as-judge)

Metriche calcolate via Ragas su 100 query del dataset v2.

| Metrica | Definizione | Range |
|---|---|---|
| `faithfulness` | quota di statement della risposta groundabili nei chunk recuperati | 0-1 |
| `answer_relevancy` | similarità coseno fra domande retro-generate dalla risposta e query originale | 0-1 |

**Judge**: `claude-sonnet-4-6` (sia W7 sia F.2 — continuità con
W7 dopo cambio judge da Opus per esaurimento credito, vedi
[`RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md)
"Modifica setup judge").

**Soglie metodologiche** definite a monte in
[`RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md)
nota 9 (scritta **prima** del run W7 come vincolo metodologico):

- `faithfulness` gruppo A (non-limit) mediana ≥0.75 (accettabile),
  ≥0.85 (buono), <0.65 (da indagare)
- `answer_relevancy` globale mediana ≥0.80
- 0 query gruppo A con `faithfulness` <0.4

**Numeri F.2** (100 query, judge Sonnet 4.6, 76 minuti, $6.82):
`faithfulness` mediana globale **0.886** (target ≥0.85 PASS),
`answer_relevancy` mediana globale **0.815** (target ≥0.80 PASS).
Verdict: **GO ready-with-followup**. Dettaglio per gruppo / per
norma / bottom-5 / top-5 in
[`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md).

---

## Decisioni metodologiche centrali

5 decisioni che caratterizzano il benchmark e lo distinguono da
approcci standard.

### 1. Tassonomia query: positive / negative / edge

- **positive** — query rispondibile dal corpus, `gold_chunks` non
  vuoti, comportamento atteso = risposta groundata con citazioni
  verified.
- **negative** — query non rispondibile dal corpus (fonti escluse
  v1: codice penale, decreti settoriali, ISO, Direttive UE non
  recepite, EDPB, provvedimenti Garante v1.1), `gold_chunks` vuoti,
  comportamento atteso = fail-graceful con dichiarazione di limite.
- **edge** — query rispondibile in linea di principio ma con limiti
  di capability v1. Esempio canonico: Q5 (cross-norma con
  vocabolari disgiunti, capability multi-query/HyDE v1.1).

La tassonomia è derivata dai 5 use case di
[`SCOPE.md`](../../SCOPE.md) e tracciata per ogni query nel campo
`query_type` di `gold_answers_*.json`.

### 2. Curatela giuridica come secondo livello di validazione

La curatela non si limita a redigere `gold_answer`: include sanity
check giuridico sull'annotazione `gold_chunks`. 3 categorie di flag
formalizzate in W7-prep:

- **gold sbagliato** — errore di annotazione (esempio: Q9 vecchio
  gold conteneva `art_167` Codice Privacy come reato-presupposto
  231, ma 167 è reato autonomo, non presupposto; pattern
  allucinazione `art_25-undecies` isolato a Q5+Q9).
- **corpus insufficiente** — chunk richiesto fuori corpus v1
  (esempio: dispositivo del codice penale richiamato dai
  reati-presupposto 231).
- **capability insufficiente** — architettura v1 non basta
  (esempio: Q5 richiede multi-query / HyDE, capability v1.1).

Pattern di processo replicabile su future iterazioni. Vedi
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) "Curatela gold
answers W7-prep" + audit completo in
[`spike/ANNOTATION_SAMPLING_231.md`](../../spike/ANNOTATION_SAMPLING_231.md).

### 3. Pattern "dichiarazione di limite corpus"

Quando una query richiede contenuto fuori corpus, la `gold_answer`
chiude con dichiarazione esplicita user-facing:
`"...non incluso nel corpus normativo di riferimento"` (con
varianti di concordanza). Pattern formalizzato in W7-prep,
applicato in 11 query positive di v1 + esteso a v2 con flag
`has_corpus_limit_declaration=true` (23 query in v2).

In F.2 il pattern lessicale canonico **non è più rispettato**
runtime: il modello Sonnet 4.6 usa varianti ("il contesto fornito
non contiene riferimenti sufficienti…"). Drift lessicale 23/23 sul
flag a monte. La detection runtime via regex è ufficialmente
inaffidabile (vedi follow-up 1 sotto). Le metriche Ragas non sono
sensibili al drift — valutano coerenza semantica, non match
lessicale.

### 4. Specifica a monte (spec-first)

`RAGAS_RUN_NOTES.md` è stato scritto **prima** del run W7, con
soglie + criteri di decisione `ready/not-ready` espliciti. Lo
stesso vincolo è stato applicato a F.2 (le note 1-9 a monte sono
state preservate immutate; gli esiti W7 e F.2 sono in coda). Le
modifiche metodologiche post-run sono dichiarate esplicitamente:

- W7 segregò Q35/Q19 come "runtime corpus limit" ex-post, con
  motivazione (falsi negativi del flag a monte).
- F.2 eredita il flag dal dataset (non lo modifica) e dichiara
  questa "lettura segregata via flag dataset" come pattern
  strutturale, non come nuova modifica ex-post.

Nessun ricalcolo silenzioso di aggregati per spostare la mediana
sopra soglia. Pattern di onestà metodologica.

### 5. Drift control fra run

Le 38 positive Q1-Q50 sono comuni a W7 e F.2. Confronto su stesse
query → `faithfulness` median **−0.042**, `answer_relevancy`
median **−0.007**. Entrambi sotto soglia metodologica 0.05 → judge
e pipeline confermati stabili tra 2026-05-20 e 2026-05-21. Senza
questo controllo F.2 sarebbe un numero isolato non confrontabile.
Causa plausibile del piccolo drift residuo: non-determinismo
reranker MPS (score CrossEncoder varia di pochi millesimi tra run,
documentato in [`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md)).

---

## Limiti del benchmark

Lista esplicita. Nessun limite nascosto.

- **N=38 positive in v1 / N=77 positive in v2** non è
  statisticamente potente per claim generali su "RAG legal
  italiano". Il benchmark caratterizza **questo sistema su questo
  corpus**, non un punto di riferimento universale. Le 100 query
  v2 sono stratificate per cluster ma con n=1-6 per cluster
  (cluster-level analysis è informativo, non inferenziale).
- **Judge singolo (Sonnet 4.6)** introduce bias di severità
  sconosciuto. Non esiste storico Ragas su italiano legale né su
  Sonnet 4.6 come judge. 3-5 divergenze qualitative
  judge-vs-intuizione umana annotate in W7 e F.2 (vedi rispettivi
  report § "Analisi qualitativa bottom-5"). Confronto con judge
  alternativi (Opus, GPT-4o-mini) è follow-up v1.1.
- **Retrieval-bound queries gonfiano lettura aggregata Ragas** se
  non segregate via flag `has_corpus_limit_declaration`. Senza
  segregazione il gruppo A (non-limit) appare peggiore di quanto
  sia. F.2 applica segregazione esplicita (Q35 + Q19 in "Lettura
  segregata via flag dataset" — vedi
  [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md)).
- **Failure mode Ragas `answer_relevancy=0.0` su scope-out**: il
  judge valuta "non pertinente" una risposta che dichiara
  correttamente di non avere i dati. È un fallimento della metrica,
  non del sistema. F.2 mostra distribuzione bimodale
  (mean 0.609 vs median 0.815) come segnale; 28/100 query con
  rel=0.0 esatto. La mediana è la statistica primaria, la mean è
  sanity check secondario sul peso degli zeri.
- **Q5 zero-recall persistente** in v1 e v2: query cross-norma con
  vocabolari disgiunti (AI/HR + reati-presupposto 231), capability
  v1.1 (multi-query/HyDE/query rewriting). Diagnosi in
  [`spike/Q5_RETRIEVAL_DIAG.md`](../../spike/Q5_RETRIEVAL_DIAG.md)
  + [`spike/CORPUS_231_DIAG.md`](../../spike/CORPUS_231_DIAG.md).
  Documentato come capability v1.1 in
  [`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md) § "Retrieval
  avanzato v1.1".
- **Drift lessicale "dichiarazione di limite corpus"** 23/23 in
  F.2: la detection runtime via regex è obsoleta. Le metriche
  Ragas non sono sensibili al drift. La sostituzione con
  LLM-as-judge è follow-up v1.1 #1.

---

## Come riprodurre

I run del benchmark sono riproducibili dagli script in `spike/`.
Le istruzioni operative complete sono in
[`BENCHMARK_BASELINE.md`](../../data/benchmark/BENCHMARK_BASELINE.md)
§ "Come riprodurre / rilanciare" (build candidati gold → apply
gold validato → esegui benchmark retrieval).

Entry-point dei run principali:

- Benchmark retrieval W3+W4 (4 setup × 50 query):
  `scripts/run_benchmark_w3.py` e
  `scripts/run_benchmark_w3_with_expansion.py` (per terminology +
  graph).
- Ragas W7 (38 positive v1):
  `spike/run_ragas_eval.py`.
- Ragas F.2 (100 query v2):
  `spike/run_ragas_eval_v2.py` (configurato con
  `prompt_caching=disabled` post-pre-flight — vedi
  [`spike/PHASE_F2_PREFLIGHT.md`](../../spike/PHASE_F2_PREFLIGHT.md)).

Pre-requisiti: Qdrant up, collection `italian_legal_v1_hybrid`
popolata (865 chunk dopo split annex_III), `.env` con
`ANTHROPIC_API_KEY` per i run cloud.

---

## Verdict v1 e follow-up v1.1

**Verdict F.2 (2026-05-21)**: **GO ready-with-followup**. Pipeline
cloud Sonnet 4.6 promossa al rilascio pubblico v1.0. Vedi
[`SCOPE.md`](../../SCOPE.md) registro 2026-05-21 +
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) voce 35 per la
decisione di sblocco.

3 follow-up v1.1 promossi in
[`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md)
§ "Follow-up v1.1":

1. **Detection automatica `runtime_corpus_limit_observed` via
   LLM-as-judge.** Drift lessicale 23/23 chiude la possibilità di
   usare regex per identificare runtime quando una risposta dichiara
   limite del corpus. Sostituzione: prompt mirato, una call binaria
   per output, popolare il flag automaticamente, validare contro
   flag manuali esistenti (Q19, Q35). Stima: 4-6 ore + ~$1-2.
2. **Validazione incrociata judge.** Rieseguire un sottoinsieme
   (query con `recall@5=1` e `faith` Sonnet judge `<0.7`, es. Q79)
   con secondo judge (Opus 4.7 se budget Anthropic ricostituito,
   oppure GPT-4o-mini per costo ridotto). Discrimina bias judge da
   decomposizione granulare Ragas. Stima: ~$0.50-1 + 1-2 ore.
3. **Tuning system prompt italiano su pattern canonico.** Drift
   23/23 conferma e amplia il finding W7. Modifica chirurgica a
   [`core/rag_prompt/system_prompt.it.md`](../../core/rag_prompt/system_prompt.it.md).
   Non blocca v1.0 (le metriche non dipendono dal pattern
   lessicale); rende affidabile la detection runtime una volta
   implementato il follow-up 1. Stima: 1-2 ore.

Osservazione esplorativa **non promossa** a follow-up: Q79 ("gap
testo norma vs dottrina WP29") — caso isolato con n=1, da
monitorare in benchmark futuri ma non roadmap. Vedi
[`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md)
§ "Osservazioni esplorative".

Evoluzioni architetturali correlate (query cross-norma capability
v1.1, estensione corpus codice penale per reati-presupposto 231,
graph multi-normativa avanzato, validazione legale formale dei link
del graph): vedi [`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md).

---

## File correlati

### Benchmark autoritativi (in `data/benchmark/`)

- [`CORPUS_OVERVIEW.md`](../../data/benchmark/CORPUS_OVERVIEW.md) — struttura corpus v1, convenzioni `chunk_id`, fragment per oversize, norme escluse
- [`STATS.md`](../../data/benchmark/STATS.md) — composizione dataset v1 (lunghezze, citazioni, dichiarazione di limite)
- [`BENCHMARK_BASELINE.md`](../../data/benchmark/BENCHMARK_BASELINE.md) — baseline W2 dense puro + istruzioni di riproduzione
- [`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md) — benchmark retrieval esteso W3+W4 (4 setup × 50 query) + tutti i re-run W4
- [`BENCHMARK_V2_CURATION_BRIEF.md`](../../data/benchmark/BENCHMARK_V2_CURATION_BRIEF.md) — spec a monte della curatela v2 (Q51-Q100)
- [`RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md) — spec metodologica pre-run + esiti W7 e F.2
- [`BENCHMARK_RAGAS_W7.md`](../../data/benchmark/BENCHMARK_RAGAS_W7.md) — risultati Ragas W7 (38 positive v1)
- [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md) — risultati Ragas F.2 (100 query v2) + verdict GO ready-with-followup
- [`gold_answers_v1.json`](../../data/benchmark/gold_answers_v1.json) e [`gold_answers_v2.json`](../../data/benchmark/gold_answers_v2.json) — dataset (gold_chunks + gold_answer + flag)
- [`gold_validated_v2.json`](../../data/benchmark/gold_validated_v2.json) — annotazione retrieval validata (chunk_id verificati in Qdrant)
- [`ragas_aggregates_v2.json`](../../data/benchmark/ragas_aggregates_v2.json) · [`ragas_results_v2.json`](../../data/benchmark/ragas_results_v2.json) · [`ragas_pipeline_outputs_v2.json`](../../data/benchmark/ragas_pipeline_outputs_v2.json) — artefatti primari F.2

### Spike e diagnostica (in `spike/`)

- [`ANNOTATION_SAMPLING_231.md`](../../spike/ANNOTATION_SAMPLING_231.md) — audit annotazione 231 in W7-prep (6 query ispezionate, bug `art_25-undecies` isolato a Q5+Q9)
- [`Q5_RETRIEVAL_DIAG.md`](../../spike/Q5_RETRIEVAL_DIAG.md) + [`CORPUS_231_DIAG.md`](../../spike/CORPUS_231_DIAG.md) — diagnostica Q5 (capability vs gap corpus)
- [`BENCHMARK_DISTRIBUTION_ANALYSIS.md`](../../spike/BENCHMARK_DISTRIBUTION_ANALYSIS.md) + [`V1_VS_V2_OVERLAP_VIEW.md`](../../spike/V1_VS_V2_OVERLAP_VIEW.md) — analisi distribuzione benchmark v1 e overlap v1↔v2 (input alla curatela v2)
- [`SMOKE_GOLD_COMPARISON.md`](../../spike/SMOKE_GOLD_COMPARISON.md) — smoke pre-W7 generazione (5 query) con caveat metodologici per Ragas W7
- [`BENCHMARK_W3_v2.md`](../../spike/BENCHMARK_W3_v2.md) — pipeline outputs su gold v2 (100 query, retrieval-only)
- [`PHASE_E_MERGE_REPORT.md`](../../spike/PHASE_E_MERGE_REPORT.md) — merge v1+v2 → gold_answers_v2.json
- [`PHASE_F1_DIAGNOSTIC.md`](../../spike/PHASE_F1_DIAGNOSTIC.md) — diagnostico pre-F.2 (drift v1 W7 vs F.1, regex pattern canonico)
- [`PHASE_F2_PREFLIGHT.md`](../../spike/PHASE_F2_PREFLIGHT.md) — pre-flight cost F.2 (decisione `prompt_caching=disabled`)
- [`CORPUS_INGESTION_AUDIT.md`](../../spike/CORPUS_INGESTION_AUDIT.md) — audit completezza ingestione corpus (0 query benchmark v1 impattate)
