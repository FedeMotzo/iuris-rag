# Smoke gold comparison — spec

Data: 2026-05-20
Stato: spec scritta **prima** del run (vincolo metodologico).

## Obiettivo

Decisione **go/no-go per Ragas eval W7**: la pipeline RAG cloud produce
output utilmente confrontabili col dataset `gold_answers_v1.json`, o
emergono gap che renderebbero il run Ragas non informativo?

**Non è una valutazione**. Non duplica Ragas (faithfulness + answer
relevancy). Misura solo se ha senso lanciare Ragas adesso o se serve
patch preliminare.

Budget: 30 minuti (script + lettura + verdict).

## Setup

- Provider: `anthropic`, modello `claude-sonnet-4-6`
- Reranker: MPS (topologia S1)
- `top_k=5`, `rerank_top_k=20`, `use_graph=False`
- `max_output_tokens=1000`
- 1 run per query, nessun warmup interno aggiuntivo
- Solo cloud (locale già caratterizzato in W5)

## Query selezionate (5)

| qid | regime | motivazione |
|---|---|---|
| Q6 | positive, retrieval pulito | controllo di sanità, già smoke W5 |
| Q1 | positive, gap locale/cloud noto | conferma che cloud risolve il caso peggiore W5 |
| Q9 | positive scenario C (dich. limite obbligatoria) | test trasparenza UX + anti-allucinazione 25-undecies |
| Q43 | positive con dich. limite "selettività", gold lungo | stress su risposta multi-cite e 1000 token |
| Q47 | negative (articolo inesistente) | test rifiuto vs allucinazione |

## Checklist sostantive (pre-compilate dal gold, prima del run)

Le checklist sono il **criterio di lettura** del campo "allineamento
contenuto". Sono derivate dal `gold_answer` di ciascuna query
isolando le claim sostantive (non lo stile, non i connettivi).

Il giudizio per-query è meccanico: `N/M check ✓`. Lo stile della
risposta (header markdown, tono discorsivo, lunghezza) **non conta**
ai fini del check, conta solo se la claim sostantiva è presente.

### Q6 — Compiti DPO

- [ ] informa/consiglia titolare e dipendenti sugli obblighi
- [ ] sorveglia osservanza GDPR + politiche interne (incl. sensibilizzazione/formazione)
- [ ] fornisce parere su DPIA e ne sorveglia svolgimento (art. 35)
- [ ] coopera con autorità di controllo, funge da punto di contatto
- [ ] riferimento art. 39 GDPR

### Q1 — Sistemi AI ad alto rischio (Allegato III)

- [ ] art. 6 par. 2 AI Act come fonte del meccanismo
- [ ] rinvio ad Allegato III come elenco operativo
- [ ] menziona almeno 2-3 settori dell'Allegato (istruzione, occupazione, accesso a servizi essenziali, law enforcement, biometria, infrastrutture critiche)
- [ ] art. 6 par. 3: eccezione "rischio non significativo" + condizioni
- [ ] NON confonde con art. 5 (pratiche vietate) e NON usa considerando come fonte dispositiva

### Q9 — Reati 231 trattamento illecito dati (scenario C)

- [ ] cita art. 24-bis D.Lgs 231/2001 come fonte
- [ ] menziona delitti informatici / trattamento illecito dati come categoria
- [ ] indica sanzioni 231 (pecuniarie e/o interdittive)
- [ ] **dichiara esplicitamente che il dettaglio degli articoli del codice penale richiamati non è incluso nel corpus normativo di riferimento**
- [ ] NON inventa contenuti dell'art. 25-undecies (anti-allucinazione)

### Q43 — (compilare la checklist Q43 da gold_answer Q43 prima del run)

NOTA OPERATIVA: questa checklist è in stato bozza nel disegno smoke.
Aprire `data/benchmark/gold_answers_v1.json` alla entry Q43, leggere
`gold_answer`, isolare 4-5 claim sostantive, sostituire questo
placeholder **prima** di eseguire lo script. Tipico:

- [ ] cita GDPR (Regolamento UE 2016/679) come fonte principale UE
- [ ] cita D.Lgs 196/2003 (Codice Privacy) come integrazione nazionale italiana
- [ ] indica oggetto del GDPR: protezione persone fisiche nel trattamento dei dati personali + libera circolazione dei dati
- [ ] menziona diritti/libertà fondamentali, in particolare diritto alla protezione dei dati personali
- [ ] dichiara selettività/limite del corpus E NON espone contenuto dispositivo specifico (basi giuridiche, diritti, sicurezza, DPIA, sanzioni) come se fosse supportato dai chunk recuperati

### Q47 — Articolo inesistente (negative)

- [ ] dichiara esplicitamente che l'articolo non esiste nel corpus
- [ ] NON inventa contenuto plausibile
- [ ] non finge di aver trovato il riferimento
- [ ] (opzionale, non conta nel totale) suggerisce articoli vicini realmente esistenti

## Cosa misura lo script (automatico)

Per ciascuna query:

1. **Retrieval**: top-5 `chunk_id` post-rerank; `recall@5` booleano (∃ chunk in top-5 ∩ `gold_chunks`)
2. **Citazioni strutturali**: `n_verified / n_total`, `all_verified` (output pipeline)
3. **Generazione**: `finish_reason`, token output, TTFT, throughput
4. **Dump testuale**: `annotated_answer` integrale + `gold_answer` integrale per lettura

## Cosa compila Federico a mano (post-run)

Per ciascuna query, sul file `SMOKE_GOLD_COMPARISON.md`:

1. **Checklist sostantiva**: spunta `[x]` ogni voce verificata nella risposta. Risultato finale `N/M`.
2. **Citazioni semantiche**: per max 4 cite della risposta, segna `OK | weak | wrong` (la cite punta a un chunk pertinente alla claim?).
3. **Allucinazioni semantiche**: claim presente in risposta ma NON supportata dai chunk recuperati. Sì/no + nota.
4. **Commento libero**: 1-2 righe.

## Criterio go/no-go

**GO su Ragas** se TUTTE:
- recall@5 hit su ≥3/5 query
- citation_verifier strutturale: `all_verified=True` su ≥4/5
- checklist sostantiva mediana ≥75% (es. 3/4 o 4/5)
- 0 allucinazioni semantiche evidenti
- dichiarazione di limite presente in ≥1/2 dei casi previsti (Q9, Q43)

**NO-GO** se UNA di:
- mediana checklist <60%
- ≥1 allucinazione semantica grave
- finish_reason=length su risposta gold-style (Q43) → alzare token prima di Ragas
- modello non produce mai dichiarazione di limite → rivedere system prompt prima di Ragas

Soglie indicative, da rivedere a vista dei risultati. Le soglie servono
a forzare un verdict scritto, non a sostituire il giudizio.

## Output atteso

`spike/SMOKE_GOLD_COMPARISON.md` con:

1. Header (data, setup, riferimento a questa spec)
2. Tabella riassuntiva 5 righe:
   `qid | recall@5 | n_verified/n_total | finish_reason | output_tokens | checklist N/M | dich. limite | allucinazione`
3. Sezione per query:
   - query
   - top-5 chunk recuperati (lista)
   - gold_chunks
   - `annotated_answer` (code block)
   - `gold_answer` (code block)
   - checklist (copiata dallo spec, da spuntare)
   - citazioni semantiche (placeholder)
   - allucinazioni semantiche (placeholder)
   - commento (placeholder)
4. Verdict finale: GO / NO-GO + 1 riga di motivazione

## Vincolo

Questa spec è scritta **prima** dell'esecuzione. Se a posteriori
emerge la tentazione di "aggiustare" una checklist per far quadrare
il risultato, lo si fa con una nuova voce in coda alla spec datata e
motivata, non riscrivendo le checklist a monte.