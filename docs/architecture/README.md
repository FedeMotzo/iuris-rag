# Architettura — overview tecnico

Porta d'ingresso a `docs/architecture/`. Documento di sintesi per
chi vuole capire come è fatto il sistema, dopo aver letto il
benchmark in [`data/benchmark/`](../../data/benchmark/) e prima di
scendere ai singoli moduli.

Riferimenti a monte: [`SCOPE.md`](../../SCOPE.md) per il contratto v1,
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) per il registro
decisioni completo (35 voci datate).

---

## Cosa fa il sistema

Pipeline RAG su corpus di **6 norme primarie** in tema privacy / AI /
cybersecurity / responsabilità d'impresa (GDPR, AI Act, Codice
Privacy, D.Lgs 231/2001, NIS2, L. 132/2025). Input: domanda in
italiano. Output: risposta con citazioni nel formato
`[cite:CHUNK_ID]` verificate strutturalmente contro il set di chunk
recuperati.

Due fasi distinte:

- **Ingestion** (batch, offline): parser → chunking → embedding →
  indicizzazione in Qdrant. Idempotente per UUID v5 deterministico
  da `chunk_id`. Eseguita una volta al setup, ri-eseguita solo se
  cambiano corpus o convenzione di chunking.
- **Query** (online, streaming): retrieval ibrido → rerank →
  espansione grafo opzionale → prompt builder → generazione LLM →
  verifica citazioni. Latenza end-to-end p50 con cloud Sonnet 4.6
  ~12-19 s (vedi [`spike/SMOKE_RAG_PIPELINE_RESULTS.md`](../../spike/SMOKE_RAG_PIPELINE_RESULTS.md)).

Audience del sistema: ricercatori e practitioner RAG legal italiano
(DPO, compliance officer, avvocati privacy/AI) interessati a
metodologia e numeri riproducibili. Vedi [`SCOPE.md`](../../SCOPE.md)
registro 2026-05-20 (pivot pre-fase G).

---

## Diagramma ad alto livello

```
INGESTION (batch, offline)
─────────────────────────────────────────────────

   ┌────────────────────────────────────┐
   │ Sorgenti normative                 │
   │  · Normattiva XML Akoma Ntoso (IT) │
   │  · EUR-Lex HTML rendering (UE)     │
   └─────────────────┬──────────────────┘
                     │
                     v
   ┌──────────────────────────────────┐
   │ italian_legal_parser             │
   │ eur_lex_parser                   │
   │ (+ normattiva_client/eur_lex_*)  │
   └─────────────────┬────────────────┘
                     │
                     v
              ┌────────────┐
              │  chunking  │
              │ (article / │
              │  recital / │
              │  annex pt) │
              └─────┬──────┘
                    │
                    v
            ┌───────────────┐
            │   embedding   │
            │ (bge-m3 +     │
            │  prefix IT)   │
            └───────┬───────┘
                    │
                    v
       ┌────────────────────────┐
       │       Qdrant           │
       │ named vectors:         │
       │  · dense (bge-m3)      │
       │  · sparse (Qdrant/bm25)│
       └────────────────────────┘


QUERY (online, streaming)
─────────────────────────────────────────────────

   ┌────────────┐
   │   query    │
   └─────┬──────┘
         │
         v
   ┌──────────────┐
   │ terminology  │  (espansione sigle, pre-retrieval)
   └─────┬────────┘
         │
         v
   ┌────────────────────────────────────┐
   │ hybrid_retriever                   │
   │  · dense + sparse Qdrant           │
   │  · RRF server-side                 │
   │  · reranker bge-reranker-v2-m3     │
   └─────────────────┬──────────────────┘
                     │
                     v
   ┌────────────────────────────────────┐
   │ normative_graph (opzionale)        │
   │ espansione 1-hop bidirezionale     │
   │ 22 link curati, "not legally val." │
   └─────────────────┬──────────────────┘
                     │
                     v
   ┌────────────────────────────────────┐
   │ rag_prompt                         │
   │ system_prompt.it.md +              │
   │ user prompt [cite:CHUNK_ID]        │
   └─────────────────┬──────────────────┘
                     │
                     v
   ┌────────────────────────────────────┐
   │ llm_provider                       │
   │  · AnthropicProvider (default)     │
   │  · OllamaProvider (fallback)       │
   │ streaming via Iterator             │
   └─────────────────┬──────────────────┘
                     │
                     v
   ┌────────────────────────────────────┐
   │ citation_verifier                  │
   │ regex [cite:X] + set membership    │
   │ soft warning (annotate, no drop)   │
   └─────────────────┬──────────────────┘
                     │
                     v
              ┌─────────────┐
              │ RAGResponse │
              └─────────────┘
```

`serving` è l'orchestratore che compone retrieval → rerank →
generate → verify e gestisce streaming + timings per fase. Vedi
[`core/serving/README.md`](../../core/serving/README.md) per il
dettaglio operativo.

---

## Componenti core

Modulo per modulo, con scopo in 1 frase e link al riferimento
operativo quando esiste. La doc dettagliata oggi esiste solo per
`serving`; gli altri 10 hanno docstring nei sorgenti e test in
`tests/`.

| Modulo | Scopo | Riferimento |
|---|---|---|
| `italian_legal_parser` | Parser XML Akoma Ntoso → chunk gerarchici con eId/URN nativi (Capo > Sezione > Articolo > Comma) | — |
| `eur_lex_parser` | Parser HTML EUR-Lex dual-template (iniziale per considerando, consolidata per articoli) + Annex III AI Act splittato per macro-punto | — |
| `chunking` | Da output parser a chunk indipendenti (`article`, `article_fragment` per oversize, `recital`, `annex_point`) | — |
| `embedding` | Wrapper bge-m3 con instruction prefix italiano obbligatorio, MPS auto-detect, singleton | — |
| `vector_store` | Wrapper Qdrant: ingestion idempotente UUID v5, query API con named vectors dense+sparse | — |
| `hybrid_retriever` | Retrieval ibrido dense + sparse + RRF server-side + reranker post-hoc opzionale; espone `retrieve(graph_links=...)` per integrazione `normative_graph` | — |
| `terminology` | Query expansion via lookup table (`aliases.yaml`) — espande sigle italiane (FRIA, DPIA, scoring) pre-retrieval su entrambi i canali | — |
| `normative_graph` | Espansione 1-hop bidirezionale a valle del retrieval su graph statico 22 link curati a mano, cap 5 chunk espansi per query, deterministica | [`graph.yaml`](../../core/normative_graph/graph.yaml) · [note curatela](../methodology/graph_curation_notes.md) |
| `citation_verifier` | Validazione strutturale `[cite:CHUNK_ID]` contro set retrieval. Soft warning, marker non verificati annotati inline come `[cite:X NON VERIFICATA]` | — |
| `llm_provider` | Interfaccia astratta + `AnthropicProvider` (default) + `OllamaProvider` (fallback). Streaming primo-classe via `Iterator[GenerationChunk]` | — |
| `rag_prompt` | Builder user prompt (`[chunk_id:] hierarchy --- text ===`) + loader system prompt italiano da Markdown editabile | [`system_prompt.it.md`](../../core/rag_prompt/system_prompt.it.md) |
| `serving` | `RAGPipeline` orchestrator retrieval → rerank → generate → citation_verify. Streaming + timings per fase. `query()` sync, `query_stream()` eventi | [`README.md`](../../core/serving/README.md) |

Note: `normattiva_client` e `eur_lex_client` sono moduli di trasporto
HTTP (fetch sorgenti normative) usati una sola volta in ingestion,
non parte del runtime di query — coerentemente non sono elencati
sopra. Il `eur_lex_client` è bloccato da AWS WAF al 2026-05-18:
corpus EUR-Lex v1 ingerito da fixture statiche in
`data/cache/eurlex/IT/` (vedi [`spike/EURLEX_FINDINGS.md`](../../spike/EURLEX_FINDINGS.md)
e [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) voce 15).

---

## Stack tecnico

Scelte chiave del layer di runtime. Per il razionale esteso vedi
il registro decisioni in [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md).

| Layer | Scelta | Razionale (1 riga) |
|---|---|---|
| Embedding | `BAAI/bge-m3` con instruction prefix italiano obbligatorio | Senza prefix le sigle del dominio (DPIA, DPO, AI Act, Garante) hanno similarity 0.38-0.64; con prefix >0.75 |
| Reranker | `BAAI/bge-reranker-v2-m3` (MPS float32, batch=8, max_length=512) | Strict-dominant su dense puro a `rerank_top_k=20`: +6pp R@10, +18pp MRR senza regressioni puntuali |
| Vector DB | Qdrant (Apache-2.0) | Dense + sparse vectors nativi nella stessa collection, RRF server-side da v1.10 |
| BM25 | Qdrant sparse vectors via FastEmbed `Qdrant/bm25` | Single-roundtrip, tokenizzazione preserva suffissi `-bis`/`-undecies` e abbreviazioni `D.Lgs` |
| Parser normativo IT | XML Akoma Ntoso diretto da Normattiva + parser custom XPath (`lxml`) | URN granulari nativi (`eId="art_2-bis"`) e gerarchia esplicita (chapter/section), risparmia post-processing del Markdown |
| Parser EUR-Lex | HTML rendering dual-template (iniziale + consolidata) | AKN inesistente, Formex via Cellar costoso; HTML ha classi ELI semantiche (`oj-ti-art`, `eli-subdivision`) e id stabili (`art_N`, `rct_N`) |
| LLM cloud default | Anthropic Claude Sonnet 4.6 (`claude-sonnet-4-6`) | TTFT ~1.6 s vs prefill cold Qwen 14B ~14-22 s su M4 Pro; costo ~$0.01-0.02/query tollerato dal target professional |
| LLM locale fallback | Qwen2.5-14B Q4_K_M via Ollama | Non degenera su prompt RAG strutturati, ammette i limiti del retrieval, no hallucination cross-norma (Minerva-7B scartato post-spike per repetition loop) |
| Citation verifier | Deterministico strutturale (regex + set membership), no LLM-as-judge | Faithfulness semantica delegata a Ragas (vedi `data/benchmark/BENCHMARK_RAGAS_F2.md`); separazione di concerns |
| LLM serving | Ollama (dev locale) | vLLM rinviato a v1.1, non in scope v1 |
| Orchestrazione | Python diretto in `serving.RAGPipeline` | LangGraph rinviato a v1.1: pipeline lineare attuale non giustifica statefulness |
| Eval | Ragas (faithfulness + answer_relevancy) | Langfuse non integrato in v1; metriche retrieval R@K/MRR/NDCG custom |

Toolchain di sviluppo: Python 3.11+, `pyproject.toml`, `pytest`,
`ruff`. Deploy locale via Docker Compose (`docker-compose.yml`
solo Qdrant in v1, non l'app intera — decisione pivot 2026-05-20:
no demo deployata pubblicamente, vedi [`SCOPE.md`](../../SCOPE.md)
registro).

---

## Decisioni architetturali chiave

5 decisioni che spiegano perché il sistema è fatto così invece che
in modi alternativi plausibili. Numeri di voce riferiti al registro
in [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md).

### 1. XML AKN diretto vs Markdown via `normattiva2md` (voce 11)

**Scelta**: parser custom XPath su XML Akoma Ntoso da
`dati.normattiva.it`, non riuso di `ondata/normattiva_2_md`.

**Razionale**: l'XML AKN ha `eId="art_2-bis"` nativi e gerarchia
esplicita (`chapter/section/article`); il Markdown del parser
upstream perdeva URN granulari e schiacciava la gerarchia in `<h2>`
testuali. Il chunk_id deterministico downstream dipende dall'eId.

### 2. BM25 backend: Qdrant sparse vectors, non Postgres FTS (voce 16)

**Scelta**: BM25 implementato via FastEmbed `Qdrant/bm25` come
sparse vector nella stessa collection del dense.

**Razionale**: lo SCOPE originale prevedeva Postgres FTS "per ridurre
dipendenze" — scelta pre-datata la decisione di tenere Qdrant come
vector DB primario. Sparse nello stesso store elimina il sync
two-backend e abilita RRF nativo server-side. Smoke test ha
confermato che la tokenizzazione preserva `-bis`/`-undecies`/`D.Lgs`.

### 3. Hybrid retrieval con default `rerank_top_k=20` strict-dominant (voce 18)

**Scelta**: setup produttivo è hybrid + reranker top-20, non top-50.

**Razionale**: top-20 è strict-dominant su dense puro (+17pp R@10
con hybrid, +6pp ulteriori con reranker, zero regressioni puntuali).
Top-50 sale di altri +10pp R@10 in media ma introduce regressioni
su 3-4 query (es. Q3 R@10 1.000 → 0.750) — non strict-dominant.
Top-50 resta esposto come parametro opzionale. Vedi
[`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md).

### 4. Citation verifier deterministico, non LLM-as-judge (voce 19)

**Scelta**: validazione strutturale di `[cite:CHUNK_ID]` via regex
+ set membership; marker non verificati annotati inline come
`[cite:X NON VERIFICATA]`, mai rimossi.

**Razionale**: la verifica "il chunk citato è nel contesto?" è
deterministica e non richiede LLM; la verifica "l'affermazione è
coerente col chunk?" è LLM-as-judge e resta a Ragas faithfulness
(W7 + F.2). Separazione di concerns: il verifier ha confine minimo
e testabile, 0 dipendenze esterne. Soft warning preferito a hard
fail per non rompere lo stream in produzione.

### 5. Cloud default, locale fallback (voce 20)

**Scelta**: LLM cloud Anthropic Sonnet 4.6 come default;
Qwen2.5-14B via Ollama come fallback locale / demo offline.

**Razionale**: prefill cold di Qwen 14B Q4_K_M su M4 Pro è 14-22 s
per prompt 2k-3k token, indipendentemente da topologia MPS. Target
audience professional (DPO, studi legali) tollera costo API
trascurabile (~$0.01-0.02/query) in cambio di TTFT ~1.6 s. Locale
resta primo-classe per demo offline e dev testing, con topologia
MPS condizionale documentata (reranker MPS con cloud, reranker
CPU con locale — vedi [`spike/MPS_COABITATION_RESULTS.md`](../../spike/MPS_COABITATION_RESULTS.md)).

### Bonus — Graph multi-normativa statico, "not legally validated" (voce 15 SCOPE registro + W4 PROJECT_CONTEXT)

**Scelta**: 22 link cross-norma curati a mano in `graph.yaml`, con
disclaimer "not legally validated" esplicito nel file.

**Razionale**: il graph funziona come **bonus context per la
generation**, non come strumento di rescue del retrieval —
copertura concettuale 64% delle query positive ma graph-rescued
solo 1 query (Q39). Validazione legale formale, estensione del
catalogo via parsing automatico di rinvii, UI di editing: tutto
v1.1. Vedi [`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md) §
"Graph multi-normativa" e [note di curatela](../methodology/graph_curation_notes.md).

---

## Limiti noti v1

Lista esplicita. Tutti hanno fonte autoritativa nel repo.

- **UC4 Garante rinviato a v1.1**. SCOPE prevede 5 use case
  (classificazione AI Act, timeline obblighi, DPIA vs FRIA,
  provvedimenti Garante, multi-normativa 231+AI). UC1/UC2/UC3/UC5
  risolti; UC4 rimandato — corpus docweb eterogeneo (provvedimenti,
  ordinanze, FAQ) fuori scope tecnico v1. Sistema risponde
  "non trovo riferimenti pertinenti" alle query Garante. Vedi
  [`SCOPE.md`](../../SCOPE.md) registro 2026-05-19.
- **Citation verifier è strutturale, non semantico**. Cattura
  marker malformati ma non riferimenti normativi semanticamente
  sbagliati (es. modello cita considerando invece di articolo
  quando entrambi nel contesto). La verifica semantica è delegata
  a Ragas; verdict F.2 (100q, judge Sonnet 4.6): faith mediana
  0.886, rel mediana 0.815 — sopra entrambe le soglie SCOPE
  (≥0.85, ≥0.80). Vedi [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md).
- **Q5 cross-norma vocabolari disgiunti — zero-recall persistente**.
  Query del benchmark "AI per decisioni HR + responsabilità 231/2001"
  riclassificata da `positive` a `edge` in W7-prep: corpus 231
  completo, gap è di capability retrieval (no overlap lessicale fra
  vocabolario HR e vocabolario penale-amministrativo, no chiusura
  del gap da bge-m3 multilingue). Richiede multi-query / HyDE /
  query rewriting LLM-assisted. Vedi
  [`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md) § "Retrieval
  avanzato v1.1".
- **Detection regex "dichiarazione di limite corpus" obsoleta in v2**.
  Pattern canonico definito in W7-prep
  (`"...non incluso nel corpus normativo di riferimento"`) non
  matcha più nessuna delle 23 risposte F.2 con
  `has_corpus_limit_declaration=true` — drift lessicale sistematico
  del modello, 23/23. La detection runtime via regex è
  inaffidabile; le metriche Ragas non sono sensibili al problema
  (valutano coerenza semantica, non match lessicale). Sostituzione
  con LLM-as-judge in v1.1. Vedi
  [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md)
  follow-up 1.
- **Codice penale fuori corpus v1**. Il D.Lgs 231/2001 elenca i
  reati-presupposto richiamando articoli del c.p. (es. 615-ter,
  635-bis), ma il c.p. non è ingerito. Conseguenza: query come Q9
  ("reati presupposto trattamento illecito dati") rispondibili
  solo a livello di art. 24-bis + dichiarazione esplicita di
  limite. Estensione candidata v1.1: ingerire il sottoinsieme di
  articoli c.p. richiamati dai reati-presupposto 231 (perimetro
  chiuso, ~80-120 articoli). Vedi
  [`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md) § "Estensione
  corpus v1.1".
- **AI Act Annex IV-XIII non ingeriti**. Il parser dedicato copre
  solo Annex III (8 macro-punti). Gli altri 12 allegati non hanno
  parser, sono fuori dal corpus. Nessuna query del benchmark
  attuale li referenzia, ma estensione candidata se emergono
  query reali pertinenti. Vedi
  [`spike/CORPUS_INGESTION_AUDIT.md`](../../spike/CORPUS_INGESTION_AUDIT.md).
- **Topologia MPS reranker condizionale = TODO non attivo**. Il
  `HybridRetriever` non espone `reranker_device` nel costruttore;
  il caller costruisce manualmente il `CrossEncoder` con il device
  giusto (MPS con cloud, CPU con locale). TODO esplicito in
  `core/serving/config.py`. Stima fix: 30 min + 2 test
  regressione. Vedi [`core/serving/README.md`](../../core/serving/README.md)
  § "Topologia MPS".
- **EUR-Lex client bloccato da AWS WAF**. Smoke fetch HTTP 202 +
  JS challenge dal 2026-05-18. Corpus v1 ingerito da fixture
  manuali in `data/cache/eurlex/IT/`. Re-evaluation post-v1:
  Cellar SPARQL endpoint (`data.europa.eu`), non protetto da WAF.
- **Niente async, niente multi-turn, niente caching risposte**.
  Pipeline è sync (con streaming) e stateless. Tutti rinviati
  post-v1.

---

## Link al dettaglio

Niente capitoli dedicati in `docs/architecture/` per corpus e
retrieval: i materiali esistenti in `data/benchmark/` sono
autosufficienti per audience tecnica. Per `serving` la doc
operativa vive nel modulo (no duplicato).

### Corpus
Vedi [`CORPUS_OVERVIEW.md`](../../data/benchmark/CORPUS_OVERVIEW.md)
per struttura URN, prefissi `chunk_id`, copertura per norma, fragment
per oversize, e norme escluse v1. Audit di completezza ingestione in
[`spike/CORPUS_INGESTION_AUDIT.md`](../../spike/CORPUS_INGESTION_AUDIT.md).

### Retrieval
Vedi [`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md) per
numeri retrieval aggregati e per-query (W3+W4), e
[`core/hybrid_retriever/`](../../core/hybrid_retriever/) per il codice
del modulo. Baseline W2 + istruzioni di riproduzione in
[`BENCHMARK_BASELINE.md`](../../data/benchmark/BENCHMARK_BASELINE.md).
Pipeline outputs su gold v2 (100 query) in
[`spike/BENCHMARK_W3_v2.md`](../../spike/BENCHMARK_W3_v2.md).

### Serving
- [`core/serving/README.md`](../../core/serving/README.md) — **riferimento autoritativo**, no duplicato in `docs/architecture/`. Descrive `RAGPipeline`, configurazione `.env`, architettura ASCII, topologia MPS, limiti noti.

### Generation
- Nessuna pagina dedicata. Riferimenti:
  - [`core/rag_prompt/system_prompt.it.md`](../../core/rag_prompt/system_prompt.it.md) — system prompt italiano editabile
  - [`core/llm_provider/`](../../core/llm_provider/) — interfaccia astratta + 2 implementazioni

### Eval
- [`data/benchmark/RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md) — spec metodologica pre-run + esiti W7/F.2
- [`data/benchmark/BENCHMARK_RAGAS_W7.md`](../../data/benchmark/BENCHMARK_RAGAS_W7.md) — risultati W7 (38 positive v1)
- [`data/benchmark/BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md) — risultati F.2 (100 query v2) + verdict GO ready-with-followup

### Metodologia trasversale
- [`docs/methodology/graph_curation_notes.md`](../methodology/graph_curation_notes.md) — note estese di curatela del graph multi-normativa (22 link + 2 in riserva + 3 scartati documentati)
- [`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md) — capability identificate per v1.1
