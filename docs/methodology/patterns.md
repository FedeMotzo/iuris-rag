# Pattern metodologici — iuris-rag v0.5.0

> Consolidamento dei pattern metodologici emersi durante la
> costruzione di iuris-rag v0.5.0 (8 settimane, 2026-05-13 →
> 2026-05-21). Audience: ricercatori/practitioner che vogliono
> adattare i pattern al proprio dominio, o capire come è stato
> costruito il benchmark + sistema.

**Cosa questo documento NON è:**

- Non è un tutorial RAG (per quello vedi [`../../core/README.md`](../../core/README.md)).
- Non è una descrizione architetturale (vedi
  [`../architecture/README.md`](../architecture/README.md)).
- Non sostituisce il registro decisioni datato (vedi
  [`../../PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md)) — i
  pattern qui sono il *cosa* e il *come*, il registro è il *quando*
  e il *perché su questa decisione specifica*.

I 6 pattern sono presentati nell'ordine cronologico di emersione,
non per importanza: lo spike di W0 ha preceduto tutto il resto, il
registro append-only è stato applicato dal giorno 1, la curatela
giuridica è emersa in W7-prep dopo aver visto i primi punteggi
Ragas, e così via. L'ordine racconta il percorso.

---

## Pattern 1 — Spec-first

### Cosa

Ogni fase di evaluation ha una spec metodologica scritta **prima**
dell'esecuzione del run: soglie ready/not-ready esplicite, criterio
di decisione, output atteso, vincoli su cosa NON è la fase. Le
modifiche emergenti durante l'esecuzione sono dichiarate in coda al
documento, non sovrascrivono la spec a monte.

### Perché esiste

Le metriche LLM-as-judge (Ragas faithfulness e answer_relevancy)
hanno gradi di libertà sufficienti da poter essere lette
opportunisticamente a valle del run. Senza una soglia scritta
*prima* di vedere i numeri, è troppo facile dichiarare "GO" alzando
la soglia post-hoc, o "NOT GO" abbassandola. La spec a monte
trasforma il run in una verifica, non in una negoziazione.

Il pattern è esplicito nel testo della spec stessa:

> "Questa spec è scritta **prima** dell'esecuzione. Modifiche a
> soglie, metriche o criteri di decisione fatte dopo aver visto i
> risultati vanno annotate in coda […], **non** sovrascrivendo
> queste note a monte. Le note a monte restano il baseline
> metodologico riproducibile."
>
> — [`RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md)
> "Vincolo metodologico"

### Come si applica

Prima di ogni fase di valutazione:

1. **Scrivere e committare la spec** prima di lanciare lo script di
   eval. Contenuto minimo: obiettivo, setup, metriche, soglie
   ready/not-ready con motivazione, criterio di decisione,
   esplicito "cosa NON è questa fase" (per blindare contro
   scope creep).
2. **Lanciare il run** sulla spec committata. Il commit della spec
   è il timestamp del baseline metodologico.
3. **Scrivere il report post-run** in un documento separato, con
   header che linka alla spec. Le modifiche emergenti (es. lettura
   segregata di query come runtime corpus limit) vanno **in coda**
   al report con la propria sezione "Modifica metodologica
   ex-post" e motivazione esplicita.
4. **Aggiungere l'esito in coda alla spec** come sezione
   "Esito \<fase\>", senza toccare le note 1-N a monte. Le spec
   diventano append-only come i registri (vedi
   [Pattern 2](#pattern-2--decisioni-datate-registro-append-only)).

### Esempio concreto

[`RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md) è
stato scritto il 2026-05-20 prima del run W7, con 9 note
metodologiche, criterio di decisione ready / ready-with-followup /
not-ready, e sezione "Cosa NON è W7". Il run W7 si è chiuso lo
stesso giorno con verdict **ready-with-followup** dopo
segregazione esplicita di Q35/Q19 come runtime corpus limit —
modifica documentata in coda a
[`BENCHMARK_RAGAS_W7.md`](../../data/benchmark/BENCHMARK_RAGAS_W7.md)
§ "Modifica metodologica ex-post", non camuffata in aggregati
ricalcolati silenziosamente.

Il pattern si è esteso a F.2 (2026-05-21) senza modificare la spec
W7: F.2 ha aggiunto la propria sezione "Esito F.2" in coda alla
stessa `RAGAS_RUN_NOTES.md`, applicando le note 1-9 come baseline
storica. Stesso meccanismo, stesso file, due run distanziati di
24h.

### Limiti del pattern

- **Richiede disciplina di processo**: ~30-60 minuti di scrittura
  della spec prima del run. La tentazione di "lanciamo subito e poi
  scriviamo" è forte quando lo script di eval è pronto.
- **Più costoso che valutare a posteriori**, ma paga in
  riproducibilità + resistenza al bias di lettura + trail
  metodologico citabile.
- **Le soglie pre-run possono essere mal calibrate**: la spec è
  baseline, non dogma. Ricalibrare è legittimo purché dichiarato
  in coda con motivazione, non riscritto a monte.

---

## Pattern 2 — Decisioni datate (registro append-only)

### Cosa

[`SCOPE.md`](../../SCOPE.md) e
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) sono living docs
con un registro append-only di decisioni datate. Ogni voce ha
data (ISO `YYYY-MM-DD`), descrizione della decisione, motivazione e
impatto stimato sul time-to-completion. Le decisioni vecchie non
vengono riscritte: vengono superate da decisioni nuove che le
referenziano esplicitamente.

### Perché esiste

Il contesto del "perché è fatto così" è la prima cosa che si perde
nel codice e la prima cosa che serve quando si decide come
estenderlo o cambiarlo. Git ha l'history dei file ma non
l'history del *ragionamento*: un commit message non spiega quali
alternative sono state considerate e scartate. Il registro
append-only conserva questa traccia in un singolo file leggibile
linearmente, con timestamp e impatto.

A v0.5.0 il registro
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) ha **35 voci**
datate dal 2026-05-13 al 2026-05-21, e il registro
[`SCOPE.md`](../../SCOPE.md) ne ha 15. Il volume è gestibile perché
ogni voce è una riga di tabella + paragrafo motivazione, e il file
è linkato dai README di alto livello con riferimenti puntuali.

### Come si applica

Per ogni decisione non triviale:

1. **Decidere se è registrabile**. Una decisione è "non triviale"
   se: (a) coinvolge un trade-off fra due opzioni plausibili, o
   (b) costa più di 2h implementare, o (c) può essere
   rimessa in discussione fra 1-3 mesi.
2. **Scrivere una riga nel registro**: numero progressivo,
   descrizione 1-3 frasi, motivazione 2-4 frasi (con riferimento al
   documento autoritativo: smoke, benchmark, mini-spike),
   impatto stimato.
3. **Linkare la voce dal codice o dal documento di settore** quando
   serve, con riferimento posizionale (es. "vedi
   PROJECT_CONTEXT.md voce 29").
4. **Non riscrivere le voci esistenti**: se una decisione cambia,
   nuova voce che dichiara il cambio e referenzia la precedente.

### Esempio concreto

Voce 18 di [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md):

> "Default produttivo `rerank_top_k=20` (non 50). Hybrid + reranker
> top-20 è strict-dominant su dense puro […]. Top-50 sale di altri
> +10pp R@10 in media ma introduce regressioni su 3-4 query […]
> non strict-dominant. Top-50 esposto come parametro opzionale,
> non default. — Benchmark W3 settimana 3 […]. Decisione informata
> da trade-off qualità/latenza/regressioni puntuali, non solo da
> media aggregata."

La voce documenta una decisione attualmente attiva in
[`core/serving/config.py`](../../core/serving/config.py) (default
`RAG_RERANK_TOP_K=20`) con motivazione tracciabile al benchmark
W3 ([`BENCHMARK_W3.md`](../../data/benchmark/BENCHMARK_W3.md)). Chi
volesse rimettere in discussione il default in v1.1 trova
nell'unica riga: il numero alternativo (50), perché era stato
scartato (regressioni puntuali su 3-4 query), e l'esperimento
da rifare (re-run benchmark W3 con cap aggiornato).

### Limiti del pattern

- **L'append-only diventa lungo**: 35 voci a fine v0.5.0 sono
  ancora gestibili, a 100+ servirebbe indicizzazione esplicita
  (tag tematici, indice in testa). Per ora scala via tabella "File
  del progetto" + riferimenti posizionali dai documenti di settore.
- **Disciplina richiesta**: la tentazione di "lo registro dopo" è
  costante. La voce scritta 48h dopo perde la motivazione più
  sottile.
- **Il registro non sostituisce la documentazione tecnica nei
  moduli**: una decisione architetturale registrata può anche
  vivere come docstring/TODO nel modulo che la implementa (es.
  voce 21 topologia MPS è TODO esplicito in
  [`core/serving/config.py`](../../core/serving/config.py)).

---

## Pattern 3 — Curatela giuridica come secondo livello di validazione

### Cosa

La curatela del benchmark non chiede solo "annotazione corretta?"
ma "annotazione **giuridicamente** coerente?". In W7-prep
(2026-05-19) è emersa una tassonomia di 3 categorie di flag che la
curatela deve segnalare proattivamente:

- **gold sbagliato**: errore di annotazione (es. LLM-hint
  allucinato in setup benchmark);
- **corpus insufficiente**: il chunk richiesto è fuori corpus v1
  (es. codice penale richiamato da 231 ma non ingerito);
- **capability insufficiente**: l'architettura retrieval v1 non
  basta a chiudere la query (es. cross-norma con vocabolari
  disgiunti).

### Perché esiste

Il benchmark retrieval-only (R@K, MRR, NDCG calcolati su
`gold_chunks` annotati) misura la coerenza interna del sistema con
le sue stesse annotazioni: se il gold è sbagliato, una metrica
"buona" può nascondere un problema reale, e una metrica "cattiva"
può essere falsamente attribuita a un problema di retrieval che in
realtà è un problema di annotazione o di copertura corpus.

W7-prep ha rivelato un caso emblematico: Q5 ("AI per decisioni HR
+ responsabilità 231") aveva nel gold `art_25-undecies`
(reati ambientali) — annotazione palesemente sbagliata, allucinata
da un LLM-hint in setup. Il retrieval-only la registrava come
zero-recall e tirava giù le aggregate; senza la sanity check
giuridica, il segnale era "il retrieval ha un problema sulla
multi-normativa", che è in parte vero ma per una ragione diversa
(capability cross-norma, non gap retrieval semplice).

### Come si applica

Durante la curatela di ogni query del benchmark:

1. **Leggere `gold_chunks` con occhio giuridico**, non solo
   sintattico. Se il chunk annotato non parla del tema della query,
   è candidato a flag "gold sbagliato".
2. **Verificare la presenza dei chunk pertinenti nel corpus**.
   Se un chunk che *dovrebbe* esistere non è nei gold candidate, è
   candidato a flag "corpus insufficiente" oppure "gold sbagliato
   per omissione".
3. **Distinguere capability vs gap retrieval**. Se la query è
   strutturalmente cross-norma con vocabolari disgiunti (es. HR ↔
   penale-amministrativo), è candidato a flag "capability
   insufficiente" — non risolvibile con tuning terminology/graph
   statici, richiede architetture retrieval avanzate (multi-query,
   HyDE, query rewriting LLM-assisted) → v1.1.
4. **Agire sul flag, non sull'aggregato**. Bug di annotazione → fix
   gold (es. Q9: gold ridotto da 4 chunk a 1, riscritta in
   scenario C); gap corpus → dichiarazione di limite (vedi
   [Pattern 4](#pattern-4--dichiarazione-di-limite-corpus-trasparenza-ux-strutturale));
   limite capability → riclassifica `positive` → `edge` (es. Q5).

### Esempio concreto

**Q5 — capability insufficiente**: l'audit di curatela W7-prep ha
rivelato in 3 step che (a) il gold `art_25-undecies` era allucinato
da LLM-hint, (b) il corpus 231 è completo (109 articoli, 4/4
Q5-rilevanti ingeriti), (c) il problema è di capability — bge-m3
multilingue non chiude il gap lessicale fra "lavoratori",
"valutazione", "AI" e "reato-presupposto", "responsabilità
amministrativa", "ente". Decisione: riclassifica Q5 da `positive`
a `edge`, benchmark W3 ri-aggregato su 38 positive. Vedi
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) voce 30 +
[`STATS.md`](../../data/benchmark/STATS.md) § "Audit annotazione".

**Q9 — gold sbagliato + corpus insufficiente**: stesso pattern di
allucinazione `art_25-undecies` su Q9 ("Reati 231 trattamento
illecito dati"). Audit esteso a 6 query 231-related ha confermato
che il bug è isolato a Q5+Q9, non sistemico. Q9 mantenuta
`positive` ma con gold ridotto a `art_24-bis` e
`gold_answer` riscritta in scenario C: contenuto su `art_24-bis`
(delitti informatici come reati-presupposto + sanzioni) +
dichiarazione esplicita di limite (dettaglio singole fattispecie
c.p. fuori corpus v1). Vedi
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) voce 31 +
[`spike/ANNOTATION_SAMPLING_231.md`](../../spike/ANNOTATION_SAMPLING_231.md).

### Limiti del pattern

- **Richiede competenza giuridica oltre quella di RAG/IR**. Senza
  sanity check giuridico, il benchmark misura "annotazione
  auto-consistente", non "annotazione corretta nel dominio". Il
  curatore deve saper riconoscere `art_25-undecies` come reati
  ambientali, non come "reati informatici".
- **Costo non trascurabile**: ~2.5 giorni di curatela
  LLM-assisted con revisione umana entry-per-entry su 38 positive.
  Su 380 va riconsiderato (sampling stratificato? validazione
  incrociata?).
- **Le 3 categorie non sono esaustive**. La tassonomia è
  *descrittiva* delle 2 anomalie trovate in v1 (Q5, Q9), non
  normativa. Iterazioni future potrebbero scoprire categorie
  aggiuntive ("gold parzialmente corretto", "query ambigua").

---

## Pattern 4 — Dichiarazione di limite corpus (trasparenza UX strutturale)

### Cosa

Quando una query richiede contenuto fuori corpus, la `gold_answer`
chiude con dichiarazione esplicita user-facing del tipo "...non
incluso nel corpus normativo di riferimento". È un pattern di
trasparenza UX strutturale: il sistema dichiara apertamente cosa
sa e cosa no, invece di omettere o di inventare.

Il pattern è stato formalizzato in W7-prep e applicato a
**11 query positive** del benchmark v1 ([`STATS.md`](../../data/benchmark/STATS.md)
§ "Dichiarazione di limite corpus"), poi propagato strutturalmente
al benchmark v2.

### Perché esiste

Il target audience del sistema (DPO, compliance officer, studi
legali) ha bisogno di sapere quando una risposta è *parziale per
costruzione*: se la query riguarda l'art. 615-ter c.p. richiamato
come reato-presupposto da `art_24-bis` D.Lgs 231/2001, e il c.p.
non è ingerito nel corpus v1, il sistema deve dirlo invece di
inventare il contenuto dell'art. 615-ter o di ignorarlo. La
dichiarazione di limite è il meccanismo UX che mantiene la fiducia
del professional anche quando il corpus è incompleto.

### Come si applica

Per ogni query in cui la `gold_answer` richiede contenuto fuori
corpus:

1. **Identificare cosa manca**: codice penale, decreti settoriali
   (D.Lgs 81/2008, D.Lgs 152/2006), standard ISO (fuori scope
   copyright), articoli specifici di norme già in corpus ma non
   ingeriti, eccetera.
2. **Scrivere la `gold_answer` in due parti**: (a) contenuto
   sostantivo su ciò che il corpus copre, con citazioni
   `[cite:CHUNK_ID]` regolari; (b) chiusura con dichiarazione
   esplicita di limite, lessico canonico `"...non incluso nel
   corpus normativo di riferimento"` (con varianti di concordanza
   incluso/inclusi/inclusa/incluse).
3. **Marcare il flag `has_corpus_limit_declaration=true`** nel
   dataset gold. In v1 il flag governa la segregazione in
   Gruppo A (non-limite) vs Gruppo B (limite) per la lettura
   aggregata Ragas — Gruppo B ha soglie più morbide per design
   (vedi nota 7 di
   [`RAGAS_RUN_NOTES.md`](../../data/benchmark/RAGAS_RUN_NOTES.md)).
4. **NON usare lessico tecnico interno** come `"gold_chunks
   forniti"` o `"chunk del retrieval"` nel testo user-facing.
   L'utente professional non sa cos'è un `gold_chunk`.

### Esempio concreto

**Q9** (codice penale fuori corpus): `gold_answer` riscritta in
scenario C dopo l'audit 231 di W7-prep. Contenuto su `art_24-bis`
con elenco articoli c.p. richiamati come reati-presupposto +
sanzioni pecuniarie e interdittive; chiusura con dichiarazione
esplicita che il dettaglio delle singole fattispecie c.p. richiede
il codice penale, non incluso nel corpus normativo di riferimento.

**Q24, Q26, Q27** (decreti settoriali): pattern analogo per
sicurezza sul lavoro (D.Lgs 81/2008) e ambiente (D.Lgs 152/2006).
**Q49** (standard ISO 9001): pattern analogo, dichiarazione esplicita
che le norme ISO sono standard tecnici privati non ingeribili per
ragioni di licenza.

Lista completa delle 11 query con tipo di corpus mancante
dichiarato: [`STATS.md`](../../data/benchmark/STATS.md)
§ "Dichiarazione di limite corpus".

### Limiti del pattern

- **Detection automatica oggi inaffidabile**. F.2 (2026-05-21) ha
  applicato la regex canonica sui 100 output e ha trovato **0
  match** sulle 23 query con `has_corpus_limit_declaration=true`.
  Sonnet 4.6 usa varianti lessicali ("Il contesto normativo fornito
  non contiene riferimenti sufficienti…", "Non è possibile
  confermare sulla base del solo contesto fornito…") — drift
  sistematico 23/23.
- **Pattern semantico funziona, pattern lessicale no.** La sostanza
  della dichiarazione di limite è preservata; la regex come
  detection è obsoleta. Follow-up 1 di F.2: sostituzione con
  LLM-as-judge in v1.1.
- **Ragas insensibile al drift lessicale**. Il judge valuta
  coerenza semantica, non match lessicale. Le metriche F.2
  (faith 0.886, rel 0.815) sono affidabili nonostante il drift —
  problema di classificazione runtime, non di valutazione.

---

## Pattern 5 — Tassonomia scenari A/B/C per gold_answer

### Cosa

3 scenari descrittivi di costruzione della `gold_answer`, emersi
durante curatela W7-prep:

- **Scenario A** — corpus completo + capability sufficiente:
  risposta completa con citazioni `[cite:CHUNK_ID]` regolari,
  niente dichiarazioni di limite.
- **Scenario B** — corpus completo + capability limitata: risposta
  parziale documentata, dichiara che il limite è di architettura
  retrieval (es. edge case che richiede multi-query / HyDE /
  query rewriting LLM-assisted in v1.1).
- **Scenario C** — corpus incompleto: risposta su ciò che il corpus
  copre + dichiarazione di limite (vedi
  [Pattern 4](#pattern-4--dichiarazione-di-limite-corpus-trasparenza-ux-strutturale)).

### Perché esiste

Senza una tassonomia esplicita, la `gold_answer` di una query
"difficile" rischia di essere scritta come se il sistema dovesse
rispondere come scenario A — con il risultato che faithfulness
aggregata sembra cattiva sulle query strutturalmente Gruppo B o C
(la risposta corretta è inevitabilmente parziale o dichiarativa).
La tassonomia codifica esplicitamente quando una risposta
"parziale" è giusta per costruzione vs quando è un fallimento di
pipeline. Cambia la lettura delle aggregate Ragas dalla domanda
"il sistema risponde bene?" a "il sistema risponde come gold
prescrive che debba rispondere?".

### Come si applica

Durante la scrittura della `gold_answer`:

1. **Classificare la query** in A / B / C prima di scrivere la
   risposta. La classificazione è basata su due check:
   (a) il corpus contiene i chunk necessari?
   (b) l'architettura retrieval v1 sa raggiungerli?
2. **Scrivere la `gold_answer` coerente con lo scenario**.
   Scenario A: risposta completa. Scenario B: risposta con
   esplicitazione del limite di architettura ("la query richiede
   capability v1.1 di tipo X"). Scenario C: risposta su ciò che il
   corpus copre + dichiarazione di limite user-facing.
3. **Marcare i flag corrispondenti nel dataset gold**: scenario A
   → flag standard; scenario B → tipicamente `query_type=edge`;
   scenario C → flag `has_corpus_limit_declaration=true`.
4. **Distinguere scenario B da retrieval-bound failure runtime**.
   Se in runtime il retrieval fallisce su una query annotata
   come scenario A (gold completo, capability ok in teoria), il
   modello entra correttamente in modalità "dichiarazione di
   limite" runtime — vedi Q35, Q19 in W7 + F.2. Il flag
   `runtime_corpus_limit_observed=true` cattura questa transizione,
   distinta dallo scenario C dichiarato a monte.

### Esempio concreto

**Scenario A** — Q1, Q6, Q7 (use case AI Act / GDPR puliti):
chunk gold tutti nel top-5 retrieval, risposta completa con
citazioni. Queste sono il cuore del benchmark e producono i
faithfulness mediani >0.9 del Gruppo A in W7.

**Scenario B** — Q5 (multi-normativa cross-vocabolari):
riclassificata `edge` dopo l'audit di W7-prep. La `gold_answer`
documenta esplicitamente che la query richiede capability v1.1
(multi-query / HyDE / query rewriting). Vedi
[`ROADMAP_POST_V1.md`](../../ROADMAP_POST_V1.md) § "Retrieval
avanzato v1.1 — Query cross-norma con vocabolari disgiunti".

**Scenario C** — Q9, Q24, Q49 (corpus incompleto su penale / ISO /
decreti settoriali): risposta sostanziale + dichiarazione di
limite. Lista completa delle 11 query scenario C in v1:
[`STATS.md`](../../data/benchmark/STATS.md) § "Dichiarazione di
limite corpus".

### Limiti del pattern

- **Tassonomia descrittiva, non normativa**. I 3 scenari catturano
  i casi osservati in v1, non sono esaustivi a priori. Quarta
  categoria plausibile v1.1: "gap testo norma vs dottrina"
  (osservato in Q79 di F.2, n=1, vedi
  [Pattern emergenti](#pattern-emergenti-non-ancora-consolidati)).
- **Nessun classificatore automatico**. Classificazione A/B/C
  richiede giudizio del curatore. Mitigazione: sanity check
  giuridico in curatela
  ([Pattern 3](#pattern-3--curatela-giuridica-come-secondo-livello-di-validazione)).
- **Scenario B raro in v1**: una sola query (Q5). La distinzione
  B vs C richiede n maggiore per essere validata robustamente.

---

## Pattern 6 — Mini-spike 1-2 giorni prima dell'architettura

### Cosa

Validare gli ingredienti tecnici (parser, embedding, LLM,
retrieval, transport HTTP) con codice usa-e-getta **prima** di
scrivere codice di produzione. Lo spike non entra nel MVP: serve
a calibrare le scelte architetturali, e poi viene riscritto da zero
nei moduli `core/`.

### Perché esiste

Le decisioni architetturali fatte sulla base di documentazione,
benchmark pubblici o intuizione tecnica sono spesso ribaltate
quando si misura sull'hardware e sui dati reali del progetto. Uno
spike di 1-2 giorni costa meno di una settimana di codice
costruito sopra una scelta sbagliata.

Il vincolo "spike è usa-e-getta" è esplicito nel preambolo:

> "Aggregato dei finding delle 6 sezioni dello spike tecnico.
> Lo spike è codice usa-e-getta: i file in `spike/` NON entrano
> nell'MVP."
>
> — [`spike/SPIKE_RESULTS.md`](../../spike/SPIKE_RESULTS.md)

### Come si applica

Prima di scrivere il primo modulo di produzione di una nuova fase:

1. **Identificare le 3-5 ipotesi tecniche critiche** della fase. Per
   W0: parser AKN funziona? bge-m3 distingue concetti legali
   italiani? LLM locale risponde su prompt RAG strutturato?
   Latenza end-to-end è nei budget?
2. **Scrivere uno spike per ciascuna**: script minimale,
   confronti A/B documentati, output numerici. Tempo di un'ipotesi:
   30 min - 4h, mai di più.
3. **Documentare l'esito in un singolo file aggregato** (`spike/
   SPIKE_RESULTS.md`) con sezione per ipotesi: setup, numeri
   chiave, decisione derivata. Una sezione conclusiva
   "Decisioni architetturali aggregate" raccoglie i delta sul piano
   originale.
4. **Buttare il codice spike**. Lo spike è codice di esplorazione,
   non ha test, non gestisce edge case. La tentazione di
   "sistemarlo per arrivare a produzione" porta a un MVP costruito
   su fondamenta non testate. Disciplina: il modulo `core/` di
   produzione si scrive da zero, leggendo lo spike come
   specification.

### Esempio concreto

[`spike/SPIKE_RESULTS.md`](../../spike/SPIKE_RESULTS.md) ha 6
sezioni eseguite in ~3h totali il 2026-05-16. Due hanno cambiato
decisioni architetturali significative:

- **D5 (4-bis) — LLM locale**: lo spike di confronto Minerva-7B vs
  Qwen2.5-14B ha rivelato che Minerva degenera su prompt RAG
  strutturati (repetition loop, hallucination cross-norma, echo del
  contesto), mentre Qwen2.5-14B con la stessa pipeline si comporta
  correttamente. Decisione SCOPE: LLM locale default
  Minerva-7B → Qwen2.5-14B (registro 2026-05-16,
  [`SCOPE.md`](../../SCOPE.md) voce 1).
- **D6 — Parser normativo**: lo spike sull'XML Akoma Ntoso diretto
  da Normattiva ha mostrato `eId` granulari nativi (`art_2-bis`)
  e gerarchia esplicita chapter/section, eliminando il
  post-processing del Markdown richiesto da
  `ondata/normattiva_2_md`. Decisione SCOPE: parser principale
  Markdown → XML AKN diretto (stessa voce).

Entrambe le decisioni hanno avuto impatto stimato "−1 giorno sul
time-to-completion" — più che ripagato il costo dello spike (~3h
totali per tutte e 6 le ipotesi).

### Limiti del pattern

- **Disciplina richiesta**: resistere alla tentazione di
  "sistemare lo spike" invece di buttarlo. È forte quando lo spike
  funziona bene — "basta aggiungere test" è il primo passo verso
  un MVP fragile.
- **Riferimenti allo spike nel codice di produzione** sono
  accettabili solo come citazione di un numero osservato (es. "MPS
  coabitazione bge-m3 + reranker satura 24 GB unified — vedi
  `spike/MPS_COABITATION_RESULTS.md`"), mai come dipendenza
  funzionale.
- **Tempo box stretto**: 1-2 giorni totali per N ipotesi, non per
  ipotesi. Se sfora, l'ipotesi è troppo grande per essere spike e
  va riformulata.

---

## Pattern emergenti non ancora consolidati

Osservazioni che potrebbero diventare pattern in v1.1 ma con `n=1`
oggi non hanno robustezza per essere codificate. Documentate qui
per memoria, da rivisitare con evidenze indipendenti.

- **Failure mode `answer_relevancy=0.0` su scope-out.** Ragas
  judge valuta "non pertinente" risposte che dichiarano
  correttamente il limite del corpus (la metrica re-genera N
  domande dall'answer; sulle risposte di non-rispondibilità non
  estrae domande). Distribuzione bimodale in F.2 (mean 0.609 vs
  median 0.815). Se confermato su un secondo judge indipendente
  (follow-up 2 F.2), il pattern di lettura aggregata
  "mediana primaria + mean come sanity check sul peso degli zeri"
  può essere formalizzato. Vedi
  [`BENCHMARK_RAGAS_F2.md`](../../data/benchmark/BENCHMARK_RAGAS_F2.md)
  § "Failure mode `answer_relevancy = 0.0`".
- **Gap testo norma vs dottrina interpretativa.** Q79 in F.2: il
  modello integra spontaneamente dottrina WP29 (portabilità dati
  derivati/inferiti) non groundata nei chunk. Risposta
  giuridicamente completa ma non grounded → faith 0.4286,
  rel 0.9526. Caso isolato (n=1). Se 2+ query con pattern analogo
  emergono in benchmark futuri, valutare quarta categoria nella
  tassonomia A/B/C o estensione corpus a EDPB/WP29.
- **Drift control fra run come parte della spec.** F.2 ha
  applicato controllo di drift su 38 positive comuni con W7
  (faith −0.042, rel −0.007, sotto soglia 0.05) come pre-flight
  diagnostico. Se altri run confermano valore, può diventare
  sezione obbligatoria delle spec di evaluation
  (`drift_subset` + `drift_threshold` esplicitati a monte).
