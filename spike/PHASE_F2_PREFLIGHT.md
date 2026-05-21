# Phase F.2 pre-flight — dry-run di validazione (d)+(e)

Data: 2026-05-21
Sorgente: dry-run di `spike/run_ragas_eval_v2.py --dry-sample` su Q52 + Q70.
Obiettivo: validare ridurre cost di F.2 da $13 (proiezione baseline) a target $2-4 via (d) drop context_precision + (e) Anthropic prompt caching.

---

## Task 1 — (d) Configurazione metriche

**Implementato.** [spike/run_ragas_eval_v2.py:222-235](spike/run_ragas_eval_v2.py#L222-L235):
- `context_precision` rimossa dalla lista metriche Ragas.
- Solo 2 metriche attive: `faithfulness` + `answer_relevancy`.
- Docstring modulo aggiornata con motivazione + rinvio a F.1 per le metriche retrieval (R@5/R@10/R@20/MRR già in `BENCHMARK_W3_v2.md`).

**Effetto misurato sulle LLM calls/sample**:
- Q51 (baseline 3 metriche): **8 LLM calls**
- Q52 (post-(d), 2 metriche): **3 LLM calls** ✓ riduzione 62%
- Q70 (post-(d), 2 metriche): **3 LLM calls** ✓

---

## Task 2 — (e) Anthropic prompt caching

**Implementato** ma **NON funzionante** sul pattern di prompt Ragas. Dettagli sotto.

Codice: [spike/run_ragas_eval_v2.py:85-158](spike/run_ragas_eval_v2.py#L85-L158).

Tecnica:
- Wrap di `client.messages.create` (riuso del wrapper esistente per token tracking).
- Conversione dei messaggi `user`/`system` da `content: str` a `content: [{type: text, text, cache_control: ephemeral}]`.
- TTL ephemeral (5 min standard Anthropic).
- Beta header NON aggiunto esplicitamente: Anthropic SDK ≥0.39 supporta `cache_control` direttamente nel body senza header beta (prompt caching ora GA).
- Tracking aggiornato per accumulare `cache_creation_input_tokens` e `cache_read_input_tokens` separatamente nel tracker.
- Pricing in `cost_from_tracker()` differenziato: cache_creation 1.25× input, cache_read 0.1× input, output 5× input (Sonnet 4.6 public).

---

## Task 3 — Dry-run di validazione

### Q52 — NIS2 mono-norma, simile a Q51 (isolando l'effetto caching)

| Metric | Valore |
|---|---:|
| `faithfulness` | 1.000 |
| `answer_relevancy` | 0.667 |
| n LLM calls | 3 |
| `input_tokens` (standard) | 79 |
| `cache_creation_input_tokens` | 10.978 |
| `cache_read_input_tokens` | **0** ❌ |
| `output_tokens` | 3.736 |
| cache_read ratio | **0.0%** |
| **cost effettivo** | **$0.0974** |
| Proiezione 100 sample (linear) | **~$9.74** |

### Q70 — Cross-norma 3+ (banca AML extra-UE), gold lungo su 3 norme

| Metric | Valore |
|---|---:|
| `faithfulness` | 0.786 |
| `answer_relevancy` | 0.673 |
| n LLM calls | 3 |
| `input_tokens` (standard) | 79 |
| `cache_creation_input_tokens` | 15.111 |
| `cache_read_input_tokens` | **0** ❌ |
| `output_tokens` | 2.437 |
| cache_read ratio | **0.0%** |
| **cost effettivo** | **$0.0935** |
| Proiezione 100 sample (linear) | **~$9.35** |

### Mediana

| Sample | cost | n_calls | cache_read |
|---|---:|---:|---:|
| Q52 | $0.0974 | 3 | 0 |
| Q70 | $0.0935 | 3 | 0 |
| **mediana** | **$0.0955** | 3 | 0 |

**Proiezione F.2 completo (100 sample × mediana): ~$9.50.** Ancora 2.4× sopra il target post-(d)+(e) di $4.

---

## Task 4 — Verifica caching effettiva

**Risultato: caching non efficace.** Entrambi i sample mostrano `cache_read_input_tokens=0` su tutte le 3 call.

**Diagnosi tecnica**:

Ragas (versione 0.4.3 via Instructor) effettua per sample con `faithfulness + answer_relevancy` **3 LLM calls strutturalmente diverse**:

1. **Faithfulness statement extraction**: prompt contiene `question + response` (no contexts). Output: lista di N "statements".
2. **Faithfulness statement verification**: prompt contiene `contexts (top-5 testuali) + statements_list`. Output: per ogni statement, verdict di groundedness.
3. **Answer relevancy generation**: prompt contiene `response` (no contexts, no question). Output: question sintetica retro-generata dal response.

Le 3 call hanno **prefisso user-content diverso** (cambia template istruzioni + contenuto inserito). Anthropic prefix caching match richiede prefisso identico carattere-per-carattere ≥1024 token. Il caching si attiva tecnicamente (`cache_creation_input_tokens > 0` su ogni call), ma nessun prefisso si ripete tra call → 0 cache hit.

**Aritmetica del net loss**: con caching:
- 10.978-15.111 token scritti a $3.75/Mtok = $0.041-0.057 per sample
- 0 token letti a $0.30/Mtok = $0

Senza caching, gli stessi token sarebbero stati input standard:
- 10.978-15.111 token × $3.00/Mtok = $0.033-0.045 per sample

**Overhead caching: +25% sui token cached, senza recuperare nulla via cache_read.** Net loss ~$0.01/sample × 100 = ~$1 wasted.

---

## Path possibili per ridurre cost

### A — Disabilitare caching, lasciare solo (d). Cost stimato ~$8.50/sample × 100 = **$8-9 totali**

Cambio richiesto: `enable_caching=False` nel `build_tracked_client()`.

### B — Caching strategico via prompt-structure rewriting. Cost stimato ~$5-6/sample × 100 (best case)

Richiede:
- Monkey-patch dei prompt template Ragas per separare `[context_block, variable_block]`.
- Cache_control SOLO sul context_block stabile entro sample.
- Anche dentro un sample le 3 call hanno content semantico diverso, ma le call 2+ usano stessi contexts; in teoria 1 cache hit/sample.

Complessità: alta (forks di Ragas) e fragile (prompt template Ragas cambia tra versioni). **Sconsigliato per F.2**, possibile v1.1 se F.2 diventa ricorrente.

### C — Subset sampling (es. 50 random) + (d). Cost stimato ~$4.50

50 sample stratificati × $0.089 = $4.45. Sotto target.

Trade-off: il report W7_v2 avrà aggregati su 50 invece di 100. Le tabelle "by_use_case" del W7_v2 originale avevano comunque n=1 per cluster (bug logica già documentato in PHASE_F1_DIAGNOSTIC); aggregazione cluster-level richiede di mappare qid→cluster a posteriori. Ridurre da 100 a 50 sample non degrada questa dimensione, solo dimezza statisticamente le code.

### D — Accettare $9.50 e procedere

Sopra target spec ma 27% sotto la baseline $13. Garantisce report W7_v2 completo su 100 sample.

---

## Raccomandazione operativa

**Disabilitare (e)** (cache_read=0 → overhead +9% senza beneficio) e procedere con **scenario A**. Net stima rivista: **~$8-9 per 100 sample, 2 metriche, no caching**. Sotto la baseline $13 di ~38%, sopra target spec $4 di ~2×.

Se il budget Anthropic non sostiene $8-9, ripiegare su **scenario C** (50 sample subset) per cost ~$4.50.

---

## Decisione richiesta a Federico

Tre opzioni concrete (in ordine di preferenza):

1. **Scenario A** — disable caching + run completo 100 sample, ~$8-9 totali.
2. **Scenario C** — disable caching + subset 50 sample random stratificati, ~$4.50 totali.
3. **Scenario D** — run completo con caching attivo (come è ora), ~$9.50 totali. Caching ininfluente ma non dannoso significativamente.

**NON consigliato**: scenario B (rewriting prompts Ragas) per scope F.2.

Stop dopo conferma scelta. Modifico `enable_caching` + lancio run.
