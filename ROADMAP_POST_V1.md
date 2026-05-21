# Roadmap post-v1

Evoluzioni identificate ma fuori scope v1. Ogni voce nasce da un'osservazione
concreta durante l'implementazione, non da pianificazione speculativa.

---

## Graph multi-normativa

Il modulo `core/normative_graph` è stato rilasciato in W4 con un catalogo
curato a mano di 6 link iniziali (FRIA↔DPIA, 22 GDPR↔6 AI Act, Annex III↔22
GDPR, 231 art.24-bis↔32 GDPR, 32 GDPR↔NIS2 art.24, 231 art.6↔AI Act art.9).
L'architettura è "Architettura A": espansione 1-hop bidirezionale a valle
del retrieval, deterministica, cap 5 chunk espansi per query. Nessuna
chiamata LLM, nessun tool calling, nessun multi-hop. Il graph è un asset
giuridico, non viene generato automaticamente.

Tre evoluzioni identificate ma fuori scope v1:

### 1. Estrazione automatica di rinvii testuali (~3-5 gg)

Costruire un parser regex sui pattern di citazione legale italiani:
- `art. <num>[-bis|-ter|...] [comma <num>] del [d.lgs|reg|legge] <num>/<anno>`
- `[d.lgs|reg|legge] <num>/<anno>, art. <num>`
- Rinvii a regolamenti UE: `regolamento (UE) <num>/<anno>`, `GDPR`,
  `AI Act`, `direttiva NIS2`
- Pattern italiani specifici: `presente decreto`, `predetto regolamento`,
  `articolo che precede`

Output: lista di link `auto` (campo `source: "auto"` nello schema GraphLink)
da fondere con il catalogo `curated`. Vincolo: solo riferimenti **espliciti
nel testo**, non inferenze semantiche.

Decisione di design da prendere: questi link auto-estratti vanno nello
stesso `graph.yaml` o in un file separato `graph_auto.yaml`? Tracciabilità
e revisione (giurista può rivedere `curated` e ignorare `auto`) suggeriscono
file separato.

### 2. Validazione legale formale del graph

I 6 link iniziali (ed eventuali estensioni a ~30) sono curati da un
ingegnere, non da un giurista. Il YAML porta il disclaimer "NOT legally
validated" come avvertenza esplicita.

Per la v1.1: review formale da parte di un giurista esterno (DPO o avvocato
specializzato in privacy/AI compliance) sui link `curated`. Popolare i
campi `validated_by` e `validated_at` del GraphLink. I link non validati
restano nel graph ma con `validated_by: null` come segnale di "ancora da
revisionare".

Vincolo operativo: la review costa tempo del giurista e va organizzata
come pacchetto (batch ~20-30 link alla volta).

### 3. UI di editing del graph (ambito prodotto commerciale)

Per un eventuale uso commerciale del sistema, serve un'interfaccia di
editing del graph che oggi è un YAML in repo:
- Persistenza in database (Postgres o equivalente) invece del YAML
- Audit log: chi ha aggiunto/modificato/rimosso un link, quando, con quale
  motivazione
- Workflow di approval: nuovo link proposto → review → approvato/respinto
- Vista grafica del cluster di link attorno a una norma
- Bulk import dal parser di rinvii auto-estratti (punto 1) con UI di
  approve/reject per ciascun link auto

Questo è lavoro di prodotto, non di RAG. Va fatto solo se il sistema esce
dal contesto open-source / personal-portfolio e va a un cliente reale.

---

## Lessoni dalla misura W4

La misura `graph-rescued` sul benchmark W3 (`scripts/run_benchmark_w3_with_expansion.py
--phase=graph_rescue --use-graph`) è stata eseguita due volte:

- **6 link iniziali (2026-05-19, prima passata):** 0 query rescued.
  Causa: i chunk-anchor (l'altro lato di ciascun link) non emergono nei
  top-10 delle query che avrebbero gold mancanti.
- **22 link curatela v1 (2026-05-19, seconda passata):** 1 query rescued
  (Q39 via Cod.Privacy art.2-ter ↔ GDPR art.6, deroga). Coverage
  concettuale: 25/39 query positive (64%) ricevono almeno 1 chunk
  espanso, media 1.41 espansioni/query, totale 55 chunk attivati. Top-5
  link più attivati: GDPR art.35↔AI Act art.26 (8), GDPR art.35↔AI Act
  art.27 (3), 196 art.2-ter↔GDPR art.6 (3), AI Act art.6↔GDPR art.22
  (3), GDPR art.22↔Annex III (3).

Conclusione confermata: il graph come "bonus context per la generation"
è il framing giusto in v1 — fornisce chunk addizionali utili al
ragionamento dell'LLM anche quando le metriche di retrieval non si
muovono. Come strumento di rescue del retrieval richiede o un catalogo
molto più denso, o un re-ranker che sappia leggere le relazioni del
graph (lavoro di v1.1).

---

## Query zero-recall persistenti

Sul benchmark hybrid_rrk con query expansion + graph 22 link, restano 10
query a R@10=0: Q5, Q13, Q15, Q24, Q30, Q34, Q39 (parzialmente: rescue),
Q43, Q45, Q49. Di queste, 6 ricevono almeno 1 chunk espanso dal graph
come bonus context (Q5, Q13, Q30, Q34, Q39, Q45) ma il chunk espanso non
coincide col gold mancante; 4 non vengono mai toccate dal graph perché il
top-10 non contiene anchor (Q15, Q24, Q43, Q49).

In particolare **Q5 e Q24** restano zero-recall in v1 — mismatch
semantico cross-norma non risolto da retrieval ibrido + reranker + query
expansion + graph 1-hop.

Soluzioni candidate per v1.1:

1. **Multi-query retrieval**: generare 2-3 riformulazioni della query
   originale via LLM, retrieval su tutte, dedup + ranking.
2. **HyDE (Hypothetical Document Embeddings)**: generare una risposta
   ipotetica via LLM, embeddare quella, retrieval su quella.
3. **Graph-guided retrieval a 2 stadi**: retrieve top-K iniziale,
   identifica concetti cross-norma via graph, ri-retrieve con query
   arricchita dai chunk-anchor del graph.
4. **Query rewriting con system prompt** che esplicita "cerca anche
   norme cumulative o presupposto" per query multi-normativa.

Vincolo: tutte e 4 le opzioni introducono dipendenza dall'LLM nel path
retrieval, scelta architetturale da pesare contro la garanzia di
determinismo del retrieval v1. Una via intermedia: applicare LLM solo
per le query che dopo retrieval base risultano sotto una soglia di
confidence (es. score del top-1 < threshold).

---

## Retrieval avanzato v1.1

### Query cross-norma con vocabolari disgiunti

**Caso d'uso di riferimento**: query **Q5** del benchmark v1 ("AI per
decisioni HR + responsabilità 231/2001"). Riclassificata da `positive`
a `edge` il 2026-05-19 dopo diagnostica W7-prep in 3 step
(`spike/Q5_RETRIEVAL_DIAG.md` + `spike/CORPUS_231_DIAG.md` +
`PROJECT_CONTEXT.md` registro decisioni voce 30).

La query mescola vocabolario di dominio applicativo (AI / HR /
lavoratori) con vocabolario penale-amministrativo (responsabilità
ente, reati presupposto, delitti). Il retrieval hybrid + rerank v1
**non aggancia** il corpus 231 perché:

- **BM25**: zero overlap lessicale tra "lavoratori" e "reati
  presupposto / delitti / responsabilità amministrativa"
- **Dense bge-m3**: il modello multilingue non chiude il gap
  concettuale tra dominio HR e dominio penale-amministrativo italiano
- **Graph statico**: avrebbe bisogno di link manuali su ogni
  intersezione HR + penale + privacy (combinatoria troppo alta per
  curatela)
- **Terminology**: alias parola→parola non basta per cross-norma
  reasoning multi-strato

Diagnostica del corpus (`spike/CORPUS_231_DIAG.md`) ha confermato che
il corpus 231 è **completo**: 109/109 articoli ingeriti, 4/4 articoli
Q5-rilevanti già in Qdrant. Non è gap di copertura ma gap di
**capability retrieval**.

**Architetture candidate v1.1**:

1. **Query decomposition LLM-assisted**: split Q5 in 2-3 sub-query
   ("AI HR alto rischio", "reati presupposto 231 trattamento illecito",
   "decisioni automatizzate GDPR"), retrieval su tutte, dedup + ranking.
2. **HyDE (Hypothetical Document Embeddings)**: genera una risposta
   ipotetica via LLM, embedda quella per il retrieval — sposta il
   matching dal vocabolario della domanda al vocabolario della
   risposta attesa.
3. **Query rewriting con few-shot di intersezione cross-norma**:
   esempi di pattern "use case applicativo → norma penale-presupposto"
   nel prompt di rewriting.
4. **Multi-stage retrieval**: top-K su query originale + top-K su
   query riscritta + RRF fusion.

**Validation criteria v1.1**: Q5 deve passare da R@10=0 a R@10≥0.5
con architettura v1.1 scelta, **senza degradare** le 38 positive
baseline (delta R@10 aggregato hybrid_rrk_50 ≥ −1pp ammesso, > 1pp
blocker).

**Vincolo trasversale**: tutte e 4 le architetture introducono
dipendenza dall'LLM nel path retrieval. Va pesato contro la garanzia
di determinismo del retrieval v1. Via intermedia possibile: applicare
LLM solo per le query che dopo retrieval base risultano sotto una
soglia di confidence (es. score del top-1 < threshold), così il path
deterministico resta dominante per i casi facili.

---

## Estensione corpus v1.1

### Codice penale — articoli richiamati come reati-presupposto 231

Il D.Lgs 231/2001 elenca i reati-presupposto per categoria (art. 24,
24-bis, 25, 25-bis, ..., 25-undecies, ecc.), ciascuno richiamando
articoli specifici del codice penale (es. art. 24-bis → 615-ter,
617-quater, 635-bis, 635-ter, 635-quater, 635-quinquies, 615-quater,
635-quater.1, 491-bis, 640-quinquies). Il corpus v1 include il decreto
231 completo ma NON il codice penale, quindi:

- **Q9** (reati-presupposto trattamento illecito dati) può essere
  risposta solo a livello di enumerazione dell'art. 24-bis —
  attualmente compilata come **scenario C** (gold ridotto + dichiarazione
  limite di corpus, vedi `data/benchmark/gold_answers_v1.json` Q9 e
  `PROJECT_CONTEXT.md` voce 31).
- **Query analoghe** su altre categorie reati-presupposto (caporalato,
  sicurezza lavoro, frodi fiscali, corruzione, riciclaggio, abusi di
  mercato) avrebbero lo stesso limite.
- **Risposte richiedono dichiarazione di limite** "dettaglio c.p.
  fuori corpus" come pattern stabile — formalizzato nella curatela
  W7-prep.

**Estensione candidata**: ingerire il sottoinsieme di articoli del
codice penale richiamati come reati-presupposto in tutti gli articoli
24/25/25-bis/.../25-undevicies del D.Lgs 231/2001. Perimetro chiuso e
definito dal testo del 231 stesso. Stima 80-120 articoli c.p. (estraibili
mediante regex sui rimandi `del codice penale` / `c.p.` presenti nei
commi degli articoli 231).

**Beneficio v1.1**: trasforma le risposte sui reati-presupposto da
"elenco numerico + dichiarazione limite" a "elenco + descrizione + sanzioni
+ citazione completa". Pattern molto richiesto da DPO e compliance
officer in setting di audit 231.

**Sorgente**: Normattiva AKN del codice penale (formato standard, parser
`core/italian_legal_parser` già in grado di gestirlo senza fix).

**Validation**: Q9 e query analoghe dovrebbero passare da gold-answer
scenario C (con dichiarazione limite) a gold-answer scenario A
(completa con citazioni), **senza degradare** le altre query del
benchmark. Q9 dovrebbe inoltre uscire da zero-recall (con `art_24-bis`
+ uno o più articoli c.p. richiamati nei top-10).

**Vincolo dimensionale**: ingerire l'intero codice penale (~700
articoli) NON è candidato — sarebbe oltre il perimetro privacy/AI/231
del corpus v1. Il sottoinsieme dei richiami da 231 è il taglio
corretto: pertinenza giuridica precisa, dimensione gestibile, perimetro
definito dal corpus stesso.

---

## Finding W7 (2026-05-20)

### Capability runtime corpus limit detection

Pattern emerso da W7: query del benchmark classificate come positive
non-limite a monte si comportano runtime come scenario C
(dichiarazione di limite spontanea) per failure di retrieval (omonimia
articolo, vocabolari disgiunti). Il flag binario
`has_corpus_limit_declaration` a monte non cattura queste query — in
W7 risultava in 2 falsi negativi su 27 query gruppo A (Q19, Q35).

Azione v1.1:
- secondo flag `runtime_corpus_limit_observed` nel benchmark dataset
  (già aggiunto in W7 post-eval su Q19, Q35)
- popolamento automatico: derivare il flag dal numero di statement
  non-groundabili in faithfulness Ragas, o da feature di output (es.
  presenza del pattern lessicale canonico in chiusura risposta)
- supporta segregazione automatica gruppo A / B / runtime-B nei run
  successivi del benchmark

Riferimento: `spike/BENCHMARK_RAGAS_W7.md` follow-up 1.

Stima: 3-5 ore.

### Validazione incrociata judge Ragas (opzionale)

Pattern emerso da W7: Sonnet 4.6 come judge penalizza risposte più
ricche del gold (Q17: parentesi esplicative classificate come "non in
context" pur essendo fatti veri e supportati indirettamente dal chunk
recuperato). Sospetto bias judge, non quantificato indipendentemente.

Azione v1.1 (opzionale):
- run incrociato su sottoinsieme di query con `recall@5=1` e `faith
  Sonnet judge <0.7`
- secondo judge: Opus 4.7 (con budget Anthropic predisposto) o
  GPT-4o-mini (~$0.05 stimato)
- confronto delta punteggi: se Opus/GPT-4o-mini producono faith
  sostanzialmente più alta, conferma bias Sonnet judge; altrimenti
  pattern Ragas-strutturale (decomposizione granulare).

Riferimento: `spike/BENCHMARK_RAGAS_W7.md` follow-up 2.

Stima: ~$0.50 + 1 ora.

### Tuning system prompt — pattern lessicale canonico "dichiarazione limite corpus"

Pattern emerso da smoke W6 (Q43) e confermato da W7 su tutte le query
con dichiarazione di limite spontanea: il modello usa varianti
lessicali (`"il contesto normativo fornito non contiene riferimenti
sufficienti"`) invece del pattern canonico
`"non incluso nel corpus normativo di riferimento"` definito in
PROJECT_CONTEXT.md voce 32.

Azione:
- tuning chirurgico `core/rag_prompt/system_prompt.it.md` per
  uniformare il lessico verso il pattern canonico
- naturale momento per intervento: W6 (UI Streamlit, tocca naturalmente
  il system prompt) o iterazione v1.1

Riferimento: `spike/BENCHMARK_RAGAS_W7.md` follow-up 3.

Stima: 1-2 ore.

Nota: estensione corpus codice penale (richiamato da 231) e architetture
retrieval avanzate (multi-query / HyDE per vocabolari disgiunti),
già presenti in ROADMAP_POST_V1.md da W7-prep, NON vanno duplicate. Sono
correlate al finding "runtime corpus limit detection" ma sono interventi
indipendenti.
