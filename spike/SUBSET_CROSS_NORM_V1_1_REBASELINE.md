# Subset cross-norma v1.1 — RE-BASELINE (max_tokens=4000, no boost)

**Data (UTC)**: 2026-05-27T11:38:34.366162+00:00
**Judge cost (A+B condiviso)**: ≈$4.088
**Config A**: enable_cross_norm=True, boost OFF, max_tokens=4000, reranker MPS, gen+judge Sonnet 4.6.

Baseline corretto post-fix troncamento (sostituisce SUBSET_CROSS_NORM_V1_1_RESULTS.md che era a max_tokens=1000).

## target

| qid | type | path | rescue | faith | ar |
|---|---|---|---|---|---|
| Q9 | positive | cross-norm | 1/1 (1.00) | 0.960 | 0.853 |
| Q25 | positive | fallback | 1/2 (0.50) | 0.737 | 0.000 |
| Q68 | positive | cross-norm | 3/5 (0.60) | 0.412 | 0.903 |
| Q69 | positive | cross-norm | 4/5 (0.80) | 0.412 | 0.907 |
| Q70 | positive | cross-norm | 4/5 (0.80) | 0.349 | 0.726 |
| Q71 | positive | cross-norm | 3/5 (0.60) | 0.731 | 0.859 |

## mainstream

| qid | type | path | rescue | faith | ar |
|---|---|---|---|---|---|
| Q6 | positive | fallback | 3/3 (1.00) | 1.000 | 0.786 |
| Q7 | positive | fallback | 3/3 (1.00) | 0.905 | 0.866 |
| Q63 | positive | fallback | 1/1 (1.00) | 0.862 | 0.987 |

## mono-stress

| qid | type | path | rescue | faith | ar |
|---|---|---|---|---|---|
| Q34 | positive | fallback | 1/1 (1.00) | 0.964 | 0.817 |
| Q35 | positive | fallback | 1/1 (1.00) | 1.000 | 0.745 |
| Q38 | positive | fallback | 1/1 (1.00) | 1.000 | 0.841 |

## gold-recital

| qid | type | path | rescue | faith | ar |
|---|---|---|---|---|---|
| Q1 | positive | fallback | 2/4 (0.50) | 0.889 | 0.956 |
| Q3 | positive | cross-norm | 4/4 (1.00) | 0.684 | 0.882 |
| Q8 | positive | fallback | 2/2 (1.00) | 1.000 | 0.778 |
| Q29 | positive | fallback | 1/1 (1.00) | 1.000 | 0.687 |

## Mediane per gruppo

| gruppo | n | rescue med | faith med | ar med |
|---|---|---|---|---|
| target | 6 | 0.700 | 0.571 | 0.856 |
| mainstream | 3 | 1.000 | 0.905 | 0.866 |
| mono-stress | 3 | 1.000 | 1.000 | 0.817 |
| gold-recital | 4 | 1.000 | 0.944 | 0.830 |

