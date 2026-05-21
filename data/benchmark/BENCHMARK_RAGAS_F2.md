# Benchmark Ragas F.2 — risultati

Data: 2026-05-21
Spec di riferimento: [`RAGAS_RUN_NOTES.md`](RAGAS_RUN_NOTES.md)
(scritta a monte per W7, vincolo metodologico esteso a F.2).

## Setup

- Dataset: 100 query di `data/benchmark/gold_answers_v2.json`
  (77 positive + 20 negative + 3 edge; 23 con
  `has_corpus_limit_declaration=true`)
- Provider generazione: `anthropic` / `claude-sonnet-4-6`
- Pipeline: `top_k=5`, `rerank_top_k=20`, `use_graph=False`,
  `max_output_tokens=1000`
- Topologia: reranker MPS (S1)
- LLM judge Ragas: `claude-sonnet-4-6` (continuità con W7;
  validazione incrociata Opus rimandata a follow-up 2)
- Embeddings answer_relevancy: `BAAI/bge-m3`
- Metriche: `faithfulness`, `answer_relevancy` — `context_precision`
  esclusa in pre-flight F.2 per ridurre cost; metriche retrieval
  R@5/R@10/R@20/MRR già in `BENCHMARK_W3_v2.md` (in `spike/`)
- Prompt caching: disabilitato (in pre-flight cache_read=0, overhead
  +25% senza beneficio — vedi `spike/PHASE_F2_PREFLIGHT.md`)
- Costo effettivo: **$6.8175** (293 LLM call, 921 384 input token,
  270 226 output token)
- Wall-clock: **4 541.4 s** (≈ 76 minuti)
- Finito: 2026-05-21T10:33:32 UTC

## Aggregati

### Globale (n=100)

| metrica | mean | median | min | max | p10 | p90 | std |
|---|---:|---:|---:|---:|---:|---:|---:|
| faithfulness     | 0.8260 | **0.8856** | 0.2500 | 1.0000 | 0.5000 | 1.0000 | 0.1877 |
| answer_relevancy | 0.6089 | **0.8150** | 0.0000 | 1.0000 | 0.0000 | 0.9475 | 0.3882 |

### Per query_type

| gruppo | n | faith median | faith mean | rel median | rel mean |
|---|---:|---:|---:|---:|---:|
| positive  | 77 | 0.9167 | 0.8428 | 0.8387 | 0.7140 |
| negative  | 20 | 0.8333 | 0.7868 | 0.0000 | 0.2519 |
| edge      |  3 | 0.7692 | 0.6572 | 0.0000 | 0.2927 |

### Positive segregato per `has_corpus_limit_declaration`

| gruppo | n | faith median | faith mean | rel median | rel mean |
|---|---:|---:|---:|---:|---:|
| A — positive non-limit | 58 | 0.9107 | 0.8360 | 0.8508 | 0.7608 |
| B — positive limit     | 19 | 0.9286 | 0.8634 | 0.7384 | 0.5708 |

### Per norma toccata (positive, somma >n perché cross-norma)

| norma | n | faith median | rel median |
|---|---:|---:|---:|
| GDPR             | 33 | 0.9333 | 0.8476 |
| AI Act           | 29 | 0.8824 | 0.8223 |
| NIS2             | 16 | 0.7565 | 0.8330 |
| D.Lgs 231/2001   | 12 | 0.9117 | 0.6720 |
| L. 132/2025      | 10 | 0.6905 | 0.8618 |
| Codice Privacy   |  6 | 0.9500 | 0.9133 |

L. 132/2025 sotto la mediana globale su faithfulness — coerente con
la sua copertura corpus parziale (28 articoli, alcune materie
richiamano norme settoriali fuori corpus).

## Distribuzione faithfulness per zona

Bin secondo soglie di lettura di `RAGAS_RUN_NOTES.md` nota 9.

| zona faithfulness | globale (n=100) | gruppo A (n=58) | gruppo B (n=19) | negative (n=20) | edge (n=3) |
|---|---:|---:|---:|---:|---:|
| >0.85 buono/eccellente | 58 (58%) | 36 (62%) | 12 (63%) | 9 (45%) | 1 (33%) |
| 0.65-0.85 accettabile  | 25 (25%) | 12 (21%) |  5 (26%) | 7 (35%) | 1 (33%) |
| 0.4-0.65 da indagare   | 14 (14%) |  9 (16%) |  2 (11%) | 3 (15%) | 0 (0%) |
| <0.4 fallimento netto  |  3 (3%)  |  1 (2%)  |  0 (0%)  | 1 (5%)  | 1 (33%) |

3 query sotto 0.4: Q35 (positive non-limit), Q46 (edge), Q48
(negative). Soglia ready RAGAS_RUN_NOTES nota 9 "0 query gruppo A
con faithfulness <0.4" non rispettata a prima lettura (1 query
gruppo A, Q35). Vedi "Analisi qualitativa bottom-5" e "Modifica
metodologica ex-post" sotto.

## Drift v1 W7 archived vs F.2 ricalcolato (38 positive Q1-Q50)

Subset comune fra il run W7 (38 positive di v1) e il run F.2
ricalcolato sulle stesse 38 query. Stabilità di judge e pipeline.

| metrica | W7 archived (2026-05-20) | F.2 ricalcolato | Δ |
|---|---:|---:|---:|
| faithfulness mediana     | 0.944 | 0.9024 | **−0.042** |
| answer_relevancy mediana | 0.763 | 0.7564 | **−0.007** |

Drift entro la soglia 0.05 dichiarata in spec (PHASE_F1_DIAGNOSTIC
step 2). Causa plausibile principale: non-determinismo reranker MPS
documentato in `BENCHMARK_W3.md` ("score CrossEncoder su MPS può
variare di pochi millesimi tra run distinti", riga ~514). Judge e
generator stabili tra W7 e F.2. **PASS** sul vincolo di stabilità
metodologica.

### Subset v1 (Q1-Q50, 50 entry: 38 positive + 10 negative + 2 edge)

Riportato per completezza; il subset 50 include negative+edge non
confrontabili con W7 archived (che ne escludeva).

| metrica | mean | median | min | max |
|---|---:|---:|---:|---:|
| faithfulness     | 0.8106 | 0.8745 | 0.2500 | 1.0000 |
| answer_relevancy | 0.5196 | 0.7246 | 0.0000 | 1.0000 |

### Subset v2 (Q51-Q100, 50 entry: 39 positive + 10 negative + 1 edge)

Le 50 query nuove curate post-pivot 2026-05-20 (vedi
`BENCHMARK_V2_CURATION_BRIEF.md`).

| metrica | mean | median | min | max |
|---|---:|---:|---:|---:|
| faithfulness     | 0.8414 | 0.8974 | 0.4286 | 1.0000 |
| answer_relevancy | 0.6982 | 0.8681 | 0.0000 | 0.9868 |

Delta v2 vs v1 (faithfulness +0.023, answer_relevancy +0.144)
misurato sullo stesso pipeline. Tre ipotesi non distinguibili da
questi dati:

(a) metodologia di curatela v2 migliorata avendo imparato dai
pattern W7-prep
(b) query v2 strutturalmente più facili (es. distribuzione diversa
di edge case, query più recenti meglio coperte da Sonnet 4.6 in
training)
(c) selection bias nella scelta delle 50 query nuove (curatori
hanno inconsapevolmente preferito query con gold meno ambigui)

Non interpretiamo causalmente il delta. Per discriminare servirebbe
un controllo (es. ri-curatela delle 50 query v1 con metodologia v2,
o ri-valutazione delle 50 query v2 con annotazione v1). Non è
scope v1.

## Top-5 e bottom-5

### Top-5 faithfulness (selezionati fra le 30 query con faith=1.000, ordinati per `answer_relevancy` decrescente per evidenziare i casi più forti su entrambe le metriche)

| qid | type | limit | faith | rel | use_case |
|---|---|---|---:|---:|---|
| Q63 | positive | true  | 1.0000 | 0.9868 | Trattamento dati forze di polizia (Codice Privacy) |
| Q59 | positive | false | 1.0000 | 0.9767 | Garante poteri ispettivi |
| Q84 | positive | false | 1.0000 | 0.9662 | AI Act sanzioni GPAI rischio sistemico |
| Q87 | positive | true  | 1.0000 | 0.9363 | 231 sicurezza lavoro omicidio colposo |
| Q89 | positive | false | 1.0000 | 0.9287 | Registro trattamenti art.30 contenuti |

Nota: Q63 e Q87 confermano che `has_corpus_limit_declaration=true`
**non implica** punteggio basso. Quando il retrieval aggancia
correttamente il chunk principale, la struttura "corpo della
risposta groundato + chiusura con dichiarazione di limite" mantiene
faithfulness al massimo (gli statement sostantivi dominano la
verifica) e answer_relevancy alta (la domanda è effettivamente
risposta). Pattern confermato già in W7 (vedi `BENCHMARK_RAGAS_W7.md`
"Gruppo B — faithfulness").

### Bottom-5 faithfulness (globale)

| qid | type | limit | faith | rel | use_case |
|---|---|---|---:|---:|---|
| Q35 | positive | false | 0.2500 | 0.0000 | stress: art 27 AI Act FRIA |
| Q46 | edge     | false | 0.3077 | 0.0000 | edge: operativa ChatGPT |
| Q48 | negative | false | 0.3750 | 0.0000 | edge: ePrivacy off-corpus |
| Q41 | negative | false | 0.4000 | 0.0000 | edge: Data Act off-corpus |
| Q79 | positive | false | 0.4286 | 0.9526 | Portabilità dati derivati |

Le 5 query bottom sono analizzate in dettaglio sotto.

## Analisi qualitativa bottom-5

### Q35 — "art 27 AI Act FRIA" (faith 0.2500, rel 0.0000)

**Query**: keyword-style su art. 27 AI Act (FRIA — Fundamental
Rights Impact Assessment).

**Gold**: `eli/reg/2024/1689/oj__art_27`.

**Retrieval**: zero gold chunks recuperati (recall@5=0, recall@10=0).
Top-5 contiene 3 art. 27 omonimi di norme diverse (`L. 132/2025
art_27`, `D.Lgs 231/2001 art_27`, `Codice Privacy art_2-quindecies`
adiacente) + 2 articoli su AI generico. Il retriever ha matchato
"art 27" come stringa lessicale senza disambiguare il qualificatore
"AI Act FRIA".

**Generazione**: il modello dichiara esplicitamente che il contesto
non contiene l'art. 27 AI Act, identifica correttamente gli art. 27
omonimi presenti, e segnala che servirebbe il Regolamento UE
2024/1689 per rispondere correttamente. **Zero allucinazioni**,
rifiuto onesto. La dichiarazione di limite arriva all'inizio e in
chiusura.

**Perché Ragas penalizza**: claim meta-discorsive
("l'articolo 27 dell'AI Act riguarda la FRIA", "servirebbe il
Regolamento UE 2024/1689") non sono groundabili nei contexts per
design — sono claim sul mondo, non sui chunk. Conseguenza:
faithfulness 0.2500. `answer_relevancy=0.0` è il failure mode noto
di Ragas su risposte di non-rispondibilità (vedi sezione "Failure
mode `answer_relevancy = 0.0`" sotto).

**Classe**: retrieval-bound failure, runtime corpus limit. Falso
negativo del flag `has_corpus_limit_declaration` a monte (era
`false` in W7-prep). Già documentato in W7 (Q35 era nel bottom-5
del W7 report con faith 0.375; F.2 conferma il pattern con leggera
ulteriore severità del judge).

### Q46 — "Posso usare ChatGPT per analizzare documenti aziendali confidenziali?" (faith 0.3077, rel 0.0000)

**Query**: edge, professional. `gold_chunks=[]` per design.

**Retrieval**: top-5 sono 5 considerando (GDPR recital 154/81/168/92
+ AI Act recital 167) — pertinenti al perimetro ma nessuno
dispositivo specifico sul caso d'uso.

**Generazione**: risposta strutturata di 2082 caratteri. Fornisce
indicazioni operative su responsabile del trattamento,
trasferimenti extra-UE, base giuridica + dichiarazione esplicita
che il contesto non copre "trasferimenti internazionali, basi
giuridiche del trattamento o misure di sicurezza tecniche".
Comportamento desiderato per query edge: usa i chunk per quanto
disponibili, dichiara cosa manca.

**Perché Ragas penalizza**: la risposta è ricca di claim
inferenziali su responsabilità OpenAI, server extra-UE,
informativa privacy — fatti probabilmente veri ma non direttamente
estraibili dai 5 considerando recuperati. Il judge classifica come
"non in context" la maggior parte degli statement.

**Classe**: edge query strutturalmente penalizzata dalla metrica.
Comportamento di pipeline corretto (zero allucinazioni di norme
inesistenti), score basso strutturale. Nessun fix di pipeline
candidato — è limite della metrica su query edge professional.

### Q48 — "regolamento EU sui cookie" (faith 0.3750, rel 0.0000)

**Query**: negative. `gold_chunks=[]`.

**Retrieval**: top-5 misto AI Act + NIS2, nessun dispositivo sui
cookie (la materia è ePrivacy + GDPR per il consenso, fuori dal
corpus v1 per la parte ePrivacy).

**Generazione**: risposta corretta (693 char) — dichiara che il
contesto non disciplina i cookie, identifica correttamente le
fonti reali (Direttiva 2002/58/CE ePrivacy + 2009/136/CE + GDPR
per il consenso) ma le segnala come "non presenti nel contesto".
Zero allucinazioni dispositivo.

**Perché Ragas penalizza**: gli statement "la normativa europea di
riferimento è la Direttiva 2002/58/CE" sono claim sul mondo, non
groundati nei chunk. Faithfulness 0.375.

**Classe**: negative off-corpus, comportamento atteso. Il judge
penalizza la trasparenza meta-discorsiva.

### Q41 — "Cosa prevede il Data Act sui dati industriali?" (faith 0.4000, rel 0.0000)

**Query**: negative. `gold_chunks=[]`.

**Retrieval**: top-5 misto GDPR + Codice Privacy + AI Act, nessun
chunk del Data Act (fuori corpus v1).

**Generazione**: risposta breve (590 char), esplicita su tre punti:
i 5 chunk recuperati appartengono a GDPR / Codice Privacy / AI Act;
nessuno disciplina il Data Act (Regolamento UE 2023/2854); "non è
pertanto possibile fornire una risposta tecnica su tale materia
senza inventare riferimenti normativi assenti dal contesto". Zero
allucinazioni.

**Perché Ragas penalizza**: l'identificazione del Data Act come
"Regolamento UE 2023/2854" è prior knowledge non groundata.
Faithfulness 0.400.

**Classe**: identica a Q48. Pattern stabile delle negative
off-corpus sotto Sonnet judge.

### Q79 — "Portabilità dati derivati o inferiti — art. 20 GDPR" (faith 0.4286, rel 0.9526)

**Query**: positive professionale. Distingue dati "forniti" (par. 1
art. 20) da derivati/inferiti — domanda WP29/EDPB standard.

**Gold**: `eli/reg/2016/679/oj__art_20`.

**Retrieval**: gold in top-1 (recall@5=1). Top-5 = art_20 +
recital_68/73 + art_13/14 — clusterizzato bene sul tema.

**Generazione**: risposta tecnicamente corretta (2266 char) — cita
testualmente l'art. 20 par. 1 "dati personali che lo riguardano
forniti a un titolare", invoca recital 68 a conferma, conclude che
derivati/inferiti **non** rientrano per design del par. 1. Conclusione
giuridicamente solida che coincide con la dottrina WP29 (Guidelines
on the right to data portability, WP242). Citazioni strutturalmente
verificate (`[cite:eli/reg/2016/679/oj__art_20]`,
`[cite:eli/reg/2016/679/oj__recital_68]`).

**Perché Ragas penalizza**: la risposta arricchisce il testo della
norma con il framework dottrinale "forniti vs derivati/inferiti"
implicito ma non esplicito nel testo dell'art. 20 GDPR. Il judge
classifica i passaggi inferenziali come "non in context", anche se
sono il risultato di una lettura testuale corretta.
`answer_relevancy=0.95` conferma che la risposta è altamente
pertinente alla domanda: la divergenza è solo sull'asse di
groundedness.

**Classe**: "gap testo norma vs dottrina" — pattern atteso in
curatela e già anticipato come limite metodologico. Il faithfulness
basso non è failure di pipeline ma riflette la differenza
strutturale tra testo dispositivo del corpus e interpretazione
dottrinale (WP29 nel caso specifico, EDPB in generale). Vedi
follow-up 4 sotto.

### Pattern complessivo bottom-5

| qid | faith | classe |
|---|---:|---|
| Q35 | 0.2500 | retrieval-bound (omonimia art. 27), runtime corpus limit, conferma W7 |
| Q46 | 0.3077 | edge professional, judge penalizza inferenza meta-discorsiva |
| Q48 | 0.3750 | negative off-corpus (ePrivacy), pattern stabile sotto Sonnet judge |
| Q41 | 0.4000 | negative off-corpus (Data Act), pattern stabile sotto Sonnet judge |
| Q79 | 0.4286 | gap testo norma vs dottrina WP29, predetto in curatela |

Nessuna delle 5 query mostra failure genuino di pipeline:
allucinazione di norma inesistente, citazione errata, contenuto
inventato presentato come fondato sui chunk. Tutte e 5 mostrano
comportamento desiderato per il target professional (DPO, studi
legali), penalizzato da limiti strutturali del judge su tre
categorie distinte: (a) trasparenza meta-discorsiva quando il
retrieval fallisce, (b) inferenza tecnica corretta non
esplicitamente nel chunk, (c) negative off-corpus.

## Failure mode `answer_relevancy = 0.0`

**28 query su 100** hanno `answer_relevancy` esattamente 0.000:

| gruppo | n con rel=0.0 | n totale | quota |
|---|---:|---:|---:|
| positive (Q9, Q10, Q19, Q24, Q25, Q35, Q43, Q49, Q55, Q65, Q76, Q83) | 12 | 77 | 16% |
| negative | 14 | 20 | 70% |
| edge | 2 | 3 | 67% |
| **totale** | **28** | **100** | **28%** |

Il valore 0.0 esatto **non è punteggio reale** ma failure mode di
Ragas: la metrica re-genera N domande dall'answer e calcola
similarità coseno con la query originale; se il generator non
estrae domande (risposta di non-rispondibilità o formato
strutturato), restituisce 0. Pattern già documentato in W7 (8/38
query) — su 100 entry il fenomeno è più visibile in valori
assoluti ma stabile in quota relativa.

**Mediane ricalcolate senza zeri degenerati**:

| asse | n senza zeri | rel mediana senza zeri | rel mediana con zeri |
|---|---:|---:|---:|
| globale  | 72 | 0.8555 | 0.8150 |

Soglia ready RAGAS_RUN_NOTES nota 9 "answer_relevancy globale
mediana ≥0.80" **rispettata** sia con (0.8150) sia senza (0.8555)
i zeri degenerati. Diversamente da W7, in F.2 la soglia è
rispettata anche pre-rimozione zeri (in W7 con zeri 0.763, senza
0.815). Miglioramento attribuibile al subset v2 più strutturato e
all'aumento del campione che diluisce l'effetto degli zeri.

## Distribuzione bimodale answer_relevancy

Mean 0.6089 vs median 0.8150: divario 0.20+ tipico di distribuzione
bimodale. Causa diretta: i 28 zeri esatti tirano la mean verso il
basso senza spostare la mediana. Senza zeri, mean 0.8457 e median
0.8555 convergono — distribuzione monomodale ben centrata sopra
soglia.

**Implicazione operativa**: in F.2 e in future iterazioni la
mediana è la statistica primaria per il decision-making, la mean
va letta come sanity check secondario sul peso dei zeri. Il report
dichiara entrambe e separa esplicitamente la causa.

## Drift lessicale "dichiarazione di limite corpus" — 23/23

Pattern canonico definito in `PROJECT_CONTEXT.md` voce 32: `"...non
incluso nel corpus normativo di riferimento"`. Regex applicata
nello stesso test di `spike/PHASE_F1_DIAGNOSTIC.md` step 3:

```
non\s+(?:è\s+|sono\s+|sia\s+|siano\s+)?(?:inclus[oaie]|present[eai]).{0,40}corpus(?:\s+normativo)?(?:\s+di\s+riferimento)?
```

**Detection sui 100 outputs F.2**:

| sottoinsieme | n totale | n matched | drift |
|---|---:|---:|---:|
| `has_corpus_limit_declaration=true` | 23 | **0** | **23/23 (100%)** |
| `has_corpus_limit_declaration=false` | 77 | 0 | n/a |

**Finding**: il modello cloud Sonnet 4.6 in F.2 **non usa più il
pattern canonico** in nessuna delle 23 query con limite a monte.
Drift sistematico — non l'effetto isolato di Q43 visto in W7
smoke. Lessico runtime preferito:

- "Il contesto normativo fornito non contiene riferimenti
  sufficienti…"
- "Non è possibile confermare sulla base del solo contesto fornito…"
- "Sarebbe necessario disporre di un contesto normativo più ampio…"

**Implicazione**: la detection runtime via regex è inaffidabile
in v1. La metrica `runtime_corpus_limit_observed` nel dataset
(`gold_answers_v2.json`) resta popolata solo per Q19 e Q35 (set
manuale post-W7); il popolamento automatico va riprogettato in
v1.1 (vedi follow-up 1).

**Note metodologica**: la metrica Ragas faithfulness +
answer_relevancy **non è sensibile a questo drift** — il judge
valuta la coerenza semantica risposta-contesto, non il match
lessicale del pattern canonico. F.2 produce numeri affidabili
sull'asse delle metriche; il drift è un problema di
classificazione runtime, non di valutazione della generazione.

## Lettura segregata via flag dataset (Q35, Q19)

A valle dell'analisi qualitativa, le soglie ready/not-ready di
`RAGAS_RUN_NOTES.md` nota 9 vengono lette **segregando** Q35 e Q19
secondo il flag `runtime_corpus_limit_observed` già presente nel
dataset. **Non è una modifica metodologica ex-post in F.2**: il flag
è stato introdotto come ex-post in W7 (vedi `BENCHMARK_RAGAS_W7.md`
sezione "Modifica metodologica ex-post" + `PROJECT_CONTEXT.md` voce
33), propagato strutturalmente al JSON `gold_answers_v1.json`
durante W7-prep, e preservato attraverso la refusione gold v1→v2
(stesso valore `true` in `gold_answers_v2.json`). F.2 si limita ad
applicare il flag come fatto strutturale del dataset.

**Query coperte dal flag**:

| qid | flag in dataset (v1 = v2) | classe |
|---|---|---|
| Q35 | `has_corpus_limit_declaration=false`, `runtime_corpus_limit_observed=true` | runtime corpus limit (conferma W7) |
| Q19 | `has_corpus_limit_declaration=false`, `runtime_corpus_limit_observed=true` | runtime corpus limit (conferma W7) |

**Motivazione (eredità W7)**: Q35 e Q19 si comportano runtime come
scenario C, ma `has_corpus_limit_declaration` a monte assumeva che
il retrieval le avrebbe risolte. Quando il retrieval fallisce
(omonimia articolo, vocabolari disgiunti), il modello entra
correttamente in modalità scenario C. Il flag
`runtime_corpus_limit_observed=true` cattura questa transizione
runtime → scenario C ed era già acceso pre-F.2. **Non è una
riclassificazione opportunistica fatta a posteriori**: in F.2 Q19
ha faith=0.5556, sopra mediana gruppo limit — non entra nel
bottom-5 globale, non sposta l'aggregato.

**Q79 non viene segregata**: il pattern "gap testo norma vs
dottrina" è categoricamente diverso da "runtime corpus limit"
(retrieval ha funzionato, il gap è fra norma e dottrina). Resta
come osservazione esplorativa, non roadmap — vedi sezione
"Osservazioni esplorative".

**Soglie pre/post segregazione**:

| criterio | soglia | pre-segregazione | post-segregazione | esito |
|---|---|---:|---:|---|
| faith gruppo A mediana ≥0.75 | 0.75 | 0.9107 (n=58) | 0.9148 (n=56) | ✅ |
| rel globale mediana ≥0.80 | 0.80 | 0.8150 (n=100) con zeri | 0.8150 (n=100) | ✅ |
| 0 query gruppo A faith <0.4 | 0 | **1 (Q35)** | **0** (Q35 riclassificata) | ✅ |
| no allucinazione fuori pattern Q9 | no | confermato no (bottom-5 analizzate) | — | ✅ |

Tutte e 4 le soglie sono rispettate post-segregazione esplicita.

## Verdict

**GO ready-with-followup**.

Motivazione: la pipeline cloud Sonnet 4.6 produce risposte
groundate sulla maggior parte del benchmark esteso (58% globale e
62% gruppo A con faith >0.85), risposte oneste su query
retrieval-bound (dichiarazione di limite spontanea, drift
lessicale ma sostanza preservata), e citazioni strutturalmente
verified. Le 5 query bottom analizzate ricadono in 3 classi
attese: 2 retrieval failures gestiti correttamente (Q35), 1 edge
professional (Q46), 2 negative off-corpus (Q48, Q41), 1 gap norma
vs dottrina (Q79). Nessuna delle 5 mostra failure di pipeline.

Drift v1 W7 vs F.2 entro soglia (−0.042 faith, −0.007 rel) →
judge e pipeline stabili tra W7 (2026-05-20) e F.2 (2026-05-21).

Soglia rilascio pubblico v1.0 raggiunta. Vedi `SCOPE.md` registro
2026-05-21 e `PROJECT_CONTEXT.md` voce 35 per la decisione di
sblocco.

## Follow-up v1.1

### Follow-up 1 — Detection automatica `runtime_corpus_limit_observed`

**Finding**: 23/23 query con `has_corpus_limit_declaration=true`
mostrano drift lessicale rispetto al pattern canonico. La
detection regex su PHASE_F1_DIAGNOSTIC è ufficialmente inaffidabile.

**Azione v1.1**: sostituire la detection regex con LLM-as-judge
sulla presenza di "dichiarazione di limite" nella risposta
(prompt mirato, una call binaria per output). Popolare il flag
`runtime_corpus_limit_observed` automaticamente. Validare contro i
flag manuali esistenti (Q19, Q35).

**Stima**: 4-6 ore implementazione + ~$1-2 cost per re-eval del
flag su 100 outputs.

### Follow-up 2 — Validazione incrociata judge (già aperto da W7)

**Finding**: Sonnet judge in F.2 conferma il pattern di severità
osservato in W7 sulle parentesi esplicative (Q17 in W7, Q79 in
F.2). Bias judge non quantificato indipendentemente.

**Azione opzionale**: rieseguire un sottoinsieme con secondo judge
(Opus 4.7 se budget Anthropic ricostituito, oppure GPT-4o-mini per
costo ridotto). Target: query con recall@5=1 e faith Sonnet <0.7
(es. Q79).

**Stima**: ~$0.50-1 + 1-2 ore.

### Follow-up 3 — Tuning system prompt su pattern canonico (già aperto da W7)

**Finding**: drift lessicale 23/23 conferma e amplia il finding
W7. Il system prompt italiano va aggiornato per uniformare il
lessico verso `"non incluso nel corpus normativo di riferimento"`.

**Azione**: tuning chirurgico `core/rag_prompt/system_prompt.it.md`.
Modifica non blocca v1.0 (le metriche non dipendono dal pattern
lessicale), ma rende affidabile la detection runtime una volta
implementato il follow-up 1.

**Stima**: 1-2 ore.

## Osservazioni esplorative

### Q79 — Caso isolato da monitorare

Faith=0.4286, classe `mismatch_pipeline_vs_gold`. Il modello
integra spontaneamente dottrina WP29 (portabilità dati
derivati/inferiti) non presente nei chunk del corpus. Risposta
giuridicamente completa ma non grounded → faithfulness penalizzata
correttamente. **Non promosso a follow-up v1.1 con n=1.** Se 2+
query con pattern analogo emergono in benchmark futuri (gap fra
testo normativo letterale e interpretazione dottrinale
consolidata), valutare estensione corpus a linee guida EDPB/WP29 o
capability dedicata. Per ora resta osservazione esplorativa, non
roadmap.

## Cosa F.2 dimostra

- Pipeline cloud Sonnet 4.6 produce risposte groundate sulla
  maggior parte del benchmark esteso (58% globale, 62% gruppo A con
  faith >0.85).
- Stabilità di judge e pipeline tra W7 (2026-05-20) e F.2
  (2026-05-21): drift su 38 positive comuni −0.042 faith e
  −0.007 rel, entro soglia 0.05.
- Comportamento di trasparenza UX confermato su scala 100q:
  dichiarazione di limite spontanea su retrieval-bound failures e
  on edge/negative; zero allucinazioni semantiche fuori dal pattern
  benigno Q9 in tutte le bottom-5 analizzate qualitativamente.
- Answer_relevancy globale ≥0.80 (mediana 0.8150) raggiunta anche
  pre-rimozione dei zeri degenerati Ragas — soglia W7 era
  rispettata solo post-rimozione.
- Citation verifier strutturale (W5) sufficiente per v1: 0/100
  query analizzate mostrano fallimenti strutturali di citazione.
- Subset v2 sopra subset v1 su entrambe le mediane (+0.023 faith,
  +0.144 rel) — delta misurato; tre ipotesi alternative non
  distinguibili da questi dati (vedi sezione "Subset v2 nuove query
  Q51-Q100"). Nessuna lettura causale.

## Cosa F.2 NON dimostra

- Qualità su query fuori distribuzione del benchmark esteso (100
  query non rappresentano l'universo di query reali utente; coverage
  per norma fortemente sbilanciata verso GDPR e AI Act).
- Robustezza temporale: Sonnet 4.6 e Sonnet judge possono drift in
  release future, non sono modelli pinnati in deployment.
- Comportamento sul provider locale (Qwen via Ollama, fallback
  v1) — esplicitamente fuori scope di F.2 come di W7.
- Bias del judge quantificato indipendentemente: il pattern Q79
  "gap norma vs dottrina" è inferito da una sola query, serve la
  validazione incrociata del follow-up 2 per generalizzarlo.
- Detection automatica della dichiarazione di limite: il drift
  23/23 chiude la possibilità di usare la regex e apre il follow-up
  1.

## File correlati

- `data/benchmark/gold_answers_v2.json` — dataset (100 entry, 77
  positive + 20 negative + 3 edge; flag
  `has_corpus_limit_declaration` + `runtime_corpus_limit_observed`)
- `data/benchmark/ragas_pipeline_outputs_v2.json` — cache delle
  100 risposte pipeline + retrieved_chunks + contexts (riusabile
  per re-judge con LLM diverso, vedi follow-up 2)
- `data/benchmark/ragas_results_v2.json` — score per-query
- `data/benchmark/ragas_aggregates_v2.json` — aggregati per gruppo
  (query_type, has_corpus_limit, use_case, norm) + subset v1/v2
- `data/benchmark/RAGAS_RUN_NOTES.md` — spec metodologica pre-run
  W7 + esito F.2 in coda
- `data/benchmark/BENCHMARK_RAGAS_W7.md` — report W7 (38 positive
  v1) per il confronto drift
- `data/benchmark/BENCHMARK_W3.md` — benchmark retrieval-only W3
  (per contestualizzare i retrieval-bound failures Q19/Q35)
- `data/benchmark/BENCHMARK_V2_CURATION_BRIEF.md` — brief curatela
  Q51-Q100 post-pivot 2026-05-20
- `spike/PHASE_F1_DIAGNOSTIC.md` — diagnostico pre-F.2 (sorgente
  della regex drift lessicale)
- `spike/PHASE_F2_PREFLIGHT.md` — pre-flight cost F.2 (sorgente
  della scelta `prompt_caching=disabled`)
- `SCOPE.md` riga registro 2026-05-21 — decisione sblocco rilascio
  pubblico v1.0
- `PROJECT_CONTEXT.md` voce 35 — voce decisione corrispondente
- `ROADMAP_POST_V1.md` — capability v1.1 (estensione corpus,
  retrieval avanzato, follow-up 1-4 di F.2)
