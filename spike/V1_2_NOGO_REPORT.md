# v1.2 — NO-GO da smoke test (subset paid NON eseguito)

**Branch**: `feat/cross-norm-v1-2`
**Data**: 2026-05-27
**Costo speso**: $0.08 (cassette V3 regen, 16 chiamate Sonnet 4.6).
**Costo evitato**: ~$1.50 (subset paid) + ~$0.0 di rischio implementazione su main.
**Status**: implementazione codice + cassette + unit test completati. Subset
end-to-end NON eseguito su decisione del committente dopo smoke test conclusivo.

## Cosa è stato implementato (come da brief)

### A — Prompt mono-concetto ([core/cross_norm/subquery_generator.py](../core/cross_norm/subquery_generator.py))

- Nuovo `PROMPT_TEMPLATE` che istruisce il decomposer a emettere una lista
  JSON di sub-query mono-concetto (1 per concetto saliente).
- `generate_subquery()` return type cambia da `str` a `list[str]`.
- Parser robusto (`_parse_subquery_list`): JSON puro → fallback a regex su
  stringhe quoted → fallback a split per linee. Resiste a code fences
  sbilanciati (Sonnet a volte wrappa in ```json ... senza closing).
- `max_tokens` default 200 → 400.

### B — `CrossNormRetriever` ([core/cross_norm/retriever.py](../core/cross_norm/retriever.py))

- Iterazione per ogni sub-query mono-concetto della norma N: una chiamata
  `hybrid.retrieve(sub_q, doc_urn=N)` per sub-query.
- Dedup per chunk_id mantenendo `max` del logit reranker (rerank contro la
  sub-query che lo ha recuperato; per chunk in più sub-query si tiene il
  max).
- Trace estesa: `trace["sub_queries"][norm_id]` è `list[str]` (era `str`);
  `trace["per_subquery_hits"][(norm_id, sq_idx)]` traccia ogni sub-query.

### C — Fusion score-aware ([core/cross_norm/retriever.py](../core/cross_norm/retriever.py))

- Sostituzione completa di RRF cross-source con score-aware:
  `score_final = sigmoid(max_logit)`, dedup per chunk_id, ordinamento
  decrescente, top-K. Niente normalizzazione per-source, niente pesi (come
  da brief).
- Source `global`: invariata, rerank contro query originale.
- `rrf_k` mantenuto come parametro validato per back-compat costruttore
  (unused).

### Cassette V3 ([tests/cross_norm/cassettes/subquery_responses.json](../tests/cross_norm/cassettes/subquery_responses.json))

Rigenerate Q9/Q68/Q69/Q70/Q71 (Q25 esclusa: fallback path, no sub-query).
16 chiamate Sonnet 4.6 a max_tokens=400. Costo: ~$0.08.

Tipiche cardinalità: 6-9 sub-query per (qid, norma). Esempio q68:gdpr (8
sub-query mono-concetto, ognuna ~25 parole):

```
[0] Quali obblighi prevede il GDPR per il trattamento di dati sanitari
    come categorie particolari di dati personali in ambito ospedaliero?
[1] Quando un sistema di triage automatizzato costituisce processo
    decisionale automatizzato ai sensi dell'art. 22 GDPR?
[2] In quali casi il trattamento tramite chatbot AI in ambito sanitario
    richiede una valutazione d'impatto sulla protezione dei dati (DPIA)?
... [+5]
```

### Unit test

`tests/cross_norm/`: 17 test passano (55 incluso `test_multi_norm_trigger`).
Aggiornati `conftest.py` (cassette V3 list[str] → JSON via stub),
`test_subquery_generator.py` (assert list[str], marker su qualunque sub-query),
`test_retriever.py` (call count = Σ sub-q + 1 global; score-aware fusion =
sigmoid(max_logit), non più RRF formula).

---

## Smoke test conclusivo — Q68 con cassette V3 + reranker reale

Pipeline end-to-end (Qdrant + bge-m3 + bge-reranker-v2-m3 su MPS, cassette
LLM zero-cost). Risultato:

```
FUSED TOP-20 (Q68): 19 chunk AI Act + 1 L.132. ZERO GDPR.
Gold recuperati in top-20: 0/5
Gold in top-5 (generation context): 0/5
```

### Causa radice: cross-source heterogeneity senza normalizzazione

Ogni gold è **trovato** dalla pipeline a logit decente, ma viene
**sopraffatto** in fusion da chunk AI Act saturati:

| gold | source migliore | logit max | rank fusion stimato |
|------|-----------------|:---------:|:-------------------:|
| AI Act `art_6` | filtered:ai_act sub-q #0 (classificazione alto rischio) | 0.950 | ~25 |
| AI Act `art_27` | filtered:ai_act sub-q #5 (trasparenza fornitore→deployer) | 0.917 | ~28 |
| GDPR `art_35` | filtered:gdpr sub-q #2 (DPIA) | 0.908 | ~30 |
| L.132 `art_7` | filtered:l_132 sub-q #0 (decisioni cliniche) | 0.967 | ~21 |
| GDPR `art_9` | filtered:gdpr sub-q #0 (categorie particolari) | 0.373 | ~50+ |

Fused top-20 occupato da chunk AI Act a logit 0.994-0.999: 9 sub-query
ai_act × top-1 saturato ≈ 1.0 + top-2/3 anch'essi >0.99 = **>20 chunk AI
Act sopra ogni gold non-AI-Act**.

**Spread per-source dei top-1**:
- ai_act sub-q tops: media ~0.999 (saturazione lessicale alta)
- gdpr sub-q tops: media ~0.91 (semantica concettuale, meno match lessicale)
- l_132 sub-q tops: media ~0.97 (con eccezione di una a 0.42)

La RRF v1.1 funzionava perché era **rank-based**: ogni norma garantita
contribuire un numero di slot indipendente dalla scala assoluta del suo
reranker. La fusion score-aware del brief, **senza normalizzazione**, fa
vincere la norma con la calibrazione più alta dell'intero corpus,
indipendentemente dalla rilevanza al singolo concetto.

### La diagnosi anticipata dal brief

Il brief (sezione "Log distribuzioni score per-source") prevedeva
esattamente questo esito come segnale NO-GO:

> *"se rimane spread → under-fragmentation: il decomposer sta ancora
> ri-bundlando concetti, una sola sub-query per N istituti. Indica che il
> prompt V3 va ulteriormente affilato."*

Lo smoke conferma lo spread ma chiarisce che NON è under-fragmentation del
decomposer (le sub-query sono già mono-concetto granulari, 6-9 per norma).
Lo spread è **proprietà del corpus + reranker**: AI Act chunks contengono
fraseologia lessicalmente più sovrapposta alle sub-query AI Act-style
("sistema di IA ad alto rischio", "fornitore", "deployer") di quanto i
chunk GDPR matchino le sub-query GDPR-style ("trattamento di categorie
particolari", "DPIA"). Sharpening del prompt non risolve.

## Verdetto

**NO-GO sul disegno specificato.** La causa è strutturale, non realizzativa:

- Codice e cassette sono corretti rispetto al brief (unit test verdi,
  smoke trace consistente con il design).
- Il design **vince come specificato** ma il risultato end-to-end è
  catastrofico su query 3+ norme (Q68 0/5; Q69/Q70/Q71 analoghe per
  costruzione).
- v1.1 rescue Q68 era 3/5 (`art_27`, `art_35`, `art_7` nei top-20). Lo
  smoke v1.2 li perde tutti. Regressione netta.

Lo spread per-source rilevato dal brief stesso era una soglia NO-GO; è
soddisfatta dallo smoke su un singolo target, sufficiente per fermarsi.

## Cosa **NON** mergeare in main

Il branch `feat/cross-norm-v1-2` contiene il codice. **NON merge** finché
la fusion non è revisionata. Opzioni residue (FUORI scope di questo round):

1. **Aggiungere normalizzazione per-source** (es. z-score sui logit dei
   top-K per source prima della fusion). Va contro il brief letterale ma
   risolve la dominanza di calibrazione.
2. **Tornare a rank-based con score-aware tie-break** (RRF + bonus per
   alto score singolo): preserva diversità per norma E premia segnale forte.
3. **Quote per-source nel top-K finale** (es. min 4 chunk per source nei
   top-20): forza diversità di provenienza, semplice da implementare.

Nessuna di queste è gratis e ognuna merita un brief dedicato con
pre-misurazione (come Verifica 8 ha fatto per le 4 varianti, con il
caveat che lì il pool era pre-cassette V2 — andrebbe rifatto con V3).

## Costo finale del round

- Cassette regen: $0.08 (paid, sul budget brief di $0.05).
- Smoke test: $0 (cassette + locale).
- Subset paid: **$0 (NON eseguito)**, decisione esplicita.
- Totale round: $0.08 vs budget $1.55. Risparmiati $1.47.

## File prodotti

- [core/cross_norm/subquery_generator.py](../core/cross_norm/subquery_generator.py) (modificato — su branch, non in main)
- [core/cross_norm/retriever.py](../core/cross_norm/retriever.py) (modificato — su branch, non in main)
- [tests/cross_norm/cassettes/subquery_responses.json](../tests/cross_norm/cassettes/subquery_responses.json) (V3)
- [tests/cross_norm/conftest.py](../tests/cross_norm/conftest.py), [test_subquery_generator.py](../tests/cross_norm/test_subquery_generator.py), [test_retriever.py](../tests/cross_norm/test_retriever.py) (aggiornati)
- [spike/regen_cassettes_v3.py](regen_cassettes_v3.py), [cleanup_cassettes_v3.py](cleanup_cassettes_v3.py), [smoke_cross_norm_v1_2.py](smoke_cross_norm_v1_2.py), [debug_smoke_v1_2.py](debug_smoke_v1_2.py)
- Questo report.
