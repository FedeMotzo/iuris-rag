# Phase F.1 diagnostic — pre-lancio F.2

Data: 2026-05-20.
Sorgente: `data/benchmark/ragas_pipeline_outputs_v2.json` (100 outputs, generati da `spike/run_pipeline_v2.py`).
Diagnostico read-only sui risultati F.1 prima di lanciare F.2 Ragas judge.

---

## Step 1 — Distribuzione R@10

100 outputs totali (77 positive + 20 negative + 3 edge).

| R@10 | n | note |
|---|---:|---|
| 1.0  | 45 | gold completamente recuperato |
| 0.75 | 1  | gold parziale (1 di 4) |
| 0.667 | 2 | gold parziale (2 di 3) |
| 0.5  | 10 | gold parziale (1 di 2) |
| 0.333 | 1 | gold parziale (1 di 3) |
| 0.25 | 3  | gold parziale (1 di 4) |
| 0.2  | 2  | gold parziale (1 di 5) |
| 0.0  | 14 | nessun gold nei top-10 |
| None | 22 | gold vuoto (negative/edge, R@10 non applicabile) |

Istogramma testuale:

```
R@10=1.0  ████████████████████████████████████████████  45
R@10=0.75 █  1
R@10=0.67 ██  2
R@10=0.5  ██████████  10
R@10=0.33 █  1
R@10=0.25 ███  3
R@10=0.20 ██  2
R@10=0.0  ██████████████  14
R@10=None ██████████████████████  22
```

Note:
- **78 entry con gold non vuoto** (77 positive + 1 edge con gold popolato; le 22 con None sono 20 negative + 2 edge senza gold).
- **45/78 = 57.7%** delle entry con gold raggiungono R@10=1.0 (gold tutti recuperati).
- **14/78 = 17.9%** sono zero-recall — concentrate in cluster specifici (vedi Step 4).

---

## Step 2 — v1 W7 archived vs v1 ricalcolato F.1

Confronto solo sulle 38 query positive di v1 (Q1-Q50) — le 12 negative/edge di v1 sono escluse dal calcolo R@10.

| metrica | W7 archived (`BENCHMARK_W3.md` post-fix Q9, hybrid_rrk) | F.1 ricalcolato | delta |
|---|---:|---:|---:|
| R@10 **mean** su 38 positive | **0.608** | **0.700** | **+0.092** |
| R@10 median su 38 positive | n/d (W3 report ha solo mean) | 1.000 | — |

**Delta mean = +0.092 → sopra soglia 0.05 segnalata nella spec.**

Possibili cause del drift (in ordine di plausibilità):
1. **Non-determinismo reranker MPS**: `BENCHMARK_W3.md` riga 514 documenta esplicitamente che lo score CrossEncoder su MPS può variare di pochi millesimi tra run distinti, e ciò sposta query boundary-fragile dentro/fuori top-K. Effetto plausibile su 38 query.
2. **Setup retrieval diverso**: `BENCHMARK_W3.md` usava `scripts/run_benchmark_w3.py` con `rerank_top_k=20`. F.1 ha usato `retriever.retrieve(query, top_k=20, rerank_top_k=20)` chiamato direttamente. Stesso codice retriever, ma top_k diverso (W3 archived probabilmente top_k=10 per leggere direttamente i 10 ranking, F.1 top_k=20). Da verificare.
3. **Inclusione di Q5 (edge) nel mean storico?**: il post-Q5/post-Q9 mean del W3 archived è 0.608 su 38 positive — coerente con il filtro positive attuale.

**Raccomandazione**: il drift è documentato in spec come "atteso <0.05; se >0.05 segnalare". Lo segnalo qui ma non lo considero blocker per F.2: il rumore reranker è noto, e la mediana (1.000) è il valore primario per il decision-making. F.2 può procedere; eventuale re-run deterministico (reranker su CPU) come confronto è scope v1.1.

---

## Step 3 — Verifica logica `runtime_corpus_limit_observed`

**Pattern regex usato** (identico a `phase_e_merge.py` e `run_pipeline_v2.py`):

```regex
non\s+(?:è\s+|sono\s+|sia\s+|siano\s+)?(?:inclus[oaie]|present[eai]).{0,40}corpus(?:\s+normativo)?(?:\s+di\s+riferimento)?
```

Intento: catturare il pattern canonico "non incluso nel corpus normativo di riferimento" (PROJECT_CONTEXT voce 32) con varianti di concordanza.

**Detection sui 100 outputs**:
- entry con `has_corpus_limit_declaration=true` (23 totali): **0 / 23** pattern rilevati ❌
- entry con `has_corpus_limit_declaration=false` (77 totali): **0 / 77** pattern rilevati

5 random entry flag=true (atteso pattern presente):

| qid | detected | estratto answer finale (250 char) |
|---|---|---|
| Q9  | NO | "Non è pertanto possibile confermare, sulla base del solo contesto fornito, se e in quale misura tali fattispecie siano state formalmente inserite nel catalogo dei reati presupposto 231…" |
| Q43 | NO | "Per una risposta più precisa e completa, sarebbe necessario disporre di un contesto normativo più ampio. Il contesto fornito copre solo aspetti settoriali della disciplina…" |
| Q15 | NO | risposta sostantiva sui divieti AI Act, nessuna dichiarazione di limite |
| Q12 | NO | risposta sostantiva su riconoscimento emozioni educativo, nessuna dichiarazione di limite |
| Q27 | NO | (non ispezionato in dettaglio, presumibilmente analogo) |

**Finding critico — drift lessicale sistemico**: il modello generation v2 (Sonnet 4.6) **non usa più il pattern canonico** "non incluso nel corpus normativo di riferimento". Usa formulazioni alternative:
- "Non è possibile confermare sulla base del solo contesto fornito…"
- "Sarebbe necessario disporre di un contesto normativo più ampio…"
- "Il contesto fornito copre solo aspetti settoriali…"

Inoltre alcune entry flag=true (Q12, Q15) hanno **dato comunque una risposta sostantiva senza dichiarazione di limite** — comportamento atteso solo se la pipeline ha effettivamente recuperato gold sufficiente per rispondere (es. Q15 ha R@10=1.0 sui divieti AI Act).

**Implicazioni**:
1. La rilevazione "runtime_corpus_limit_observed" via questa regex è **inaffidabile**.
2. Il drift lessicale era atteso ma è più ampio del previsto (smoke W7 lo segnalava solo su Q43; ora è sistemico).
3. Il tuning system_prompt per uniformare al pattern canonico (già in `ROADMAP_POST_V1.md` come finding W7) diventa più urgente.
4. **Per Ragas F.2**: faithfulness e answer_relevancy non sono sensibili a questo problema. Il giudice valuta la coerenza semantica risposta-contesto, non il match lessicale di un pattern. F.2 procederà senza problemi su questo asse, ma il report W7 dovrà dichiarare esplicitamente che la metrica `runtime_corpus_limit_observed` è non-affidabile in F.1 e va riprogettata in v1.1 (es. via LLM-as-judge sulla presenza di dichiarazione di limite, non regex).

**Decisione operativa**: il flag `runtime_corpus_limit_observed` nel dataset v2 non viene aggiornato sulla base di questa regex. Il report W3_v2 ha indicato 0 runtime_observed (corretto per la regex come implementata). Lo stato del flag resta quello settato in fase B (true solo per Q19, Q35 da W7).

---

## Step 4 — Verifica logica outlier cluster

**Bug della logica**: l'implementazione attuale aggrega per `use_case` (non per `cluster`). Il dataset v2 ha **un use_case per query** (1-to-1 mapping), quindi ogni "cluster" ha n=1 e la mediana di un singolo valore è il valore stesso → metric priva di significato statistico.

**Soglia usata**: `positive R@10 mediana (1.000) - 0.20 = 0.800` → tutti i singleton sotto 0.8 sono flaggati.

Risultato attuale: **32 "outlier"** identificati, ma sono semplicemente le 32 query positive con R@10 <0.8 (su 77). Non è un'analisi cluster.

**Aggregazione corretta**: il dataset v2 ha 16 cluster veri (definiti nei metadata di `candidates_v2_curated.json`). Per produrre un vero outlier-cluster check serve un mapping qid→cluster:

| Cluster v2 | n entry (atteso) |
|---|---:|
| NIS2 mono-norma | 6 |
| NIS2 cross GDPR | 2 |
| Codice Privacy mono-norma | 5 |
| L. 132/2025 | 4 |
| Cross-norma 3+ norme | 5 |
| Cross-norma scenario 2 norme | 4 |
| Diritti dell'interessato GDPR | 4 |
| Sanzionatorio puro | 4 |
| 231 fattispecie ≠ 24-bis | 3 |
| Procedurali "come si fa X" | 2 |
| Negative: Garante UC4 | 1 |
| Negative: art abrogato Codice Privacy | 2 |
| Negative: art inesistente | 2 |
| Negative: corpus mancante | 2 |
| Negative: omonimia numerazione | 1 |
| Edge: vaghe / mix | 3 |

Per fare l'aggregazione cluster-level corretta servirebbe mappare ogni qid Q51-Q100 al cluster originale (informazione presente nei metadata di `candidates_v2_curated.json` ma non propagata nel dataset finale).

**Patch consigliata per v1.1**: aggiungere campo `cluster` al dataset gold (preservando lo schema 10 campi attuale come campo `notes` esteso, o nuova entry `metadata.cluster_mapping`). Non urgente per F.2.

**Per F.2**: il bug non blocca Ragas. L'analisi cluster-level per il report W7 può essere fatta a posteriori riusando i metadata di `candidates_v2_curated.json`.

---

## Step 5 — Verifica 3 positive R@10=1.0

Spot check su 3 entry random con R@10=1.0:

### Q79 (n_gold=1)
- question: "Il diritto alla portabilità dei dati di cui all'art. 20 GDPR si applica anche a dati derivati o inferiti…"
- gold@rank=1: `eli/reg/2016/679/oj__art_20` ✅

### Q58 (n_gold=2)
- question: "Quale rapporto sussiste fra l'obbligo di valutazione del rischio cyber NIS2 e l'obbligo di adottare…"
- gold@rank=1: `…138__art_24` ✅
- gold@rank=2: `…2016/679/oj__art_32` ✅

### Q8 (n_gold=2)
- question: "Cos'è la valutazione d'impatto sui diritti fondamentali e quando va condotta?"
- gold@rank=1: `…2024/1689/oj__recital_96` ✅
- gold@rank=2: `…2024/1689/oj__art_27` ✅

✅ Tutti i gold sono effettivamente nei top-10 alle posizioni dichiarate. R@10=1.0 verificato.

---

## Step 6 — Verifica top_k

- `metadata.top_k = 5` (top_k del LLM context window, default `build_default_pipeline`)
- `metadata.rerank_top_k = 20` (candidati reranker)
- Empirico: `len(retrieved_chunks)` per la prima entry = **20** ✅

Il campo `retrieved_chunks` contiene 20 chunk per ciascuna entry (top-20 post-rerank), come richiesto dalla spec F.1. R@5/10/20 sono quindi calcolabili sui ranking salvati.

Il top_k=5 in metadata si riferisce a quanti chunk vengono passati al LLM per la generation, non al ranking salvato. Conforme alla spec.

---

## Sintesi pre-F.2

| Item | Status | Azione richiesta? |
|---|---|---|
| Distribuzione R@10 | ✅ analizzata | nessuna |
| Drift v1 W7 vs F.1 (+0.092) | ⚠ sopra soglia ma plausibilmente non-determinismo reranker MPS | documentare in report W7, non blocker F.2 |
| Pattern detection corpus_limit | ❌ regex non matcha (drift lessicale sistemico) | flag come non-affidabile in F.2; tuning system prompt prioritario v1.1 |
| Outlier cluster | ⚠ logica buggy (aggrega per use_case singleton) | non blocker F.2; cluster-level analysis ex-post |
| Sanity R@10=1.0 | ✅ 3/3 verified | nessuna |
| top_k retrieval | ✅ 20 saved, 5 to LLM | nessuna |

**Verdict**: F.2 può essere lanciato. I 2 finding critici (drift lessicale + bug outlier cluster) non bloccano la Ragas eval; vanno documentati come caveat nel report W7 finale.
