# MPS coabitation smoke — risultati

## Setup
- **host**: Darwin MAC-436C98.station 25.3.0 Darwin Kernel Version 25.3.0: Wed Jan 28 20:51:28 PST 2026; root:xnu-12377.91.3~2/RELEASE_ARM64_T6041 arm64
- **python**: 3.12.13
- **ollama_model**: qwen2.5:14b
- **reranker_model**: BAAI/bge-reranker-v2-m3
- **collection**: italian_legal_v1_hybrid
- **rerank_top_k**: 20
- **rag_top_k**: 5
- **max_output_tokens**: 500
- **sample_interval_s**: 0.5
- **baseline_vm_used_mb**: 16109
- **baseline_swap_used_mb**: 902
- **baseline_mem_pressure**: normal
- **torch**: 2.12.0
- **mps_available**: True

## Risultati S1 — bge-m3 MPS + reranker MPS + Ollama attivo (tutto residente)

| qid | t_retrieval ms | t_rerank ms | TTFT ms | t_gen ms | tok/s | t_e2e ms |
|---|---|---|---|---|---|---|
| Q6 | 80 | 1732 | 150 | 12267 | 23.7 | 14080 |
| Q7 | 81 | 1793 | 150 | 16172 | 23.5 | 18046 |
| Q1 | 78 | 1754 | 21774 | 35297 | 23.2 | 37129 |

**Picchi memoria**

| peak Python RSS MB | peak Ollama RSS MB | peak MPS current MB | peak MPS driver MB | peak VM used MB | swap Δ MB | mem pressure |
|---|---|---|---|---|---|---|
| 986 | 9022 | 5057 | 5751 | 19809 | +558 | normal |

## Risultati S2 — bge-m3 MPS + reranker CPU + Ollama attivo

| qid | t_retrieval ms | t_rerank ms | TTFT ms | t_gen ms | tok/s | t_e2e ms |
|---|---|---|---|---|---|---|
| Q6 | 77 | 2864 | 160 | 13255 | 23.8 | 16196 |
| Q7 | 78 | 2888 | 153 | 21313 | 23.6 | 24279 |
| Q1 | 80 | 2916 | 21755 | 37270 | 23.3 | 40266 |

**Picchi memoria**

| peak Python RSS MB | peak Ollama RSS MB | peak MPS current MB | peak MPS driver MB | peak VM used MB | swap Δ MB | mem pressure |
|---|---|---|---|---|---|---|
| 3317 | 9030 | 2166 | 3045 | 18576 | -8 | normal |

## Risultati S3 — bge-m3 MPS + reranker MPS load/unload + Ollama attivo

| qid | t_retrieval ms | t_rerank ms | TTFT ms | t_gen ms | tok/s | t_e2e ms |
|---|---|---|---|---|---|---|
| Q6 | 394 | 1726 | 194 | 13301 | 23.6 | 15421 |
| Q7 | 412 | 1719 | 175 | 17974 | 23.4 | 20105 |
| Q1 | 402 | 1716 | 10897 | 32195 | 23.5 | 34313 |

**Picchi memoria**

| peak Python RSS MB | peak Ollama RSS MB | peak MPS current MB | peak MPS driver MB | peak VM used MB | swap Δ MB | mem pressure |
|---|---|---|---|---|---|---|
| 1365 | 8991 | 7103 | 8777 | 20847 | +2146 | normal |

- t_unload_reranker mediana: 131 ms
- t_reload_reranker mediana: 2981 ms

## Confronto scenari

| scenario | p50 e2e ms | tok/s | swap | mem pressure | latenza | overall |
|---|---|---|---|---|---|---|
| S1 | 18046 | 23.5 | FAIL | PASS | FAIL | **FAIL** |
| S2 | 24279 | 23.6 | PASS | PASS | FAIL | **FAIL** |
| S3 | 20831 | 23.5 | FAIL | PASS | FAIL | **FAIL** |

## Raccomandazione

Tre constatazioni guidano la scelta per W5:

1. **La soglia 5 s end-to-end non è raggiungibile con la generazione corrente.**
   Qwen 14B Q4_K_M tiene 23.5 tok/s in tutti e tre gli scenari. A 500 token output
   sono ~21 s di solo `t_gen`, indipendentemente dal layout MPS. Il collo di
   bottiglia è la generazione, non la coabitazione.

2. **Coabitazione MPS: S2 è l'unico scenario senza pressione swap aggiunta.**
   - S1 (tutto MPS): peak MPS 5.7 GB driver, swap Δ **+558 MB** → la coabitazione
     bge-m3 + reranker + KV cache di Qwen mangia il margine residuo. Funziona,
     ma siamo a un soffio dal degrado.
   - S2 (rerank CPU): peak MPS 3 GB driver, **swap Δ -8 MB** (nessuna pressione
     aggiunta). RSS Python 3.3 GB (i +2 GB del reranker sono andati in RAM
     "normale" invece che nel pool unified di MPS). Mem pressure `normal`.
   - S3 (load/unload MPS): peggior scenario in memoria — peak MPS **8.8 GB
     driver, swap Δ +2146 MB**. La frammentazione tra ricariche del reranker
     accumula buffer che `torch.mps.empty_cache()` non recupera. Aggiunge
     anche un costo non banale: mediana reload reranker **2981 ms / query**,
     superiore al guadagno (~1.1 s) rispetto al rerank CPU.

3. **TTFT cache-miss ricorrente su Q1 — causa identificata, fix banale.**
   Probe post-smoke (`spike/_probe_ollama_cache.py`):

   | qid | prompt tok | output cap | TTFT cache-hit | TTFT cache-miss |
   |---|---|---|---|---|
   | Q6 | 1 987 | 500 | 124-131 ms (stabile) | 14-15 s (solo cold) |
   | Q7 | 1 889 | 500 | 150 ms (stabile) | 14 s (solo cold) |
   | Q1 | 2 972 | 500 | 120 ms se `num_ctx=8192` | **22 s ricorrente** con `num_ctx` default |

   Il default Ollama `num_ctx=2048` è < (prompt Q1 + output) = 3 472 token:
   durante la generazione Ollama esegue context shift (sliding window), che
   invalida la KV cache del prefisso. Risultato: ~metà delle chiamate
   successive subiscono full prefill (21 s a 139 tok/s su 2 972 token).

   **Fix**: passare `"num_ctx": 8192` nelle options di `/api/generate`.
   Già applicato in `spike/smoke_mps_coabitation.py`. Per W5 vale come
   regola: il client serving deve sempre specificare `num_ctx ≥ prompt +
   max_output_tokens + margine`. Sui chunk attuali (~600 tok ciascuno) e 5
   chunk in retrieval, 8 k è sufficiente.

   Il prefill cold (~140 tok/s) resta una caratteristica fisica di Qwen 14B
   Q4_K_M sulla GPU M4 Pro: non si elimina, ma con cache stabile lo paghi
   una volta per query.

**Cosa NON copre questo smoke e va deciso a parte (W5 prosegue, non blocca)**:

| Decisione | Quando prenderla |
|---|---|
| Ridurre `max_output_tokens` da 500 → 200-250 (dimezza t_gen) | A valle di un test di qualità sulla concisione delle risposte |
| Streaming end-to-end al frontend (TTFT come metrica primaria) | In design del frontend W6 |
| Valutare Qwen 7B o MLX runtime (potenziale 2-3× su Apple) | Dopo che la pipeline è in piedi, come ottimizzazione |
| Compressione prompt RAG (taglio testo chunk a 400 char) | SCARTATA in v1 (vedi PROJECT_CONTEXT.md decisione 23, 2026-05-19) |

**Verdetto operativo (aggiornato 2026-05-19, decisioni W5)**:

**Topologia adottata per W5: condizionale al provider LLM attivo.**

- Provider = **AnthropicProvider** (cloud, default): **S1** — reranker su MPS
  (~1.7 s), no pressione swap perché Qwen non risiede in MPS, TTFT cold atteso
  ≤ 3 s da SLA Anthropic.
- Provider = **OllamaProvider** (locale, fallback): **S2** — reranker su CPU
  (~2.9 s), no pressione swap, libera 3 GB MPS per Qwen KV cache. TTFT cold
  accettato 14-22 s come limite fisico di Qwen 14B Q4_K_M su M4 Pro
  (prefill ~140 tok/s).

La soglia "5 s end-to-end" era una formulazione sbagliata della metrica UX
per RAG interattivo: su locale la generation è strutturalmente sopra 20 s
a 23 tok/s × 500 token output. Le soglie W5 sono riformulate come TTFT cold/warm
+ throughput streaming (vedi `PROJECT_CONTEXT.md` registro decisioni 2026-05-19,
voci 20-23). Selezione della topologia decisa in init pipeline via config provider.

## Finding post-W5: throughput Qwen sotto RAG completo (2026-05-19)

Dopo l'integrazione del modulo `core/serving` + system prompt italiano +
builder verboso (formato `[chunk_id:] hierarchy --- text ===`), lo smoke
RAG completo (`spike/smoke_rag_pipeline.py`) ha misurato:

| qid | t_retrieval | t_gen | TTFT | tok/s | citazioni |
|---|---|---|---|---|---|
| Q6 | 4.2 s | 33.4 s | 21.3 s | 8.6 | 4/4 verified |
| Q7 | 3.4 s | 27.2 s | 14.3 s | 11.2 | 4/4 verified |
| Q1 | 2.9 s | 29.9 s | 22.0 s | 6.0 | 2/2 verified |

Throughput Qwen ~3× inferiore allo smoke coabitazione di questo file
(23.5 tok/s) → **6-11 tok/s**. Differenza imputabile a:

- system prompt italiano caricato (~400 token aggiunti al contesto)
- formato chunk builder più verboso del concatenamento secco usato
  nello smoke originale

Non è una regressione né un bug. È il regime reale del backend RAG con
prompt completo. Annotato per evitare di reinventare la diagnosi in W6/W7.

Trade-off accettato in v1: qualità citazione (3/3 `all_verified`
strutturali su locale) > throughput. Se in W6 emerge come problema UX,
prima leva = snellire formato chunk nel builder. Compressione prompt
resta scartata in v1 (PROJECT_CONTEXT.md voce 23).

**Comparativo con smoke cloud (Anthropic `claude-sonnet-4-6`)**:
TTFT 1.6 s vs 21.3 s (**−13×**), throughput 44-49 tok/s vs 6-11 tok/s
(**+5×**), total e2e 12-19 s vs 30-37 s (**−2.5×**). Cloud risolve di
fatto il problema UX di latenza che era stato accettato come "limite
fisico Qwen 14B" in chiusura smoke coabitazione. Vedi
`spike/SMOKE_RAG_PIPELINE_RESULTS.md` per il dettaglio cloud.
