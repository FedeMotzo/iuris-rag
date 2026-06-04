# Federated cross-collection RAG — diagnosi aperta

Briefing tecnico autocontenuto. Diagnosi attiva, non chiusura.

---

## 1. Il problema in forma astratta

Pipeline RAG federata su un corpus partizionato. Il corpus è suddiviso in
sotto-collezioni disgiunte identificate da una chiave `doc_urn` (es. un URN
per ogni famiglia documentale). Ogni sotto-collezione contiene documenti
chunkati e indicizzati.

Una query utente puo' essere:
- **mono-sotto-collezione**: il materiale rilevante sta in una sola
  sotto-collezione → pipeline standard hybrid retrieve + rerank;
- **cross-sotto-collezione**: la query richiede materiale complementare
  da N≥2 sotto-collezioni (N tipico = 2-4); il sistema deve recuperare
  documenti rilevanti da OGNI sotto-collezione attivata e fonderli in un
  unico contesto top-K passato all'LLM generation.

Per le query cross, il flusso e':
1. Trigger lessicale deterministico → set di sotto-collezioni attivate.
2. Decomposer LLM → per ogni sotto-collezione attivata, una o piu' sub-query
   focalizzate sul materiale di quella sotto-collezione.
3. Retrieval per (sotto-collezione, sub-query): hybrid BM25+dense con filter
   sulla sotto-collezione, top-N via Qdrant RRF interno, rerank
   cross-encoder, top-K.
4. Source aggiuntiva "global": retrieval contro la query originale senza
   filter, rerank contro la query originale.
5. Fusion cross-sotto-collezione dei pool risultanti → top-K_final.
6. Top-5 di top-K_final passato come contesto alla generation LLM.

**Sintomo**: documenti che sono dichiaratamente rilevanti per la query
(target_set noto da un benchmark curato) non compaiono nel top-K_final, o
piu' specificamente non compaiono nei top-5 che la generation riceve.
Risultato downstream misurabile: `recall@5` (frazione del target_set
presente nel top-5) sotto il livello desiderato; `faithfulness` (RAGAS
metric, in [0,1]) degradata di conseguenza.

---

## 2. Stack tecnico

- Vector store: Qdrant 1.10+ con collezione `italian_legal_v1_hybrid` (865
  chunk totali) con due vector field per chunk: dense (1024-dim, bge-m3) e
  sparse (BM25 via fastembed `Qdrant/bm25`).
- Embedding dense: BAAI/bge-m3, batch su MPS (Mac M4 Pro).
- Embedding sparse: BM25 via fastembed.
- Hybrid retrieval: Qdrant `query_points` con `prefetch` su dense+sparse e
  `FusionQuery(Fusion.RRF)` → top-N candidati.
- Cross-encoder reranker: BAAI/bge-reranker-v2-m3 via
  sentence-transformers `CrossEncoder.predict()`; output gia' in (0,1) per
  default (sigmoide applicata nel head del modello).
- Decomposer LLM: Anthropic Claude Sonnet 4.6, temperatura 0, `max_tokens`
  400 per richiesta sub-query.
- Generation LLM: stesso modello, `max_tokens` 4000.
- Eval judge: RAGAS `faithfulness` + `answer_relevancy`, judge LLM stesso
  Sonnet 4.6.

---

## 3. Diagnosi iniziale, poi falsificata

L'ipotesi iniziale era: i documenti target mancanti sono **strutturalmente
non recuperabili** dal retrieval scenario-based perche' la loro rubrica
lessicale non matcha la query utente; servono ponti curati a mano
(graph expansion) per agganciare a target_node un nodo source nominato dal
retrieval scenario-based.

**Falsificata empiricamente** misurando il pool pre-rerank di OGNI
sotto-collezione attivata per le 4 query target del benchmark
(Q68/Q69/Q70/Q71). Risultato:

- 4 dei 5 documenti mancanti sono gia' nei top-20 pre-rerank di almeno una
  sotto-collezione attivata.
- I rank in cui compaiono: 6, 6, 11, 13, 15, 16.
- Solo 1 documento mancante (su 6 misurati) e' assente dal pool
  pre-rerank: e' un artefatto di sub-query approssimata (sub-query priva
  del vocabolario tecnico specifico, es. "trasferimento dati paesi terzi"
  non nominato).

Conclusione: il problema **non e' il retrieval**. E' la combinazione di
rerank per-source + fusion cross-source che scarta documenti gia'
presenti nel pool.

L'ipotesi graph expansion e' stata abbandonata anche perche' su 5
documenti target solo 1 ha un ponte curato esplicito (per cui un ponte
curato a mano e' costoso da generare e fragile: serve una decisione
giuridica per ogni link).

---

## 4. Le 3 classi del problema

Stratificazione emersa dalle misurazioni.

### Classe 1 — soppressione in fusion

**Sintomo**: il documento target e' rerankato a rank 5-10 nella sua
sotto-collezione di provenienza con score reranker alto (0.85-0.97
assoluto). Sopravvive al cutoff per-source. Ma viene scartato dalla
fusion cross-source: rank fusion finale 27-50+.

**Causa identificata**: la fusion attuale e' RRF cross-source. RRF aggrega
solo per rank, scartando lo score assoluto. Un documento che appare in UNA
sola source con rank 6 e score reranker 0.95 ottiene RRF score ~1/66 =
0.015. Un documento che appare in DUE source con rank 1+rank 1 e score
reranker 0.85+0.30 ottiene RRF score ~2/61 = 0.033 e vince. La fusion non
e' consapevole della qualita' del segnale.

**Numero candidati nei target**: 2/5 dei target mancanti sono Classe 1
(score reranker alto, single-source, RRF li affoga).

### Classe 2 — taglio al cutoff per-source

**Sintomo**: documento target rerankato a rank 15-16 nella sua
sotto-collezione (entro il rerank window di 20 ma vicino al fondo).
Sopravvive al rerank ma con basso margine di sopravvivenza, e cambi
minori a top_k_per_source o all'input retrieval lo escludono.

**Causa identificata**: margine ridotto. Non investigato in profondita'
perche' i numeri suggeriscono che e' un caso intermedio fra Classe 1 e
Classe 3.

**Numero candidati**: 1/5 (un singolo caso, AI Act art_6 sulla seconda
query in cui appare).

### Classe 3 — svalutazione del cross-encoder

**Sintomo**: documento target rerankato a rank 6-17 nella sua
sotto-collezione con score reranker BASSO (0.02-0.59 assoluto).
Sopravvive marginalmente o cade fuori dal cutoff.

**Causa identificata**: la sub-query LLM (prompt template V2) istruisce il
decomposer a "nominare TUTTI gli istituti attivati dallo scenario per
questa sotto-collezione" → produce sub-query ENCICLOPEDICHE che enumerano
6+ concetti distinti. Il cross-encoder, che valuta olisticamente la
coppia (query, document), preferisce documenti GENERICI che toccano molti
dei concetti enumerati rispetto a documenti SPECIALIZZATI che toccano un
solo concetto in modo profondo.

Esempio quantitativo (sub-query GDPR per query Q68):

> "Quali obblighi prevede il GDPR per un trattamento di dati sanitari
> (art. 9) tramite sistema automatizzato con profilazione (art. 22) a
> larga scala in ambito ospedaliero, con riferimento a DPIA (art. 35),
> misure di sicurezza e pseudonimizzazione (art. 32), nomina del
> responsabile del trattamento (art. 28) e informativa all'interessato
> (artt. 13-14)?"

Reranker top-1 = un recital narrativo del corpus (preamble) che paragrafa
molti dei concetti elencati. Reranker rank-10+ per gli articoli specifici
(art_9, art_22).

Test di refutazione: sostituendo questa sub-query con una sub-query
sintetica mirata (`"Trattamento di categorie particolari di dati personali
ex art. 9 GDPR"`), il documento target sale al rank 1 con score 0.999.
Il cross-encoder e' capace; il problema e' il prompt del decomposer.

**Numero candidati**: 3/5.

### Distribuzione classi sui 5 documenti target mancanti

| classe | count | meccanismo |
|--------|-------|------------|
| 1 — fusion RRF sopprime alto-score single-source | 2 | (sotto-collezione satura) |
| 2 — cutoff rerank per-source | 1 | margine ridotto |
| 3 — sub-query enciclopedica svaluta in rerank | 3 | prompt-driven |

(Le somme superano 5 perche' alcuni target appartengono a piu' classi
quando appaiono in piu' query — es. AI Act art_6 e' Classe 1 in Q68,
Classe 2 in Q69.)

---

## 5. Cosa abbiamo testato

Sequenza temporale. Ogni passo riporta ipotesi, costo, esito quantitativo,
meccanismo di fallimento.

### 5a. Top-K widening per-source: 5 → 16

**Ipotesi**: i target sono in pool pre-rerank a rank 6-16; alzando
`top_k_per_source` da 5 a 16, sopravvivono al cutoff per-source ed entrano
in fusion. Costo latenza profilato come 1.00x (il rerank costa fissato).

**Costo eseguito**: ~$1.50 (subset 19 query con generation+judge).

**Risultato**:
- `recall@20` target group invariata a 0.70 (era 0.70 baseline).
- I 5 target mancanti vengono entrati in fusion ma TUTTI a rank fusion
  finale 27, 29, 43, 53, >60, >60 (probe con `top_k_final=60`).
- Regressione su una query (Q70 -0.20 recall@20) per ricomposizione
  della fusion top-20: gold che baseline aveva in top-20 ne escono.

**Meccanismo di fallimento**: top-K widening sposta solo l'input alla
fusion, non la fusion stessa. RRF cross-source continua a sopprimere
candidati single-source. Inoltre la generation usa top-5 del fusion: un
target a rank fusion 27 non raggiunge mai il contesto LLM, indipendentemente
da `top_k_per_source`.

### 5b. Single-rerank cross-source contro query originale

**Ipotesi**: eliminare la fusion cross-source. Fondere il pool pre-rerank
di TUTTE le sotto-collezioni e fare un rerank unico contro la query
originale. Vincere il segnale di rilevanza assoluta.

**Costo eseguito**: zero (rerank locale offline su dump esistenti).

**Risultato**:
- 1/6 target mancante (annex_III__point_5) entra in top-20 single-rerank.
- 2/14 documenti che baseline v1.1 aveva correttamente recuperati
  sopravvivono al single-rerank.
- Top-5 del single-rerank di OGNI query dominato da recital narrativi
  del corpus (preamble).

**Meccanismo di fallimento**: la query originale e' uno scenario applicativo
multi-norma. Il cross-encoder, contro questa query ampia, premia documenti
narrativi che paragrafano lo scenario. La sub-query targettizzata stava
facendo lavoro reale di disambiguazione (nominare l'articolo specifico
spingeva l'articolo specifico al top). Togliere la sub-query distrugge
quel segnale.

### 5c. 4 varianti di fusion alternative (offline su pool esistenti)

**Ipotesi**: a parita' di input (post-rerank per-source), una funzione di
fusion diversa da RRF puo' recuperare i target Classe 1.

**Costo eseguito**: zero.

**Varianti testate**:

- **b.1 RRF score-aware**: `score_RRF * score_norm_reranker` dove
  `score_norm` e' min-max sui top-K della source.
- **b.2 Quote per-source garantite**: top-3 di ogni source riservati nel
  top-20 finale; slot residui via RRF.
- **b.3 Single-source boost**: chunk presenti in UNA sola source con
  score reranker > 0.7 ottengono boost moltiplicativo 1.5x.
- **b.4 Source pesate**: peso per-source proporzionale al numero di
  sub-query attivate per quella source.

**Risultati netti** (target recuperati a rank ≤20 senza regressione su
gold v1.1):

| variante | netto | dettaglio |
|----------|-------|-----------|
| RRF baseline (K=16) | 0 | 0/5 nei top-20 |
| b.1 score-aware | **+2** | recupera 2/5 ma entrambi a rank 20 (cosmetico per top-5 gen) |
| b.2 quote | 0 | recupera 2/5 ma sostituisce 2 v1.1 |
| b.3 single-source boost | +1 | recupera 1 v1.1 perso |
| b.4 source pesate | 0 | nessun cambiamento |

**Meccanismo di fallimento**: nessuna trasformazione rank-based ricrea il
segnale di rilevanza scartato dalla RRF. b.1 incorpora score reranker ma
solo come fattore moltiplicativo; i target con score 0.55-0.60 single-source
restano sotto i multi-source che accumulano RRF. La generazione vede top-5,
non top-20: il guadagno di b.1 e' invisibile downstream.

### 5d. Prompt mono-concetto V3 + fusion score-aware grezza

**Ipotesi**: il prompt V2 produce sub-query enciclopediche (Classe 3). Un
prompt V3 mono-concetto (1 sub-query per concetto) produce sub-query
focalizzate. Il reranker, contro sub-query focalizzate, premia i documenti
specifici (Verifica H4 dimostra: gli stessi target a rank 1 con score 0.95+
contro sub-query sintetiche mirate). Combinato con fusion `sigmoid(max
logit) + dedup max`, il segnale di rilevanza assoluta vince.

**Costo eseguito**: $0.08 cassette V3 (16 chiamate Sonnet 4.6) + smoke test
locale zero-cost.

**Risultato smoke Q68**:
- Sub-query generate dal V3: 8 per GDPR, 9 per AI Act, 6 per L.132 (totale
  23 sub-query per la query Q68).
- Pool fuso (deduplicato cross-source): 212 candidati unici.
- Top-20 dominato da chunk AI Act: 19 AI Act + 1 L.132. ZERO GDPR.
- 0/5 target mancanti in top-20.

**Distribuzione score sigmoide per source nel pool Q68**:

| source | n | median | IQR | max | n sub-query |
|--------|---|--------|-----|-----|-------------|
| ai_act | 80 | 0.7228 | 0.0813 | 0.7309 | 9 |
| l_132_2025 | 25 | 0.5316 | 0.1170 | 0.7302 | 6 |
| gdpr | 90 | 0.5119 | 0.0565 | 0.7283 | 8 |
| global | 17 | 0.5003 | 0.0025 | 0.5321 | 1 |

**Meccanismo di fallimento identificato**: il cross-encoder satura a
livelli diversi per source. La source AI Act ha vocabolario tecnico denso
("sistema di IA ad alto rischio", "fornitore", "deployer") che matcha
fortemente le sub-query AI Act-style: il reranker assegna logit alti (sigmoide
0.72+) a molti chunk. La source GDPR ha vocabolario piu' discorsivo
("trattamento di dati", "interessato"): il reranker discrimina meglio,
con spread piu' ampio (0.51 mediana, 0.73 max). La fusion `sigmoid(max
logit)` raw senza normalizzazione lascia che la source piu' satura vinca
sempre, indipendentemente dalla rilevanza al concetto specifico.

Gold posizioni nel pool fuso Q68 (rank di fusion, su 212):

| target | source migliore | logit max | rank fusion |
|--------|-----------------|-----------|-------------|
| L.132 art_7 | l_132 | 0.967 | 39 |
| AI Act art_6 | ai_act | 0.950 | 46 |
| AI Act art_27 | ai_act | 0.917 | 53 |
| GDPR art_35 | gdpr | 0.908 | 55 |
| GDPR art_9 | gdpr | 0.373 | 93 |

I primi 20 sono saturati da chunk AI Act a logit 0.99+ che non sono
target. I target a logit 0.91-0.97 non entrano.

### 5e. Prompt V3 + fusion score-aware con normalizzazione robusta per-source

**Ipotesi successiva al fallimento 5d**: il problema 5d e' la calibrazione
cross-source non uniforme. Normalizzare per-source rimuove l'asimmetria.

**Design specifico testato**:
1. `sigmoid(max_logit)` per ogni chunk.
2. Dedup per chunk_id su pool unito: max degli score.
3. Per ogni source, mediana e IQR degli score sigmoide.
4. Guard sources `low-signal`: se IQR < 0.05 la source NON partecipa alla
   normalizzazione robusta; i suoi candidati entrano in "gated fallback"
   (ammessi se sigmoide raw > 0.6 E se restano slot dopo i normalizzati).
5. Floor sigmoide < 0.5 → scarta.
6. Per source con IQR ≥ 0.05: `z = (sigmoid − median_source) / IQR_source`.
7. Ordina per z discendente, top-K_final = 20.
8. Slot residui via gated fallback ordinati per sigmoide raw.

**Costo eseguito**: $1.90 totale (subset paid 19 query + gen + judge).

**Risultato subset misurato vs baseline v1.1**:

| gruppo | metrica | baseline v1.1 | v1.2 (5e) | Δ |
|--------|---------|---------------|-----------|---|
| target cross-norma | recall@5 mediana | 0.40 | **0.20** | **-0.20** |
| target cross-norma | recall@20 mediana | 0.70 | 0.55 | -0.15 |
| target cross-norma | faith mediana | 0.571 | 0.522 | -0.049 |
| sentinelle | faith mediana | 0.934 | 0.977 | +0.043 (rumore) |
| corpus_limit | faith mediana | 0.820 | 0.841 | +0.021 (rumore) |
| mono-stress | faith mediana | 1.000 | 0.893 | -0.107 (rumore) |
| gold-recital | faith mediana | 0.945 | 1.000 | +0.055 (rumore) |

(Le sentinelle e mono-stress sono path fallback: retrieval byte-identico.
Le Δ sono nondeterminismo gen+judge.)

**Telemetria A/B/C/D sui 5 target mancanti**:

| qid | gold | concetto nominato dalle sub-query | in top-5 | rank fusion | categoria |
|-----|------|:---------------------------------:|:--------:|:-----------:|:---------:|
| Q68 | AI Act art_6 | si | no | >20 | B |
| Q68 | GDPR art_9 | si | no | 19 | B |
| Q69 | AI Act art_6 | si | no | >20 | B |
| Q70 | GDPR art_44 | no | no | >20 | C |
| Q70 | 231 art_25-octies | si | no | >20 | B |
| Q71 | annex_III point_5 | no | no | >20 | C |

Aggregato: 0 A, 4 B, 2 C, 0 D. Soglia di successo richiesta dal brief
implementazione: ≥3 A E 0 B. Fallimento netto.

**Distribuzioni score per source nel run misurato** (esempi):

```
Q68:  gdpr     n=89  median=0.512  IQR=0.056  max=0.728  → z_max = 3.86 (DOMINA)
      ai_act   n=79  median=0.723  IQR=0.081  max=0.731  → z_max = 0.10 (SCHIACCIATA)
      l_132    n=25  median=0.532  IQR=0.117  max=0.730  → z_max = 1.69
      global   n=17  median=0.500  IQR=0.002  max=0.532  → low-signal, gated

Q70:  gdpr     n=90  median=0.554  IQR=0.122  max=0.728  → z_max = 1.43
      ai_act   n=65  median=0.720  IQR=0.035  max=0.731  → LOW-SIGNAL (gated)
      dlgs_231 n=45  median=0.501  IQR=0.023  max=0.702  → LOW-SIGNAL (gated)
      nis2     n=43  median=0.555  IQR=0.102  max=0.731  → z_max = 1.73
      global   n=7   median=0.518  IQR=0.013  max=0.541  → low-signal, gated

Q71:  gdpr     n=84  median=0.515  IQR=0.068  max=0.729  → z_max = 3.15 (DOMINA)
      ai_act   n=71  median=0.720  IQR=0.053  max=0.731  → z_max = 0.21 (SCHIACCIATA)
```

`n_gated_in_top_k = 0` per OGNI query del run: 20 candidati normalizzati
saturano tutti gli slot del top-K finale, i gated non entrano mai. Quando
una source finisce gated (ai_act in Q70, dlgs_231 in Q70), i suoi
candidati sono effettivamente esclusi.

**Meccanismo di fallimento**: la z-normalizzazione assume distribuzioni
roughly simmetriche attorno alla mediana. Sui dati reali una source ha
distribuzione saturata-al-top (ai_act: mediana 0.72, max 0.73, lunga coda
inferiore → z_max ≈ 0.10) e un'altra ha distribuzione spread-ampia (gdpr:
mediana 0.51, max 0.73, distribuzione roughly uniforme → z_max ≈ 3.86).
La z-norm non rende comparabili queste forme: comprime quella saturata a
z≈0, espande quella ampia a z≈3-4. **Il bias di calibrazione si SPOSTA da
una source all'altra, non si rimuove**. Prima ai_act vinceva sempre per
saturazione assoluta; ora gdpr vince sempre per spread z.

Effetto collaterale osservato anche su query con recall@5 invariato (Q9):
top-5 cambia composizione (la z-norm seleziona la coda meno calibrata
della source dominante), e la faithfulness LLM degrada 0.96 → 0.48 anche
con il documento target ancora presente al rank 3.

---

## 6. Il vincolo strutturale che emerge

Sezione critica per restringere lo spazio delle soluzioni residue.

### a. Forme di distribuzione score eterogenee per source

Il cross-encoder usato (bge-reranker-v2-m3) produce, sui dati reali del
corpus, distribuzioni score con forme **fondamentalmente diverse** per
sotto-collezione. Tre archetipi osservati:

- **Saturata-al-top**: source con vocabolario tecnico denso e
  ripetitivo. Molti chunk matchano fortemente le sub-query tipiche di
  quella source. Mediana alta (0.70+), IQR moderato (0.04-0.08), max
  vicino alla mediana (saturazione vicino a sigmoide 0.73, asintoto del
  cross-encoder). Esempio: AI Act.

- **Spread-ampia**: source con vocabolario discorsivo e variato. I chunk
  hanno match qualitativi diversi. Mediana bassa (0.50-0.55), IQR ampio
  (0.06-0.12), distribuzione roughly uniforme nell'intervallo. Esempio:
  GDPR.

- **Degenere a rumore**: source con basso match alle sub-query specifiche
  della query corrente (es. la "global" source contro query
  scenario-based, oppure source attivate dal trigger ma con poco
  materiale rilevante). Mediana ~0.50, IQR < 0.01, distribuzione
  collassata vicino al floor. Esempio: global, NIS2 su alcune query
  dove il trigger e' stato troppo permissivo.

### b. Nessuna normalizzazione locale rende comparabili forme diverse

Provato sperimentalmente (z-score in 5e). Z-norm assume simmetria;
schiaccia la saturata, espande la ampia. Min-max ha lo stesso problema
opposto (saturata: max-min piccolo → z amplificato; ampia: max-min grande
→ z compresso). Sigmoide ridondante (gli score sono gia' sigmoide
applicata).

### c. Lo score reranker dentro una source resta segnale interpretabile

Within una source, lo score reranker discrimina i target dai distrattori
in modo soddisfacente: target a 0.91+, distrattori a 0.51, con margine.
Il segnale per-source e' valido. Il problema e' cross-source.

### d. Top-5 generation come binding constraint

La generation LLM riceve i top-5 della fusion finale. Non i top-20.
Qualsiasi strategia che porta i target a rank 15-20 della fusion e'
cosmetica per il sistema downstream.

---

## 7. Cosa e' gia' stato escluso

Approcci da NON ripetere.

- **Top-K widening pre-fusion** (5a): non sposta la fusion, e
  riti-organizza solo l'input.
- **Single rerank cross-source contro query originale** (5b):
  catastrofico, recital narrativi vincono.
- **Tutte le 4 varianti di fusion rank-based o RRF-derived testate**
  (5c): nessuna trasformazione rank-based ricrea il segnale di rilevanza
  scartato. Il guadagno top-20 non raggiunge top-5.
- **Sub-query enciclopediche V2** (refutate dal test H4 in Verifica 9):
  causa diretta della Classe 3; sostituite da V3 mono-concetto.
- **Fusion score-aware grezza senza normalizzazione** (5d): saturazione
  asimmetrica fa vincere la source piu' satura.
- **Fusion score-aware con normalizzazione per-source z-score robusta +
  floor + gated low-signal** (5e): forme distribuzionali eterogenee
  rendono la z-norm distorta; il bias si sposta non si rimuove.
- **Graph expansion del pool** (escluso da Verifica 3): solo 1/5 target
  ha un ponte curato esplicito; non scalabile per costo curatoriale.

---

## 8. Telemetria disponibile

Artefatti che una chat o un agente con accesso al filesystem possono
chiedere o ispezionare direttamente.

- `spike/data/graph_diagnosis_pools.json` — pool pre-rerank per source
  (4 query target × 4-5 source × 20 candidati con rank e RRF score
  Qdrant).
- `spike/data/graph_diagnosis_postrerank.json` — pool post-rerank
  per-source (4 query target × 4-5 source × 20 candidati con rank e
  score reranker).
- `spike/data/fusion_variants_simulation.json` — risultati delle 4
  varianti di fusion simulate offline (5c) con top-20 e ranking gold
  per ogni variante.
- `spike/data/smoke_q68_fused_pool.json` — pool fuso completo (212
  candidati unici) per Q68 con la fusion mono-concetto + sigmoide grezza
  (5d), con score per source, sub-query attribuzioni multiple, e
  stats_per_source (mediana, IQR, max).
- `spike/data/subset_v1_2_outputs.json` — run subset paid completo (5e):
  19 query × retrieved_chunks top-20, generation, score RAGAS,
  classificazione A/B/C/D per i 5 target mancanti, e trace_summary con
  fusion_stats per source per ogni query cross-norma (`source_stats`
  con n, median, IQR, q1, q3, max, min; `low_signal_sources`,
  `n_normalized`, `n_gated_in_top_k`, `z_top_k_*`).
- `spike/data/v1_1_rescue_at_5_baseline.json` — baseline ricalcolata
  per recall@5 per query.
- `tests/cross_norm/cassettes/subquery_responses.json` — cassette V3
  mono-concetto per Q9/Q68/Q69/Q70/Q71 (formato JSON: `list[str]` per
  ogni (qid, source)).

---

## 9. Domanda aperta

Date queste evidenze, esistono direzioni per fondere candidati cross-
sotto-collezione quando il cross-encoder produce distribuzioni score con
forme strutturalmente diverse per sotto-collezione e qualsiasi
normalizzazione locale (z-score, min-max, sigmoide) ne distorce sempre
una, ma la rilevanza assoluta interna a ciascuna sotto-collezione resta
segnale valido?
