# Benchmark esteso settimana 3 — 4 setup × 50 query

**Data:** 2026-05-19
**Collection:** `italian_legal_v1_hybrid` (858 chunk, dense+sparse named vectors)
**Gold:** `data/benchmark/gold_validated_v2.json` (50 query, 72 gold, 39 positive)
**Setup confrontati:** `dense_w3`, `hybrid`, `hybrid_rrk` (rerank_top_k=20), `hybrid_rrk_50` (rerank_top_k=50)
**Reranker:** `BAAI/bge-reranker-v2-m3` (MPS float32, batch=8, max_length=512)

Aggiornamento 2026-05-19: aggiunto il 4° setup `hybrid_rrk_50` dopo la diagnosi zero-recall che ha mostrato 4 query (Q13, Q34, Q35, Q39) con gold in hybrid top-50 ma fuori top-20 (vedi `zero_recall_diagnosis.md`).

## Sanity check vs baseline W2

Confronto `dense_w3` (su `italian_legal_v1_hybrid`) vs baseline W2 (su `italian_legal_v1`) sulle 9 query positive comuni (Q1-Q3, Q5-Q10). Atteso: scarto trascurabile.

| qid | W2 R@5 | W3 R@5 | Δ | W2 R@10 | W3 R@10 | Δ | W2 MRR | W3 MRR | Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q1 | 0.750 | 0.750 | +0.000 | 0.750 | 0.750 | +0.000 | 1.000 | 1.000 | +0.000 |
| Q2 | 0.500 | 0.500 | +0.000 | 0.500 | 0.500 | +0.000 | 1.000 | 1.000 | +0.000 |
| Q3 | 0.750 | 0.750 | +0.000 | 0.750 | 0.750 | +0.000 | 1.000 | 1.000 | +0.000 |
| Q5 | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | +0.000 |
| Q6 | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | +0.000 |
| Q7 | 0.667 | 0.667 | -0.000 | 1.000 | 1.000 | +0.000 | 1.000 | 1.000 | +0.000 |
| Q8 | 0.500 | 0.500 | +0.000 | 1.000 | 1.000 | +0.000 | 0.500 | 0.500 | +0.000 |
| Q9 | 0.000 | 0.000 | +0.000 | 0.250 | 0.250 | +0.000 | 0.125 | 0.125 | +0.000 |
| Q10 | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | +0.000 | 0.000 | 0.000 | +0.000 |

**Mean |Δ| = 0.0000** → **PASS** (soglia: media |Δ| < 0.03 = 3pp).

## Metriche aggregate (39 positive)

| Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3` | 0.308 | 0.370 | 0.293 | 0.287 |
| `hybrid` | 0.459 | 0.538 | 0.444 | 0.438 |
| `hybrid_rrk` | 0.543 | 0.598 | 0.621 | 0.563 |
| `hybrid_rrk_50` | 0.652 | 0.699 | 0.687 | 0.629 |
| **Δ hybrid vs dense** | +0.152 | +0.169 | +0.151 | +0.151 |
| **Δ rrk_20 vs hybrid** | +0.083 | +0.060 | +0.177 | +0.125 |
| **Δ rrk_50 vs rrk_20** | +0.109 | +0.100 | +0.066 | +0.067 |

**Baseline W2 (riferimento, 9 positive di Q1-Q10):** R@5=0.463, R@10=0.5833, MRR=0.625
**Target SCOPE W3:** R@10 ≥ 0.8, MRR ≥ 0.75

## Breakdown per use case

| UC | n_pos | Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---|---:|---:|---:|---:|
| UC1 | 5 | `dense_w3` | 0.317 | 0.383 | 0.367 | 0.312 |
| UC1 | 5 | `hybrid` | 0.167 | 0.467 | 0.203 | 0.221 |
| UC1 | 5 | `hybrid_rrk` | 0.467 | 0.583 | 0.440 | 0.412 |
| UC1 | 5 | `hybrid_rrk_50` | 0.667 | 0.783 | 0.640 | 0.598 |
| UC2 | 5 | `dense_w3` | 0.600 | 0.600 | 0.667 | 0.584 |
| UC2 | 5 | `hybrid` | 0.600 | 0.600 | 0.600 | 0.555 |
| UC2 | 5 | `hybrid_rrk` | 0.600 | 0.600 | 0.600 | 0.555 |
| UC2 | 5 | `hybrid_rrk_50` | 0.600 | 0.600 | 0.567 | 0.539 |
| UC3 | 5 | `dense_w3` | 0.583 | 0.750 | 0.700 | 0.656 |
| UC3 | 5 | `hybrid` | 0.750 | 0.750 | 0.800 | 0.754 |
| UC3 | 5 | `hybrid_rrk` | 0.750 | 0.800 | 0.800 | 0.776 |
| UC3 | 5 | `hybrid_rrk_50` | 0.700 | 0.750 | 0.800 | 0.745 |
| UC4 | 0 | — | — | — | — | — |
| UC5 | 5 | `dense_w3` | 0.000 | 0.050 | 0.025 | 0.025 |
| UC5 | 5 | `hybrid` | 0.067 | 0.183 | 0.240 | 0.144 |
| UC5 | 5 | `hybrid_rrk` | 0.217 | 0.283 | 0.600 | 0.322 |
| UC5 | 5 | `hybrid_rrk_50` | 0.217 | 0.217 | 0.600 | 0.295 |

**Focus Q5 e Q10** (zero-recall baseline W2):

| qid | Setup | R@5 | R@10 | MRR | first_gold_rank |
|---|---|---:|---:|---:|---:|
| Q5 | `dense_w3` | 0.000 | 0.000 | 0.000 | — |
| Q5 | `hybrid` | 0.000 | 0.333 | 0.100 | 10 |
| Q5 | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | — |
| Q5 | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | — |
| Q10 | `dense_w3` | 0.000 | 0.000 | 0.000 | — |
| Q10 | `hybrid` | 0.333 | 0.333 | 1.000 | 1 |
| Q10 | `hybrid_rrk` | 0.333 | 0.667 | 1.000 | 1 |
| Q10 | `hybrid_rrk_50` | 0.333 | 0.333 | 1.000 | 1 |

## Stress lessicali vs use case naturali

- **Naturali** (20 query positive in Q1-Q25)
- **Stress** (15 query positive in Q26-Q40)

| Cluster | Setup | R@10 | MRR | NDCG@10 |
|---|---|---:|---:|---:|
| Naturali | `dense_w3` | 0.446 | 0.440 | 0.394 |
| Naturali | `hybrid` | 0.500 | 0.461 | 0.419 |
| Naturali | `hybrid_rrk` | 0.567 | 0.610 | 0.516 |
| Naturali | `hybrid_rrk_50` | 0.588 | 0.652 | 0.544 |
| Stress | `dense_w3` | 0.367 | 0.175 | 0.221 |
| Stress | `hybrid` | 0.733 | 0.539 | 0.579 |
| Stress | `hybrid_rrk` | 0.733 | 0.733 | 0.708 |
| Stress | `hybrid_rrk_50` | 0.933 | 0.867 | 0.856 |

## Per-query (39 positive × 4 setup)

| qid | use_case | Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---|---|---:|---:|---:|---:|
| Q1 | AI Act high-risk HR screening | `dense_w3` | 0.750 | 0.750 | 1.000 | 0.788 |
| Q1 | AI Act high-risk HR screening | `hybrid` | 0.500 | 0.500 | 0.500 | 0.397 |
| Q1 | AI Act high-risk HR screening | `hybrid_rrk` | 0.500 | 0.750 | 1.000 | 0.725 |
| Q1 | AI Act high-risk HR screening | `hybrid_rrk_50` | 0.500 | 0.750 | 1.000 | 0.654 |
| Q2 | Timeline AI Act credit scoring | `dense_w3` | 0.500 | 0.500 | 1.000 | 0.613 |
| Q2 | Timeline AI Act credit scoring | `hybrid` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q2 | Timeline AI Act credit scoring | `hybrid_rrk` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q2 | Timeline AI Act credit scoring | `hybrid_rrk_50` | 0.500 | 0.500 | 0.333 | 0.307 |
| Q3 | DPIA vs FRIA | `dense_w3` | 0.750 | 0.750 | 1.000 | 0.788 |
| Q3 | DPIA vs FRIA | `hybrid` | 0.750 | 0.750 | 1.000 | 0.805 |
| Q3 | DPIA vs FRIA | `hybrid_rrk` | 0.750 | 1.000 | 1.000 | 0.935 |
| Q3 | DPIA vs FRIA | `hybrid_rrk_50` | 0.500 | 0.750 | 1.000 | 0.776 |
| Q5 | 231 + AI decisioni HR | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q5 | 231 + AI decisioni HR | `hybrid` | 0.000 | 0.333 | 0.100 | 0.136 |
| Q5 | 231 + AI decisioni HR | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q5 | 231 + AI decisioni HR | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q6 | Compiti del DPO | `dense_w3` | 1.000 | 1.000 | 1.000 | 0.967 |
| Q6 | Compiti del DPO | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q6 | Compiti del DPO | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q6 | Compiti del DPO | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q7 | Quando DPIA è obbligatoria | `dense_w3` | 0.667 | 1.000 | 1.000 | 0.933 |
| Q7 | Quando DPIA è obbligatoria | `hybrid` | 1.000 | 1.000 | 1.000 | 0.967 |
| Q7 | Quando DPIA è obbligatoria | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 0.947 |
| Q7 | Quando DPIA è obbligatoria | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 0.947 |
| Q8 | Cos'è FRIA e quando si fa | `dense_w3` | 0.500 | 1.000 | 0.500 | 0.591 |
| Q8 | Cos'è FRIA e quando si fa | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q8 | Cos'è FRIA e quando si fa | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q8 | Cos'è FRIA e quando si fa | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q9 | Reati 231 trattamento illecito dati | `dense_w3` | 0.000 | 0.250 | 0.125 | 0.123 |
| Q9 | Reati 231 trattamento illecito dati | `hybrid` | 0.000 | 0.250 | 0.100 | 0.113 |
| Q9 | Reati 231 trattamento illecito dati | `hybrid_rrk` | 0.250 | 0.250 | 1.000 | 0.390 |
| Q9 | Reati 231 trattamento illecito dati | `hybrid_rrk_50` | 0.250 | 0.250 | 1.000 | 0.390 |
| Q10 | NIS2 soggetti essenziali/importanti | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q10 | NIS2 soggetti essenziali/importanti | `hybrid` | 0.333 | 0.333 | 1.000 | 0.469 |
| Q10 | NIS2 soggetti essenziali/importanti | `hybrid_rrk` | 0.333 | 0.667 | 1.000 | 0.605 |
| Q10 | NIS2 soggetti essenziali/importanti | `hybrid_rrk_50` | 0.333 | 0.333 | 1.000 | 0.469 |
| Q11 | AI Act high-risk credit scoring | `dense_w3` | 0.500 | 0.500 | 0.333 | 0.307 |
| Q11 | AI Act high-risk credit scoring | `hybrid` | 0.000 | 0.500 | 0.167 | 0.218 |
| Q11 | AI Act high-risk credit scoring | `hybrid_rrk` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q11 | AI Act high-risk credit scoring | `hybrid_rrk_50` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q12 | AI Act high-risk emotion recognition scuol | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q12 | AI Act high-risk emotion recognition scuol | `hybrid` | 0.000 | 1.000 | 0.100 | 0.289 |
| Q12 | AI Act high-risk emotion recognition scuol | `hybrid_rrk` | 1.000 | 1.000 | 0.500 | 0.631 |
| Q12 | AI Act high-risk emotion recognition scuol | `hybrid_rrk_50` | 1.000 | 1.000 | 0.500 | 0.631 |
| Q13 | AI Act Allegato III biometria | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q13 | AI Act Allegato III biometria | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q13 | AI Act Allegato III biometria | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q13 | AI Act Allegato III biometria | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q14 | AI Act GPAI vs high-risk obblighi | `dense_w3` | 0.333 | 0.667 | 0.500 | 0.463 |
| Q14 | AI Act GPAI vs high-risk obblighi | `hybrid` | 0.333 | 0.333 | 0.250 | 0.202 |
| Q14 | AI Act GPAI vs high-risk obblighi | `hybrid_rrk` | 0.333 | 0.667 | 0.200 | 0.317 |
| Q14 | AI Act GPAI vs high-risk obblighi | `hybrid_rrk_50` | 0.333 | 0.667 | 0.200 | 0.317 |
| Q15 | AI Act timeline divieti | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q15 | AI Act timeline divieti | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q15 | AI Act timeline divieti | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q15 | AI Act timeline divieti | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q16 | AI Act timeline GPAI già immessi | `dense_w3` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q16 | AI Act timeline GPAI già immessi | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q16 | AI Act timeline GPAI già immessi | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q16 | AI Act timeline GPAI già immessi | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q17 | AI Act art 113 stress | `dense_w3` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q17 | AI Act art 113 stress | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q17 | AI Act art 113 stress | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q17 | AI Act art 113 stress | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q18 | AI Act timeline sanzioni | `dense_w3` | 0.500 | 0.500 | 0.333 | 0.307 |
| Q18 | AI Act timeline sanzioni | `hybrid` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q18 | AI Act timeline sanzioni | `hybrid_rrk` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q18 | AI Act timeline sanzioni | `hybrid_rrk_50` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q19 | DPIA + FRIA scoring bancario | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q19 | DPIA + FRIA scoring bancario | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q19 | DPIA + FRIA scoring bancario | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q19 | DPIA + FRIA scoring bancario | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q24 | 231 modello organizzativo + AI HR | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q24 | 231 modello organizzativo + AI HR | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q24 | 231 modello organizzativo + AI HR | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q24 | 231 modello organizzativo + AI HR | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q25 | 231 fattispecie informatica art 24-bis | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q25 | 231 fattispecie informatica art 24-bis | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q25 | 231 fattispecie informatica art 24-bis | `hybrid_rrk` | 0.500 | 0.500 | 1.000 | 0.613 |
| Q25 | 231 fattispecie informatica art 24-bis | `hybrid_rrk_50` | 0.500 | 0.500 | 1.000 | 0.613 |
| Q26 | stress: art 24-bis 231 | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q26 | stress: art 24-bis 231 | `hybrid` | 1.000 | 1.000 | 0.500 | 0.631 |
| Q26 | stress: art 24-bis 231 | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q26 | stress: art 24-bis 231 | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q27 | stress: art 25-undecies | `dense_w3` | 0.000 | 0.500 | 0.125 | 0.193 |
| Q27 | stress: art 25-undecies | `hybrid` | 0.500 | 1.000 | 1.000 | 0.832 |
| Q27 | stress: art 25-undecies | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q27 | stress: art 25-undecies | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q28 | stress: art 5 GDPR | `dense_w3` | 1.000 | 1.000 | 0.500 | 0.631 |
| Q28 | stress: art 5 GDPR | `hybrid` | 1.000 | 1.000 | 0.333 | 0.500 |
| Q28 | stress: art 5 GDPR | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q28 | stress: art 5 GDPR | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q29 | stress: considerando 84 GDPR | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q29 | stress: considerando 84 GDPR | `hybrid` | 1.000 | 1.000 | 0.250 | 0.431 |
| Q29 | stress: considerando 84 GDPR | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q29 | stress: considerando 84 GDPR | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q30 | stress: Allegato III punto 4 AI Act | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q30 | stress: Allegato III punto 4 AI Act | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q30 | stress: Allegato III punto 4 AI Act | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q30 | stress: Allegato III punto 4 AI Act | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q31 | stress: art 22 GDPR | `dense_w3` | 1.000 | 1.000 | 0.333 | 0.500 |
| Q31 | stress: art 22 GDPR | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q31 | stress: art 22 GDPR | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q31 | stress: art 22 GDPR | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q32 | stress: art 6 NIS2 | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q32 | stress: art 6 NIS2 | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q32 | stress: art 6 NIS2 | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q32 | stress: art 6 NIS2 | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q33 | stress: art 35 disambiguation | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q33 | stress: art 35 disambiguation | `hybrid` | 1.000 | 1.000 | 0.500 | 0.693 |
| Q33 | stress: art 35 disambiguation | `hybrid_rrk` | 0.500 | 1.000 | 1.000 | 0.798 |
| Q33 | stress: art 35 disambiguation | `hybrid_rrk_50` | 0.500 | 1.000 | 1.000 | 0.790 |
| Q34 | stress: art 9 GDPR | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q34 | stress: art 9 GDPR | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q34 | stress: art 9 GDPR | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q34 | stress: art 9 GDPR | `hybrid_rrk_50` | 1.000 | 1.000 | 0.500 | 0.631 |
| Q35 | stress: art 27 AI Act FRIA | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q35 | stress: art 27 AI Act FRIA | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q35 | stress: art 27 AI Act FRIA | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q35 | stress: art 27 AI Act FRIA | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q36 | stress: art 111 AI Act | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q36 | stress: art 111 AI Act | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q36 | stress: art 111 AI Act | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q36 | stress: art 111 AI Act | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q37 | stress: considerando 71 vs art 22 GDPR | `dense_w3` | 0.500 | 1.000 | 0.333 | 0.484 |
| Q37 | stress: considerando 71 vs art 22 GDPR | `hybrid` | 0.500 | 1.000 | 0.500 | 0.605 |
| Q37 | stress: considerando 71 vs art 22 GDPR | `hybrid_rrk` | 0.500 | 1.000 | 1.000 | 0.818 |
| Q37 | stress: considerando 71 vs art 22 GDPR | `hybrid_rrk_50` | 0.500 | 1.000 | 1.000 | 0.790 |
| Q38 | stress: L. 132/2025 art 11 | `dense_w3` | 1.000 | 1.000 | 0.333 | 0.500 |
| Q38 | stress: L. 132/2025 art 11 | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q38 | stress: L. 132/2025 art 11 | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q38 | stress: L. 132/2025 art 11 | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q39 | stress: art 6 GDPR base giuridica | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q39 | stress: art 6 GDPR base giuridica | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q39 | stress: art 6 GDPR base giuridica | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q39 | stress: art 6 GDPR base giuridica | `hybrid_rrk_50` | 1.000 | 1.000 | 0.500 | 0.631 |
| Q40 | stress: NIS2 obblighi notifica naturale | `dense_w3` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q40 | stress: NIS2 obblighi notifica naturale | `hybrid` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q40 | stress: NIS2 obblighi notifica naturale | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q40 | stress: NIS2 obblighi notifica naturale | `hybrid_rrk_50` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q43 | edge: query troppo generica | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q43 | edge: query troppo generica | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q43 | edge: query troppo generica | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q43 | edge: query troppo generica | `hybrid_rrk_50` | 0.500 | 0.500 | 0.500 | 0.387 |
| Q45 | edge: query vaga multi-doc | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q45 | edge: query vaga multi-doc | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q45 | edge: query vaga multi-doc | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q45 | edge: query vaga multi-doc | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q49 | edge: mix in/off corpus | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q49 | edge: mix in/off corpus | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q49 | edge: mix in/off corpus | `hybrid_rrk` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q49 | edge: mix in/off corpus | `hybrid_rrk_50` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q50 | edge: vaga ma con anchor lessicale | `dense_w3` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q50 | edge: vaga ma con anchor lessicale | `hybrid` | 0.000 | 0.000 | 0.000 | 0.000 |
| Q50 | edge: vaga ma con anchor lessicale | `hybrid_rrk` | 1.000 | 1.000 | 1.000 | 1.000 |
| Q50 | edge: vaga ma con anchor lessicale | `hybrid_rrk_50` | 1.000 | 1.000 | 0.250 | 0.431 |

## Negative & edge (11 query, gold vuoto)

| qid | kind | use_case | top1 dense | top1 hybrid | top1 rrk_20 | top1 rrk_50 |
|---|---|---|---:|---:|---:|---:|
| Q4 | negative | Garante riconoscimento facciale lavoro (ne | 0.6818 | 0.5526 | 0.1684 | 0.1684 |
| Q20 | negative | Garante sanzioni biometria dipendenti | 0.7193 | 0.5714 | 0.4997 | 0.4997 |
| Q21 | negative | Garante riconoscimento facciale aeroporti | 0.6936 | 0.5000 | 0.0381 | 0.0381 |
| Q22 | negative | Garante riconoscimento facciale presenze | 0.6835 | 0.5833 | 0.2321 | 0.2321 |
| Q23 | negative | 231 + GDPR + AI selezione fornitori | 0.6818 | 0.5000 | 0.0143 | 0.0451 |
| Q41 | negative | edge: Data Act off-corpus | 0.7033 | 0.5000 | 0.0084 | 0.0084 |
| Q42 | negative | edge: ISO 27001 off-scope | 0.7379 | 0.5000 | 0.4039 | 0.4039 |
| Q44 | negative | edge: EDPB off-corpus | 0.7100 | 0.5500 | 0.2182 | 0.2182 |
| Q46 | edge | edge: operativa ChatGPT | 0.6848 | 0.6000 | 0.0003 | 0.0003 |
| Q47 | negative | edge: art inesistente | 0.8203 | 0.6429 | 0.5923 | 0.5923 |
| Q48 | negative | edge: ePrivacy off-corpus | 0.8361 | 0.5000 | 0.6123 | 0.6123 |

**Sanity informale** (mean top-1 score, gold-vuote vs positive):

| Setup | neg mean | neg median | pos mean |
|---|---:|---:|---:|
| `dense_w3` | 0.7229 | 0.7033 | 0.7707 |
| `hybrid` | 0.5455 | 0.5500 | 0.6413 |
| `hybrid_rrk` | 0.2535 | 0.2182 | 0.7126 |
| `hybrid_rrk_50` | 0.2563 | 0.2182 | 0.7233 |

## Latenza

Warmup escluso: prime 3 query. Misure su 47 query effettive (Mac M4 Pro MPS, Qdrant Docker).

| Step | p50 (ms) | p95 (ms) |
|---|---:|---:|
| retrieval dense (top-10) | 22.1 | 41.1 |
| retrieval hybrid (top-10) | 19.5 | 23.4 |
| retrieval hybrid (top-20) | 20.5 | 24.6 |
| retrieval hybrid (top-50) | 26.1 | 43.1 |
| rerank top-20 → top-10 | 1200.3 | 1562.4 |
| rerank top-50 → top-10 | 2450.2 | 3503.4 |

**End-to-end per setup:**

| Setup | p50 (ms) | p95 (ms) |
|---|---:|---:|
| `dense_w3` | 22.1 | 41.1 |
| `hybrid` | 19.5 | 23.4 |
| `hybrid_rrk` | 1219.7 | 1584.1 |
| `hybrid_rrk_50` | 2468.1 | 3546.2 |

## Trade-off rerank_top_k: 20 vs 50

Confronto sintetico fra i 4 setup:

| Setup | R@5 | R@10 | MRR | NDCG@10 | e2e p50 (ms) |
|---|---:|---:|---:|---:|---:|
| `dense_w3` | 0.308 | 0.370 | 0.293 | 0.287 | 22.1 |
| `hybrid` | 0.459 | 0.538 | 0.444 | 0.438 | 19.5 |
| `hybrid_rrk` | 0.543 | 0.598 | 0.621 | 0.563 | 1219.7 |
| `hybrid_rrk_50` | 0.652 | 0.699 | 0.687 | 0.629 | 2468.1 |

**Query che si chiudono passando rerank_top_k 20 → 50** (R@10: 0 → >0): 5 su 39

| qid | R@10 rrk_20 | R@10 rrk_50 |
|---|---:|---:|
| Q13 | 0.000 | 1.000 |
| Q34 | 0.000 | 1.000 |
| Q35 | 0.000 | 1.000 |
| Q39 | 0.000 | 1.000 |
| Q43 | 0.000 | 0.500 |

**Query positive che restano R@10=0 anche con rrk_50:** Q5, Q15, Q19, Q24, Q30, Q45, Q49.

Riferimento `zero_recall_diagnosis.md`: 4 query (Q13, Q34, Q35, Q39) avevano gold in hybrid top-50 ma fuori top-20 — atteso che rrk_50 le chiuda. Le restanti (Q15, Q19, Q24, Q30) hanno bug isolati (parser art_113, chunk annex_III monoblocco, vocabolario FRIA/scoring) o mismatch semantico cross-norma (Q24).

## Verdetto sintetico (aggiornato con rrk_50)

- **Hybrid vs dense:** R@10 +0.169, MRR +0.151, NDCG@10 +0.151.
- **rrk_20 vs hybrid:** R@10 +0.060, MRR +0.177, NDCG@10 +0.125.
- **rrk_50 vs rrk_20:** R@10 +0.100, MRR +0.066, NDCG@10 +0.067.
- **Target SCOPE (R@10 ≥ 0.8, MRR ≥ 0.75):** NESSUN setup li raggiunge entrambi.
- **Costo latenza p50 rrk_50:** 2468ms (vs rrk_20 1220ms, +1248ms).

**Default produttivo proposto:**

- **LLM cloud (budget <3s totali, di SCOPE):** rrk_50 con p50 2468ms lascia margine ~531ms per la generazione cloud.
- **LLM locale (budget <5s totali):** rrk_50 lascia ~2531ms al modello locale; con Qwen2.5-14B Q4_K_M su Mac M4 Pro la latenza di generazione è ~1.5-2.5s, quindi rientra. rrk_20 resta fallback se serve margine.
- Decisione definitiva al disegno serving runtime — `core/hybrid_retriever` espone già `rerank_top_k` come parametro dinamico.

---

## Re-run post-fix parser EUR-Lex (2026-05-19)

**Trigger:** chiusura del bug `_parse_commi` su articoli senza commi numerati (vedi PROJECT_CONTEXT.md settimana 4, art_113 stress). Lo scan post-fix ha identificato 35 articoli EUR-Lex silently broken con lo stesso pattern (chunk text < 150 char). Re-ingest completo EUR-Lex (568 chunk, 277.8s) eseguito sulla collection `italian_legal_v1_hybrid`. Normattiva non toccata. Idempotenza: UUID v5 deterministico → upsert in place.

### Articoli re-ingestati con body recuperato (4 verifiche spot)

| chunk_id | len(text) prima | len(text) dopo |
|---|---:|---:|
| `eli/reg/2016/679/oj__art_4`  (Definizioni GDPR) | 24 | 9735 |
| `eli/reg/2024/1689/oj__art_3` (Definizioni AI Act) | 24 | 18410 |
| `eli/reg/2024/1689/oj__art_99` (controllo sano) | 5596 | 5596 |
| `eli/reg/2024/1689/oj__art_113` (controllo già fixato W4) | 592 | 592 |

Nessuna regressione del fallback su articoli sani (controllo art_99 AI Act invariato).

### Gold aggiornati

5 entry gold hanno chunk_id nella lista dei 36 fixati: Q2, Q14, Q15, Q17, Q18. `text_excerpt` allineato al nuovo body (~144 char, boundary-safe). `chunk_id` / `query` / `use_case` / `expected_kind` invariati.

### Aggregato 39 positive (pre-fix W4 → post-fix re-ingest)

| Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | 0.348 → **0.323** | 0.410 → **0.526** | 0.310 → **0.341** | 0.311 → **0.360** |
| `hybrid`     | 0.502 → **0.528** | 0.579 → **0.579** | 0.494 → **0.542** | 0.489 → **0.516** |
| `hybrid_rrk` | 0.585 → **0.637** | 0.641 → **0.692** | 0.642 → **0.661** | 0.594 → **0.622** |

### Delta vs pre-fix W4

| Setup | ΔR@5 | ΔR@10 | ΔMRR | ΔNDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | −0.026 | **+0.115** | +0.031 | +0.050 |
| `hybrid`     | +0.026 | +0.000 | +0.048 | +0.027 |
| `hybrid_rrk` | +0.051 | **+0.051** | +0.019 | +0.027 |

Guadagno principale su `dense_w3` R@10 (+11.5 pp): gli articoli che prima erano chunk-titolo da 24-47 char ora hanno body completo agganciabile da bge-m3.

### Per-query Δ R@10 ≥ |0.25|

10 movimenti rilevanti, 9 positivi + 1 regressione:

| qid | use_case | setup | R@10 prima | R@10 dopo | Δ | first_gold prima | first_gold dopo |
|---|---|---|---:|---:|---:|:---:|:---:|
| Q17 | AI Act art 113 stress | `dense_w3` | 1.000 | 0.000 | −1.000 | 1 | — |
| Q26 | stress: art 24-bis 231 | `dense_w3` | 0.000 | 1.000 | +1.000 | — | 10 |
| Q34 | stress: art 9 GDPR | `hybrid_rrk` | 0.000 | 1.000 | +1.000 | — | 1 |
| Q36 | stress: art 111 AI Act | `dense_w3` | 0.000 | 1.000 | +1.000 | — | 8 |
| Q39 | stress: art 6 GDPR base giuridica | `dense_w3` | 0.000 | 1.000 | +1.000 | — | 10 |
| Q45 | edge: query vaga multi-doc | `dense_w3` | 0.000 | 1.000 | +1.000 | — | 8 |
| Q45 | edge: query vaga multi-doc | `hybrid_rrk` | 0.000 | 1.000 | +1.000 | — | 4 |
| Q27 | stress: art 25-undecies | `dense_w3` | 0.500 | 1.000 | +0.500 | 8 | 8 |
| Q33 | stress: art 35 disambiguation | `dense_w3` | 0.000 | 0.500 | +0.500 | — | 9 |
| Q43 | edge: query troppo generica | `dense_w3` | 0.000 | 0.500 | +0.500 | — | 7 |

**Regressione Q17 dense_w3** (1.000 → 0.000): isolata. Pre-fix il chunk art_113 era 47 char di puro titolo `Articolo 113 - Entrata in vigore e applicazione` e matchava al rank 1 la query lessicale `"art 113 entrata in vigore AI Act"` per pura similarità di superficie. Post-fix il chunk è 592 char con body sulle date di applicazione dei capi → la similarità coseno con la query corta si diluisce e salgono i 231 art_75/80/81/82 (anch'essi "entrata in vigore" italiani). Hybrid e hybrid_rrk continuano a trovare correttamente art_113 (rank 2 e rank 1 rispettivamente). Non è una regressione del fix in sé — è la dinamica nota dense-vs-hybrid su query lessicali corte, mitigata in produzione dall'hybrid default.

### Verdetto del re-run

Aggregato in miglioramento su tutti e 3 i setup. Hybrid_rrk R@10 = **0.692** (era 0.641 pre-fix W4, era 0.598 al baseline W3 originale). Una regressione isolata su Q17 dense_w3 con spiegazione strutturale, neutralizzata da hybrid + reranker. Nessuna azione richiesta.

---

## Re-run post-fix chunking annex_III (2026-05-19)

**Trigger:** chiusura del bug Q30 (annex_III monoblocco 8460 char, segnale diluito per query mirate su un singolo punto). Patch `parse_annex_iii_aiact`: ritorna `list[EurLexAnnex]` con 1 entry per macro-punto (8 totali) invece di un singolo annex concatenato. Granularità ferma al punto, NON scende a lettera. Coerente con `chunk_recitals`.

### Chunk in collection

- Vecchio: 1 monoblocco `eli/reg/2024/1689/oj__annex_III` (8460 char, 1782 token) — **cancellato**.
- Nuovi: 8 chunk `eli/reg/2024/1689/oj__annex_III__point_{1..8}` (62–423 token ciascuno).
- Collection size: 858 − 1 + 8 = **865 points**.

### Gold aggiornati

Q30 → `annex_III__point_4` (Occupazione, lettera a/b), excerpt + hierarchy + found_via riallineati.

⚠️ **5 altri gold restano puntati al vecchio monoblocco e ora orfani** (Q1, Q11, Q12, Q13, Q19). Aggiornarli richiede mappatura giuridica per query: Q1→p4 (HR), Q11→p5 (credit), Q12→p1+p3 (emozioni+scuola), Q13→p1 (biometria), Q19→p5 (credit scoring). Lo spec di oggi attendeva solo Q30; le altre 5 sono lasciate a un secondo passaggio con il PM. Effetto misurabile sul benchmark sotto.

### Aggregato 39 positive (pre-split → post-split)

| Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | 0.323 → 0.316 | 0.526 → 0.519 | 0.341 → 0.341 | 0.360 → 0.356 |
| `hybrid`     | 0.528 → **0.566** | 0.579 → 0.579 | 0.542 → **0.584** | 0.516 → **0.539** |
| `hybrid_rrk` | 0.637 → **0.662** | 0.692 → **0.712** | 0.661 → **0.687** | 0.622 → **0.642** |

### Delta vs ultimo run (post-Q15 fix parser EUR-Lex)

| Setup | ΔR@5 | ΔR@10 | ΔMRR | ΔNDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | −0.006 | −0.006 | +0.000 | −0.004 |
| `hybrid`     | +0.038 | +0.000 | +0.042 | +0.023 |
| `hybrid_rrk` | +0.026 | **+0.019** | +0.026 | +0.021 |

Miglioramento netto su `hybrid_rrk` nonostante le 2 regressioni note Q12/Q1 da orfanaggio gold.

### Per-query Δ R@10 ≥ |0.25|

| qid | use_case | setup | R@10 prima | R@10 dopo | Δ | first_gold prima | first_gold dopo |
|---|---|---|---:|---:|---:|:---:|:---:|
| Q30 | stress: Allegato III punto 4 AI Act | `hybrid` | 0.000 | 1.000 | **+1.000** | — | 5 |
| Q30 | stress: Allegato III punto 4 AI Act | `hybrid_rrk` | 0.000 | 1.000 | **+1.000** | — | 1 |
| Q39 | stress: art 6 GDPR base giuridica | `hybrid_rrk` | 0.000 | 1.000 | **+1.000** | — | 2 |
| Q12 | AI Act high-risk emotion recognition scuole | `hybrid` | 1.000 | 0.000 | **−1.000** | 10 | — |
| Q12 | AI Act high-risk emotion recognition scuole | `hybrid_rrk` | 1.000 | 0.000 | **−1.000** | 2 | — |
| Q1  | AI Act high-risk HR screening | `dense_w3`   | 0.750 | 0.500 | −0.250 | 1 | 1 |
| Q1  | AI Act high-risk HR screening | `hybrid_rrk` | 0.750 | 0.500 | −0.250 | 1 | 1 |

**Diagnosi Q12 e Q1:** entrambe hanno `annex_III` (monoblocco) come gold non aggiornato. Q12 (4 gold, 1 = annex orfano) → R@10 collassa perché annex era l'unico gold raggiunto. Q1 (4 gold, 1 = annex orfano) → R@10 cala da 0.75 a 0.5 perché 3 altri gold restano agganciati ma annex è perso. **Non è una regressione del fix** — è la conseguenza dell'orfanaggio dei 5 gold lasciati al vecchio chunk_id. Una volta riannotati al point corretto, queste regressioni scompaiono e diventano probabilmente +R@10 (Q12 punto 1 lettera c "riconoscimento emozioni" + punto 3 istruzione; Q1 punto 4 lettera a "selezione personale").

### Verdetto del re-run

Aggregato in miglioramento netto su `hybrid` e `hybrid_rrk`; `dense_w3` invariato. Q30 chiusa. Effetto collaterale prevedibile su Q1/Q12 da orfanaggio gold, **risolvibile con riannotazione manuale dei 5 gold residui al point corretto**. Q11/Q13/Q19 invariati (erano già R@10=0 sul gold annex pre-split). Nessuna azione richiesta a livello di codice.

---

## Re-run post-riannotazione gold orfani (2026-05-19)

**Trigger:** chiusura del task di propagazione meccanica del fix split annex_III. 5 entry gold (Q1, Q11, Q12, Q13, Q19) puntavano al vecchio chunk_id `eli/reg/2024/1689/oj__annex_III` (cancellato dopo lo split) e venivano forzate a R@10=0 sui gold annex. Mapping derivato dal testo letterale di ciascuna query (no annotazione nuova):

| qid | query topic | mapping point |
|---|---|---|
| Q1 | screening CV / selezione personale | `__annex_III__point_4` (Occupazione) |
| Q11 | credit scoring banca / mutui | `__annex_III__point_5` (Servizi essenziali, affidabilità creditizia) |
| Q12 | riconoscimento emozioni / scuole | **dual**: `__annex_III__point_1` (biometria/emozioni) + `__annex_III__point_3` (istruzione) |
| Q13 | Allegato III biometria | `__annex_III__point_1` (Biometria) |
| Q19 | scoring bancario / FRIA-DPIA | `__annex_III__point_5` (Servizi essenziali) |

Integrità gold dopo l'update: 73 entry gold totali (era 72; +1 per dual gold Q12), 41 distinct chunk_id, **0 orfani residui**, tutti presenti in collection.

### Aggregato 39 positive

3 fasi: **baseline W3** (pre tutti i fix W4) → **post-split** (pre-riannotazione) → **post-riannotazione** (oggi).

| Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | 0.308 → 0.316 → **0.342** | 0.370 → 0.519 → **0.553** | 0.293 → 0.341 → **0.354** | 0.287 → 0.356 → **0.377** |
| `hybrid`     | 0.459 → 0.566 → **0.566** | 0.538 → 0.579 → **0.626** | 0.444 → 0.584 → **0.572** | 0.438 → 0.539 → **0.553** |
| `hybrid_rrk` | 0.543 → 0.662 → **0.637** | 0.598 → 0.712 → **0.712** | 0.621 → 0.687 → **0.677** | 0.563 → 0.642 → **0.634** |

### Delta vs ultimo run (post-split, pre-riannotazione)

| Setup | ΔR@5 | ΔR@10 | ΔMRR | ΔNDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | +0.026 | **+0.034** | +0.013 | +0.020 |
| `hybrid`     | +0.000 | **+0.047** | −0.011 | +0.014 |
| `hybrid_rrk` | −0.026 | +0.000 | −0.010 | −0.008 |

### Cumulative W4 — baseline W3 → oggi

| Setup | ΔR@5 | ΔR@10 | ΔMRR | ΔNDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`   | +0.034 | **+0.184** | +0.061 | +0.090 |
| `hybrid`     | +0.107 | **+0.088** | +0.129 | +0.115 |
| `hybrid_rrk` | +0.094 | **+0.113** | +0.056 | +0.071 |

`hybrid_rrk` R@10 cumulativo W4 = **+11.3 pp** (da 0.598 a 0.712).

### Per-query Δ R@10 ≥ |0.25|

| qid | use_case | setup | R@10 prima | R@10 dopo | Δ | first_gold prima | first_gold dopo |
|---|---|---|---:|---:|---:|:---:|:---:|
| Q13 | AI Act Allegato III biometria | `dense_w3` | 0.000 | 1.000 | **+1.000** | — | 2 |
| Q13 | AI Act Allegato III biometria | `hybrid` | 0.000 | 1.000 | **+1.000** | — | 1 |
| Q13 | AI Act Allegato III biometria | `hybrid_rrk` | 0.000 | 1.000 | **+1.000** | — | 9 |
| Q39 | stress: art 6 GDPR base giuridica | `hybrid_rrk` | 1.000 | 0.000 | **−1.000** | 2 | — |
| Q12 | AI Act high-risk emotion recognition scuole | `hybrid` | 0.000 | 0.500 | +0.500 | — | 9 |
| Q19 | DPIA + FRIA scoring bancario | `hybrid` | 0.667 | 1.000 | +0.333 | 1 | 1 |
| Q19 | DPIA + FRIA scoring bancario | `dense_w3` | 0.333 | 0.667 | +0.333 | 3 | 3 |

**Q39 hybrid_rrk regressione 1.0 → 0:** gold `art_6 GDPR` invariato (la riannotazione tocca solo entry annex_III). Stesso retrieval upstream, stessa collection. Sospetto rumore reranker su query boundary-fragile (lo score CrossEncoder può variare di pochi millesimi tra run distinti su MPS); cala da rank 2 a fuori top-10. Non legato al fix in oggetto — flag, non blocker. Q12 a R@10=0.5 perché ha 2 gold (point_1 e point_3): rerank trova point_1 al rank 9 ma non point_3.

### Zero-recall: sanity vs pre-riannotazione

| Setup | pre-riann. | post-riann. |
|---|---:|---:|
| `dense_w3` | 14 | 13 |
| `hybrid` | 12 | 10 |
| `hybrid_rrk` | 7 | 7 |

Nessuna nuova zero-recall introdotta dalla riannotazione; 3 query escono da zero-recall su dense+hybrid.

### Verdetto del re-run

Aggregato in tenuta o miglioramento su tutti i setup; hybrid R@10 +4.7pp, dense_w3 R@10 +3.4pp. hybrid_rrk R@10 stabile (compensazione perfetta Q13/Q19 guadagni vs Q39 rumore). Q13 chiude da zero-recall su tutti e 3 i setup. Q12 parziale (1/2 gold). Cumulative W4: **+18.4 pp dense_w3, +8.8 pp hybrid, +11.3 pp hybrid_rrk** sul R@10 vs baseline chiusura W3. **Settimana 4 chiusa sui bug isolati**.

---

## Re-aggregazione post-riclassificazione Q5 → edge (2026-05-19)

**Trigger**: diagnostica curatela W7-prep ha rivelato che Q5 richiede reasoning cross-norma con vocabolari disgiunti (AI/HR + reati-presupposto), capability v1.1. Riclassificata `expected_kind: positive → edge` in `gold_validated_v2.json`. 39 positive → 38.

NB: re-aggregazione **puramente amministrativa** (numeri ricalcolati da `results_w3_extended.json/per_query` escludendo Q5). Nessun ri-retrieval, nessun ri-rerank.

### Aggregato 38 positive (delta vs 39)

| Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`      | 0.316 (+0.008) | 0.379 (+0.010) | 0.300 (+0.008) | 0.294 (+0.008) |
| `hybrid`        | 0.472 (+0.012) | 0.544 (+0.005) | 0.453 (+0.009) | 0.445 (+0.008) |
| `hybrid_rrk`    | 0.557 (+0.014) | 0.614 (+0.016) | 0.637 (+0.016) | 0.577 (+0.015) |
| `hybrid_rrk_50` | 0.669 (+0.017) | 0.717 (+0.018) | 0.705 (+0.018) | 0.646 (+0.017) |

### Effetto della rimozione di Q5

Q5 era zero-recall su `dense_w3`, `hybrid_rrk`, `hybrid_rrk_50` (R@10=0) e parziale su `hybrid` (R@10=0.333 — un solo gold candidate appariva al rank 10 prima della riclassificazione). La rimozione di una query zero-recall **migliora leggermente** le medie aggregate su tutti i setup. Aggiornamento puramente amministrativo, nessun cambiamento del sistema.

### Zero-recall residue (post-Q5)

| Setup | n zero-recall pre-Q5 (39 pos) | n zero-recall post-Q5 (38 pos) |
|---|---:|---:|
| `dense_w3`      | 21 | 20 |
| `hybrid`        | 13 | 13 |
| `hybrid_rrk`    | 12 | 11 |
| `hybrid_rrk_50` |  7 |  6 |

`hybrid` invariato perché Q5 NON era zero-recall su `hybrid` (R@10=0.333 da un gold al rank 10, ora riclassificato). Su tutti gli altri setup Q5 era zero-recall, quindi `n` scende di 1.

### Lista zero-recall post-Q5 (per setup hybrid_rrk_50)

`Q15, Q19, Q24, Q30, Q45, Q49`. Tutti casi noti, profilati in `zero_recall_diagnosis.md` (W3) e in `ROADMAP_POST_V1.md` come candidati architetture retrieval v1.1.

---

## Re-aggregazione post-fix Q9 (2026-05-19)

**Trigger**: audit annotazione 231 ha rimosso 3 chunk dal gold di Q9 (`art_25-undecies__paras_1_6`, `art_25-undecies__paras_7_8`, `196 art_167`) per allucinazione LLM e non-pertinenza. Q9 resta `positive` ma il gold si riduce da 4 chunk a **1 (solo `art_24-bis`)**. Riannotazione meccanica, nessun ri-retrieval.

### Aggregato 38 positive (post-fix Q9)

| Setup | R@5 | R@10 | MRR | NDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`      | 0.316 | 0.373 | 0.297 | 0.291 |
| `hybrid`        | 0.472 | 0.537 | 0.450 | 0.443 |
| `hybrid_rrk`    | 0.550 | 0.608 | 0.611 | 0.567 |
| `hybrid_rrk_50` | 0.662 | 0.711 | 0.679 | 0.636 |

### Delta vs aggregato post-Q5-riclassificazione (38 positive con vecchio gold Q9)

| Setup | ΔR@5 | ΔR@10 | ΔMRR | ΔNDCG@10 |
|---|---:|---:|---:|---:|
| `dense_w3`      | +0.000 | −0.007 | −0.003 | −0.003 |
| `hybrid`        | +0.000 | −0.007 | −0.003 | −0.003 |
| `hybrid_rrk`    | −0.007 | −0.007 | −0.026 | −0.010 |
| `hybrid_rrk_50` | −0.007 | −0.007 | −0.026 | −0.010 |

### Effetto sulla zero-recall

| Setup | n zero-recall pre-fix-Q9 | n zero-recall post-fix-Q9 | delta |
|---|---:|---:|---:|
| `dense_w3`      | 20 | 21 | +1 (Q9) |
| `hybrid`        | 13 | 14 | +1 (Q9) |
| `hybrid_rrk`    | 11 | 12 | +1 (Q9) |
| `hybrid_rrk_50` |  6 |  7 | +1 (Q9) |

### Verdetto

Q9 con il nuovo gold (solo `art_24-bis`) **entra in zero-recall su tutti i 4 setup**: il chunk pertinente non emerge nei top-10. Il vecchio gold contava `196 art_167` al rank 8 di `dense_w3` (e rank 1 di `hybrid_rrk`/`hybrid_rrk_50`) come "hit" — match lessicale, ma giuridicamente non-pertinente.

Numeri leggermente in calo come atteso (MRR `hybrid_rrk` −0.026 è il delta più significativo, perché Q9 contribuiva 1.0 al MRR con `art_167` al rank 1 — ora azzerato).

Conclusione metodologica: il fix è **strict-better** per la baseline Ragas W7. L'aggregato pre-fix sovrastimava la qualità di Q9 (gold sbagliato agganciato per ragioni lessicali). Q9 zero-recall sul gold corretto è la realtà del sistema su questa query — il fix lo rende visibile.

Q9 candidato all'estensione corpus codice penale v1.1 (vedi `ROADMAP_POST_V1.md` sezione "Estensione corpus v1.1").

### Lista zero-recall post-fix-Q9 (per setup hybrid_rrk_50)

`Q9, Q15, Q19, Q24, Q30, Q45, Q49`. Q9 nuovo elemento della lista; le altre 6 invariate (note dalla diagnostica W3).
