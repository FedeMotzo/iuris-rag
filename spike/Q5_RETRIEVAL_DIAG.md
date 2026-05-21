# Diagnostica retrieval Q5

**Query**: `L'uso di sistemi AI per decisioni che riguardano i lavoratori può attivare responsabilità ai sensi del D.Lgs 231/2001?`

**Gold attuali** (is_gold=true in `gold_validated_v2.json`):

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6`
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8`
- `eli/reg/2016/679/oj__art_22`

**Gold proposti** (da curatela manuale):

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167`
- `eli/reg/2016/679/oj__art_22`

## Modalità: `dense`

| rank | score   | chunk_id                                                                  | hierarchy | flag |
|------|---------|---------------------------------------------------------------------------|-----------|------|
|    1 |  0.7286 | eli/reg/2024/1689/oj__recital_57                                          | Considerando 57 |  |
|    2 |  0.7040 | eli/reg/2024/1689/oj__annex_III__point_4                                  | Allegato III - Sistemi di IA ad alto rischio di cui all'a... |  |
|    3 |  0.7032 | akn/it/act/legge/stato/2025-09-23/132__art_11                             | Capo II > art. 11 |  |
|    4 |  0.7006 | akn/it/act/legge/stato/2025-09-23/132__art_15                             | Capo II > art. 15 |  |
|    5 |  0.6995 | akn/it/act/legge/stato/2025-09-23/132__art_7                              | Capo II > art. 7 |  |
|    6 |  0.6993 | akn/it/act/legge/stato/2025-09-23/132__art_1                              | Capo I > art. 1 |  |
|    7 |  0.6921 | akn/it/act/legge/stato/2025-09-23/132__art_13                             | Capo II > art. 13 |  |
|    8 |  0.6901 | akn/it/act/legge/stato/2025-09-23/132__art_12                             | Capo II > art. 12 |  |
|    9 |  0.6886 | eli/reg/2024/1689/oj__recital_1                                           | Considerando 1 |  |
|   10 |  0.6882 | eli/reg/2024/1689/oj__recital_85                                          | Considerando 85 |  |

**Summary `dense`**: gold attuali nei top-10 = **0/3** · gold proposti nei top-10 = **0/3**

Rank per ciascun gold proposto:
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → fuori top-10
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167` → fuori top-10
- `eli/reg/2016/679/oj__art_22` → fuori top-10

## Modalità: `hybrid`

| rank | score   | chunk_id                                                                  | hierarchy | flag |
|------|---------|---------------------------------------------------------------------------|-----------|------|
|    1 |  0.6429 | eli/reg/2024/1689/oj__recital_57                                          | Considerando 57 |  |
|    2 |  0.5333 | eli/reg/2024/1689/oj__annex_III__point_4                                  | Allegato III - Sistemi di IA ad alto rischio di cui all'a... |  |
|    3 |  0.5000 | akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_152              | art. 152 |  |
|    4 |  0.3333 | eli/reg/2024/1689/oj__art_26                                              | Capo III - SISTEMI DI IA AD ALTO RISCHIO > art. 26 |  |
|    5 |  0.3167 | eli/reg/2024/1689/oj__recital_92                                          | Considerando 92 |  |
|    6 |  0.2500 | akn/it/act/legge/stato/2025-09-23/132__art_11                             | Capo II > art. 11 |  |
|    7 |  0.2000 | akn/it/act/legge/stato/2025-09-23/132__art_15                             | Capo II > art. 15 |  |
|    8 |  0.1667 | eli/reg/2024/1689/oj__recital_93                                          | Considerando 93 |  |
|    9 |  0.1667 | akn/it/act/legge/stato/2025-09-23/132__art_7                              | Capo II > art. 7 |  |
|   10 |  0.1429 | akn/it/act/legge/stato/2025-09-23/132__art_1                              | Capo I > art. 1 |  |

**Summary `hybrid`**: gold attuali nei top-10 = **0/3** · gold proposti nei top-10 = **0/3**

Rank per ciascun gold proposto:
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → fuori top-10
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167` → fuori top-10
- `eli/reg/2016/679/oj__art_22` → fuori top-10

## Modalità: `hybrid_rrk20`

| rank | score   | chunk_id                                                                  | hierarchy | flag |
|------|---------|---------------------------------------------------------------------------|-----------|------|
|    1 |  0.3184 | eli/reg/2024/1689/oj__recital_57                                          | Considerando 57 |  |
|    2 |  0.3152 | akn/it/act/legge/stato/2025-09-23/132__art_11                             | Capo II > art. 11 |  |
|    3 |  0.3083 | akn/it/act/legge/stato/2025-09-23/132__art_1                              | Capo I > art. 1 |  |
|    4 |  0.2261 | eli/reg/2024/1689/oj__annex_III__point_4                                  | Allegato III - Sistemi di IA ad alto rischio di cui all'a... |  |
|    5 |  0.1957 | eli/reg/2024/1689/oj__recital_85                                          | Considerando 85 |  |
|    6 |  0.1861 | eli/reg/2024/1689/oj__recital_92                                          | Considerando 92 |  |
|    7 |  0.1392 | eli/reg/2024/1689/oj__recital_91                                          | Considerando 91 |  |
|    8 |  0.1344 | akn/it/act/legge/stato/2025-09-23/132__art_12                             | Capo II > art. 12 |  |
|    9 |  0.1018 | akn/it/act/legge/stato/2025-09-23/132__art_7                              | Capo II > art. 7 |  |
|   10 |  0.0969 | eli/reg/2024/1689/oj__recital_93                                          | Considerando 93 |  |

**Summary `hybrid_rrk20`**: gold attuali nei top-10 = **0/3** · gold proposti nei top-10 = **0/3**

Rank per ciascun gold proposto:
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → fuori top-10
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167` → fuori top-10
- `eli/reg/2016/679/oj__art_22` → fuori top-10

## Verdetto preliminare

**0/3 gold proposti nei top-10 di hybrid_rrk20**. Fix annotazione corregge la pertinenza giuridica ma Q5 resta zero-recall: il retrieval non vede i chunk proposti. Problema separato di retrieval / parser / chunking / vocabolario da diagnosticare prima di ri-annotare il gold.

