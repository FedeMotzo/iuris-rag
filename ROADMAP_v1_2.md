# ROADMAP v1.2 — Cross-norma retrieval

Stato a chiusura v1.1 (branch `feat/cross-norm-v1-1`, 2026-05-27).

---

## 1. Cosa v1.1 ha consegnato

- **Trigger lessicale ≥2 norme** — `core/cross_norm/multi_norm_trigger.py`.
  Deterministico (regex sulle 6 norme del corpus: GDPR, AI Act, D.Lgs
  231/2001, NIS2, Codice Privacy, L. 132/2025). Zero LLM nel trigger.
- **Decomposition LLM-assisted** — `core/cross_norm/subquery_generator.py`.
  Sub-query per norma generata da Sonnet 4.6 con vocabolario norma iniettato
  da `norm_glossary.yaml`. Prompt template V2 con clausola di nominazione
  esplicita degli istituti (FRIA, DPIA, numeri di articolo, Allegato III).
- **Retrieval per-norma + filter Qdrant + RRF fusion** —
  `core/cross_norm/retriever.py` (`CrossNormRetriever`). Per ogni norma:
  retrieval hybrid filtrato per `doc_urn`; più un retrieval globale sulla
  query originale; fusione RRF (rrf_k=60, source pesate uguali). Fallback
  deterministico su hybrid standard se il trigger rileva <2 norme.
- **Integrazione pipeline opt-in** — `RAGPipeline(enable_cross_norm=False)`
  + env var `RAG_ENABLE_CROSS_NORM`. Default OFF: zero impatto su utenti
  esistenti e su query mono-norma.
- **Fix max_tokens generation 1000→4000** — artefatto di troncamento delle
  risposte multi-norma eliminato. A 1000 token le risposte cross-norma a
  3-4 norme troncavano mid-sezione (Q69 `finish_reason=length` all'inizio
  della sezione NIS2, mai sviluppata); a 4000 completano. Vedi sotto
  "diagnosi+fix Q69".
- **Sentinelle non-regressione** — su subset misurato: zero falsi positivi
  trigger (tutte le sentinelle mainstream e corpus_limit → path fallback),
  faith/ar mainstream invariati o migliori. Test integrazione cross-norm
  tutti verdi (`tests/cross_norm/`).

### Diagnosi + fix troncamento Q69 (consegnato in v1.1)

Diagnosticato in `spike/PRE_BOOST_PRECHECK.md` (step 0.B): a max_tokens=1000
Q69 tronca a `finish_reason=length` prima di sviluppare la sezione NIS2 (3ª
norma); a 6000 completa in ~1955 token. Fix: default produzione 1000→4000
(commit `fix(generation): max_tokens default 1000→4000`). Re-baseline del
subset a 4000 in `spike/SUBSET_CROSS_NORM_V1_1_REBASELINE.md`.

Nota empirica rilevante dal re-baseline (1000→4000, 6 target): il
troncamento in alcuni casi *mascherava* faithfulness bassa, non la
deprimeva. Es. Q70 faith 0.750→0.349: la risposta troncata a 1000 si
fermava prima del contenuto meno fedele, gonfiando artificialmente il
faith. Il numero a 4000 è quello reale.

---

## 2. Limiti noti v1.1 (dichiarati esplicitamente)

- **Chunk definitori meta-giuridici non recuperati da query scenario-based.**
  Caso paradigmatico: `art_6 AI Act` ("Regole di classificazione dei
  sistemi ad alto rischio") ASSENTE in Q68/Q69/Q70/Q71 nonostante
  decomposition + filter per-norma. La rubrica definitoria non si aggancia
  lessicalmente a sub-query orientate-obblighi (ASSENTE anche in filtered
  top-15). Stesso fenomeno per `annex_III__point_5` (Q71).
- **Variabilità Sonnet sulla nominazione della rubrica dell'articolo.**
  Stesso prompt template, output diversi: `art_9 GDPR` a rank 14 in Q68
  (sub-query usa "dati sanitari") vs rank 5 in Q69 (sub-query nomina
  "categorie particolari di dati personali", la rubrica ufficiale). Il
  reranker premia il match con la rubrica; la sub-query non la nomina in
  modo affidabile.
- **Query mono-norma con gold definitorio non rescued da decomposition.**
  Es. `Q25 art_24-bis 231`: il trigger non scatta (1 sola norma rilevata),
  quindi nessuna decomposition. Il gap è intra-norma (recupero art_24-bis),
  non cross-norma — fuori dal raggio d'azione della pipeline v1.1.
- **Boost type-aware article>recital: testato e NON promosso in v1.1.**
  Misurazione A/B (`spike/BOOST_ARTICLE_RESULTS.md`, coefficiente 1.15/0.85):
  1/4 criteri pre-dichiarati passati. C1 target rescue +0.05 FAIL (Δ mediana
  0.000; migliora solo Q70 +0.20 rescue / +0.227 faith ma la mediana non si
  muove), C3 mono-stress FAIL (Q34 -0.061, Q35 -0.053 faith), C4 gold-recital
  FAIL (Q1 -0.056 faith). Effetto misto: aiuta alcune cross-norma ma degrada
  query mono-norma high-faith e gold-recital. Rimandato a v1.2 con tuning del
  coefficiente. Codice scartato da core (no orphan code); esperimento
  documentato in `spike/`.
- **Test gold-recital su benchmark v3 limitato.** 7 query con ≥1 gold recital
  (Q1, Q3, Q7, Q8, Q29, Q37, Q88); 4 usate nel subset boost. Campione
  sotto-popolato per conclusioni robuste sull'effetto recital.

---

## 3. v1.2 scope dichiarato

- **Graph expansion del pool retrieval pre-rerank.** Usare
  `core/normative_graph` (22 link cross-norma curati a mano in v1.0,
  attualmente integrazione opzionale post-rerank "bonus context") per
  espandere il pool di candidati *prima* del rerank. Obiettivo: raggiungere
  chunk definitori (art_6 AI Act) via link normativi quando una sub-query li
  cita, anche se il retrieval lessicale non li aggancia.
- **Boost type-aware article>recital con tuning del coefficiente.**
  Ripartire dalla misurazione A/B v1.1 (1.15/0.85 non promosso). Esplorare
  coefficienti meno aggressivi e/o boost condizionato al tipo di query, per
  non degradare mono-norma e gold-recital. Reintrodurre il codice
  (`classify_chunk_type` + boost in `_rerank`) solo se un nuovo A/B passa i
  criteri.
- **Sub-query rubrica-aware.** Mitigare la variabilità Sonnet (limite v1.1):
  istruire la decomposition a nominare la *rubrica ufficiale* dell'articolo
  bersaglio quando lo scenario la attiva (es. "categorie particolari di dati
  personali" non "dati sanitari"). Validare su Q68 (art_9 da rank 14 → ≤5).

---

## 4. Fuori scope v1.2 (rimandate a v1.3+)

- **Norm router LLM per norme implicite.** Query che non menzionano
  esplicitamente una norma ma la attivano semanticamente (il trigger
  lessicale v1.1 non scatta: es. Q6/Q7 → 0 norme). Richiede un router
  LLM-based, fuori dal design deterministico v1.1/v1.2.
- **HyDE per query intra-norma con vocabolari disgiunti.** Es. Q9 con corpus
  codice penale: il gap è di vocabolario tra query e corpus, non cross-norma.
- **Estensione corpus codice penale** (articoli c.p. richiamati come reati
  presupposto 231). Caso Q25/Q9: gli articoli c.p. non sono nel corpus v1.
- **Multi-stage retrieval (anchor + cross-references).** Recupero a due
  stadi: ancora sull'articolo principale, poi espansione sui riferimenti
  incrociati interni al testo normativo.

---

## Artefatti di misurazione (riferimento)

- `spike/PRE_BOOST_PRECHECK.md` — step 0 (gold-recital count, Q69 truncation, stress queries)
- `spike/SUBSET_CROSS_NORM_V1_1_RESULTS.md` — subset 12-query @ max_tokens=1000 (superato)
- `spike/SUBSET_CROSS_NORM_V1_1_REBASELINE.md` — re-baseline @ max_tokens=4000 (config A)
- `spike/BOOST_ARTICLE_RESULTS.md` — A/B boost + verdetto + re-baseline impact
- `data/benchmark/ragas_pipeline_outputs_boost_ab.json` — output intermedio A+B
