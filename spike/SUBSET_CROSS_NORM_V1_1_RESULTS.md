# Subset cross-norma v1.1 — misurazione end-to-end

**Data (UTC)**: 2026-05-27T09:18:25.917885+00:00
**Judge cost**: ≈$0.968 (36 judge calls)
**Config**: enable_cross_norm=True, reranker MPS attivo, gen Sonnet 4.6 top_k=5, judge Sonnet 4.6, sub-query cassette V2 (Q68/Q69) + live.

## Verifica trigger (sentinelle + corpus_limit)

| qid | gruppo | detect_norms | path | atteso |
|---|---|---|---|---|
| Q6 | sentinella | [] | fallback | ✓ fallback |
| Q7 | sentinella | [] | fallback | ✓ fallback |
| Q63 | sentinella | ['codice_privacy'] | fallback | ✓ fallback |
| Q87 | sentinella | ['dlgs_231'] | fallback | ✓ fallback |
| Q43 | corpus_limit | [] | fallback | ✓ fallback |
| Q94 | corpus_limit | [] | fallback | ✓ fallback |

**Zero falsi positivi**: tutte le sentinelle e corpus_limit → path fallback.

## Target cross-norma (6)

| qid | type | detect_norms | path | rescue | faith | ar |
|---|---|---|---|---|---|---|
| Q9 | positive | dlgs_231,codice_privacy | cross-norm | 1/1 (1.00) | 1.000 | 0.824 |
| Q25 | positive | dlgs_231 | fallback | 1/2 (0.50) | 0.700 | 0.000 |
| Q68 | positive | gdpr,ai_act,l_132_2025 | cross-norm | 3/5 (0.60) | 0.400 | 0.898 |
| Q69 | positive | gdpr,ai_act,nis2 | cross-norm | 4/5 (0.80) | 0.450 | 0.900 |
| Q70 | positive | gdpr,ai_act,dlgs_231,nis2 | cross-norm | 3/5 (0.60) | 0.750 | 0.710 |
| Q71 | positive | gdpr,ai_act,nis2,l_132_2025 | cross-norm | 4/5 (0.80) | 0.714 | 0.761 |

## Sentinelle mainstream (4)

| qid | type | detect_norms | path | rescue | faith | ar |
|---|---|---|---|---|---|---|
| Q6 | positive | — | fallback | 3/3 (1.00) | 1.000 | 0.786 |
| Q7 | positive | — | fallback | 3/3 (1.00) | 0.920 | 0.866 |
| Q63 | positive | codice_privacy | fallback | 1/1 (1.00) | 1.000 | 0.987 |
| Q87 | positive | dlgs_231 | fallback | 1/1 (1.00) | 1.000 | 0.936 |

## Corpus_limit (2)

| qid | type | detect_norms | path | rescue | faith | ar |
|---|---|---|---|---|---|---|
| Q43 | positive | — | fallback | 1/2 (0.50) | 0.773 | 0.000 |
| Q94 | negative | — | fallback | n/a | 0.900 | 0.000 |

## Gold mancanti in top-20 (target cross-norma)

- **Q9**: nessuno (rescue completo)
- **Q25**: ['akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis']
- **Q68**: ['eli/reg/2016/679/oj__art_9', 'eli/reg/2024/1689/oj__art_6']
- **Q69**: ['eli/reg/2024/1689/oj__art_6']
- **Q70**: ['akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies', 'eli/reg/2016/679/oj__art_44']
- **Q71**: ['eli/reg/2024/1689/oj__annex_III__point_5']

## Tabella sintetica

| gruppo | n | rescue med | faith med | ar med |
|---|---|---|---|---|
| target cross-norma | 6 | 0.700 | 0.707 | 0.792 |
| sentinelle | 4 | 1.000 | 1.000 | 0.901 |
| corpus_limit | 2 | 0.500 | 0.836 | 0.000 |

_Non-regressione: confronta sentinelle/corpus_limit vs F.2 v3 archived (data/benchmark/ragas_aggregates_v2.json / BENCHMARK_RAGAS_W7_v2.md)._

## Note di lettura

_(da compilare manualmente)_

