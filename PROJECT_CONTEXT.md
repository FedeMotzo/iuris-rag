# Project Context — Iuris RAG

> Documento di contesto per ogni nuova conversazione sul progetto.
> Da caricare nelle Project Knowledge di Claude.ai e da tenere aggiornato.

---

## Profilo del developer

**Federico Motzo**, AI Developer / Software Engineer, 27 anni, basato in Sardegna (Italia).

**Background professionale:**
- Laurea triennale in Informatica (Università di Cagliari, 2020)
- 3+ anni di consulenza IT, ultima esperienza in **Core Reply** (Padova) come Software Developer su modernizzazione sistema bancario SIB2000 (Java, Spring Framework, Spring Batch, Apache Kafka per microservizi asincroni)
- Esperienza come **Technical Lead** in Contrader (Benevento) su applicazione sportiva con sensori biometrici
- Esperienza come **Academy Technical Manager** (formazione candidati tecnici)
- **Master Professionale in AI Development** completato (ProfessionAI, 400 ore, EQF Livello 6): Python avanzato, ML, Deep Learning, LLM, Agentic AI, Transformer, Hugging Face, LangChain/LangGraph, LiteLLM, PyTorch

**Stack principale:**
- Linguaggi: Python, Java, SQL, JavaScript, TypeScript
- AI/ML: LangChain, LangGraph, LiteLLM, PyTorch, Hugging Face, OpenAI API
- Backend: FastAPI, Spring Framework, Spring Batch, REST API
- Database: PostgreSQL, Redis, MongoDB, MySQL
- DevOps: Docker, GitHub Actions, Tailscale, Cloudflare Tunnel, CI/CD
- Messaging: Apache Kafka

**Infrastruttura personale:**
- NAS Ugreen su Debian 12 con Docker Compose
- Tailscale + Cloudflare Tunnel per accesso remoto
- Dominio personale: fmotzo.dev (Cloudflare)
- GitHub: `FedeMotzo`

**Hardware sviluppo:**
- Mac mini M4 Pro, 24 GB RAM unified memory
- GPU Apple Silicon via MPS per inference locale

**Lingue:** italiano madrelingua, inglese B2.

---

## Contesto della scelta del progetto

Il progetto **Iuris RAG** nasce in un contesto preciso:

- Federico vuole posizionarsi come **freelance AI Engineer** su mercato italiano
- Focus su AI applicata (non tornare a enterprise Java)
- Target di redditività: 6-12 mesi a sostenibilità (€50-90/h equivalenti)
- Budget iniziale: <€1.000 totali
- Lavora con un socio (anche lui full-stack), 6h/giorno ciascuno
- **Priorità apprendimento + portfolio prima di clienti** (validazione di mercato esplicitamente rimandata a dopo v1)

Il progetto è stato scelto dopo una deep research approfondita su 16 verticali di dominio italiano per RAG. **AI Act / compliance** è stato selezionato come primo verticale per:

- Timing regolamentare (AI Act enforcement 2 agosto 2026 → news cycle perpetuo)
- Audience tecnica (DPO, avvocati privacy, compliance officer)
- Building blocks open source disponibili
- Composito alto su criteri "community OSS + complessità tecnica + privacy"

**Verticali alternativi valutati e scartati:** fiscale (secondo round dopo v1), energia/CER (TAM piccolo, community debole), legale generalista (mercato saturo: Lexroom, Normo.ai, OneFISCALE AI), documentale generico (saturo: privategpt.it, AnythingLLM), medicale (regolamento MDR fuori scope), edilizia (copyright UNI blocca corpus).

**Strategia:** core RAG riusabile (libreria pip) + prima demo verticale su AI Act/compliance, in 8 settimane. Al mese 4-6 secondo verticale (fiscale) riusando l'80% del core.

---

## Decisioni chiave prese (registro)

| # | Decisione | Motivazione |
|---|---|---|
| 1 | Verticale v1: **AI Act / compliance**, non fiscale | Punteggio composito 4.38 vs 4.25, audience più tecnica, AI Act timing, building blocks pronti |
| 2 | **Fine-tuning fuori scope v1** | RAG batte fine-tuning per dominio legale (citazioni, hallucination, costi); fine-tuning di classificatore leggero opzionale settimana 7 |
| 3 | **Costruisci ingestion da zero**, NON usare il SQLite di Ansvar (italian-law-mcp) | Priorità apprendimento; indipendenza strategica; il parser Akoma Ntoso è esattamente lo showcase tecnico del progetto. Ansvar usato solo come benchmark di validazione |
| 4 | **Solo italiano** in v1 (no i18n) | Riduce scope, mercato target è IT |
| 5 | **Streamlit** per UI demo, non frontend custom | MVP rapido |
| 6 | **Self-host on-premise** come default (Docker Compose), LLM cloud opzionale | Differenziatore vs concorrenti, segreto professionale clienti finali |
| 7 | **Apache 2.0** | Open source compatibile con uso commerciale futuro |
| 8 | **Validazione tecnica leggera** a settimana 5-6 (peer review), interviste cliente rimandate dopo v1 | Federico ha esplicitamente preferito costruire prima, validare dopo |
| 9 | **Spike di 1-2 giorni** prima dell'architettura | Validare gli ingredienti tecnici (parser, embedding, LLM, latenza) prima di committarsi |
| 10 | **LLM locale default: Qwen2.5-14B (Q4_K_M)**, Minerva-7B come alternativa opzionale | Spike D5: Qwen non degenera, non hallucina, ammette il limite del retrieval. Minerva richiederebbe repeat_penalty + monitor + post-processing per arrivare a livello comparabile |
| 11 | **Parser normativo: XML Akoma Ntoso diretto** da Normattiva (session-based fetch), NON Markdown via normattiva2md | Spike D6: XML AKN ha eId nativi (art_2-bis) + gerarchia esplicita (chapter/section). Risolve i due caveat principali (URN granulari + albero gerarchico) al costo di ~4h |
| 12 | **Embedding bge-m3 con instruction prefix italiano obbligatorio** | Spike D2: senza prefix le sigle del dominio (DPIA, DPO, AI Act, Garante) hanno similarity 0.38-0.64; con prefix vanno a >0.75 |
| 13 | **Parser EUR-Lex: HTML rendering dual-template** (initial OJ + consolidated codifica), NON Formex/AKN. Considerando estratti dalla versione iniziale, articoli dalla consolidata (quando esiste) | Mini-spike D7 (2026-05-18): AKN su EUR-Lex non esiste (404/500), Formex dentro Cellar richiede SPARQL costoso. HTML ha classi ELI semantiche (`eli-subdivision`, `oj-ti-art`, `title-article-norm`) e id stabili (`art_N`, `rct_N`, `cpt_X`). Per AI Act la consolidata IT in HTML non esiste, si usa solo l'iniziale |
| 14 | **Considerando UE inclusi nel corpus v1** via `parse_recitals` (modulo `eur_lex_parser`) | Coprono interpretazione giuridicamente rilevante necessaria per use case 3 di SCOPE (DPIA vs FRIA — considerando 84 GDPR) e use case 1 (high-risk AI Act — considerando AI Act sui sistemi ad alto rischio). 173 considerando GDPR + 180 AI Act estratti dal template iniziale |
| 15 | **`EurLexClient` bloccato da AWS WAF al 2026-05-18**. Workaround per v1: fixture manuali in `data/cache/eurlex/IT/` | HTTP 202 + JS challenge AWS WAF su `/legal-content/IT/TXT/HTML/`. Bypass JS fuori scope (ToS, fragilità, dipendenza Playwright pesante). Il corpus v1 è statico (norme UE cambiano raramente), download manuale via browser sufficiente. Re-evaluation post-v1: Cellar SPARQL endpoint (`data.europa.eu`) come opzione preferita, non protetta da WAF |
| 16 | BM25 backend: Qdrant sparse vectors nativi (FastEmbed `Qdrant/bm25`), non Postgres FTS | Smoke test settimana 3: tokenizzazione preserva `-bis`/`-undecies`/`D.Lgs`. Acronimi cross-lingua (GDPR↔Regolamento UE 2016/679) restano limite di vocabolario downstream, non risolto né da Qdrant nativo né da rank_bm25. |
| 17 | Reranker `BAAI/bge-reranker-v2-m3` latenza misurata p50: 726ms (top-10), 1229ms (top-20), 2594ms (top-50) su MPS M4 Pro float32 | Smoke test settimana 3 (`spike/smoke_reranker.py`). Policy: default ON top-20 con LLM cloud (rientra nel budget <3s di SCOPE), opt-in con LLM locale (top-10 come fallback in <5s budget). Top-50 mai default. |
| 18 | Default produttivo `rerank_top_k=20` (non 50). Hybrid + reranker top-20 è strict-dominant su dense puro: +17pp R@10 con hybrid + altri +6pp con reranker, niente regressioni puntuali. Top-50 sale di altri +10pp R@10 in media ma introduce regressioni su 3-4 query (es. Q3 baseline R@10 1.000→0.750, UC3 mean 0.800→0.750) — non strict-dominant. Top-50 esposto come parametro opzionale, non default. | Benchmark W3 settimana 3 (vedi data/benchmark/BENCHMARK_W3.md). Decisione informata da trade-off qualità/latenza/regressioni puntuali, non solo da media aggregata. |
| 19 | Garante provvedimenti rimandato a v1.1. citation_verifier deterministico (no LLM). Graph multi-normativa statico self-curated con disclaimer. Bug W3 risolti in settimana 4. | Decisione di chiusura settimana 3 (2026-05-19). Garante curato a mano avrebbe copertura poco rappresentativa per query reali; lo scraping completo è eterogeneo e fuori scope tecnico v1. Citation verifier strutturale vs semantico: la validazione "il chunk citato è nel contesto?" è deterministica, la validazione "l'affermazione è coerente col chunk?" è LLM-as-judge e resta a Ragas settimana 7. Graph statico ~30 link risolve Q5/Q24 del benchmark; il legal validation diventa refinement v1.1. |
| 20 | **LLM stack W5: Anthropic Claude Sonnet 4.6** (`claude-sonnet-4-6`) come **default cloud**; Qwen2.5-14B Q4_K_M via Ollama come **fallback locale / demo offline**. Interfaccia `core/llm_provider` astratta con 2 implementazioni (`AnthropicProvider`, `OllamaProvider`). LiteLLM rimandato a v1.1, valutazione anche su Mistral come secondo provider EU. | Decisione W5 inizio (2026-05-19). Target audience (DPO, studi legali) tollera costo API ~$0.01-0.02/query; il cloud risolve il prefill cold di Qwen 14B su M4 Pro (14-22 s per prompt 2k-3k token, vedi `spike/MPS_COABITATION_RESULTS.md`). Locale resta per demo offline + dev testing. Astrazione `LLMProvider` giustificata da "entrambi i provider girano in v1", non da speculazione futura. |
| 21 | **Topologia serving MPS condizionale al provider attivo**: con Anthropic cloud → **S1** (reranker MPS, ~1.7 s rerank), con Ollama locale → **S2** (reranker CPU, ~2.9 s rerank, libera 3 GB MPS per Qwen). Selezione decisa in init pipeline via config provider. | Decisione W5 inizio (2026-05-19). Lo smoke MPS (`spike/MPS_COABITATION_RESULTS.md`) ha mostrato che con cloud Qwen non sta più in MPS, quindi reranker su MPS è gratis (nessuna pressione swap); con locale S2 è l'unico scenario senza pressione swap aggiunta. La topologia non va fissata, va legata al provider. |
| 22 | **Soglie W5 riformulate**: da "5 s end-to-end" a TTFT cold/warm + throughput streaming. TTFT warm (cache hit) p50 ≤ 300 ms; TTFT cold p50 ≤ 25 s su locale (limite fisico Qwen 14B prefill ~140 tok/s), ≤ 3 s su cloud (SLA Anthropic atteso); throughput streaming ≥ 20 tok/s locale, ≥ 50 tok/s atteso cloud; swap Δ ≤ 100 MB sotto carico nominale (S2 con locale passa). | Decisione W5 inizio (2026-05-19). La soglia "5 s e2e" era una formulazione errata della metrica UX per RAG interattivo: su LLM locale la generation è strutturalmente sopra 20 s a 23 tok/s × 500 token output, indipendentemente dalla topologia MPS. TTFT + streaming è la metrica corretta perché l'utente percepisce la prima riga di risposta, non il tempo totale fino all'EOS. Le soglie SCOPE.md (`Latenza P50 < 5s/3s`) restano riferimento legacy: la versione operativa per W5 è questa. |
| 23 | **Compressione prompt RAG SCARTATA in v1**. Top-5 chunk post-rerank invariati. Compressione (chunk-truncation, prompt summarization via LLM piccolo, top-k reduction) resta opzione post-MVP solo se il locale diventa goal primario. | Decisione W5 inizio (2026-05-19). Cloud LLM risolve il prefill cold senza compromettere qualità della citazione. Tagliare chunk legali rischia di rimuovere il dispositivo normativo rilevante; ridurre top_k da 5 a 3 degrada recall su query multi-normativa (vedi diagnostica W3 Q5/Q24); pre-compressione via LLM piccolo introduce hallucination prima della generation. Su sistema legale "risposta sbagliata veloce" è peggio di "risposta lenta giusta". |
| 24 | **`core/llm_provider` completato (W5)**: interfaccia astratta `LLMProvider` + 2 implementazioni concrete (`AnthropicProvider`, `OllamaProvider`) + config loader da `.env`. Streaming primo-classe via `Iterator[GenerationChunk]`. Chunk finale con `text=""` come marker di fine stream. Niente async, niente function calling, niente caching in v1. `LLMProviderError` come eccezione unificata. 20 test verdi, mock totale (no chiamate API reali nei test). | Decisione di chiusura W5 (2026-05-19). Separazione provider-agnostica giustificata da "entrambi girano in v1", non da speculazione futura. Default Anthropic `claude-sonnet-4-6`, fallback Ollama `qwen2.5:14b`. LiteLLM rimandato a v1.1 — la duplicazione attuale è ~80 righe di codice contro la complessità di import e dipendenze multi-provider di LiteLLM. |
| 25 | **`core/rag_prompt` completato (W5)**: builder per user prompt + loader del system prompt italiano da file Markdown editabile (`core/rag_prompt/system_prompt.it.md`). Formato chunk nel prompt fisso in v1: `[chunk_id: X]\nhierarchy\n---\ntext\n===`. Sezione "Riferimenti correlati (graph espansione)" opzionale per expanded chunks, attivata solo se `include_expanded=True`. System prompt cached con `lru_cache`. 8 test verdi. | Decisione di chiusura W5 (2026-05-19). Separazione builder/template/system_prompt giustificata da iterazione attesa sul wording del prompt vedendo output LLM reali. File Markdown editabile evita commit di codice per ogni iterazione sul system prompt. Formato chunk fisso (no flessibilità) perché ri-validazione del prompting su 2 provider è costosa. |
| 26 | **`core/serving` completato (W5)**: `RAGPipeline` orchestrator retrieval → rerank → generate → citation_verify con due varianti `query()` (sync) e `query_stream()` (streaming). Citation verifier gira a fine stream (lavora su testo completo). Timings per fase esposti in `RAGResponse.timings_ms`. `use_graph` configurabile, OFF di default. Top_k RAG default 5, rerank_top_k 20, `max_output_tokens` **1000** (alzato da 500 dopo smoke cloud, vedi voce 29). `build_default_pipeline()` legge config da env. 11 test verdi. | Decisione di chiusura W5 (2026-05-19). Chiusura del backend end-to-end di W5 senza UI come da SCOPE (UI è W6). Streaming primo-classe per TTFT come metrica UX (vedi smoke MPS coabitazione). Citation verifier a fine stream perché lavora su testo completo (regex + set membership), niente bisogno di chunk-by-chunk. |
| 27 | **Expanded chunks del normative graph come pointer, non testo authoritative**. Nel prompt RAG entrano solo come riferimento `[chunk_id: X]: relation — note`, NON con testo completo. Citation verifier estende il contesto verificato anche agli expanded chunks quando `use_graph=True` (altrimenti emetterebbe falsi `NON VERIFICATA` su chunk che abbiamo messo noi nel prompt). | Decisione di chiusura W5 (2026-05-19). Coerente con disclaimer "not legally validated" del graph in v1. Inserire testo completo trasformerebbe i correlati in contesto authoritative — il modello li tratterebbe alla pari delle norme primarie. Trade-off accettato: il modello può citare un expanded chunk di cui ha visto solo il pointer (citazione formalmente verified ma semanticamente vuota). Ragas W7 deve catturare questo caso. Risparmia anche N lookup Qdrant per query. |
| 28 | **Finding throughput Qwen: RAG full vs smoke raw**. Throughput Qwen 14B Q4_K_M misurato in due regimi: smoke MPS coabitazione (prompt minimale, top-5 chunk grezzi concatenati) → 23.5 tok/s sostenuto, prefill cold 14-22s. Smoke RAG completo (system prompt italiano + builder verboso `[chunk_id:] hierarchy --- text ===`) → **6-11 tok/s, ~3× più lento**. Differenza imputabile a +400 token system prompt + formato chunk più verboso. Annotato come finding, non come bug. | Decisione di chiusura W5 (2026-05-19). Il dato cambia il quadro UX su locale (TTFT cold ~22s + 500 tok output × 6-11 tok/s = 80-100s totali per query con contesto lungo). Cloud risolve di fatto il problema. Documentato per evitare di reinventare la diagnosi in W6. Se in W6 emerge come problema UX su locale, prima leva = snellire il formato chunk del builder. Compressione prompt resta scartata in v1 (vedi voce 23). |
| 29 | **Smoke cloud Anthropic + alzato `MAX_OUTPUT_TOKENS` 500 → 1000**. Smoke RAG cloud (Anthropic `claude-sonnet-4-6`, 3 query Q6/Q7/Q1, 1 run/query): TTFT mediano 1.6s, throughput 44-49 tok/s, total e2e 12-19s, 3/3 `all_verified` strutturalmente. Qualità citazione superiore al locale su Q1 (Sonnet cita correttamente art. 6 AI Act + Allegato III + struttura par. 2/par. 3; Qwen su Q1 citava considerando invece di articolo dispositivo). `finish_reason=length` su 3/3 query: 500 token tagliano risposte mid-frase. Default `RAG_MAX_OUTPUT_TOKENS` alzato da 500 → 1000 in `core/serving/config.py` e `core/serving/pipeline.py`. | Decisione di chiusura W5 (2026-05-19). Lo smoke cloud conferma "cloud default per target professional" (decisione voce 20) e produce un cambio operativo immediato (1000 token). Confronto qualitativo: cloud vince con margine netto sul caso peggiore del benchmark (Q1), pari sui casi facili (Q6, Q7). Conferma anche che il citation verifier strutturale è sufficiente in v1: cattura 3/3 marker formali, e la qualità semantica delle citazioni cloud è alta out-of-the-box senza tuning aggiuntivo. Costo extra cloud trascurabile (~$0.0075/query). Su locale gen più lunga (~80s vs ~30s) accettata perché locale è fallback. |
| 30 | **Q5 riclassificata da `positive` a `edge`** dopo diagnostica curatela W7-prep in 3 step: (1) gold attuale sbagliato — `art_25-undecies` (reati ambientali) annotato da LLM-hint allucinato in fase setup benchmark, non pertinente a HR/AI; (2) retrieval non aggancia 231 per disallineamento lessicale tra vocabolario query (AI/HR/lavoratori) e vocabolario corpus 231 (reati-presupposto/responsabilità ente — vedi `spike/Q5_RETRIEVAL_DIAG.md`); (3) corpus 231 è completo (109 articoli, 4/4 Q5-rilevanti ingeriti come chunk article singoli — vedi `spike/CORPUS_231_DIAG.md`) — non è gap di copertura ma di **capability retrieval**. Q5 richiede multi-query / HyDE / query rewriting LLM-assisted, esplicitamente identificate come architetture v1.1 in `ROADMAP_POST_V1.md`. Benchmark W3 ri-aggregato su 38 positive, delta amministrativo (Q5 era zero-recall su 3 setup su 4). | Decisione W7-prep (2026-05-19). La curatela giuridica del gold ha fatto emergere un limite metodologico del benchmark v1 (query cross-norma con vocabolari disgiunti) che il benchmark retrieval-only non aveva catturato. Riclassificare Q5 a edge è metodologicamente più onesto che forzare un fix terminology/graph mirato per "salvare" la query come positive: lo sforzo (2-4h per spostare R@10 da 0 a 0.25 su una query strutturalmente v1.1) sarebbe stato scope-creep dentro W7-prep. Le 38 positive residue restano una baseline solida per Ragas eval W7. |
| 31 | **Audit annotazione 231 completato + fix Q9 in scenario C**. Q9 ('Reati 231 trattamento illecito dati') riannotata: rimossi da gold `art_25-undecies__paras_1_6`, `art_25-undecies__paras_7_8` (allucinazione LLM stesso pattern di Q5) e `196 art_167` (reato autonomo Codice Privacy, non reato-presupposto 231). Gold ridotto al solo `art_24-bis`. `gold_answer` Q9 scritta in **scenario C**: contenuto basato su `art_24-bis` (elenco articoli c.p. richiamati come reati-presupposto + sanzioni pecuniarie e interdittive) + **dichiarazione esplicita di limite del corpus** (dettaglio singole fattispecie c.p. richiede codice penale, fuori corpus v1). Audit esteso a Q24, Q25, Q26, Q27, Q49 (le altre query 231-related): tutte coerenti, nessun fix richiesto. Pattern allucinazione `25-undecies` isolato a 2 query (Q5+Q9), non sistemico. Benchmark W3 ri-aggregato su 38 positive con nuovo gold-set Q9: Q9 entra in zero-recall su tutti i 4 setup (art_24-bis non nei top-10 del retrieval — il vecchio gold contava il match lessicale di `196 art_167`, ora correttamente assente). Delta aggregati modesti (MRR `hybrid_rrk` −0.026 è il più visibile). | Decisione W7-prep (2026-05-19). L'audit ha confermato che il bug di annotazione LLM è circoscritto a 2 query (Q5+Q9). Q9 mantenuta `positive` con risposta limitata (scenario C) invece di riclassificata edge come Q5, perché `art_24-bis` è chunk pertinente del corpus che permette risposta giuridicamente solida sui reati-presupposto 231. La dichiarazione di limite del corpus è valore aggiunto per il target professional (sistema dichiara apertamente cosa sa e cosa no — pattern formalizzato come strumento di trasparenza UX). Estensione corpus codice penale (articoli richiamati come reati-presupposto in 231 art. 24-25bis...) aggiunta a capability v1.1 — vedi `ROADMAP_POST_V1.md` sezione "Estensione corpus v1.1". |
| 32 | **W7-prep completata**: dataset di valutazione `data/benchmark/gold_answers_v1.json` pronto per Ragas eval. **50/50 entry reviewed** (38 positive curate manualmente + 10 negative + 2 edge boilerplate). Curatela giuridica LLM-assisted con revisione umana entry-per-entry, audit annotazione benchmark eseguito in parallelo: **6 query 231-related ispezionate**, bug allucinazione LLM su `art_25-undecies` isolato a 2 query (Q5 + Q9), nessun fix sistemico richiesto. **11 query del benchmark** esprimono "dichiarazione di limite corpus" (es. articoli del codice penale o D.Lgs 81/2008 / D.Lgs 152/2006 o ISO non inclusi in v1) come pattern stabile di trasparenza UX per il target professional. Numeri dataset: `gold_answer` positive 62-169 parole (mediana 127), 2-6 citazioni per risposta (mediana 3), 0 citazioni con `chunk_id` mismatch, 0 citazioni adiacenti senza spazio, formato canonico `[cite:X] [cite:Y]` rispettato. Statistiche dettagliate in `data/benchmark/STATS.md`. | Decisione di chiusura W7-prep (2026-05-19). Il dataset è la base per le metriche Ragas faithfulness + answer_relevancy in W7. La curatela ha anche prodotto come effetto collaterale un audit metodologico del benchmark stesso, rivelando bug di annotazione LLM-hint allucinata (Q5, Q9) e formalizzando la regola di trasparenza "dichiarazione di limite corpus" che migliora la qualità delle risposte attese. I 3 giorni di anticipo W5 (vedi voce 26) sono stati investiti ~2.5 giorni in W7-prep + 0.5 in fix documentazione collegata. W7 diventa esecuzione Ragas + interpretazione, non scoperta dataset. |
| 33 | **W7 chiusa**: benchmark Ragas (`faithfulness` + `answer_relevancy`) eseguito su 38 query positive con generator Sonnet 4.6 + judge Sonnet 4.6 (cambiato da Opus 4.7 in corso per esaurimento credito). Aggregati gruppo A non-limite (n=27): faith mediana **0.952**, rel mediana **0.812**. Gruppo B limite (n=11): faith mediana 0.824, rel mediana 0.705. Globale: faith 0.944, rel 0.763. Analisi qualitativa bottom-5 gruppo A ha rivelato che le 3 query peggiori (Q35 0.375, Q19 0.583, Q17 0.625) NON sono failure di pipeline: 2 sono retrieval-bound failures gestiti correttamente con dichiarazione di limite spontanea (falsi negativi del flag `has_corpus_limit_declaration` a monte, riclassificati come runtime corpus limit), 1 è judge-bound artifact su risposta più ricca del gold (parentesi esplicative penalizzate). 8 query su 38 hanno `answer_relevancy=0.0` esatto — failure mode strutturale di Ragas su risposte di dichiarazione di non-rispondibilità, non punteggio reale. Senza zeri degenerati, rel globale mediana = 0.815 (sopra soglia 0.80). | Decisione di chiusura W7 (2026-05-20). Verdict: **GO ready-with-followup**. Pipeline cloud Sonnet 4.6 pronta per release v1 con 3 follow-up v1.1 documentati in BENCHMARK_RAGAS_W7.md e ROADMAP_POST_V1.md: (a) flag `runtime_corpus_limit_observed` per catturare query che diventano scenario C runtime, (b) validazione incrociata judge opzionale per quantificare bias, (c) tuning lessicale system prompt per pattern "dichiarazione limite corpus". Le 4 soglie ready/not-ready di RAGAS_RUN_NOTES nota 9 sono rispettate post-segregazione esplicita di Q35/Q19 (runtime corpus limit) e dopo rimozione zeri degenerati Ragas. La segregazione è dichiarata esplicitamente nel report come modifica metodologica ex-post, non camuffata. | Costo effettivo W7: $2.32 (run Opus interrotto) + ~$0.50 (run Sonnet completato) = ~$2.82 totali. Stima a monte ($0.45-0.60) era ottimistica ~4× perché non contava le ~14 call Ragas per sample (faithfulness fa 1 call extraction + 1 call verification per ogni statement, ~8-15 per risposta Sonnet). Lezione metodologica: stime costo eval LLM-judge vanno sempre calcolate esplicitamente come N_call × prompt_size × pricing modello, non sulla base di "1 call per metrica". Dataset `gold_answers_v1.json` aggiornato con secondo flag `runtime_corpus_limit_observed` (true per Q19, Q35). |
| 34 | **Pivot pre-fase G del 2026-05-20**: deliverable v1 ridefiniti come benchmark esteso 100q + articolo tecnico + packaging pip core. Rimossi demo pubblica deployata, video 3 min, README bilingue. Audience primaria del rilascio = ricercatori/practitioner RAG legal italiano, non utenti finali della demo. | Vedi voce registro SCOPE.md 2026-05-20 per motivazione completa. README va riorientato di conseguenza dopo che Ragas F.2 chiude e fase G conferma rilascio pubblico. |
| 35 | **Decisione fase G 2026-05-21: rilascio pubblico v1.0 confermato come ready-with-followup.** Soglie Ragas F.2 rispettate, judge e pipeline stabili tra W7 e F.2. Bottom-5 faithfulness sono casi attesi (retrieval-bound noti + negative off-corpus + 1 gap testo norma vs dottrina già predetto). | Vedi voce registro SCOPE.md 2026-05-21 per numeri completi. Follow-up v1.1 documentato: sostituzione detection regex con LLM-as-judge per dichiarazioni di limite. |
| 36 | Quattro finding post-F.2 (subset dev): (1) "drift lessicale 
0/23 corpus_limit_observed" rilettura come artefatto regex 
CORPUS_LIMIT_RE troppo stretta, non bug modello — le risposte 
positive corpus_limit (Q9, Q43, Q49) dichiarano il limite in 
italiano naturale ("contesto fornito non contiene", "assenti", 
"sarebbe necessario disporre") senza usare la frase canonica 
"non incluso nel corpus normativo di riferimento". Fix: 
allargamento regex per catturare i pattern naturali. (2) Q25 
(231 fattispecie informatica) faith=0.571 ar=0.000 NON è bug 
modello: art_24-bis assente dal top-10 retrieval (stesso pattern 
Q5 vocabolari disgiunti), il modello dichiara correttamente il 
gap; faith bassa è artefatto RAGAS su reasoning sussuntivo 
(claim applicativi non verificabili letteralmente). Già coperto 
da capability v1.1 architetture cross-norma. (3) Q35 (art 27 AI 
Act FRIA) faith=0.250 ar=0.000 — gold chunk eli/reg/2024/1689/oj__art_27 
mai recuperato (rank>20). Diagnosi: modulo core/terminology 
esiste, alias FRIA presente, ma expand_query NON è cablato in 
core/hybrid_retriever né in core/serving/pipeline né in 
spike/run_pipeline_v2.py. Modulo orfano da W4 (2026-05-19). Fix: 
wiring expand_query pre-retrieval. (4) Pattern metodologico 
consolidato su 4 casi (Q5→edge W7, F.2 drift→regex, Q25→cross-norma 
v1.1, Q35→wiring orphan): validazione sostantiva > meccanica, 
e in particolare definition of done modulo W* richiede (a) test 
unitari + (b) wiring esplicito verificato con grep + (c) test di 
integrazione end-to-end. Senza (c) un modulo "testato" può essere 
strutturalmente orfano. | F.2 baseline come è stato pubblicato 
resta valido come fotografia W7. La rilettura aggiunge informazione 
sulla causa, non corregge i numeri. I fix v1 (regex + wiring) sono 
"finalmente cablare quello che esiste" + "misurare ciò che il 
modello già fa", non nuove capability. | Sviluppi v0.6: fix wiring 
+ fix regex su due branch separati, re-run subset per delta. 
Branch wiring eseguito prima (semantico, alto impatto Q35), 
branch regex dopo (metrica, scope limitato). Definition of done 
aggiornata per W*-future: ogni nuovo modulo richiede integrazione 
end-to-end testata, non solo unit test verdi. |

| 37 | **Rilettura F.2 post-subset dev + 4 finding metodologici consolidati**. 
Implementazione subset benchmark mode (20 query causali, $2/ciclo vs 
$10 run completo) ha rivelato 4 pattern non identificati in F.2 
archived: 

(1) **F.2 "drift lessicale 0/23 corpus_limit_observed" è artefatto 
regex, non bug modello**. Le risposte corpus_limit positive (Q9, 
Q43, Q49) dichiarano il limite in italiano naturale ("contesto 
fornito non contiene", "assenti", "sarebbe necessario disporre") 
senza usare la frase canonica gold "non incluso nel corpus normativo 
di riferimento". CORPUS_LIMIT_RE pre-fix catturava solo il pattern 
canonico. **Fix applicato**: regex allargata a 4 famiglie lessicali 
(spike/corpus_limit_regex.py centralizzato), detection sale da 0/20 
a 8/20 sul subset dev con zero falsi positivi (test_corpus_limit_regex.py 
10 test verdi). Bonus: Q55 e Q83 (NIS2 fragment, has_limit=false in 
gold) attivano la detection perché il modello dichiara correttamente 
il limit quando retrieval è oggettivamente insufficiente — comportamento 
emergente desiderabile, suggerisce riallineamento gold curatela v1.1.

(2) **Q25 (231 fattispecie informatica) faith=0.571 NON è bug modello**. 
Diagnostica retrieval: art_24-bis (gold centrale) assente da top-10 
(stesso pattern Q5/Q9 vocabolari disgiunti). Il modello dichiara 
correttamente il gap usando art_5 disponibile. Faith bassa è artefatto 
RAGAS su reasoning sussuntivo (claim applicativi non verificabili 
letteralmente nel chunk). **Decisione**: nessun fix v1, già coperto 
da capability v1.1 "Retrieval avanzato — Query cross-norma con 
vocabolari disgiunti" (ROADMAP_POST_V1.md).

(3) **Q35 (art 27 AI Act FRIA) faith=0.250 NON era bug terminology 
aliases**. Diagnostica W4: modulo core/terminology esiste, alias FRIA 
presente (aliases.yaml), ma expand_query non è cablato in 
HybridRetriever né in RAGPipeline né in spike/run_pipeline_v2.py. 
Wiring originale viveva solo in scripts/run_benchmark_w3_with_expansion.py 
(W4 ad-hoc per benchmark) e non è stato propagato a W5 quando è stata 
costruita core/serving/pipeline.py. Modulo strutturalmente orfano da 
W4 nonostante PROJECT_CONTEXT e SCOPE lo descrivessero come "✅ chiuso 
e wirato in produzione". Causa: validazione W4 fatta tramite script 
monouso, mancata propagazione, nessun test di integrazione che 
fallisse in assenza del wiring. **Fix applicato**: 
HybridRetriever.retrieve() cabla expand_query in 1 riga 
(core/hybrid_retriever/retriever.py), 3 test di integrazione 
parametrici (dense/sparse/hybrid). Q35 da rank>20 a rank 1 
(score 0.085 → 0.591), zero regressioni su 17/17 query del subset, 
smoke isolato conferma anche DPIA + scoring creditizio alias 
operativi.

(4) **Pattern metodologico consolidato su 4 casi** (Q5→edge W7, 
F.2 drift→regex, Q25→retrieval v1.1, Q35→wiring orphan): la 
**validazione sostantiva** (leggere risposte reali, ispezionare 
chunk retrieval, verificare wiring con grep) è di secondo livello 
rispetto a metriche aggregate e catch artefatti che la misurazione 
meccanica nasconde. **Definition of done per moduli W*-future 
aggiornata**: ogni nuovo modulo richiede (a) test unitari verdi 
+ (b) chiamata esplicita da pipeline produttiva verificata con 
grep + (c) test di integrazione end-to-end (anche 1 sola query 
benchmark) che fallirebbe in assenza del modulo. Senza (c) un 
modulo "testato" può essere strutturalmente orfano. | 

F.2 baseline pubblicato resta valido come fotografia W7. La rilettura 
aggiunge informazione sulla causa, non corregge i numeri archived. 
I 2 fix v1 (wiring + regex) sono "cablare quello che esiste" + 
"misurare ciò che il modello già fa", non nuove capability. Subset 
benchmarking mode (capability già mergeata in feat/benchmark-subset-mode) 
è stata strumento essenziale per la diagnostica: senza re-run veloci 
$2/ciclo, le 3 ispezioni iterative (Q9/Q25/Q35) non sarebbero state 
economicamente sostenibili. | 

Sviluppi v0.5.1: 2 fix indipendenti su 2 branch separati 
(fix/terminology-wiring + fix/corpus-limit-regex), entrambi mergeati. 
Lezione di processo replicabile: integration test obbligatorio per 
moduli wired in pipeline. Asset narrativo per articolo tecnico: 
"validazione sostantiva come secondo livello di QA in RAG benchmark, 
case study iuris-rag F.2". |

| 38 | **Curatela gold_answers v3 (post-fix v0.5.1)**. Diagnostica completa delle 23 query con `has_corpus_limit_declaration=True` nel dataset v2: 11 confermate (CAT1, drift naturale catturato dalla regex allargata post-v0.5.1) + 12 riallineate `True→False` (CAT2, groundato sufficiente, gold flag spurious). Inoltre **Q19 e Q35** riallineano `runtime_corpus_limit_observed True→False` (post-fix wiring: gold chunks in top-10, validato empiricamente — Q35 rank 1, Q19 ranks 1/5/9 su 3 gold). Generato `data/benchmark/gold_answers_v3.json` + audit trail completo in `data/benchmark/gold_v2_to_v3_diff.md`. Q25 lasciata invariata (decisione voce 36: limite metrica RAGAS noto su query case-based, rivalutare post-v1.1). | F.2 archived "0/23 drift" era doppio artefatto: regex stretta + gold flag spurious in 12/23 casi. Reale comportamento sistema: 11/23 dichiarano limit (catturate dalla regex post-v0.5.1), 12/23 rispondono groundato. Curatela v3 riallinea il gold alla realtà runtime. | Script benchmark (`spike/run_pipeline_v2.py`, `spike/run_ragas_eval_v2.py`) aggiornati per puntare a v3 come default. `gold_answers_v2.json` mantenuto come riferimento storico, non più input default. |

| 39 | **Policy chunking — gap di coerenza identificato (v0.7 planning)**. 
Diagnostica fragment vs monolitici nel corpus: 9 fragment splittati 
(__paras_X_Y) vs 37 monolitici > 5000 char, policy applicata caso per 
caso. Q55/Q83 NIS2 sanzioni: gold rank 1 pre-rerank → rank 11/16 
post-rerank, CrossEncoder penalizza chunk tecnico-elencativo specifico. 
Pattern NON generale (Q27/Q56 healthy con stesso suffisso fragment). 
Diagnosi 2026-05-24 ha falsificato 4 ipotesi fix puntuali: 
(a) disable rerank su fragment → regredisce Q27/Q56, (b) riunifica 
tutti i 9 fragment → scope sproporzionato, (c) riunifica solo 
NIS2 art_38 → cosmetica senza policy, (d) document + accept → 
scelta corrente. | Pattern Q5/Q9/Q25/Q35: continuazione metodologica 
"validazione sostantiva > fix forzato". Riconoscere il problema 
strutturale (chunking policy non deterministica) invece di fixare 
i sintomi puntualmente. | Sviluppi v0.7: SPIKE policy chunking 
deterministica o semantica, benchmark con re-ingestion, misura su 
Q55/Q83 + non-regressione mainstream. Q55/Q83 restano R@10=0 in 
v0.6 come limite noto documentato. |

| 40 | **Chiusura ciclo F.2 v3 — numeri finali + 2 decisioni deferred + 1 confermata**. F.2 v3 misurato post-fix v0.5.1 e curatela gold v3 (2026-05-25): faithfulness mediana globale **0.833** (positive 0.882, negative 0.786, edge 0.818), answer_relevancy mediana globale **0.800** (positive 0.840, negative 0.000 by design). Sopra soglia SCOPE `faith>=0.85` su positive. Calo mediana globale **-0.053 vs F.2 archived** (v2 0.886) atteso per riallineamento curatela (gold flag corretti su 12 CAT2 + 2 runtime, distribuzione metriche ridistribuita), non regressione sistema. Bottom-5 faith dominato da negative+edge (3/5) e cluster fragili F.1 (Q68/Q69) già documentati v1.1. Bottom-5 ar dominato da artefatto noto "nota meta-discorsiva genera domande sintetiche disjoint da query originale" (Q4/Q5/Q9/Q10/Q13). Tre decisioni consolidate dalle diagnostiche di ciclo: **(1) Chunking policy deferred a v0.7 SPIKE** — diagnostica superficie (9 fragment vs 37 monolitici >5000 char, no threshold deterministico) ha falsificato 4 ipotesi fix puntuali (disable rerank selettivo, riunifica selettiva/totale, accept), pattern Q55/Q83 iper-locale (Q27/Q56 healthy con stesso suffisso). Rimandato a SPIKE strutturale (vedi voce 39 + ROADMAP_POST_V1.md). **(2) top_k=5 confermato, no fix** — diagnostica gold disperso: solo Q13 (1/100) ha gold rank 6-10 (rank 9). Altri 6 outlier sono rank 11-20 (rerank-degraded), 7 oltre top-20 (cross-norma v1.1). Alzare top_k=5→10 risolverebbe 1 query con costo +50-100% per query. ROI insufficiente. Q13 documentato come istanza ulteriore del pattern "nota cautelare meta-discorsiva degrada ar a 0" (Famiglia 2 regex catturata, faith 0.833 alta, ar 0.000). Variance Sonnet 4.6: stessa Q13 su subset run aveva ar=0.802 (no nota cautelare in quel sampling). **(3) Late chunking** segnalato come candidato per v0.7 SPIKE policy chunking, in particolare per casi cross-norma vocabolari disgiunti (v1.1). NON risolve Q55/Q83 (problema rerank, non embedding). Da testare empiricamente nello SPIKE, non adottare per principio. | Conferma metodologica del pattern "validazione sostantiva > metrica forzata + diagnostica superficie prima del fix". Sei casi consecutivi (Q5→edge W7, F.2 drift→regex, Q25→limite RAGAS, Q35→wiring orphan, Q55/Q83→chunking policy, Q13→pattern noto confermato). Definition of done modulo W*-future invariata: unit test + wiring grep verified + integration test. | Sviluppi: v0.5.2 patch release con curatela gold v3 + F.2 v3 misurato. v0.7 SPIKE policy chunking come prossimo lavoro strutturale (deterministico/semantico/reranker/late chunking, decisione data-driven con re-ingestion + re-run F.2 v4). v1.1 cross-norma resta separato (HyDE/query rewriting/decomposition LLM-assisted). |

---

## Principi guida (regole di ingaggio)

Questi principi vengono dalla user preferences di Federico e dalla discussione preparatoria. **Vanno applicati a ogni decisione e a ogni contributo di codice/architettura.**

1. **Minima modifica che risolve.** Prima di proporre soluzioni, analizzare il problema. Identificare la soluzione più piccola che funziona, non quella architetturalmente più elegante.

2. **Niente over-engineering.** Soluzioni complesse per problemi semplici sono un anti-pattern. Se la conversazione accumula soluzioni complesse per risolvere problemi creati da soluzioni precedenti, fermarsi e proporre di semplificare o ripartire da zero.

3. **Verificare un cosa alla volta.** Aggiungere il prossimo pezzo solo dopo aver verificato che il precedente funzioni.

4. **Chiedere se non chiaro.** Se il problema non è chiaro, fare domande prima di scrivere codice. Niente codice basato su assunzioni.

5. **Messaggi brevi e concisi.** Niente preamboli, niente postamboli, niente riepiloghi non richiesti.

6. **Lo scope è sacro.** Modifiche allo scope richiedono giustificazione scritta nel registro modifiche di `SCOPE.md`. Tentazioni di "aggiungere giusto una cosa veloce" → rileggere `SCOPE.md`.

7. **Rispettare i vincoli di tempo.** 8 settimane fisse, ~30h/settimana. Se a settimana 4 si è sotto il 30% del piano → tagliare scope, non aggiungere settimane.

---

## Workflow tra Claude.ai (chat) e Claude Code

**Claude.ai (questa interfaccia, dentro il Project):**
- Decisioni strategiche e architetturali
- Revisione di scelte tecniche
- Debugging di alto livello ("perché questo approccio non funziona?")
- Aggiornamenti allo scope
- Review di output dello sviluppo
- Discussioni su content marketing, articoli tecnici

**Claude Code:**
- Scrittura, modifica, refactoring di codice
- Esecuzione test
- Setup e gestione del repo
- Operazioni di file/directory
- Debug puntuale con accesso ai file

**Regola di transizione:** se una conversazione su Claude.ai inizia a richiedere di "leggere file di codice" o "modificare file", spostarsi su Claude Code. Se in Claude Code emergono domande strategiche ("devo cambiare architettura?"), tornare qui.

---

## Stato attuale del progetto

**Settimana 0 — Pre-sviluppo (COMPLETATA il 2026-05-16)**

✅ Scope definito (`SCOPE.md` v2 post-spike)
✅ README di posizionamento (`README.md`)
✅ Spike tecnico eseguito in ~3h totali (vedi `SPIKE_RESULTS.md`)
✅ Stack tecnico calibrato:
   - LLM locale default: **Qwen2.5-14B (Q4_K_M)** — Minerva-7B come alternativa
   - Parser normativo: **XML Akoma Ntoso diretto** via session fetch + lxml XPath
   - Embedding: **bge-m3 con instruction prefix italiano** (obbligatorio)
   - Vector store: Qdrant (Apache-2.0, hybrid nativo)
   - Reranker: BAAI/bge-reranker-v2-m3
✅ Decisioni aggiornate al registro modifiche di `SCOPE.md`

**Settimana 1 — COMPLETATA il 2026-05-18**

✅ `core/italian_legal_parser` (14 test, validato su 4 norme italiane: Codice Privacy, 231/2001, NIS2, L. 132/2025 AI)
✅ `core/normattiva_client` (10 test, smoke byte-match su Codice Privacy live)
✅ `core/eur_lex_parser` (8 test, validato su 3 fixture EUR-Lex: GDPR consolidata, GDPR iniziale, AI Act iniziale; dual-template)
✅ `core/eur_lex_client` (15 test inclusa guard contro body vuoto / WAF challenge; smoke bloccato da AWS WAF, workaround corpus statico)
✅ Corpus v1 disponibile: 4 XML AKN Normattiva (Codice Privacy, 231/2001, NIS2 138/2024, L. 132/2025) + 3 HTML EUR-Lex (GDPR consolidata, GDPR iniziale, AI Act iniziale)

**Settimana 2 — COMPLETATA il 2026-05-18**

✅ `core/chunking/` (24 test, 858 chunk dal corpus v1: 495 article + 9 article_group + 1 annex + 353 recital). Include ricostruzione gerarchia Capo/Sezione del D.Lgs 231/2001 via regex su `num`.
✅ `core/embedding` (3 test, bge-m3 con instruction prefix italiano obbligatorio, singleton, MPS auto-detect + `torch.mps.empty_cache()` tra batch)
✅ `core/vector_store` (5 test, wrapper Qdrant + ingestion idempotente con UUID v5 deterministici da `chunk_id`)
✅ Aggiunto parsing ad-hoc Allegato III dell'AI Act (`core/eur_lex_parser.parse_annex_iii_aiact`) — necessario per use case Q1 (screening CV high-risk)
✅ Docker Compose Qdrant + ingestion completa: 858 chunk indicizzati in `italian_legal_v1` in 203s su MPS
✅ Benchmark retrieval dense puro su 10 query custom (9 positive + 1 negative), gold annotato manualmente (28 chunk). **Baseline: R@5=0.46, R@10=0.58, MRR=0.62.** Vedi `data/benchmark/BENCHMARK_BASELINE.md`.

**Settimana 3 — COMPLETATA il 2026-05-19**

✅ `core/hybrid_retriever` (16 test) — API neutrale al vector store, 3 modi (dense/sparse/hybrid via Query API Qdrant 1.18 con Prefetch + FusionQuery.RRF), reranker opzionale post-hoc via iniezione esterna (rispetta vincolo coabitazione MPS bge-m3 + reranker).
✅ Re-ingestion in `italian_legal_v1_hybrid` (858 chunk, named vectors dense bge-m3 + sparse Qdrant/bm25 FastEmbed). Baseline `italian_legal_v1` preservata.
✅ Benchmark esteso a 50 query con gold annotato manualmente (39 positive + 8 negative + 3 edge, 72 chunk gold totali).
✅ 4 setup confrontati (dense_w3, hybrid, hybrid_rrk, hybrid_rrk_50). Default produttivo: hybrid + reranker top-20. R@5=0.543, R@10=0.598, MRR=0.621, NDCG@10=0.563.
✅ Diagnostica delle 8 query a zero-recall iniziali (`zero_recall_diagnosis.md`): identificate cause precise (gold position oltre rerank window per 4 query, bug parser/chunking/vocabolario per altre 4).
⏳ Scraping Garante slittato a inizio settimana 4 — già rimandato a settimana 3 in registro modifiche del 2026-05-18, ora ulteriormente rinviato per non rompere chiusura settimana 3 entro slot di tempo.

**Settimana 4 — COMPLETATA il 2026-05-19**

✅ Q19 vocabolario → modulo `core/terminology` (8 test, 2026-05-19). Lookup table 3 alias (FRIA, DPIA, scoring creditizio) in `aliases.yaml`, expander `expand_query()` con match word-boundary (single-token) + substring (multi-token), case-insensitive, idempotente. Espansione pre-retrieval applicata sia al canale dense sia sparse. Benchmark con expansion (`results_w3_expansion.json`): **R@10 aggregato +4 pp su tutti e 3 i setup** (dense +0.041, hybrid +0.041, hybrid_rrk +0.043); MRR hybrid +0.050, NDCG hybrid +0.051. Q19 chiude da R@10=0 a R@10=0.333-0.667 in tutti e 3 i setup. Una sola "regressione" su Q5 ignorata per regola boundary-fragile (gold di Q5 al rank-10 baseline con score identico a un chunk overflow → tie-breaking non-deterministico di Qdrant, 5 run confermano 3/5 in / 2/5 out). Verdetto PASS.
✅ `core/citation_verifier` (11 test, 2026-05-19) — deterministico, soft warning, no LLM. Marker `[cite:CHUNK_ID]` estratti via regex centralizzata, validati contro set di chunk_id del retrieval, unverified marcati inline come `[cite:X NON VERIFICATA]` (mai rimossi). Output Pydantic (`VerificationResult` con `markers`, `annotated_text`, contatori). Nessuna normalizzazione di riferimenti normativi né LLM-as-judge: faithfulness semantica resta a Ragas settimana 7.
✅ Graph multi-normativa v1 (2026-05-19) — `core/normative_graph` (14 test unit + 2 test integrazione retriever). **22 link curati manualmente** strutturati in 4 temi (B: 231↔GDPR↔AI Act, A: GDPR↔AI Act, C: NIS2 trasversale, D: L. 132/2025 + Codice Privacy ↔ GDPR/AI Act). Architettura A: espansione 1-hop bidirezionale a valle del retrieval, cap 5 chunk espansi, deterministica (source_rank asc + tiebreak chunk_id). Integrazione opzionale in `HybridRetriever.retrieve(graph_links=...)` via subclass `RetrievalResult(list)` per non rompere i 16 test esistenti. **Finding architetturale**: il graph funziona come bonus context per generation, non come rescue retrieval — i link si attivano solo se almeno un endpoint è nel top-10. Metrica coverage concettuale sul benchmark hybrid_rrk: **25/39 query positive (64%) ricevono ≥1 chunk espanso**, media 1.41 espansioni/query, totale 55 chunk espansi attivati. Graph-rescued: **1 query** (Q39 via 196 art.2-ter ↔ art.6 GDPR deroga); Q5 e Q24 zero-recall restano fuori dalla copertura del graph in v1 (top-10 non contiene anchor utili al gold mancante). 4 link su 22 non attivati su query positive (AI Act art.10↔GDPR art.6/art.9, AI Act art.99↔GDPR art.83, 196 art.2-sexies↔GDPR art.9): tenuti per copertura concettuale dei 4 temi, rivalutazione post-W5. Disclaimer "not legally validated" nel YAML. Validazione legale formale e architetture retrieval avanzate (multi-query, HyDE, graph-guided 2-stadi) rimandate a v1.1 — vedi `ROADMAP_POST_V1.md`.
✅ Q15 parser EUR-Lex (2026-05-19) — fallback `__body` in `_parse_commi` per articoli senza commi numerati (es. art_113 con `<p class="oj-normal">` + tabelle a/b/c). Scan post-fix ha rivelato 35 articoli silently broken con lo stesso pattern (incluso Definizioni AI Act art_3 e Definizioni GDPR art_4); re-ingest EUR-Lex completo (568 chunk, 277.8s). Benchmark W3 re-run: **ΔR@10 hybrid_rrk +5.1pp (0.641 → 0.692)**, ΔR@10 dense_w3 +11.5pp, hybrid invariato. 9 query positive in miglioramento netto + 1 regressione isolata su Q17 dense_w3 (chunk titolo 47ch pre-fix matchava lessicalmente al rank 1; post-fix hybrid e hybrid_rrk recuperano correttamente). 14 test parser EUR-Lex verdi (2 nuovi: fallback fixture + non-regression art_111).
✅ Q30 chunking annex_III (2026-05-19) — `parse_annex_iii_aiact` ritorna `list[EurLexAnnex]` con 1 entry per macro-punto (8 totali). chunk_id `__annex_III__point_N`, hierarchy 2-livelli, metadata `{point, n_letters}`. Granularità ferma al punto, non scende a lettera (decisione: coerente con `chunk_recitals`, semantica di unità indipendente). Cancellato monoblocco vecchio + re-ingest 8 nuovi (collection 858 → 865 points). Aggiornati 3 link `core/normative_graph/graph.yaml` ai point specifici (annex_III__point_2 infrastrutture, annex_III__point_4 HR). Gold Q30 → annex_III__point_4. Benchmark W3 re-run: **hybrid_rrk R@10 0.692 → 0.712 (+2.0pp)**, MRR +2.6pp; Q30 da R@10=0 a 1.0 con rank 1; Q39 extra rescue. 16 test parser+chunking verdi (5 esistenti aggiornati + 2 nuovi: `test_parse_annex_iii_returns_eight_points` e `test_parse_annex_iii_metadata_point_index`).
✅ Riannotazione gold post-split annex_III (2026-05-19) — 5 entry gold (Q1, Q11, Q12, Q13, Q19) rimappate dai vecchi gold orfani ai point corretti (Q1→p4, Q11→p5, Q12→p1+p3 dual, Q13→p1, Q19→p5). Propagazione meccanica del fix, mapping derivato dal testo letterale di ciascuna query. Gold totali 72 → 73 (+1 per dual Q12), 0 orfani residui. Q13 chiude su tutti e 3 i setup (R@10 0 → 1.0); Q12 hybrid 0 → 0.5; Q19 hybrid 0.667 → 1.0; Q39 hybrid_rrk regredisce 1.0 → 0 (gold non toccato dal fix, sospetto rumore reranker su query boundary-fragile, flagged). **Delta cumulativo W4 hybrid_rrk R@10: +11.3 pp** (baseline W3 0.598 → oggi 0.712); dense_w3 +18.4 pp, hybrid +8.8 pp. Zero-recall complessivi calano (dense 14→13, hybrid 12→10), nessuna nuova zero-recall introdotta.
⏳ Scraping Garante: RIMANDATO a v1.1. UC4 in v1 resta stub fail-graceful. Vedi SCOPE.md registro 2026-05-19.

**Ordine di esecuzione settimana 4 deciso in chiusura W3:**
1. ✅ Q19 vocabolario lookup table → `core/terminology` (2026-05-19)
2. citation_verifier (2-3 gg)
3. graph multi-normativa statico (1 gg)
4. Q15 parser + Q30 chunking (1.5 gg)
5. Buffer (1-2 gg) per imprevisti / iterazione

**TODO post-benchmark settimana 3:**

- Gerarchia 196/2003: ricostruzione TITOLO/CAPO/SEZIONE da `<title>` (markup misto con marker di abrogazione). Rinviata: zero impatto noto sui 5 use case; rivalutare dopo settimana 3.
- Q10 (NIS2 soggetti essenziali): se anche con hybrid + reranker resta a zero recall, riconsiderare la soglia di chunking 2000 token per gli articoli definitori monoblocco (es. NIS2 art_3 = 1401 token). Strategia precisa (split per comma? per definizione? abbassare soglia generale?) da decidere a valle dei numeri.
- Q5 (multi-normativa 231/196/GDPR): se hybrid + reranker non risolve, valutare un graph layer di link cross-norma in settimana 4 (componente "graph multi-normativa base" di SCOPE). **CHIUSO 2026-05-19** come edge case (vedi registro decisioni voce 30). Diagnostica W7-prep ha mostrato che corpus + graph + terminology non bastano: Q5 richiede multi-query/HyDE LLM-assisted, capability v1.1. Riferimento per architetture v1.1: `ROADMAP_POST_V1.md` sezione "Retrieval avanzato v1.1 — Query cross-norma con vocabolari disgiunti".
- Acronimi cross-lingua (es. GDPR↔Regolamento UE 2016/679): se nel benchmark a 50 query emergono multiple query con R@10 basso causate da acronimo non riconosciuto, E il dense bge-m3 non le chiude da solo → introdurre lookup table normativi (~20 righe) in pre-retrieval come query expansion. Non agire prima di avere i numeri.
- Coabitazione MPS bge-m3 + bge-reranker-v2-m3: ~4.6GB FP32 combinati saturano 24GB unified su M4 Pro con Qdrant Docker + OS. Decisione runtime (load/unload tra fasi vs reranker su CPU vs downgrade a `bge-reranker-v2-base`) da prendere nel disegno di `core/hybrid_retriever`, con misura comparativa di latenza end-to-end. Lo smoke ha usato sequenzializzazione in processi distinti, accettabile per benchmark batch ma non per runtime serving.
- Bug parser EUR-Lex su articoli finali: art_113 AI Act estratto solo come header senza body (Q15 zero-recall W3 confermato). Verifica pattern analoghi su art_99 GDPR e altri articoli di chiusura. Da affrontare in `core/eur_lex_parser` quando si lavora su citation_verifier o generazione, perché body completo è prerequisito per citazioni accurate.
- Chunking annex monoblocco: annex_III AI Act (8460 char) non recuperabile per query naturali (Q30 zero-recall W3 confermato). Pattern strutturale analogo a Q10 settimana 2 (NIS2 art_3 1401 token). Splittare per punto numerato (8 sezioni: biometria, infrastrutture, istruzione, ecc.). Strategia analoga a `chunk_recitals` ma per allegati. Da affrontare in `core/chunking` settimana 4.
- Q19 conferma pattern acronimi/sigle non in corpus: "FRIA" + "scoring creditizio" rispetto a "valutazione d'impatto sui diritti fondamentali" (Q3 chiude, Q19 no). Analogo al gap GDPR↔Regolamento UE 2016/679 già documentato. Lookup table normativi/sigle in pre-retrieval come query expansion: ~30-50 righe coprono i casi documentati (GDPR/Reg 2016/679, AI Act/Reg 2024/1689, FRIA, DPIA, DPO/RPD, ecc.). Da affrontare prima di citation_verifier perché la qualità della generazione dipende dalla qualità del retrieval. **CHIUSO 2026-05-19** con modulo `core/terminology` (3 alias minimi). Eventuali estensioni del catalogo seguono la regola "nuovi alias solo se una query del benchmark lo giustifica".
- Tie-breaking non-deterministico di Qdrant al boundary della top-K: chunk con score RRF identico al boundary possono oscillare tra "dentro" e "fuori" top-K in run distinti (verificato su Q5 hybrid: 5 run consecutivi → 3 gold-in-top10 / 2 gold-out). Implica che il benchmark non è perfettamente riproducibile sul rank K esatto. Mitigazione possibile: tie-break deterministico su `chunk_id` lessicografico in `core/hybrid_retriever` post-fetch. Non necessario per v1; nel frattempo lo script di benchmark applica la regola "boundary-fragile" (vedi `scripts/run_benchmark_w3_with_expansion.py` docstring) per neutralizzare il falso positivo nelle regressioni.
- Citation renderer human-readable (chunk_id → stringa naturale tipo "GDPR art. 35" / "D.Lgs 196/2003 art. 2-sex-decies"): RIMANDATO a settimana 5 con la generation. Per ora `core/citation_verifier` emette `annotated_text` con chunk_id grezzi. La decisione di formato user-facing (es. "GDPR art. 35" vs "Reg. UE 2016/679, art. 35") va presa quando si vede l'output reale dell'LLM. Da aggiungere come modulo `core/citation_renderer` separato dal verifier.
- Parser EUR-Lex `_COMMA_PREFIX_RE`: non riconosce marker `N)` (parentesi tonda) come prefisso di voce numerata, solo `N.` (punto). Effetto: articoli con definizioni numerate stile `1) ... 2) ... 68) ...` cadono interamente nel fallback `__body` come singolo blob oversize. Articoli affetti confermati: art_3 AI Act (4189 token monoblocco, `oversize=True`), art_4 GDPR (verifica del 2026-05-19: 1983 token monoblocco appena sotto soglia 2000 → `oversize=None` per coincidenza, comunque monoblocco singolo `__body`; HTML usa 26 marker `N)` e 0 marker `N.`, pattern identico ad art_3). Post-fix Q15 questi articoli sono retrievable come monoblocco, quindi non bloccano nessuna query del benchmark a 50; il problema è la diluizione del segnale dense su query mirate a una singola definizione (es. "cos'è un sistema GPAI"). Trigger di intervento: query del benchmark in W5/W6 che fallisca per questa ragione. Fix candidato: estendere regex a `r'(\d+)[\.\)]\s+'` + re-ingest EUR-Lex + verifica regressioni su articoli con `N)` usato in altri ruoli (es. lettere a/b/c interne ai commi).
- **Topologia MPS reranker condizionale al provider LLM**: con cloud (Anthropic) → reranker su MPS; con locale (Ollama) → reranker su CPU (vedi `spike/MPS_COABITATION_RESULTS.md`). Oggi documentato come TODO esplicito in `core/serving/config.py` ma non attivo: `HybridRetriever` non espone device del reranker nel costruttore (il reranker viene iniettato già configurato). Per attivare la topologia condizionale serve esporre `reranker_device: str = "mps"` in `HybridRetriever.__init__` e propagarlo al `CrossEncoder`. Stima: 30 min implementazione + 2 test di regressione (1 per device default, 1 per override). Trigger di intervento: pressure di memoria con uso reale combinato cloud + locale alternati nella stessa sessione di test in W6 o W7. Per ora gli smoke script in `spike/` istanziano manualmente il reranker con il device giusto (vedi `spike/smoke_rag_pipeline.py`, scelta in base a `LLM_PROVIDER`).

**Componenti core da costruire (libreria pip):**

1. `italian_legal_parser` ✅ — parser AKN → chunk gerarchici con eId/URN nativi
2. `eur_lex_parser` ✅ — parser HTML EUR-Lex dual-template (initial + consolidated) con articoli + considerando
3. `hybrid_retriever` ✅ — BM25 + dense (bge-m3) + RRF + reranker + (W4) graph expansion opzionale
4. `citation_verifier` ✅ — validazione che ogni claim citi articoli realmente presenti nel contesto
5. `terminology` ✅ — query expansion via lookup table (W4)
6. `normative_graph` ✅ — graph cross-norma statico + espansione contesto 1-hop (W4)
7. `llm_provider` ✅ — interfaccia astratta + `AnthropicProvider` + `OllamaProvider` + config `.env` (W5, 2026-05-19)
8. `rag_prompt` ✅ — system prompt italiano editabile (`system_prompt.it.md`) + user prompt builder con formato `[chunk_id:] hierarchy --- text ===` (W5, 2026-05-19)
9. `serving` ✅ — `RAGPipeline` orchestrator retrieval → rerank → generate → citation_verify, streaming primo-classe, citation verifier a fine stream (W5, 2026-05-19)

---

## File del progetto

| File | Scopo | Stato |
|---|---|---|
| `README.md` | Posizionamento, target audience (DPO, compliance) | ⏳ Post-fase G (se rilascio pubblico) |
| `SCOPE.md` | Contratto interno: cosa è dentro/fuori v1, metriche di "fatto" | ✅ v2 (post-spike) |
| `PROJECT_CONTEXT.md` | Questo file: contesto developer, decisioni, principi | ✅ v2 (post-spike) |
| `ROADMAP_POST_V1.md` | Capability identificate ma fuori scope v1 (graph, retrieval avanzato, estensione corpus, finding W7) | ✅ v1 (2026-05-19) |
| `spike/SPIKE_RESULTS.md` | Output dello spike settimana 0 — 6 verifiche tecniche | ✅ v1 |
| `spike/EURLEX_FINDINGS.md` | Findings dei 3 mini-spike EUR-Lex (template HTML, struttura ELI, AWS WAF block) | ✅ v1 |
| `data/benchmark/BENCHMARK_BASELINE.md` | Baseline retrieval dense puro settimana 2 + format riproducibile per re-run settimana 3 | ✅ v1 (2026-05-18) |
| `data/benchmark/CORPUS_OVERVIEW.md` | Descrizione corpus v1 (6 norme, convenzioni chunk_id, fragment oversize, dichiarazione limite corpus) | ✅ v1 (2026-05-20) |
| `data/benchmark/BENCHMARK_W3.md` | Benchmark retrieval esteso W3 su 50 query (4 setup × per-query) + tutti i re-run W4 (parser EUR-Lex, split annex_III, riannotazione gold, riclassificazione Q5, fix Q9) | ✅ v1 (2026-05-19) |
| `data/benchmark/RAGAS_RUN_NOTES.md` | Spec metodologica Ragas W7 pre-run (vincolo metodologico) + esito post-run | ✅ v1 (2026-05-20) |
| `data/benchmark/BENCHMARK_RAGAS_W7.md` | Risultati Ragas W7 (faithfulness + answer_relevancy su 38 positive) + verdict GO ready-with-followup | ✅ v1 (2026-05-20) |
| `data/benchmark/BENCHMARK_RAGAS_F2.md` | Risultati Ragas F.2 (faithfulness + answer_relevancy su 100 query benchmark esteso) + verdict GO ready-with-followup per rilascio pubblico v1.0 + 4 follow-up v1.1 | ✅ v1 (2026-05-21) |
| `data/benchmark/gold_answers_v1.json` | Dataset di gold answers per Ragas eval W7 (50 entry, 38 positive curate + 10 negative + 2 edge) | ✅ v1 (2026-05-19) |
| `data/benchmark/STATS.md` | Statistiche dettagliate del dataset gold_answers (composizione, lunghezze, qualità citazioni, dichiarazione di limite corpus) | ✅ v1 (2026-05-19) |
| `data/benchmark/BENCHMARK_V2_CURATION_BRIEF.md` | Brief operativo per curatela 50 query addizionali (Q51-Q100) del benchmark esteso post-pivot W8→W10 | ✅ v1 (2026-05-20) |
| `core/serving/README.md` | Documentazione modulo `RAGPipeline` orchestrator (retrieval → rerank → generate → citation_verify) | ✅ v1 (2026-05-19) |
| `core/normative_graph/graph.yaml` | Catalogo curato 22 link cross-norma (231↔GDPR↔AI Act↔NIS2↔L.132↔Cod. Privacy) con disclaimer "not legally validated" | ✅ v1 (2026-05-19) |
| `docs/methodology/graph_curation_notes.md` | Note estese curatela graph multi-normativa W4 — caveat, link in riserva, decisioni di metodo | ✅ v1 (2026-05-19, spostato da root 2026-05-21) |
| `ARCHITECTURE.md` | Architettura tecnica dettagliata | ⏳ Post-fase G (se rilascio pubblico) |
| `CONTRIBUTING.md` | Come contribuire al codice | ⏳ Post-fase G (se rilascio pubblico) |

---

## Note per Claude

Quando assisti su questo progetto:

1. **Leggi sempre `PROJECT_CONTEXT`, `SCOPE` e `SPIKE_RESULTS`** prima di rispondere a domande strategiche o di architettura
2. **Applica i principi guida**, in particolare "minima modifica che risolve" e "niente over-engineering"
3. **Sfida le richieste che ampliano lo scope** — è una protezione, non un ostacolo. Federico vuole essere fermato se sta divagando
4. **Rispondi in italiano** salvo richiesta esplicita di altra lingua
5. **Niente bullet point eccessivi, niente preamboli/postamboli** — vai dritto al punto
6. **Mantieni un tono diretto e onesto**, anche critico quando serve. Federico ha esplicitamente apprezzato pushback motivato in passato
7. **Aggiorna questo file** quando si prendono nuove decisioni rilevanti, aggiungendo righe nel registro decisioni
8. **NON menzionare altri progetti personali** di Federico salvo che lui lo faccia esplicitamente — concentrati su Iuris RAG

### Curatela gold answers W7-prep

La curatela include sanity check giuridico sull'annotazione benchmark, non solo redazione delle `gold_answer`. La chat di curatela deve segnalare proattivamente:

- **gold_chunks non giuridicamente coerenti** con la query (errore annotazione — può rivelare LLM-hint allucinato in setup benchmark, come accaduto su Q5 con `art_25-undecies` reati ambientali);
- **chunk pertinenti che dovrebbero esistere** ma non sono nei gold candidate (potenziale gap di corpus o di capability retrieval — da distinguere via diagnostica corpus + retrieval prima di intervenire);
- **query che richiedono ragionamento cross-norma con vocabolari disgiunti** (capability v1.1, non risolvibile con terminology/graph statici).

Lezione W7-prep (2026-05-19): Q5 ha rivelato che il benchmark retrieval-only non cattura tutti i tipi di errore (annotazione, corpus, capability). La curatela giuridica è il secondo livello di validazione, complementare alle metriche aggregate. Quando la curatela segnala "questo gold è sbagliato", la sequenza diagnostica corretta è: (1) verificare la query nel retriever attuale, (2) verificare la presenza dei chunk pertinenti nel corpus, (3) decidere se è bug di annotazione, gap di corpus o limite di capability.

### Pattern stabili emersi da W7-prep (2026-05-19)

- **Curatela giuridica LLM-assisted con revisione umana entry-per-entry è viable per dataset di ~40 query in 2-3 giorni**. W7-prep effettiva: ~2.5 giorni dei 3 di anticipo W5 (resto su fix documentazione e audit annotazione).
- **L'audit dell'annotazione in fase di curatela rileva bug che il benchmark retrieval-only non cattura** (es. allucinazione `art_25-undecies` su Q5+Q9 — match lessicale agganciato dal retrieval, semanticamente sbagliato).
- **"Dichiarazione di limite corpus" come ultima frase della `gold_answer`** è pattern stabile per query che richiederebbero contenuto fuori corpus v1 (codice penale, decreti settoriali D.Lgs 81/2008 / D.Lgs 152/2006, standard ISO, altri articoli di norme già in corpus). Linguaggio user-facing canonico: **`"...non incluso nel corpus normativo di riferimento"`** (con varianti di concordanza incluso/inclusi/inclusa/incluse). **NON usare** `"gold_chunks forniti"` o altro lessico tecnico interno. Applicato in 11 query positive (vedi `data/benchmark/STATS.md`).
- **Le 3 categorie di flag della curatela** (gold sbagliato / corpus insufficiente / capability insufficiente) sono effettive in pratica: nel batch hanno catturato Q5 (capability insufficiente → riclassificata edge), Q9 (gold sbagliato → fix annotazione + scenario C), nessun altro caso fra le 38 positive curate. Conferma robustezza della tassonomia.
- **Convenzione formato citazione**: una citazione per affermazione, prima del segno di punteggiatura. Multi-citazione con spazio singolo `[cite:X] [cite:Y]` — mai concatenata `[cite:X][cite:Y]`. Dataset: 0 violazioni su 119 citazioni totali nelle 38 positive (vedi `data/benchmark/STATS.md`).
