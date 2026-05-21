# Benchmark distribution analysis — read-only

Data: 2026-05-20
Fase: pivot W7→W10 step 3 — design del benchmark esteso (target 100 query totali).
Sorgente: `data/benchmark/gold_answers_v1.json` (38 query positive + 10 negative + 2 edge).
Script: [`spike/analyze_distribution.py`](analyze_distribution.py).

**Obiettivo:** identificare cluster sotto-rappresentati nelle 38 query
positive attuali, per progettare la composizione delle 50 query nuove.
Analisi read-only.

---

## Step 1 — Distribuzione per norma di appartenenza dei gold_chunks

**Tabella riassuntiva** (una query può comparire in più righe se cross-norma):

| Norma toccata | n query | % su 38 |
|---|---:|---:|
| GDPR (Reg UE 2016/679)        | 12 | 31.6% |
| AI Act (Reg UE 2024/1689)     | 19 | 50.0% |
| Codice Privacy (D.Lgs 196/2003) |  1 |  2.6% |
| D.Lgs 231/2001                |  6 | 15.8% |
| NIS2 (D.Lgs 138/2024)         |  3 |  7.9% |
| L. 132/2025                   |  2 |  5.3% |

**Mono-norma vs cross-norma**:

| Pattern | count | qid |
|---|---:|---|
| Mono-norma GDPR                | 8 | Q6, Q7, Q28, Q29, Q31, Q34, Q37, Q39 |
| Mono-norma AI Act              | 15 | Q1, Q2, Q8, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q30, Q35, Q36, Q50 |
| Mono-norma Codice Privacy      | 0 | — |
| Mono-norma D.Lgs 231/2001      | 5 | Q9, Q25, Q26, Q27, Q49 |
| Mono-norma NIS2                | 3 | Q10, Q32, Q40 |
| Mono-norma L. 132/2025         | 2 | Q38, Q45 |
| **Cross-norma 2 norme**        | 5 | Q3, Q19, Q24, Q33, Q43 |
| **Cross-norma 3+ norme**       | 0 | — |

Note:
- Codice Privacy compare solo come gold cross-norma (Q43 "Cosa dice la legge sulla privacy" → GDPR art.1 + Codice Privacy art.1). Mai mono-norma.
- L. 132/2025 ha 2 mono-norma (Q38 art.11, Q45 vago "normativa AI Italia 2025").
- **Cross-norma 3+ norme: 0 query.** Pattern non rappresentato.

---

## Step 2 — Distribuzione per tipo di chunk

| Tipo chunk | count totale | n query in cui appare almeno 1 |
|---|---:|---:|
| article          | 50 | 33 |
| article_fragment |  2 |  1 |
| recital          |  8 |  6 |
| annex            |  7 |  6 |
| other            |  0 |  0 |

`annex` = 7 chunk: tutti su Annex III AI Act (gli unici annex ingeriti — vedi `spike/CORPUS_INGESTION_AUDIT.md`).
Articoli dominano (50/67 = 75% dei gold_chunks). Recital usati come fonte interpretativa in 6 query (Q3, Q29, Q31, Q37, ecc.).

---

## Step 3 — Distribuzione per use case SCOPE

Mapping manuale ai 5 UC. UC4 (Garante) escluso per design v1 (decisione 2026-05-19).

| Use case | n query | qid |
|---|---:|---|
| UC1 — GDPR compliance        | 10 | Q6, Q7, Q28, Q29, Q31, Q33, Q34, Q37, Q39, Q43 |
| UC2 — AI Act                 | 19 | Q1, Q2, Q3, Q8, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q30, Q35, Q36, Q38, Q45, Q50 |
| UC3 — 231 responsabilità ente|  6 | Q9, Q24, Q25, Q26, Q27, Q49 |
| UC4 — Garante                |  0 | — (v1.1) |
| UC5 — NIS2 / cybersecurity   |  3 | Q10, Q32, Q40 |

**AI Act domina (50% delle positive).** NIS2 e Codice Privacy (lato italiano) sono sotto-rappresentati.

---

## Step 4 — Distribuzione per tipologia di query

**Avvertenza metodologica**: la classificazione automatica dello script
falliva su 28/38 query (19 false positives su "Stress/edge" perché il
prefisso `use_case` contiene la parola "stress:" come etichetta del
setter del benchmark, NON come tipologia di query). Ho rifatto la
classificazione **manualmente** leggendo ciascuna `question`, ignorando
il prefisso `use_case`.

| Tipologia | count | % su 38 | qid |
|---|---:|---:|---|
| **Lookup definitorio** (keyword nudo "art N di Z" / "Cos'è X")    | 18 | 47.4% | Q8, Q13, Q17, Q26, Q27, Q28, Q29, Q30, Q31, Q32, Q33, Q34, Q35, Q36, Q37, Q38, Q39, Q50 |
| **Condizionale** (quando/se/ricade/scatta)                        | 11 | 28.9% | Q1, Q2, Q7, Q10, Q11, Q12, Q14, Q15, Q16, Q18, Q25 |
| **Procedurale** (quali sono i compiti/obblighi)                   |  3 |  7.9% | Q6, Q9, Q40 |
| **Cross-norma scenario** (situazione professionale multi-norma)   |  3 |  7.9% | Q3, Q19, Q24 |
| **Stress/edge** (intenzionalmente vago)                           |  3 |  7.9% | Q43, Q45, Q49 |
| **Sanzionatorio puro** (solo sanzioni)                            |  0 |  0.0% | — |

Casi borderline annotati:
- Q8 ("Cos'è la FRIA e quando va condotta?") classificata lookup ma è ibrida lookup+condizionale.
- Q25 ("Un dipendente accede abusivamente al sistema...") classificata condizionale ma è scenario concreto mono-norma 231.
- Q50 ("sanzioni AI Act multe massime") classificata lookup, non sanzionatorio: è una query keyword su sanzioni, non una domanda sull'impianto sanzionatorio.

Pattern dominante: **47% delle query sono "lookup keyword nudo"** — il setter del benchmark ha generato molte query stile "art N di Z" per stressare il retrieval. Sono utili per testare il pipeline ma non rappresentano realisticamente l'uso professionale (DPO/avvocato che fanno query in linguaggio naturale).

---

## Step 5 — `has_corpus_limit_declaration` vs runtime osservato

| Categoria | n | qid |
|---|---:|---|
| flag=true, runtime=true (corpus limit confermato)                | 11 | Q9, Q12, Q13, Q15, Q24, Q25, Q26, Q27, Q43, Q45, Q49 |
| flag=true, runtime=false (overflag — assente, dato W7)           |  0 | — |
| **flag=false, runtime=true (FALSO NEGATIVO del flag)**           |  **2** | **Q19, Q35** |
| flag=false, runtime=false (standard)                             | 25 | Q1, Q2, Q3, Q6, Q7, Q8, Q10, Q11, Q14, Q16, Q17, Q18, Q28, Q29, Q30, Q31, Q32, Q33, Q34, Q36, Q37, Q38, Q39, Q40, Q50 |

11 query erano dichiarate "corpus limit" a monte, 2 lo sono diventate
solo runtime (Q19 banca AI scoring, Q35 art 27 AI Act FRIA). Il flag
a monte è uno strumento di curatela imperfetto: cattura il pattern
atteso ma può mancare casi dove il retrieval fallisce per disallineamento
lessicale (Q19) o omonimia di articolo cross-norma (Q35).

---

## Step 6 — Cluster sotto-rappresentati

Sulla base degli step 1-5, ecco i cluster con copertura insufficiente
nelle 38 positive attuali:

### 1. NIS2 (D.Lgs 138/2024) — 3 query su 38

Use case UC5 ha solo 3 query (Q10, Q32, Q40), tutte mono-norma. NIS2 è
norma di scope esplicito v1 ma rappresentata circa quanto L. 132/2025
(2 query). Aree non coperte:
- soggetti rilevanti vs soggetti essenziali (Q10 c'è, ma una sola)
- obblighi di governance + accountability (assenti)
- catena di fornitura ICT (assente)
- supervisione e sanzioni NIS2 (assente)
- interazione NIS2 ↔ GDPR (data breach) (assente)

**Atteso benchmark esteso: 6-8 query NIS2.**

### 2. Codice Privacy (D.Lgs 196/2003 lato italiano) — 0 mono-norma

Il Codice Privacy nazionale (sezioni 2-bis...2-sexies-decies, artt.
175-176, ecc. — articoli italiani non semplicemente armonizzati col
GDPR) è completamente assente come mono-norma. Le 107 entry ingerite
in Qdrant per il Codice Privacy non sono mai gold-target diretto. Aree:
- protezione dati su condanne penali / casellario (art. 2-octies, attuale gold cross di Q43)
- trattamenti per fini di giustizia, ordine pubblico, polizia (artt. 175+)
- Garante (artt. 153-160, anche se UC4 è v1.1, il chi-è-il-Garante può essere UC1)
- sanzioni penali e amministrative italiane

**Atteso benchmark esteso: 4-6 query Codice Privacy mono-norma.**

### 3. L. 132/2025 (Disposizioni AI italiane) — 2 query su 38

Norma neo-introdotta nello scope v1. Coperta solo da Q38 (art. 11
lavoro) e Q45 (vaga). Aree non coperte:
- regimi autorizzativi italiani specifici AI
- coordinamento con AI Act (interazione esplicita)
- responsabilità (sanitaria, professionale)
- monitoraggio italiano

**Atteso benchmark esteso: 4-5 query L. 132/2025.**

### 4. Cross-norma 3+ norme — 0 query

Pattern completamente assente. Scenari professionali reali integrano
spesso 3+ norme (es. "banca usa AI per assunzioni" → GDPR + AI Act +
231 + L. 132/2025). Le 5 cross-norma attuali sono tutte 2 norme.

**Atteso benchmark esteso: 4-6 query cross-norma 3+ (scenari professionali realistici, target DPO/avvocati).**

### 5. Tipologia "Cross-norma scenario" — 3 query su 38

Solo Q3, Q19, Q24 sono scenari realistici. Il resto è dominato da
"lookup keyword nudo" (18/38 = 47%). Per un benchmark **rappresentativo
dell'uso professionale** servono più scenari ricchi.

**Atteso benchmark esteso: 8-10 nuove query cross-norma scenario.**

### 6. Sanzioni e responsabilità — 0 query "sanzionatorio puro"

Sanzioni GDPR (artt. 83-84), 231 (artt. 9-13, sanzioni interdittive),
NIS2 (sanzioni amministrative), AI Act (artt. 99-101) sono praticamente
assenti come topic primario. Q50 e Q18 toccano sanzioni AI Act ma sono
condizionale/lookup, non query strutturate sul regime sanzionatorio.

**Atteso benchmark esteso: 4-5 query sanzionatorie.**

### 7. Diritti dell'interessato GDPR (artt. 12-22) — sotto-rappresentato

Le 12 query GDPR coprono principalmente DPO, DPIA, base giuridica,
profilazione. Diritti dell'interessato (accesso, rettifica, oblio,
limitazione, portabilità, opposizione) — pratica quotidiana di un DPO
— sono coperti solo indirettamente. Q31 (art.22 decisioni automatizzate)
è l'unica diretta sui diritti.

**Atteso benchmark esteso: 3-4 query diritti dell'interessato.**

### 8. AI Act annex ≠ III — 0 query

Q1/Q13/Q19/Q30 toccano Annex III. Gli altri 12 annex AI Act non sono
referenziati (e non sono ingeriti — vedi corpus audit). Coerente con
quanto già segnalato.

**Decisione**: non aggiungere query sugli altri annex AI Act senza prima
estendere il parser (vedi `CORPUS_INGESTION_AUDIT.md` raccomandazione
fase 3). Se 0 nuove query li toccano → declassare il parser fix a v1.1.

---

## Step 7 — Composizione consigliata per 50 query nuove

Vincolo: il benchmark v1 ha 11 negative + 2 edge su 50 totali (22%
negative+edge). Mantengo proporzione 22% sulle 50 nuove = 11 nuove
negative+edge, 39 nuove positive.

Composizione target (39 positive + 11 negative/edge = 50):

| Cluster | n query proposte | motivazione |
|---|---:|---|
| **NIS2 mono-norma** (governance, supply chain ICT, sanzioni, supervisione) | 6 | UC5 sotto-rappresentato; copre lacune step 6 punto 1 |
| **NIS2 cross-norma con GDPR** (data breach gestione doppia) | 2 | scenario reale DPO+CISO |
| **Codice Privacy mono-norma** (Garante competenze art.153-160 in UC1, condanne penali art.2-octies, trattamenti giustizia art.175+) | 5 | gap netto: 0 mono-norma attuali; UC4 ESCLUSO ma le competenze del Garante in UC1 OK |
| **L. 132/2025 mono-norma e cross-norma con AI Act** (regimi italiani specifici, sanità, lavoro, monitoraggio) | 4 | norma nuova nello scope, coperta solo da 2 query |
| **Cross-norma 3+ norme** (scenari professionali realistici: banca AI HR + 231 + GDPR + L.132; sanità AI + GDPR + L.132 sanitario; PA AI + NIS2 + GDPR) | 5 | pattern oggi 0; valore alto per posizionamento target professional |
| **Cross-norma scenario 2 norme** (oltre i 3 attuali) | 4 | bilanciare il dominio "lookup keyword" |
| **Diritti dell'interessato GDPR** (accesso, oblio, portabilità, limitazione) | 4 | UC1 sotto-rappresentato sui diritti |
| **Sanzionatorio puro** (regime sanzionatorio strutturato GDPR / 231 / NIS2 / AI Act) | 4 | 0 query attuali; topic centrale per compliance |
| **231 fattispecie specifiche oltre 24-bis** (corruzione, riciclaggio, abusi mercato, sicurezza sul lavoro 25-septies) | 3 | UC3 sotto-rappresentato sulle fattispecie diverse da informatica |
| **Stress/lookup keyword AGGIUNTIVI** (nuovi articoli emersi dall'audit corpus che non hanno gold attuale, es. art.41-44 GDPR autorità di controllo, art.83 GDPR sanzioni) | 2 | riempire angoli rimasti, basso costo |
| **Subtotale positive nuove** | **39** | |
| **Negative bilanciate** (articolo inesistente cross-norma, articolo abrogato del Codice Privacy, domanda formalmente in scope ma fuori corpus, query Garante UC4) | 8 | testa fail-graceful su nuovi cluster |
| **Edge** (query genuinamente ambigua, mix in/off corpus, vaga su L.132/NIS2) | 3 | bilanciare gli edge attuali |
| **Subtotale negative+edge nuove** | **11** | |
| **TOTALE NUOVE** | **50** | |

**Distribuzione finale benchmark esteso atteso (100 totale)**:

| Norma toccata | v1 (38 pos) | nuove (39 pos) | totale | % |
|---|---:|---:|---:|---:|
| GDPR              | 12 | ~17 | ~29 | 38% |
| AI Act            | 19 | ~13 | ~32 | 42% |
| Codice Privacy    |  1 | ~5  | ~6 | 8% |
| 231/2001          |  6 | ~6  | ~12 | 16% |
| NIS2              |  3 | ~9  | ~12 | 16% |
| L. 132/2025       |  2 | ~5  | ~7 | 9% |

(Le % sommano oltre 100 perché cross-norma contano in più righe.)

Distribuzione tipologie attesa post-estensione: lookup keyword scende
da 47% a ~30%, cross-norma scenario sale da 8% a ~25%, restanti
tipologie più bilanciate.

---

## Step 8 — Sintesi finale

### 3 finding più importanti

1. **Il benchmark v1 è "AI-Act-pesante e lookup-keyword-pesante"**: 50% delle query toccano AI Act, 47% sono lookup keyword nudo. Riflette il setter (interesse personale verticale + necessità di stressare il retrieval su singoli articoli). Non è rappresentativo dell'uso DPO reale, che integra GDPR + 231 + L.132 + NIS2 con scenari concreti.

2. **NIS2, Codice Privacy lato italiano, L. 132/2025 e cross-norma 3+ sono praticamente assenti**. NIS2 ha 3 query (8%), Codice Privacy 0 mono-norma, L. 132/2025 2 query (5%), cross-norma 3+ norme 0. Sono norme di scope v1 ma sotto-test.

3. **Il flag `has_corpus_limit_declaration` ha già rivelato 2 falsi negativi su 27 query gruppo A** (Q19, Q35, vedi W7). Sul benchmark esteso a 100 query è atteso che la proporzione di falsi negativi resti simile (~7%), suggerendo 7-10 query in totale che cadranno come "runtime corpus limit" sul corpus v1. L'estensione corpus codice penale (v1.1) potrebbe convertirne 2-4 in groundable. Il resto resta scenario C strutturale.

### 3 implicazioni operative per il design delle 50 query nuove

1. **Privilegiare scenari professionali su lookup keyword**. Nuove query cross-norma 3+ norme (5 proposte) e cross-norma scenario 2 norme (4 proposte) cambiano il bilanciamento da 47%→30% lookup. Avvicina il benchmark a misurazione realistica della pipeline.

2. **Allineare la curatela al gap noto del corpus AI Act annex**. Decidere PRIMA della curatela: se ≥1 delle 50 nuove query referenzia annex AI Act ≠ III, ALLORA pianificare estensione parser (`CORPUS_INGESTION_AUDIT.md` raccomandazione). Se 0 nuove query li toccano, conferma rinvio a v1.1.

3. **Coprire le sanzioni come topic primario**. 0 query sanzionatorie pure su 38 è anomalo per benchmark legal compliance: sanzioni sono spesso la sezione più consultata dai DPO. 4 proposte (regime sanzionatorio strutturato GDPR/231/NIS2/AI Act) coprono il gap.

### Zone di rischio nella curatela

- **NIS2 retrieval potrebbe essere fragile**: solo 3 query positive attuali, e ingestion completa (44 articoli) ma testata poco. Atteso più "runtime corpus limit" tra le 6-8 nuove query NIS2. Se ≥3 cadono in scenario C → flagare per design re-evaluation prima del re-run Ragas (potrebbe richiedere terminology expansion / query rewriting prima della valutazione).

- **Cross-norma 3+ norme è terra inesplorata**: gold-chunks set di queste 5 nuove query non è banale da curare manualmente (richiede ragionamento giuridico cross-strato, non match lessicale). Stima: ~30-45 min/query di curatela giuridica + audit = ~3-4 ore solo su queste 5. Da budgetare esplicitamente.

- **Codice Privacy mono-norma** richiede pulizia preliminare: i 114 articoli abrogati non vanno mai come gold; va assicurato che le 5 nuove query Codice Privacy puntino solo agli articoli vigenti (107 effettivi su 221 nel sorgente).

- **Sanzionatorio puro**: rischia retrieval fragile se query è generica ("sanzioni AI Act") perché matchera multi-articolo (artt. 99, 100, 101). Le 4 query proposte vanno disegnate o (a) keyword nudo specifico ad articolo, o (b) scenario condizionale ("multe massime per provider GPAI") per evitare ambiguità.

- **Garante in UC4 escluso**: le 5 query Codice Privacy proposte includono "competenze del Garante" che però è UC1 (lato GDPR/Codice Privacy), non UC4 (provvedimenti scraping). Da chiarire nella curatela: la chiamata mira al lato normativo, non al lato documentale dei provvedimenti — non è creep su UC4.
