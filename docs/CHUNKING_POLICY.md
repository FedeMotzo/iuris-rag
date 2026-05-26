# Policy di Chunking — iuris-rag

**Versione**: 1.0 (2026-05-25)
**Riferimento codice canonico**: [`core/chunking/chunker.py`](../core/chunking/chunker.py)
**Stato**: policy implementata e in uso da W2/W3, documentata
retroattivamente in v0.5.2 post-analisi 2026-05-25
(vedi [`docs/INGESTION_FLOW_ANALYSIS_2026-05-25.md`](INGESTION_FLOW_ANALYSIS_2026-05-25.md)).

## Principio guida

Una norma viene spezzata in chunk per consentire retrieval mirato
conservando autosufficienza semantica. La policy bilancia 2 vincoli
in tensione:

- **Specificità rispetto alla query** (chunk non troppo grandi)
- **Autosufficienza semantica** (chunk non troppo piccoli o tagliati
  fuori dal contesto sistematico)

## Parametro centrale

**`CHUNK_TOKEN_THRESHOLD = 2000`** (token bge-m3)

Definito in [`core/chunking/chunker.py:16`](../core/chunking/chunker.py#L16).
È l'unico parametro globale della policy. Tutto il resto è branch
logica deterministica.

Motivazione: 2000 token corrispondono a ~6000-8000 caratteri per
testi giuridici italiani (rapporto char/token tipico). Sotto questa
soglia un chunk è gestibile dal LLM (`top_k=5` → context ~10000
token totali, ben dentro la finestra Sonnet 4.6 di 200k) **e**
retrievable con specificità ragionevole.

Token counter: tokenizer `BAAI/bge-m3` lru-cached in
[`core/chunking/_tokenizer.py`](../core/chunking/_tokenizer.py).
Non c'è threshold a `char` count separato.

## Decision tree

Dato un articolo estratto dal parser (AKN o EUR-Lex), branch
deterministico implementato identicamente in
[`core/chunking/_normattiva.py:96-152`](../core/chunking/_normattiva.py#L96-L152)
e [`core/chunking/_eurlex.py:100-157`](../core/chunking/_eurlex.py#L100-L157):

```text
if articolo.tokens <= 2000:
    → chunk monolitico
      chunk_id = {doc_urn}__{article_eid}
      chunk_type = "article"

elif articolo non ha commi numerati separabili
     (es. solo body monolitico, AKN senza paragraph, EUR-Lex fallback __body):
    → chunk monolitico oversize
      chunk_id = {doc_urn}__{article_eid}
      chunk_type = "article"
      metadata.oversize = true        # flag esplicito
      log INFO "Monoblock article ...: %d tokens, no commi to split"

elif articolo > 2000 token AND ha commi numerati:
    → split greedy bin-packing su commi
      chunk_id = {doc_urn}__{article_eid}__paras_{first}_{last}
      chunk_type = "article_group"
      metadata.{group_index, group_count, first_comma, last_comma}
```

**Greedy bin-packing** ([`core/chunking/chunker.py:61-83`](../core/chunking/chunker.py#L61-L83)):
aggiunge commi al chunk corrente finché non supera 2000 token, poi
apre un nuovo chunk. Non c'è bilanciamento o ottimizzazione globale
(no DP). Un singolo comma > 2000 token entra nel proprio gruppo
(chunk over-soglia accettato senza split intra-comma).

## Granularità di base

| Tipo | Unità di chunk | `chunk_type` |
|---|---|---|
| Articolo di legge ≤ 2000 token | Articolo intero | `article` |
| Articolo lungo con commi separabili | Gruppi di commi (`__paras_X_Y`) | `article_group` |
| Articolo lungo senza commi separabili | Articolo intero con flag `oversize` | `article` |
| Considerando UE | Considerando singolo | `recital` |
| Allegato III AI Act | Punto (8 chunk: `III__point_1` … `III__point_8`) | `annex` |
| Allegato monolitico (fallback altri allegati) | Allegato intero | `annex` |

`chunk_id` format dettagliato in
[`docs/INGESTION_FLOW_ANALYSIS_2026-05-25.md`](INGESTION_FLOW_ANALYSIS_2026-05-25.md)
§4.4.

## Eccezioni hard-coded esistenti

Tre punti di codice contengono eccezioni documentate. Sono **eccezioni
motivate**, non casi ad-hoc:

### 1. Allegato III AI Act — split per 8 macro-punti
- **File**: [`core/eur_lex_parser/parser.py:114-168`](../core/eur_lex_parser/parser.py#L114-L168)
- **Condizione hard-coded**: `if celex != "32024R1689": return []`
- **Motivazione**: Allegato III è una lista di 8 settori applicativi
  indipendenti (biometria, infrastrutture critiche, istruzione,
  occupazione, servizi essenziali, contrasto, migrazione/asilo,
  amministrazione giustizia). Chunking monolitico aggregherebbe
  sotto-temi senza affinità semantica. Lo split per punto risolve
  Q30 in W3 baseline (vedi `data/benchmark/BENCHMARK_W3.md` registro
  2026-05-19).
- **Granularità**: ferma al punto, **non** scende a lettera.
  Decisione: il punto è l'unità tematica autosufficiente
  (analogamente a `chunk_recitals`).

### 2. Fallback `__body` per EUR-Lex — articoli senza commi numerati
- **File**: [`core/chunking/_eurlex.py:128-131`](../core/chunking/_eurlex.py#L128-L131)
- **Logica**: se l'articolo EUR-Lex ha 1 solo "comma" con `number=None`
  (parser ha fatto fallback su `<p class="oj-normal">` libero o
  tabelle), il chunk è tenuto monolitico anche se oversize.
- **Motivazione**: gestisce template iniziale AI Act (`art_113`
  e simili senza struttura comma numerata `1./2./3.`). Risolve Q15
  in W4 (vedi PROJECT_CONTEXT.md registro 2026-05-19).

### 3. D.Lgs 231/2001 Capo+Sezione — carry-over gerarchia
- **File**: [`core/chunking/_normattiva.py:48-86`](../core/chunking/_normattiva.py#L48-L86)
- **Logica**: ricostruzione gerarchia per markup AKN misto (Capo e
  Sezione come `<chapter>` siblings invece di nesting; un
  `num="SEZIONE II"` che segue `num="Capo I"` è in realtà
  sotto-sezione di Capo I).
- **NON è eccezione di chunking**: è parser hardening su quirks
  specifici di Normattiva su 231/2001. Documentato come quirk noto.

## Quando aggiungere nuove eccezioni

Una nuova eccezione hard-coded è giustificata **solo se**:

1. **La norma sorgente ha struttura non-articolare** che il decision
   tree generico non gestisce bene (esempio: nuovo Allegato con
   sotto-strutture diverse dai punti)
2. **Il chunking deterministico produce chunk che falliscono
   retrieval/generation** su una query specifica del benchmark
   (esempio: Q30 ha motivato split Allegato III)
3. **Il fix architetturale generico non è proporzionato** al caso
   specifico (preferire eccezione hard-coded documentata vs refactor
   della policy)

Le eccezioni devono essere documentate con:
- Commento inline che cita il caso motivante (qid benchmark o
  descrizione)
- Aggiornamento di questa policy
- Test fixture nei test di chunking ([`tests/chunking/`](../tests/chunking/))

## Quando NON serve eccezione

- **Articoli lunghi ma tematicamente unitari** (es. AI Act art_3
  Definizioni, 18410 char): restano monolitici per costruzione,
  non perdono qualità retrieval (diagnostica 2026-05-25 conferma —
  correlazione `n_chunks_grandi vs metriche RAGAS` ≈ 0).
- **Articoli con commi numerati tradizionali**: il decision tree
  threshold-token li gestisce automaticamente (no intervento manuale
  necessario).

## Sanity post-ingestion

Dopo ogni re-ingestion di una norma, eseguire:

```bash
spike/.venv/bin/python scripts/sanity_check_corpus.py
```

Verifica 4 invarianti:
1. Tutti i `gold_chunks` del benchmark v3 esistono in Qdrant
2. Conteggio totale chunk = aspettativa baseline (865 post-W4)
3. Conteggio chunk per `doc_urn` vs distribuzione attesa
4. Validità formato `chunk_id` (regex canonica)

Vedi [§6 di INGESTION_FLOW_ANALYSIS_2026-05-25.md](INGESTION_FLOW_ANALYSIS_2026-05-25.md#6-sanity-check-attuali)
per il contesto sui sanity check pre-esistenti vs quelli aggiunti
da questo script.

## Limiti noti

- **Q55/Q83 (NIS2 sanzioni)**: il chunk `__art_38__paras_1_11` è
  coerente con la policy ma viene degradato dal CrossEncoder
  `bge-reranker-v2-m3` (rank 1 pre-rerank → rank 11/16 post-rerank).
  Problema **reranker-side**, non chunking. Decisione 2026-05-25:
  deferred a SPIKE separato. Vedi [`ROADMAP_POST_V1.md`](../ROADMAP_POST_V1.md)
  sezione "Policy chunking — gap di coerenza (v0.7 planning)" +
  aggiornamento 2026-05-25.
- **Cross-norma vocabolari disgiunti (Q5, Q9, Q25, Q68-Q72)**:
  problema query-side (gap semantico tra phrasing utente e
  terminologia legale). **Non è chunking**. Roadmap v1.1
  (HyDE / query rewriting / decomposition LLM-assisted).

## Riferimenti

- [`core/chunking/chunker.py`](../core/chunking/chunker.py) — decision tree, threshold, dispatcher
- [`core/chunking/_normattiva.py`](../core/chunking/_normattiva.py) — chunking AKN-specific (Normattiva)
- [`core/chunking/_eurlex.py`](../core/chunking/_eurlex.py) — chunking EUR-Lex-specific (articoli + recital + annex)
- [`core/chunking/_tokenizer.py`](../core/chunking/_tokenizer.py) — token counter bge-m3
- [`core/eur_lex_parser/parser.py`](../core/eur_lex_parser/parser.py) — `parse_annex_iii_aiact` (eccezione 1)
- [`docs/INGESTION_FLOW_ANALYSIS_2026-05-25.md`](INGESTION_FLOW_ANALYSIS_2026-05-25.md) — analisi tecnica completa del flusso ingestion
- [`PROJECT_CONTEXT.md`](../PROJECT_CONTEXT.md) — registro decisioni storiche
- [`ROADMAP_POST_V1.md`](../ROADMAP_POST_V1.md) — SPIKE chunking v0.7 planning
