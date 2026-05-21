# Ragas eval W7 — note metodologiche pre-run

Data: 2026-05-20
Stato: spec scritta **prima** del run (vincolo metodologico).

## Obiettivo

Valutare quantitativamente **la generazione** della pipeline RAG cloud
(Sonnet 4.6) su 38 query positive del benchmark, usando le metriche
Ragas `faithfulness` e `answer_relevancy` con Opus 4.7 come LLM judge.

**Non è una valutazione del retrieval.** Il retrieval è già caratterizzato
da W3 (`BENCHMARK_W3.md`, recall@k vs gold_chunks). W7 misura ciò che
W3 non cattura: la qualità semantica della risposta generata rispetto al
contesto recuperato e alla domanda.

Decisione attesa a valle: **pipeline ready per release v1**, oppure
serve iterazione (tuning system prompt, formato builder, ecc.) prima di
v1.

## Setup

- Dataset: 38 query `positive` di `data/benchmark/gold_answers_v1.json`
- Provider generazione: `anthropic` / `claude-sonnet-4-6`
- Pipeline: `top_k=5`, `rerank_top_k=20`, `use_graph=False`, `max_output_tokens=1000`
- Topologia: reranker MPS (S1)
- LLM judge Ragas: `claude-opus-4-7` via `langchain_anthropic`
- Metriche: `faithfulness`, `answer_relevancy` — niente metriche retrieval (duplicano W3)
- Costo atteso: ~$0.45-0.60 totale
- Wall-clock atteso: ~15 minuti

## Note metodologiche (eredità dallo smoke gold comparison)

Queste 6 note vengono da `spike/SMOKE_GOLD_COMPARISON.md` e restano
valide per W7 — anzi diventano centrali nell'interpretazione dei punteggi
Ragas aggregati.

1. **Retrieval-bound failures ≠ generation failures.** Quando il
   retriever non porta i chunk corretti (gap noto v1.1 su query
   cross-norma a vocabolari disgiunti, vedi `BENCHMARK_W3.md`), la
   generazione fa la cosa giusta sui chunk disponibili + dichiara il
   limite del corpus. Ragas non distingue questo caso da un fallimento
   genuino: produrrà punteggio basso su entrambi. Da segregare in
   lettura.

2. **Faithfulness e answer_relevancy daranno punteggio basso su query
   retrieval-bound** (vedi nota 1 e nota 7). Interpretare come
   *expected behavior*, non come fallimento di pipeline.

3. **Allucinazione benigna su Q9** (osservata nello smoke): Sonnet cita
   `art. 24-bis D.Lgs 231/2001` in chiusura come riferimento mancante,
   numero corretto da prior knowledge ma NON supportato dai chunk. Per
   `faithfulness` è negativo. Comportamento meta-cognitivamente corretto
   (segnala il gap) ma metricamente penalizzato. Verificare se altre
   query mostrano il pattern.

4. **Drift lessicale Q43** (osservato nello smoke): dichiarazione di
   limite con lessico diverso dal pattern canonico
   `"non incluso nel corpus normativo di riferimento"` (vedi
   `PROJECT_CONTEXT.md` voce 32). Sostanza identica, lessico diverso.
   Eventuale finding per W6 (tuning system prompt), non blocca W7.

5. **Q1 checklist 4/5 retrieval-bound**: il check mancato ("settori
   Allegato III") richiede chunk dell'Allegato non recuperati. Stesso
   pattern di Q9/Q43 in forma più lieve. Da segnalare nel report.

6. **Pattern trasparenza UX confermato**: nello smoke il modello produce
   dichiarazioni esplicite di limite quando il retrieval è incompleto,
   mai inventa contenuto dispositivo non supportato. Il citation
   verifier strutturale + il system prompt italiano funzionano come
   progettati per il target professional.

## Note specifiche Ragas

7. **Le 11 query "dichiarazione di limite corpus"** (vedi `STATS.md`):
   Q9, Q12, Q13, Q15, Q24, Q25, Q26, Q27, Q43, Q45, Q49. Aspettare
   cluster di score basso 0.4-0.7 su `faithfulness` per queste query —
   la dichiarazione di limite è una claim non groundable nei chunk per
   design. Segregare in due gruppi:
   - **Gruppo A "non-limite" (27 query)**: comportamento standard atteso
   - **Gruppo B "limite" (11 query)**: punteggio strutturalmente più basso
     atteso

   Lo script di eval legge il flag `has_corpus_limit_declaration` da
   `gold_answers_v1.json` (aggiunto pre-run) e calcola aggregati
   separati per Gruppo A e Gruppo B.

8. **Opus 4.7 come judge introduce bias di severità sconosciuto.** Non
   esiste storico Ragas su questo dataset né su Opus come judge per
   italiano legale. Il primo run è baseline. Annotare qualitativamente
   **3-5 query** in cui il punteggio Opus diverge dalla tua intuizione
   umana (rileggendo question + answer + score), per calibrare la
   fiducia nel judge. Casi attesi di divergenza:
   - Opus penalizza dichiarazioni di limite legittime (gruppo B) →
     conferma nota 7
   - Opus premia risposte stilisticamente ricche ma sostantivamente
     parziali → da indagare
   - Opus penalizza risposte fedeli ma stringate → da indagare

9. **Soglie di lettura aggregate v1**:
   - **Faithfulness gruppo A (27 non-limite)**: mediana **≥0.75**
     accettabile, ≥0.85 buono, <0.65 da indagare. Sotto soglia richiede
     analisi caso per caso prima di v1.
   - **Answer_relevancy su tutte 38**: mediana **≥0.80** accettabile.
     Metrica meno sensibile al pattern "dichiarazione di limite" perché
     la risposta è comunque pertinente alla domanda. Soglia uguale su
     gruppo A e B.
   - **Faithfulness gruppo B (11 limite)**: nessuna soglia hard. Il
     punteggio aggregato è informativo per documentare il fenomeno, non
     per decidere ready/not-ready.

## Criterio di decisione ready/not-ready per v1

**Pipeline ready** se TUTTE:
- mediana faithfulness gruppo A ≥0.75
- mediana answer_relevancy globale ≥0.80
- 0 query con faithfulness <0.4 nel gruppo A (sarebbe fallimento netto
  di groundedness, va capito caso per caso)
- nessuna evidenza sistematica di allucinazione benigna fuori dal
  pattern Q9 (=in chiusura, dopo dichiarazione di limite)

**Pipeline ready-with-followup** se:
- soglie sopra rispettate ma con 3+ query nel gruppo A con
  faithfulness 0.4-0.6 → annotare per W6/iterazione, non bloccare v1

**Pipeline not-ready** se:
- mediana faithfulness gruppo A <0.65, oppure
- ≥3 query gruppo A con faithfulness <0.4, oppure
- pattern di allucinazione che NON è il caso benigno Q9 (=in mezzo alla
  risposta, presentata come fondata sui chunk)

Le soglie sono indicative e basate su letteratura Ragas + giudizio sul
dataset. Sono punti di partenza per forzare un verdict scritto, non
dogmi. Se i risultati suggeriscono che le soglie sono mal calibrate,
documentare la nuova calibrazione in coda al report W7 con motivazione,
non riscrivere queste a monte.

## Output atteso

1. `data/benchmark/ragas_pipeline_outputs_v1.json` — cache delle 38
   risposte pipeline (question, contexts top-5, answer, ground_truth,
   has_corpus_limit_declaration). Generato in step 1 dello script,
   riusabile se il giudizio Ragas crasha o se vuoi ri-giudicare con un
   judge diverso senza rigenerare le risposte.

2. `data/benchmark/ragas_results_v1.json` — score per query
   (faithfulness, answer_relevancy) + metadata (qid, group A/B).

3. `data/benchmark/ragas_aggregates_v1.json` — aggregati: mediana,
   media, p25, p75 per metrica per gruppo.

4. `BENCHMARK_RAGAS_W7.md` — report scritto post-run, struttura:
   - header (data, setup, riferimento a queste note)
   - tabella aggregati gruppo A vs gruppo B
   - top-5 e bottom-5 query per ciascuna metrica
   - sezione "Divergenze Opus judge vs intuizione umana" (3-5 query)
   - verdict ready / ready-with-followup / not-ready con motivazione

## Cosa NON è W7

Per blindare contro scope creep:

- Tuning system prompt sulla base dei risultati Ragas → eventuale W6 /
  iterazione post-W7
- Tuning formato chunk del builder → eventuale W6 / iterazione
- Confronto cloud (Sonnet) vs locale (Qwen) sotto Ragas → locale è
  fallback, non oggetto di valutazione v1
- Implementazione metriche custom oltre Ragas standard → fuori scope
- Re-run benchmark retrieval (W3) con configurazioni alternative →
  fuori scope
- Estensione corpus (codice penale, decreti settoriali) per "salvare" le
  11 query limite → esplicitamente v1.1, vedi `ROADMAP_POST_V1.md`
- Confronto judge alternativi (GPT-4, Qwen, ecc.) → primo run è
  baseline Opus; confronto judge eventualmente in iterazione successiva

## Pre-run checklist

Prima di lanciare lo script:

- [ ] questo file committato
- [ ] `gold_answers_v1.json` aggiornato con flag
      `has_corpus_limit_declaration: true` per le 11 query
      (Q9, Q12, Q13, Q15, Q24, Q25, Q26, Q27, Q43, Q45, Q49) e `false`
      per le restanti 27 positive
- [ ] `.env` con `ANTHROPIC_API_KEY` valida (stessa key copre generator
      Sonnet e judge Opus)
- [ ] Qdrant Docker up
- [ ] `ragas` + `langchain_anthropic` installati nel venv
- [ ] script `spike/run_ragas_eval.py` scritto da Claude Code e
      letto/validato

## Vincolo metodologico

Questa spec è scritta **prima** dell'esecuzione. Modifiche a soglie,
metriche o criteri di decisione fatte dopo aver visto i risultati vanno
annotate in coda a `BENCHMARK_RAGAS_W7.md` con motivazione, **non**
sovrascrivendo queste note a monte. Le note a monte restano il baseline
metodologico riproducibile.

## Esito W7 (2026-05-20, post-run)

Run completato 2026-05-20 con judge Sonnet 4.6 (vedi sezione
"Modifica setup judge" sopra). Verdict: **GO ready-with-followup**.

Risultati e analisi qualitativa: vedi `BENCHMARK_RAGAS_W7.md` (in `data/benchmark/`).

Soglie ready/not-ready (nota 9 sopra) rispettate **post-segregazione
esplicita** di:
- Q35, Q19 come runtime corpus limit (falsi negativi del flag
  `has_corpus_limit_declaration` a monte, comportamento runtime allineato
  al gruppo B)
- Q17 come judge-bound artifact (penalizzazione judge su parentesi
  esplicative in risposta correttamente groundata)

La segregazione è dichiarata come modifica metodologica ex-post nel
report, non camuffata in aggregati ricalcolati silenziosamente.

Le note 1-9 a monte di questo file restano valide e immutate come
baseline metodologico riproducibile per future iterazioni del benchmark.

## Esito F.2 (2026-05-21, post-run benchmark esteso 100 query)

Run completato 2026-05-21 con judge Sonnet 4.6 (continuità con W7
post "Modifica setup judge"). 100 query (77 positive + 20 negative
+ 3 edge), wall-clock 4 541 s, cost $6.8175. Verdict: **GO
ready-with-followup**. Soglia rilascio pubblico v1.0 raggiunta.

Aggregati globali: faithfulness mediana **0.886**, answer_relevancy
mediana **0.815**. Drift v1 W7 archived vs F.2 ricalcolato (38
positive Q1-Q50): faith −0.042, rel −0.007 — entro soglia 0.05.

Risultati, analisi qualitativa bottom-5, modifica metodologica
ex-post e follow-up v1.1 in [`BENCHMARK_RAGAS_F2.md`](BENCHMARK_RAGAS_F2.md).

Le note 1-9 e l'esito W7 sopra restano immutati come baseline
storica. F.2 estende il pattern senza riscrivere la spec a monte.