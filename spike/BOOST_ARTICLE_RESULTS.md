# Boost article>recital — risultati A vs B

**Data (UTC)**: 2026-05-27T11:38:34.369351+00:00
**Judge cost (A+B)**: ≈$4.088
**A**: boost OFF · **B**: boost ON (article×1.15, recital×0.85) · max_tokens=4000, cross-norm ON, reranker MPS.

## target — Δ(B−A)

| qid | path | rescueA | rescueB | Δrescue | faithA | faithB | Δfaith | arA | arB | Δar |
|---|---|---|---|---|---|---|---|---|---|---|
| Q9 | cross-norm | 1.000 | 1.000 | +0.00 | 0.960 | 0.480 | -0.480 | 0.853 | 0.857 | +0.005 |
| Q25 | fallback | 0.500 | 0.500 | +0.00 | 0.737 | 0.526 | -0.211 | 0.000 | 0.000 | +0.000 |
| Q68 | cross-norm | 0.600 | 0.600 | +0.00 | 0.412 | 0.622 | +0.210 | 0.903 | 0.903 | +0.000 |
| Q69 | cross-norm | 0.800 | 0.800 | +0.00 | 0.412 | 0.500 | +0.088 | 0.907 | 0.892 | -0.015 |
| Q70 | cross-norm | 0.800 | 1.000 | +0.20 | 0.349 | 0.576 | +0.227 | 0.726 | 0.804 | +0.078 |
| Q71 | cross-norm | 0.600 | 0.600 | +0.00 | 0.731 | 0.613 | -0.118 | 0.859 | 0.848 | -0.011 |

## mainstream — Δ(B−A)

| qid | path | rescueA | rescueB | Δrescue | faithA | faithB | Δfaith | arA | arB | Δar |
|---|---|---|---|---|---|---|---|---|---|---|
| Q6 | fallback | 1.000 | 1.000 | +0.00 | 1.000 | 1.000 | +0.000 | 0.786 | 0.721 | -0.065 |
| Q7 | fallback | 1.000 | 1.000 | +0.00 | 0.905 | 0.952 | +0.048 | 0.866 | 0.824 | -0.042 |
| Q63 | fallback | 1.000 | 1.000 | +0.00 | 0.862 | 1.000 | +0.138 | 0.987 | 0.987 | +0.000 |

## mono-stress — Δ(B−A)

| qid | path | rescueA | rescueB | Δrescue | faithA | faithB | Δfaith | arA | arB | Δar |
|---|---|---|---|---|---|---|---|---|---|---|
| Q34 | fallback | 1.000 | 1.000 | +0.00 | 0.964 | 0.903 | -0.061 | 0.817 | 0.819 | +0.002 |
| Q35 | fallback | 1.000 | 1.000 | +0.00 | 1.000 | 0.947 | -0.053 | 0.745 | 0.745 | +0.000 |
| Q38 | fallback | 1.000 | 1.000 | +0.00 | 1.000 | 1.000 | +0.000 | 0.841 | 0.841 | +0.000 |

## gold-recital — Δ(B−A)

| qid | path | rescueA | rescueB | Δrescue | faithA | faithB | Δfaith | arA | arB | Δar |
|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | fallback | 0.500 | 0.500 | +0.00 | 0.889 | 0.833 | -0.056 | 0.956 | 0.956 | +0.000 |
| Q3 | cross-norm | 1.000 | 1.000 | +0.00 | 0.684 | 0.880 | +0.196 | 0.882 | 0.875 | -0.007 |
| Q8 | fallback | 1.000 | 1.000 | +0.00 | 1.000 | 1.000 | +0.000 | 0.778 | 0.728 | -0.050 |
| Q29 | fallback | 1.000 | 1.000 | +0.00 | 1.000 | 1.000 | +0.000 | 0.687 | 0.670 | -0.018 |

## Aggregati per gruppo (mediane)

| gruppo | n | rescue A | rescue B | Δrescue | faith A | faith B | Δfaith | ar A | ar B | Δar |
|---|---|---|---|---|---|---|---|---|---|---|
| target | 6 | 0.700 | 0.700 | +0.000 | 0.571 | 0.551 | -0.020 | 0.856 | 0.853 | -0.003 |
| mainstream | 3 | 1.000 | 1.000 | +0.000 | 0.905 | 1.000 | +0.095 | 0.866 | 0.824 | -0.042 |
| mono-stress | 3 | 1.000 | 1.000 | +0.000 | 1.000 | 0.947 | -0.053 | 0.817 | 0.819 | +0.002 |
| gold-recital | 4 | 1.000 | 1.000 | +0.000 | 0.944 | 0.940 | -0.004 | 0.830 | 0.802 | -0.028 |

## Re-baseline impact (max_tokens 1000 → 4000) — 6 target

Confronto faith/ar tra vecchio run (max_tokens=1000, SUBSET_CROSS_NORM_V1_1_RESULTS.md) e config A nuovo (max_tokens=4000). Quantifica quanta 'faith bassa v1.1' era artefatto troncamento.

| qid | faith@1000 | faith@4000 | Δfaith | ar@1000 | ar@4000 | Δar |
|---|---|---|---|---|---|---|
| Q9 | 1.000 | 0.960 | -0.040 | 0.824 | 0.853 | +0.028 |
| Q25 | 0.700 | 0.737 | +0.037 | 0.000 | 0.000 | +0.000 |
| Q68 | 0.400 | 0.412 | +0.012 | 0.898 | 0.903 | +0.005 |
| Q69 | 0.450 | 0.412 | -0.038 | 0.900 | 0.907 | +0.007 |
| Q70 | 0.750 | 0.349 | -0.401 | 0.710 | 0.726 | +0.016 |
| Q71 | 0.714 | 0.731 | +0.016 | 0.761 | 0.859 | +0.099 |

## Verdetto

_(compilato dallo script step 3 — vedi sezione sotto, criteri pre-dichiarati)_

### Criteri pre-dichiarati (verifica numerica)

- C1 target rescue medio +0.05: A=+0.700 B=+0.700 Δ=+0.000 → **FAIL**
- C2 mainstream nessun gold perso top-20 → **PASS**
- C3 mono-stress nessun Δfaith < -0.05 → **FAIL** (Q34:-0.061, Q35:-0.053, Q38:+0.000)
- C4 gold-recital nessun Δfaith < -0.05 → **FAIL** (Q1:-0.056, Q3:+0.196, Q8:+0.000, Q29:+0.000)

### VERDETTO: **BOOST FUORI v1.1 → ROADMAP v1.2** (1/4 passano, fail: ['C1', 'C3', 'C4'])

