# BENCHMARK W3 v2 — pipeline outputs su gold_answers_v2.json

**Start (UTC):** 2026-05-24T13:13:38.219806+00:00
**End (UTC):** 2026-05-24T13:19:54.361766+00:00
**Provider:** anthropic · model: `claude-sonnet-4-6`
**Pipeline params:** top_k=5, rerank_top_k=20, use_graph=False, max_output_tokens=1000.
**Reranker device:** MPS (topologia S1). Collection: `italian_legal_v1_hybrid`.

## 1. Sintesi globale (100 query)

| metrica | mediana |
|---|---:|
| R@5 (su query con gold)  | 0.100 |
| R@10 (su query con gold) | 0.200 |
| R@20 (su query con gold) | 0.750 |
| MRR (su query con gold)  | 0.181 |
| n query con R@10=1.0     | 7 |
| n query con R@10=0.0     | 8 |

## 2. Per query_type

| type | n | R@5 | R@10 | R@20 | MRR | n R@10=1 | n R@10=0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| positive | 18 | 0.100 | 0.200 | 0.750 | 0.181 | 7 | 8 |
| negative+edge | 2 | — | — | — | — | — | — |

- Negative+edge con pattern canonico 'corpus_limit' nella answer: **0 / 2** → []
- Negative+edge con risposta sostantiva (>200 char, no pattern): **2** → ['Q94', 'Q96']

## 3. Per cluster v2 (Q51-Q100)

Aggregati per use_case (proxy del cluster). Soglia outlier: R@10 mediana < globale - 0.20.

| use_case | n | R@10 med | MRR med |
|---|---:|---:|---:|
| 231 sicurezza lavoro omicidio colposo | 1 | 1.000 | 1.000 |
| Banca outsourcing IA AML extra-UE | 1 | 0.200 | 0.250 |
| NIS2 sanzioni soggetti essenziali | 1 | 0.000 | 0.091 |
| NIS2 sanzioni soggetti importanti | 1 | 0.000 | 0.062 |
| PA regionale IA graduatorie sociali | 1 | 0.000 | 0.083 |
| Pharma IA farmacovigilanza | 1 | 0.000 | 0.000 |
| Procedura DPIA passi e contenuti | 1 | 1.000 | 1.000 |
| Sanità chatbot AI triage paziente | 1 | 0.200 | 0.500 |
| Trattamento dati forze di polizia | 1 | 1.000 | 0.500 |

## 4. Per norma toccata

| norma | n query | R@10 med |
|---|---:|---:|
| AI Act | 7 | 0.200 |
| Codice Privacy | 2 | 0.500 |
| D.Lgs 231/2001 | 5 | 0.200 |
| GDPR | 8 | 0.200 |
| L. 132/2025 | 2 | 0.100 |
| NIS2 | 5 | 0.000 |

## 5. Confronto v1 (Q1-Q50) vs v2 (Q51-Q100)

| metrica | v1 (n positive) | v2 (n positive) | cumulato |
|---|---:|---:|---:|
| R@5 med | 0.000 (9) | 0.200 (9) | 0.100 |
| R@10 med | 0.500 | 0.200 | 0.200 |
| R@20 med | 0.500 | 1.000 | 0.750 |
| MRR med | 0.111 | 0.250 | 0.181 |

Nota drift: confronto vs `BENCHMARK_W3.md` (W7-prep) per pipeline drift. Se R@10 v1 attuale differisce >0.05 da W3-prep → indagare.

## 6. Paired queries intenzionali

| Tema | qid coppia | R@10 entrambi | answer differente? |
|---|---|---|---|
| art_38__paras_1_11 NIS2 sanzioni | Q55,Q83 | 0.00 / 0.00 | sì |
| NIS2 art_25 notifica | Q54,Q57 | n/a (qid non in run) | n/a |
| L.132 art_9 trattamento dati | Q64,Q67 | n/a (qid non in run) | n/a |

## 7. Runtime corpus_limit observed (post-eval)

Query positive con `has_corpus_limit_declaration=false` ma pattern canonico presente nella answer: **0 / 18**


Drift lessicale (has_corpus_limit_declaration=true ma pattern canonico non rilevato): **9**
Lista qid:
- `Q9` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q13` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q15` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q25` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q43` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q49` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q63` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q87` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q88` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex

**Decisione**: pattern documentato qui, dataset `gold_answers_v2.json` non aggiornato. Eventuale fix runtime_corpus_limit_observed in v1.1.

