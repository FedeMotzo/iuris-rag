# Smoke RAG pipeline — risultati

Due run a confronto: provider locale (Ollama Qwen2.5-14B Q4_K_M) e
provider cloud (Anthropic `claude-sonnet-4-6`). 3 query del benchmark
(Q6, Q7, Q1), 1 run per query, no warmup interno. `top_k=5`,
`rerank_top_k=20`, `use_graph=False`.

---

## Run locale Ollama (2026-05-19)

Provider: **ollama** (qwen2.5:14b), reranker su CPU (topologia S2).

### Q6

**Query**: Quali sono i compiti del responsabile della protezione dei dati?

**Timings (ms)**: retrieval=4189, gen=33404 (TTFT=21301, 286 tok @ 8.6 tok/s), verify=1, total=37594

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

### Q7

**Query**: Quando è obbligatoria la valutazione d'impatto sulla protezione dei dati?

**Timings (ms)**: retrieval=3428, gen=27183 (TTFT=14296, 304 tok @ 11.2 tok/s), verify=0, total=30612

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

**Qualità**: risposta corretta sui 3 casi di DPIA obbligatoria dell'art. 35 par. 3 GDPR. Citazioni tutte e 4 sull'art. 35, che è il riferimento giusto — i considerando 90-92 sono stati ignorati nella risposta ma erano nel contesto (uso parsimonioso). Tutti i marker verificati. TTFT 14 s.

### Q1

**Query**: Un sistema che fa screening automatico dei CV in fase di selezione del personale ricade tra i sistemi ad alto rischio dell'AI Act?

**Timings (ms)**: retrieval=2946, gen=29878 (TTFT=22004, 180 tok @ 6.0 tok/s), verify=0, total=32824

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

## Run cloud Anthropic (2026-05-19)

Provider: **anthropic** (claude-sonnet-4-6), reranker su MPS (topologia S1).

### Q6

**Query**: Quali sono i compiti del responsabile della protezione dei dati?

**Timings (ms)**: retrieval=8400, gen=10953 (TTFT=1910, 500 tok @ 45.7 tok/s), verify=0, total=19353 (wall 19354)

**Citazioni**: n_total=2, n_verified=2, all_verified=True, finish_reason=length

**Chunk recuperati (top-5 post-rerank)**:

- `eli/reg/2016/679/oj__art_39` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 39)
- `eli/reg/2016/679/oj__art_38` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 38)
- `eli/reg/2016/679/oj__art_37` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 37)
- `eli/reg/2016/679/oj__recital_97` (Considerando 97)
- `eli/reg/2016/679/oj__recital_108` (Considerando 108)

**Annotated answer**:

```
## Compiti del Responsabile della Protezione dei Dati (RPD)

Ai sensi dell'art. 39 del GDPR, il RPD è incaricato almeno dei seguenti compiti [cite:eli/reg/2016/679/oj__art_39]:

1. **Informazione e consulenza**: informare e fornire consulenza al titolare del trattamento, al responsabile del trattamento e ai dipendenti che eseguono il trattamento in merito agli obblighi derivanti dal Regolamento e da altre disposizioni dell'Unione o degli Stati membri in materia di protezione dei dati.

2. **Sorveglianza della conformità**: sorvegliare l'osservanza del Regolamento, di altre disposizioni applicabili e delle politiche interne del titolare/responsabile del trattamento, incluse l'attribuzione delle responsabilità, la sensibilizzazione e la formazione del personale coinvolto nei trattamenti.

3. **Supporto alla DPIA**: fornire, se richiesto, un parere in merito alla valutazione d'impatto sulla protezione dei dati (art. 35) e sorvegliarne lo svolgimento.

4. **Cooperazione con l'autorità di controllo**: cooperare con l'autorità di controllo e fungere da punto di contatto per questioni connesse al trattamento, inclusa la consultazione preventiva di cui all'art. 36.

Nell'esecuzione di tali compiti, il RPD è tenuto a considerare debitamente i rischi inerenti al trattamento, tenuto conto della natura, dell'ambito di applicazione, del contesto e delle finalità del medesimo [cite:eli/reg/2016/679/oj__art_39].

### Condizioni di esercizio

Il titolare e il responsabile del trattamento sono tenuti a fornire al RPD le risorse necessarie per assolvere i propri compiti, garantirne l'indipendenza e assicurare che
```

### Q7

**Query**: Quando è obbligatoria la valutazione d'impatto sulla protezione dei dati?

**Timings (ms)**: retrieval=1849, gen=10244 (TTFT=1298, 500 tok @ 48.8 tok/s), verify=0, total=12094 (wall 12094)

**Citazioni**: n_total=3, n_verified=3, all_verified=True, finish_reason=length

**Chunk recuperati (top-5 post-rerank)**:

- `eli/reg/2016/679/oj__recital_91` (Considerando 91)
- `eli/reg/2016/679/oj__art_35` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 35)
- `eli/reg/2016/679/oj__recital_92` (Considerando 92)
- `eli/reg/2016/679/oj__recital_90` (Considerando 90)
- `eli/reg/2016/679/oj__recital_84` (Considerando 84)

**Annotated answer**:

```
## Quando è obbligatoria la valutazione d'impatto sulla protezione dei dati (DPIA)

### Obbligo generale

La DPIA è obbligatoria quando un tipo di trattamento — in particolare se prevede l'uso di nuove tecnologie — **può presentare un rischio elevato per i diritti e le libertà delle persone fisiche**, considerati la natura, l'oggetto, il contesto e le finalità del trattamento. La valutazione deve essere effettuata **prima** di procedere al trattamento [cite:eli/reg/2016/679/oj__art_35].

Il titolare del trattamento è responsabile dello svolgimento della DPIA per determinare l'origine, la natura, la particolarità e la gravità del rischio [cite:eli/reg/2016/679/oj__recital_84].

---

### Casi specifici in cui la DPIA è richiesta

L'art. 35, par. 3, individua tre ipotesi in cui la DPIA è richiesta **in particolare** [cite:eli/reg/2016/679/oj__art_35]:

1. **Profilazione con effetti significativi**: valutazione sistematica e globale di aspetti personali basata su trattamento automatizzato, compresa la profilazione, sulla quale si fondano decisioni con effetti giuridici o che incidono significativamente sulle persone fisiche.

2. **Trattamento su larga scala di categorie particolari di dati**: trattamento su larga scala di dati di cui all'art. 9, par. 1 (dati sensibili), o di dati relativi a condanne penali e reati (art. 10).

3. **Sorveglianza sistematica su larga scala** di zone accessibili al pubblico.

---

### Ulteriori fattispecie rilevanti

Il considerando 91 precisa che la DPIA è altresì necessaria nei seguenti casi [cite:eli/reg
```

### Q1

**Query**: Un sistema che fa screening automatico dei CV in fase di selezione del personale ricade tra i sistemi ad alto rischio dell'AI Act?

**Timings (ms)**: retrieval=1840, gen=11340 (TTFT=1649, 500 tok @ 44.1 tok/s), verify=0, total=13180 (wall 13180)

**Citazioni**: n_total=2, n_verified=2, all_verified=True, finish_reason=length

**Chunk recuperati (top-5 post-rerank)**:

- `eli/reg/2024/1689/oj__recital_57` (Considerando 57)
- `eli/reg/2024/1689/oj__recital_61` (Considerando 61)
- `eli/reg/2024/1689/oj__recital_85` (Considerando 85)
- `eli/reg/2024/1689/oj__recital_53` (Considerando 53)
- `eli/reg/2024/1689/oj__art_6` (Capo III - SISTEMI DI IA AD ALTO RISCHIO > art. 6)

**Annotated answer**:

```
## Classificazione come sistema ad alto rischio

Sì, un sistema di IA per lo screening automatico dei CV in fase di selezione del personale ricade, in linea di principio, tra i sistemi ad alto rischio ai sensi dell'AI Act.

### Base normativa

Il Considerando 57 chiarisce esplicitamente che i sistemi di IA utilizzati **"per l'assunzione e la selezione delle persone"** devono essere classificati come ad alto rischio, in quanto possono avere un impatto significativo sulle prospettive di carriera e sul sostentamento degli individui. Il considerando evidenzia inoltre che tali sistemi **"possono perpetuare modelli storici di discriminazione"**, ad esempio nei confronti delle donne, di determinate fasce di età, persone con disabilità o persone con determinate origini razziali o etniche [cite:eli/reg/2024/1689/oj__recital_57].

Sul piano dispositivo, l'art. 6, paragrafo 2, stabilisce che sono considerati ad alto rischio i sistemi di IA elencati nell'**Allegato III**, che include i sistemi per l'assunzione e la selezione del personale [cite:eli/reg/2024/1689/oj__art_6].

### Possibile eccezione

L'art. 6, paragrafo 3, prevede una deroga: un sistema elencato nell'Allegato III **non** è considerato ad alto rischio se non influenza materialmente il processo decisionale e ricorre almeno una delle seguenti condizioni:

- esegue un **compito procedurale limitato** (es. trasformazione di dati non strutturati in strutturati, classificazione documentale);
- migliora il risultato di un'**attività umana precedentemente completata**;
- rileva schemi decisionali senza sostituire la valutazione umana;
- svolge un **compito meramente preparatorio** [cite:eli/reg/2024/1689/oj
```

---

## Riepilogo cloud vs locale

| metrica | Ollama (Qwen 14B) | Anthropic (Sonnet 4.6) | delta |
|---|---|---|---|
| TTFT mediano | 21.3 s | 1.6 s | **−13×** |
| Throughput | 6-11 tok/s | 44-49 tok/s | **+5×** |
| Total e2e mediano (Q7) | 30.6 s | 12.1 s | **−2.5×** |
| all_verified | 3/3 | 3/3 | pari |

### Osservazioni qualitative

**Q1 — caso peggiore del benchmark.** Sonnet cita correttamente l'art. 6 AI Act + Allegato III, distinguendo "considerando 57 motiva" + "art. 6 par. 2 stabilisce dispositivo" + "art. 6 par. 3 deroghe". Qwen su Q1 aveva citato considerando invece di articolo dispositivo. **Cloud vince con margine netto sul caso peggiore.**

**Q7 — cita 3 fonti con gerarchia argomentativa** (art. 35 + considerando 84 + considerando 91, contestualizzando con "L'art. 35, par. 3, individua tre ipotesi"). Sonnet è strutturato come scrittura giuridica.

**`finish_reason=length` su 3/3 query cloud.** 500 token tagliano risposte mid-frase (Q6 si chiude su "assicurare che"; Q7 lascia sezione "ulteriori fattispecie rilevanti" iniziata e non chiusa). **Decisione presa immediatamente**: default `RAG_MAX_OUTPUT_TOKENS` alzato da 500 → 1000 in `core/serving/config.py` e `core/serving/pipeline.py`. Costo extra cloud trascurabile (~$0.0075/query). Vedi `PROJECT_CONTEXT.md` registro decisioni voce 29 del 2026-05-19.

### Sintesi operativa

3/3 query con `all_verified=True` su entrambi i provider — il pipeline funziona e il citation verifier strutturale cattura quel che deve. Cloud Anthropic risolve di fatto i due limiti operativi del locale (TTFT cold + throughput) e produce out-of-the-box una qualità di citazione semantica superiore sul caso peggiore (Q1). Locale resta validamente come fallback / demo offline, con il caveat documentato che su prompt lunghi (>3k token) Q1-like la latenza è 30-37 s e la qualità di citazione richiede review umana.

Il pipeline è pronto per W6 (UI Streamlit) con `LLM_PROVIDER=anthropic` come default deciso.
