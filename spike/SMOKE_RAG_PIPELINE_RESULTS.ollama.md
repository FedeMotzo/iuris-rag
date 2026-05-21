# Smoke RAG pipeline — risultati

Provider: **ollama** (qwen2.5:14b), top_k=5, rerank_top_k=20, use_graph=False. 1 run/query (no warmup interno).

## Q6

**Query**: Quali sono i compiti del responsabile della protezione dei dati?

**Timings (ms)**: retrieval=4189, gen=33404 (TTFT=21301, 286 tok @ 8.6 tok/s), verify=1, total=37594 (wall 37594)

**Citazioni**: n_total=4, n_verified=4, all_verified=True, finish_reason=stop

**Chunk recuperati (top-5 post-rerank)**:

- `eli/reg/2016/679/oj__art_39` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 39)
- `eli/reg/2016/679/oj__art_38` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 38)
- `eli/reg/2016/679/oj__art_37` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 37)
- `eli/reg/2016/679/oj__recital_97` (Considerando 97)
- `eli/reg/2016/679/oj__recital_108` (Considerando 108)

**Annotated answer**:

```
Il responsabile della protezione dei dati è incaricato di svolgere almeno i seguenti compiti:

a) Informare e fornire consulenza sulle obbligazioni derivanti dal regolamento sulla protezione dei dati personali, nonché da altre disposizioni dell'Unione o degli Stati membri in materia di protezione dei dati [cite:eli/reg/2016/679/oj__art_39].

b) Sorvegliare l'osservanza del regolamento e delle politiche interne del titolare del trattamento riguardo alla protezione dei dati personali, inclusa la sensibilizzazione e formazione del personale coinvolto nei trattamenti [cite:eli/reg/2016/679/oj__art_39].

c) Fornire pareri sulla valutazione d'impatto sulla protezione dei dati e sorvegliarne l'implementazione [cite:eli/reg/2016/679/oj__art_39].

d) Cooperare con le autorità di controllo e fungere da punto di contatto per questioni relative al trattamento, come la consultazione preventiva [cite:eli/reg/2016/679/oj__art_39].
```

**Qualità**: risposta corretta e strutturata sui 4 compiti previsti dall'art. 39 GDPR (informare, sorvegliare, fornire pareri DPIA, cooperare con autorità). Tutte e 4 le citazioni puntano allo stesso chunk `art_39`, che è effettivamente quello giusto (l'art. 38 sulla posizione del DPO e l'art. 37 sulla designazione non sono il riferimento corretto per "compiti"). Il modello ha selezionato il chunk pertinente fra i 5 disponibili. Tutti i marker verificati. Latenza dominata da TTFT 21 s (Qwen 14B prefill su prompt ~2k token).

## Q7

**Query**: Quando è obbligatoria la valutazione d'impatto sulla protezione dei dati?

**Timings (ms)**: retrieval=3428, gen=27183 (TTFT=14296, 304 tok @ 11.2 tok/s), verify=0, total=30612 (wall 30612)

**Citazioni**: n_total=4, n_verified=4, all_verified=True, finish_reason=stop

**Chunk recuperati (top-5 post-rerank)**:

- `eli/reg/2016/679/oj__recital_91` (Considerando 91)
- `eli/reg/2016/679/oj__art_35` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 35)
- `eli/reg/2016/679/oj__recital_92` (Considerando 92)
- `eli/reg/2016/679/oj__recital_90` (Considerando 90)
- `eli/reg/2016/679/oj__recital_84` (Considerando 84)

**Annotated answer**:

```
La valutazione d'impatto sulla protezione dei dati è obbligatoria quando un tipo di trattamento, considerata la sua natura, l'oggetto, il contesto e le finalità, può presentare un rischio elevato per i diritti e le libertà delle persone fisiche [cite:eli/reg/2016/679/oj__art_35]. In particolare, è richiesta nei seguenti casi:

- Una valutazione sistematica e globale di aspetti personali relativi a persone fisiche basata su un trattamento automatizzato, compresa la profilazione, e sulla quale si fondano decisioni che hanno effetti giuridici o incidono in modo significativo su dette persone fisiche [cite:eli/reg/2016/679/oj__art_35].
- Il trattamento su larga scala di categorie particolari di dati personali, come quelli menzionati nell'articolo 9, paragrafo 1, o di dati relativi a condanne penali e reati [cite:eli/reg/2016/679/oj__art_35].
- La sorveglianza sistematica su larga scala di una zona accessibile al pubblico [cite:eli/reg/2016/679/oj__art_35].
```

**Qualità**: risposta corretta sui 3 casi di DPIA obbligatoria dell'art. 35 par. 3 GDPR. Citazioni tutte e 4 sull'art. 35, che è il riferimento giusto — i considerando 90-92 sono stati ignorati nella risposta ma erano nel contesto (uso parsimonioso). Lieve imprecisione: la risposta dice "in particolare, è richiesta nei seguenti casi" e poi elenca le 3 ipotesi, mentre il par. 3 dice "in particolare nei casi seguenti" — sostanzialmente equivalente. Tutti i marker verificati. TTFT 14 s.

## Q1

**Query**: Un sistema che fa screening automatico dei CV in fase di selezione del personale ricade tra i sistemi ad alto rischio dell'AI Act?

**Timings (ms)**: retrieval=2946, gen=29878 (TTFT=22004, 180 tok @ 6.0 tok/s), verify=0, total=32824 (wall 32824)

**Citazioni**: n_total=2, n_verified=2, all_verified=True, finish_reason=stop

**Chunk recuperati (top-5 post-rerank)**:

- `eli/reg/2024/1689/oj__recital_57` (Considerando 57)
- `eli/reg/2024/1689/oj__recital_61` (Considerando 61)
- `eli/reg/2024/1689/oj__recital_85` (Considerando 85)
- `eli/reg/2024/1689/oj__recital_53` (Considerando 53)
- `eli/reg/2024/1689/oj__art_6` (Capo III - SISTEMI DI IA AD ALTO RISCHIO > art. 6)

**Annotated answer**:

```
Il sistema di screening automatico dei CV in fase di selezione del personale ricade tra i sistemi ad alto rischio dell'AI Act, poiché tali sistemi possono avere un impatto significativo sul futuro delle persone in termini di prospettive di carriera e sostentamento [cite:eli/reg/2024/1689/oj__recital_57]. Inoltre, i considerando 53 del regolamento specifica che sistemi di IA utilizzati per finalità come l'assunzione e la selezione delle persone dovrebbero essere classificati come ad alto rischio a meno che non soddisfino determinate condizioni restrittive [cite:eli/reg/2024/1689/oj__recital_53].
```

**Qualità**: conclusione corretta (sistema HR è high-risk), ma la motivazione è debole. Il vero riferimento dovrebbe essere **AI Act art. 6 par. 2 + allegato III punto 4** (occupazione e gestione del personale), non i considerando 57/53. L'art. 6 è effettivamente nel top-5 retrieval (rank 5), ma il modello non l'ha citato — ha preferito i considerando ai primi rank post-rerank. Entrambe le citazioni verificate strutturalmente, ma il `citation_verifier` non può vedere che mancano le citazioni "giuste". Caso d'uso che evidenzia il limite di v1: verifica strutturale ≠ verifica semantica. Latenza alta (TTFT 22 s) perché Q1 ha prompt più lungo (allegati AI Act).

---

## Sintesi smoke

3/3 query con `all_verified=True`. Latenza end-to-end mediana ~33 s, di cui ~75% generation Qwen 14B. Il pipeline funziona: retrieval → rerank → user prompt RAG → LLM → citation verify, tutto orchestrato correttamente, timings popolati, annotated_answer prodotto.

**Limite v1 esposto**: il `citation_verifier` cattura solo la corrispondenza strutturale `chunk_id ∈ retrieval_context`. Su Q1 il modello cita due considerando invece dell'articolo + allegato che sarebbero la fonte primaria — `all_verified=True` non significa "risposta semanticamente corretta". La validazione semantica resta a Ragas W7 (faithfulness LLM-as-judge).

**Prossimo step naturale**: rieseguire lo stesso smoke con `LLM_PROVIDER=anthropic` (Claude Sonnet 4.6) appena Federico ha l'API key, per confrontare (a) latenza (cloud dovrebbe stare sotto 3 s TTFT vs 14-22 s locale) e (b) qualità delle citazioni su Q1 (Sonnet 4.6 dovrebbe preferire l'articolo al considerando).
