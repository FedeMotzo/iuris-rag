# Benchmark v2 — Brief di curatela per le 50 nuove query

**Data:** 2026-05-20
**Stato:** Spec scritta a monte (vincolo metodologico). Modifiche post-curatela vanno in coda con motivazione, non sovrascrivono questa versione.

**Riferimenti:**
- `spike/BENCHMARK_DISTRIBUTION_ANALYSIS.md` — analisi distribuzione 38 positive attuali
- `spike/CORPUS_INGESTION_AUDIT.md` — audit completezza corpus (0 query benchmark v1 impattate da gap)
- `spike/DEMOKRITOS_AI_ACT_BENCHMARK_EVAL.md` — NO-GO riuso dataset esterno
- `data/benchmark/STATS.md` — statistiche dataset v1
- `PROJECT_CONTEXT.md` "Curatela gold answers W7-prep" — pattern processo curatela

## Obiettivo

Estendere `data/benchmark/gold_answers_v1.json` da 50 a 100 entry totali, aggiungendo 50 query nuove (39 positive + 11 negative/edge) curate con la stessa metodologia W7-prep. Output finale: `data/benchmark/gold_answers_v2.json`.

**Target di posizionamento del benchmark esteso:** primo benchmark RAG italiano pubblico su normativa privacy/AI con curatela giuridica entry-per-entry. Non variante di benchmark esistenti — dataset originale che dialoga con la letteratura (LegalBench-RAG, AI Act Eval Demokritos) per riferimento metodologico.

## Composizione target (50 query)

### Positive (39)

| Cluster | n | qid range proposto |
|---|---:|---|
| NIS2 mono-norma (governance, supply chain ICT, sanzioni, supervisione) | 6 | Q51-Q56 |
| NIS2 cross-norma con GDPR (data breach gestione doppia) | 2 | Q57-Q58 |
| Codice Privacy mono-norma (3 sotto-cluster) | 5 | Q59-Q63 |
| L. 132/2025 (mono-norma e cross-norma con AI Act) | 4 | Q64-Q67 |
| Cross-norma 3+ norme (scenari professionali realistici) | 5 | Q68-Q72 |
| Cross-norma scenario 2 norme (combinazioni pre-specificate) | 4 | Q73-Q76 |
| Diritti dell'interessato GDPR (artt. 12-22) | 4 | Q77-Q80 |
| Sanzionatorio puro (regime sanzionatorio strutturato) | 4 | Q81-Q84 |
| 231 fattispecie oltre 24-bis (corruzione, riciclaggio, sicurezza lavoro 25-septies) | 3 | Q85-Q87 |
| Procedurali "come si fa X" | 2 | Q88-Q89 |
| **Subtotale positive** | **39** | |

### Negative + edge (11)

| Sotto-cluster | n | qid range proposto |
|---|---:|---|
| Articolo inesistente (es. "art 999 GDPR" pattern Q47) | 2 | Q90-Q91 |
| Articolo abrogato del Codice Privacy | 2 | Q92-Q93 |
| Domanda in scope ma corpus mancante (codice penale, ISO, Direttive non recepite, EDPB) | 2 | Q94-Q95 |
| Query Garante UC4 (provvedimenti — fail-graceful) | 2 | Q96-Q97 |
| Omonimia di numerazione cross-norma (pattern Q35) | 2 | Q98-Q99 |
| Edge query vaghe / mix in-off corpus | 1 | Q100 |
| **Subtotale negative+edge** | **11** | |

**Vincolo numerazione**: qid nuove partono da Q51 (Q1-Q50 occupate, anche se Q4/Q5/Q20/Q21/Q22/Q23/Q41/Q42/Q44/Q46/Q47/Q48 sono già usate per negative/edge in v1). Numerazione continua per chiarezza.

## Composizioni dettagliate dei cluster (sotto-specifiche)

### Codice Privacy mono-norma (5 query)

| sotto-cluster | n | esempi di traiettoria query |
|---|---:|---|
| Competenze e poteri del Garante (artt. 153-160) | 2 | "Quali sono i poteri ispettivi del Garante?", "Come si nomina il collegio del Garante?" |
| Trattamenti speciali italiani (condanne penali, polizia, giustizia, intelligence) | 2 | "Trattamento dati di polizia: base giuridica?", "Casellario giudiziale: condizioni di trattamento" |
| Sanzioni penali italiane (art. 167 trattamento illecito) | 1 | "Reclusione per trattamento illecito di dati: in quali casi?" |

**Regola di disambiguazione UC4**: le query su Garante in v1 sono **solo sulla normativa primaria** (competenze, poteri di legge, formazione del collegio), **mai sui provvedimenti emanati** (UC4 v1.1). Curatela: ogni gold_chunks deve essere un articolo del Codice Privacy, non un riferimento a provvedimento. Se la query deriva verso provvedimenti, riclassificare come negative Q96-Q97.

### Cross-norma scenario 2 norme (4 query) — combinazioni pre-specificate

| combinazione | n | esempio traiettoria |
|---|---:|---|
| AI Act + GDPR (deployer obblighi vs titolare) | 2 | "L'azienda è deployer AI Act e titolare GDPR: gli obblighi si sovrappongono?" |
| 231 + GDPR (trattamento illecito come reato-presupposto) | 1 | "Il trattamento illecito di dati può essere reato-presupposto 231?" |
| NIS2 + GDPR (data breach come incidente NIS2 + violazione GDPR) | 1 | "Un data breach va notificato sia al Garante sia all'autorità NIS2?" |

### Cross-norma 3+ norme (5 query)

Pattern realistici target professional. Curatela ad alto costo (3-4 ore totali stimate, vedi zone di rischio).

| scenario | norme integrate |
|---|---|
| Banca usa AI per scoring/HR | AI Act + GDPR + 231 + L. 132/2025 |
| Sanità: chatbot AI per triage paziente | AI Act + GDPR + L. 132/2025 (sanitario) |
| PA usa AI per gestione procedure (cybersicurezza) | AI Act + NIS2 + GDPR |
| Studio legale usa AI per due diligence | AI Act + GDPR + 231 (riciclaggio reato-presupposto) |
| Industria farmaceutica usa AI in pharmacovigilance | AI Act + GDPR + NIS2 (settore sanitario essenziale) |

Curatela: gold_chunks può includere chunk da 3-4 norme diverse. Cita esplicitamente ciascuna norma nella gold_answer (pattern stabile: "Ai sensi dell'art. X del [norma A] ... Combinato disposto dell'art. Y del [norma B] ..."). Ammessa "dichiarazione di limite corpus" se uno dei riferimenti necessari non è nel corpus (atteso su L. 132/2025 sanitario, che è poco rappresentato).

### NIS2 mono-norma (6 query) — aree di copertura

| area | n | esempio |
|---|---:|---|
| Classificazione soggetti essenziali vs importanti | 1 | "Una società di trasporti rientra tra soggetti essenziali o importanti?" |
| Obblighi governance + accountability | 1 | "Quali obblighi di governance NIS2 ricadono sull'organo amministrativo?" |
| Catena di fornitura ICT | 1 | "L'azienda risponde per vulnerabilità nei suoi fornitori ICT?" |
| Notifica incidenti significativi | 1 | "Tempistiche di notifica di un incidente significativo NIS2" |
| Supervisione e sanzioni NIS2 | 1 | "Quali sanzioni amministrative prevede NIS2?" |
| Interazione con altre norme settoriali | 1 | "NIS2 si applica anche a banche già regolate da DORA?" (DORA fuori corpus → atteso dichiarazione di limite) |

### Sanzionatorio puro (4 query)

| norma | n | esempio |
|---|---:|---|
| GDPR sanzioni (artt. 83-84) | 1 | "Quale è il massimale di sanzione GDPR per violazione del diritto di accesso?" |
| 231 sanzioni interdittive (artt. 9, 13) | 1 | "In quali casi si applicano sanzioni interdittive ex 231?" |
| NIS2 sanzioni amministrative | 1 | "Sanzioni massime NIS2 per soggetti essenziali e importanti" |
| AI Act sanzioni (artt. 99-101) | 1 | "Multe massime per provider di GPAI con rischio sistemico" |

Curatela: query disegnate per essere **specifiche** (riferimento esplicito a fattispecie / ammontare / tipologia di soggetto), non generiche ("sanzioni AI Act"), per evitare ambiguità di retrieval su multi-articolo.

### Diritti interessato GDPR (4 query)

| diritto | n | esempio |
|---|---:|---|
| Accesso (art. 15) | 1 | "Tempi e modalità per il diritto di accesso ex art. 15 GDPR" |
| Oblio (art. 17) | 1 | "In quali casi il diritto all'oblio si applica anche a dati pubblicati per finalità giornalistica?" |
| Portabilità (art. 20) | 1 | "Diritto alla portabilità si applica a dati derivati dal trattamento?" |
| Limitazione (art. 18) o opposizione (art. 21) | 1 | (scelta della 4ª su limitazione/opposizione in fase curatela) |

### 231 fattispecie oltre 24-bis (3 query)

| fattispecie | n |
|---|---:|
| Corruzione (artt. 25, 25-ter) | 1 |
| Riciclaggio (art. 25-octies) | 1 |
| Sicurezza sul lavoro (art. 25-septies) | 1 |

### Procedurali "come si fa X" (2 query)

| topic | esempio |
|---|---|
| Procedura DPIA | "Quali sono i passi della procedura di DPIA?" (richiama art. 35 + linee guida; può rientrare in dichiarazione di limite per linee guida WP29 fuori corpus) |
| Registro trattamenti | "Cosa deve contenere il registro dei trattamenti ex art. 30 GDPR?" |

### L. 132/2025 (4 query)

| area | n |
|---|---:|
| Regimi italiani specifici AI (lavoro, sanità) | 2 |
| Coordinamento con AI Act | 1 |
| Monitoraggio italiano e responsabilità | 1 |

### Negative + edge dettagliato

**Articolo inesistente (2)**: pattern Q47 esteso. Es. "art 999 D.Lgs 231/2001", "art 500 AI Act". gold_chunks=[]. Test fail-graceful + assenza allucinazione del numero.

**Articolo abrogato Codice Privacy (2)**: scegliere 2 dai 114 abrogati noti. Es. "Quali sono gli obblighi del titolare ex art. 31 del Codice Privacy?" (art. 31 abrogato). gold_chunks=[]. Test: il sistema deve rifiutare con dichiarazione esplicita, non recuperare articolo errato per omonimia.

**Domanda in scope ma corpus mancante (2)**: pattern Q41 (Data Act), Q42 (ISO), Q44 (EDPB), Q48 (ePrivacy) esteso. Es. "Linee guida EDPB sul consenso", "Quali standard ISO sulla sicurezza dei dati?". gold_chunks=[].

**Query Garante UC4 (2)**: provvedimenti specifici. Es. "Provvedimento Garante contro TikTok del 2024", "Decisione del Garante su X". gold_chunks=[]. Audit obbligatorio post-curatela: verificare che nessun articolo Codice Privacy o GDPR risponda direttamente alla query — altrimenti diventa positive lato UC1, non negative UC4.

**Omonimia di numerazione (2)** — nuovo cluster ispirato a Q35:
- "Cosa dice l'articolo 9?" (ambiguo tra GDPR art. 9 categorie particolari, 231 art. 9 sanzioni interdittive, Costituzione art. 9, ecc.)
- "Articolo 6 paragrafo 1" (ambiguo tra GDPR art. 6 par. 1 e AI Act art. 6 par. 1)

Comportamento atteso: il sistema riconosce omonimia, lista le occorrenze nel corpus, chiede chiarimento OR risponde su entrambe con dichiarazione di ambiguità. gold_chunks=[] (è negative). Curatela: definire gold_answer come "il sistema deve riconoscere ambiguità e chiedere/indicare".

**Edge vaghe (1)**: pattern Q43 / Q45 / Q46. Es. "Cosa devo sapere di NIS2?" — query genericissima, comportamento atteso: dichiarazione di limite + lista delle aree principali.

## Schema entry (invariato vs v1)

Per ogni query nuova:

```json
{
  "qid": "QNNN",
  "use_case": "<descrizione concisa, es. 'NIS2 governance organi amministrativi'>",
  "query_type": "positive | negative | edge",
  "question": "<query in italiano naturale, tono professionale, NON keyword-style salvo nei casi negative/lookup>",
  "gold_chunks": [
    { "chunk_id": "<chunk_id reale del corpus Qdrant>", "hierarchy": "<...>", "text": "<...>" }
  ],
  "gold_answer": "<risposta in italiano nello stile gold_answers_v1.json: citazioni [cite:chunk_id], lunghezza 60-180 parole, max 6 citazioni, dichiarazione di limite corpus se applicabile usando pattern canonico 'non incluso nel corpus normativo di riferimento'>",
  "review_status": "reviewed",
  "has_corpus_limit_declaration": true | false,
  "runtime_corpus_limit_observed": false,
  "notes": "<note di curatela: dubbi, decisioni di scope, riferimenti>"
}
```

`runtime_corpus_limit_observed`: lasciare **`false` per tutte** le 50 nuove entry. Sarà aggiornato post Ragas v2 in base al comportamento osservato (analogo al pattern Q19/Q35 in W7).

## Vincoli di curatela

### Audit annotazione (sanity check giuridico)

Per ogni positive, controllare entry-per-entry:
- **Gold_chunks coerenti con la query**: nessun chunk_id allucinato dall'LLM, nessuna conferma di pattern Q5/Q9 (art_25-undecies fantasma).
- **Chunk_id reali in Qdrant**: verificare con script o lookup diretto. Audit fallisce in caso di chunk_id non esistente.
- **Dichiarazione di limite corretta**: se `has_corpus_limit_declaration=true`, la `gold_answer` deve includere la frase canonica `"non incluso nel corpus normativo di riferimento"`. Drift lessicale = fix in curatela.

Per ogni negative, controllare:
- **gold_chunks effettivamente vuoto** (`[]`). Se il retrieval su quella query produce match perfetto in Qdrant, la query è positive, non negative — riclassificare o sostituire.

### Stop conditions

La curatela si ferma e si segnala a Federico se:
- Una query non è curabile a 30 minuti di lavoro → flag per discussione
- Una combinazione cross-norma 3+ non ha gold_chunks coerenti in nessuna delle norme target → riclassificare a cross-norma 2 norme o sostituire
- Pattern Q5/Q9 (LLM-hint allucinato) emerge in più di 3 query → fermare la batch, audit completo prima di proseguire
- Una negative "Garante UC4" risulta avere risposta in corpus → riclassificare come positive o sostituire

### Zone di rischio (documentate per memoria curatela)

1. **NIS2 retrieval fragile**: atteso runtime corpus limit più alto della media (gold_answers_v1.json non lo ha mai stressato). Se >25% delle 8 query NIS2 ricade in scenario C, è **finding da reportare**, non bug.
2. **Cross-norma 3+ ad alto costo curatela**: ~30-45 min/query di curatela giuridica. Budgetare 3-4 ore solo per i 5 scenari.
3. **Codice Privacy mono-norma — 114 articoli abrogati**: assicurarsi che le 5 nuove query Codice Privacy puntino solo agli articoli vigenti (107 effettivi). Audit pre-curatela: lista articoli vigenti da fornire al curatore.
4. **Sanzionatorio puro — retrieval multi-articolo**: query disegnate per essere specifiche (riferimento esplicito a fattispecie o ammontare), non generiche. Vedi pattern proposto.

### Pattern stabili da W7-prep (invariati)

- Citazione: `[cite:chunk_id]` prima della punteggiatura, spazio singolo per multi-cite `[cite:X] [cite:Y]`, **mai** `[cite:X][cite:Y]`
- Dichiarazione di limite: pattern canonico `"non incluso nel corpus normativo di riferimento"` (con varianti di concordanza)
- Audit annotazione = secondo livello validazione, **non opzionale**
- Curatela LLM-assisted con revisione umana entry-per-entry (rate sostenibile ~1 ora/query, conferma W7-prep)

## Sequenza operativa proposta

| Step | Cosa | Stima |
|---|---|---|
| 1 | Generazione query candidate LLM-assisted (~80 candidate → filtra a 50) | 1 giorno |
| 2 | Curatela giuridica entry-per-entry + audit annotazione | 2-3 giorni |
| 3 | Validazione finale dataset v2 (consistency check con script) | 0.5 giorno |
| 4 | Re-run benchmark W3 + Ragas su corpus esteso (con eventuale estensione c.p. da decidere a step 1) | 1 giorno |
| 5 | Aggiornamento `BENCHMARK_W3_v2.md`, `BENCHMARK_RAGAS_W7_v2.md`, `STATS_v2.md` | 0.5 giorno |
| **Totale** | | **~5-6 giorni** |

## Decisione condizionale: estensione corpus c.p.

A valle dello step 1 (generazione candidate), decidere se estendere il corpus con articoli del codice penale richiamati da 231 art. 24-bis...25-undecies. Criterio:

- **Estendi** se ≥4 delle 50 query nuove (in particolare le 3 di "231 fattispecie oltre 24-bis" + cross-norma 3+ che toccano 231) richiedono dispositivo c.p. per essere groundabili.
- **Non estendere** se le query 231 si possono curare con dichiarazione di limite (mantenere il pattern scenario C come ora).

La decisione è **data-driven**: si basa sulle query effettivamente generate, non su intuizione. Costo estensione c.p.: 2-3 giorni se decisa.

## Cosa NON è in scope di questa fase

- ❌ Modifiche al codice di `core/` (retrieval, generazione, citation)
- ❌ Capability v1.1 (multi-query, HyDE, runtime flag automatico)
- ❌ Estensione parser annex AI Act diversi dal III (decisione condizionale post-curatela: rinvia a v1.1 se 0 query toccano annex ≠ III)
- ❌ Rientro UC4 Garante provvedimenti (resta v1.1 — solo 2 query Garante UC4 come negative)
- ❌ Tuning system prompt italiano (resta finding W7 follow-up 3)
- ❌ Estensione corpus oltre c.p. richiamati da 231 (ISO, decreti settoriali, ecc. → v1.1)

## Cosa misurare a valle (informativo)

A re-run W3 + Ragas su 100 query, raccogliere:

1. Aggregati W3 segregati per cluster nuovo (es. R@10 cluster NIS2 mono-norma vs cluster GDPR diritti)
2. Aggregati Ragas segregati per cluster nuovo (faith mediana per cluster)
3. Distribuzione `runtime_corpus_limit_observed` post-eval su 100 query (atteso 7-12% globale)
4. Identificazione nuovi pattern di failure non visti in W7 (es. retrieval fragile su NIS2, omonimia gestita male, scenari 3+ norme con gold cross che il retrieval non sa integrare)

Decisione pubblico/non-pubblico subordinata a questi numeri, come da pivot SCOPE 2026-05-20.

## Vincolo metodologico

Questo brief è scritto **prima** della generazione delle query candidate (fase 4'). Se a posteriori emerge che una composizione di cluster va modificata (es. NIS2 da 6 a 8 perché emerge un'area non prevista), la modifica va in coda a questo file con data e motivazione, **non** riscrivendo i target a monte. I target a monte restano baseline metodologico riproducibile, anche se la composizione effettiva del dataset diverge.