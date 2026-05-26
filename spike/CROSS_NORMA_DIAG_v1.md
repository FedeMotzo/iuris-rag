# Cross-norma retrieval diagnosis — 7 query problematiche v1.0

Retrieval-only su config produttiva v1.0 (hybrid RRF + bge-reranker-v2-m3, top_k=20, rerank_top_k=20). Nessuna generation, nessun judge. Source gold: `data/benchmark/gold_answers_v3.json`.

## Q5 — L'uso di sistemi AI per decisioni che riguardano i lavoratori può attivare respo

**Tipo query**: `edge`

**Query**: L'uso di sistemi AI per decisioni che riguardano i lavoratori può attivare responsabilità ai sensi del D.Lgs 231/2001?

**Gold attesi** (0 chunk):
- (nessuno: query `edge`/`negative`)

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_57` | 0.3184 | - |
| 2 | `akn/it/act/legge/stato/2025-09-23/132__art_11` | 0.3152 | - |
| 3 | `akn/it/act/legge/stato/2025-09-23/132__art_1` | 0.3083 | - |
| 4 | `eli/reg/2024/1689/oj__annex_III__point_4` | 0.2261 | - |
| 5 | `eli/reg/2024/1689/oj__recital_85` | 0.1957 | - |
| 6 | `eli/reg/2024/1689/oj__recital_92` | 0.1861 | - |
| 7 | `eli/reg/2024/1689/oj__recital_91` | 0.1392 | - |
| 8 | `akn/it/act/legge/stato/2025-09-23/132__art_12` | 0.1344 | - |
| 9 | `akn/it/act/legge/stato/2025-09-23/132__art_7` | 0.1018 | - |
| 10 | `eli/reg/2024/1689/oj__recital_93` | 0.0969 | - |
| 11 | `akn/it/act/legge/stato/2025-09-23/132__art_13` | 0.0547 | - |
| 12 | `eli/reg/2024/1689/oj__recital_9` | 0.0526 | - |
| 13 | `eli/reg/2024/1689/oj__recital_1` | 0.0498 | - |
| 14 | `akn/it/act/legge/stato/2025-09-23/132__art_15` | 0.0481 | - |
| 15 | `eli/reg/2024/1689/oj__art_2` | 0.0200 | - |
| 16 | `eli/reg/2024/1689/oj__art_26` | 0.0094 | - |
| 17 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` | 0.0067 | - |
| 18 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies` | 0.0036 | - |
| 19 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_175` | 0.0010 | - |
| 20 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_152` | 0.0008 | - |

**Gold position**: n/a (gold vuoto)

**Norme rappresentate nei top-20**:
- AI Act: 10
- L. 132/2025: 6
- Codice Privacy: 2
- D.Lgs 231/2001: 2

## Q9 — Quali sono i reati presupposto in materia di trattamento illecito di dati person

**Tipo query**: `positive`

**Query**: Quali sono i reati presupposto in materia di trattamento illecito di dati personali ai sensi del 231?

**Gold attesi** (1 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`  _(D.Lgs 231/2001)_

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167` | 0.1915 | - |
| 2 | `eli/reg/2016/679/oj__recital_75` | 0.1683 | - |
| 3 | `eli/reg/2016/679/oj__recital_19` | 0.0822 | - |
| 4 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies` | 0.0585 | - |
| 5 | `eli/reg/2016/679/oj__recital_43` | 0.0463 | - |
| 6 | `eli/reg/2016/679/oj__art_5` | 0.0444 | - |
| 7 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-ter` | 0.0354 | - |
| 8 | `eli/reg/2016/679/oj__recital_2` | 0.0284 | - |
| 9 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_58` | 0.0274 | - |
| 10 | `eli/reg/2016/679/oj__art_18` | 0.0264 | - |
| 11 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_17` | 0.0213 | - |
| 12 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` | 0.0135 | - |
| 13 | `eli/reg/2016/679/oj__art_1` | 0.0134 | - |
| 14 | `eli/reg/2016/679/oj__art_21` | 0.0117 | - |
| 15 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-novies` | 0.0111 | - |
| 16 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_15` | 0.0089 | - |
| 17 | `akn/it/act/legge/stato/2025-09-23/132__art_4` | 0.0071 | - |
| 18 | `eli/reg/2016/679/oj__art_25` | 0.0057 | - |
| 19 | `eli/reg/2024/1689/oj__recital_141` | 0.0038 | - |
| 20 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_36` | 0.0007 | - |

**Gold position**:
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → ASSENTE

**Norme rappresentate nei top-20**:
- GDPR: 9
- Codice Privacy: 5
- D.Lgs 231/2001: 4
- AI Act: 1
- L. 132/2025: 1

## Q25 — Un dipendente accede abusivamente al sistema informatico di un concorrente per f

**Tipo query**: `positive`

**Query**: Un dipendente accede abusivamente al sistema informatico di un concorrente per favorire l'azienda: l'ente risponde ai sensi del 231?

**Gold attesi** (2 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`  _(D.Lgs 231/2001)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5`  _(D.Lgs 231/2001)_

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5` | 0.0921 | ✓ |
| 2 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_45` | 0.0523 | - |
| 3 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_15` | 0.0193 | - |
| 4 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` | 0.0153 | - |
| 5 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` | 0.0082 | - |
| 6 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_26` | 0.0076 | - |
| 7 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_27` | 0.0070 | - |
| 8 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_29` | 0.0030 | - |
| 9 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_31` | 0.0026 | - |
| 10 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_33` | 0.0017 | - |
| 11 | `eli/reg/2024/1689/oj__recital_23` | 0.0016 | - |
| 12 | `eli/reg/2024/1689/oj__recital_170` | 0.0009 | - |
| 13 | `eli/reg/2024/1689/oj__recital_21` | 0.0009 | - |
| 14 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_35` | 0.0006 | - |
| 15 | `eli/reg/2016/679/oj__art_82` | 0.0005 | - |
| 16 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_132-ter` | 0.0005 | - |
| 17 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` | 0.0003 | - |
| 18 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_156` | 0.0002 | - |
| 19 | `eli/reg/2024/1689/oj__recital_2` | 0.0002 | - |
| 20 | `eli/reg/2016/679/oj__recital_21` | 0.0001 | - |

**Gold position**:
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → ASSENTE
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5` → rank 1

**Norme rappresentate nei top-20**:
- D.Lgs 231/2001: 11
- AI Act: 4
- Codice Privacy: 2
- GDPR: 2
- NIS2: 1

## Q68 — Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportar

**Tipo query**: `positive`

**Query**: Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?

**Gold attesi** (5 chunk):
- `eli/reg/2024/1689/oj__art_6`  _(AI Act)_
- `eli/reg/2024/1689/oj__art_27`  _(AI Act)_
- `eli/reg/2016/679/oj__art_9`  _(GDPR)_
- `eli/reg/2016/679/oj__art_35`  _(GDPR)_
- `akn/it/act/legge/stato/2025-09-23/132__art_7`  _(L. 132/2025)_

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_179` | 0.1287 | - |
| 2 | `akn/it/act/legge/stato/2025-09-23/132__art_7` | 0.0872 | ✓ |
| 3 | `eli/reg/2024/1689/oj__art_1` | 0.0202 | - |
| 4 | `eli/reg/2024/1689/oj__recital_140` | 0.0178 | - |
| 5 | `eli/reg/2024/1689/oj__recital_119` | 0.0110 | - |
| 6 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_132` | 0.0103 | - |
| 7 | `eli/reg/2024/1689/oj__recital_7` | 0.0089 | - |
| 8 | `eli/reg/2024/1689/oj__art_111` | 0.0055 | - |
| 9 | `eli/reg/2024/1689/oj__art_49` | 0.0026 | - |
| 10 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies` | 0.0014 | - |
| 11 | `eli/reg/2024/1689/oj__art_108` | 0.0011 | - |
| 12 | `eli/reg/2024/1689/oj__recital_97` | 0.0011 | - |
| 13 | `eli/reg/2024/1689/oj__art_109` | 0.0005 | - |
| 14 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_37` | 0.0004 | - |
| 15 | `eli/reg/2024/1689/oj__art_107` | 0.0004 | - |
| 16 | `eli/reg/2024/1689/oj__art_104` | 0.0004 | - |
| 17 | `eli/reg/2024/1689/oj__art_103` | 0.0004 | - |
| 18 | `eli/reg/2016/679/oj__recital_162` | 0.0003 | - |
| 19 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_153` | 0.0002 | - |
| 20 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_33` | 0.0001 | - |

**Gold position**:
- `eli/reg/2024/1689/oj__art_6` → ASSENTE
- `eli/reg/2024/1689/oj__art_27` → ASSENTE
- `eli/reg/2016/679/oj__art_9` → ASSENTE
- `eli/reg/2016/679/oj__art_35` → ASSENTE
- `akn/it/act/legge/stato/2025-09-23/132__art_7` → rank 2

**Norme rappresentate nei top-20**:
- AI Act: 13
- Codice Privacy: 3
- D.Lgs 231/2001: 1
- GDPR: 1
- L. 132/2025: 1
- NIS2: 1

## Q69 — Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per 

**Tipo query**: `positive`

**Query**: Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare un sistema di IA per supportare le attività di farmacovigilanza con dati provenienti da operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai sensi di AI Act, GDPR e NIS2?

**Gold attesi** (5 chunk):
- `eli/reg/2024/1689/oj__art_6`  _(AI Act)_
- `eli/reg/2016/679/oj__art_9`  _(GDPR)_
- `eli/reg/2016/679/oj__art_35`  _(GDPR)_
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`  _(NIS2)_
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25`  _(NIS2)_

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_83` | 0.4678 | - |
| 2 | `akn/it/act/legge/stato/2025-09-23/132__art_7` | 0.2657 | - |
| 3 | `eli/reg/2024/1689/oj__recital_68` | 0.1800 | - |
| 4 | `eli/reg/2024/1689/oj__art_1` | 0.1786 | - |
| 5 | `eli/reg/2024/1689/oj__recital_85` | 0.1520 | - |
| 6 | `eli/reg/2024/1689/oj__recital_140` | 0.1421 | - |
| 7 | `eli/reg/2024/1689/oj__recital_58` | 0.1158 | - |
| 8 | `eli/reg/2024/1689/oj__recital_157` | 0.0990 | - |
| 9 | `eli/reg/2024/1689/oj__art_2` | 0.0902 | - |
| 10 | `eli/reg/2024/1689/oj__art_25` | 0.0842 | - |
| 11 | `eli/reg/2024/1689/oj__recital_88` | 0.0808 | - |
| 12 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-sexies` | 0.0752 | - |
| 13 | `eli/reg/2024/1689/oj__recital_8` | 0.0610 | - |
| 14 | `eli/reg/2024/1689/oj__recital_27` | 0.0540 | - |
| 15 | `eli/reg/2024/1689/oj__art_74` | 0.0399 | - |
| 16 | `eli/reg/2024/1689/oj__art_75` | 0.0306 | - |
| 17 | `eli/reg/2024/1689/oj__annex_III__point_5` | 0.0246 | - |
| 18 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_14` | 0.0202 | - |
| 19 | `akn/it/act/legge/stato/2025-09-23/132__art_9` | 0.0068 | - |
| 20 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_3` | 0.0018 | - |

**Gold position**:
- `eli/reg/2024/1689/oj__art_6` → ASSENTE
- `eli/reg/2016/679/oj__art_9` → ASSENTE
- `eli/reg/2016/679/oj__art_35` → ASSENTE
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24` → ASSENTE
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25` → ASSENTE

**Norme rappresentate nei top-20**:
- AI Act: 15
- L. 132/2025: 2
- NIS2: 2
- Codice Privacy: 1

## Q70 — Una banca italiana intende affidare in outsourcing a un fornitore extra-UE la ge

**Tipo query**: `positive`

**Query**: Una banca italiana intende affidare in outsourcing a un fornitore extra-UE la gestione di un sistema di IA per il rilevamento di operazioni sospette di riciclaggio: quali profili AI Act, GDPR, NIS2 e 231 deve considerare in fase di selezione del fornitore?

**Gold attesi** (5 chunk):
- `eli/reg/2024/1689/oj__art_25`  _(AI Act)_
- `eli/reg/2016/679/oj__art_44`  _(GDPR)_
- `eli/reg/2016/679/oj__art_28`  _(GDPR)_
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`  _(NIS2)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies`  _(D.Lgs 231/2001)_

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_86` | 0.1926 | - |
| 2 | `eli/reg/2024/1689/oj__recital_131` | 0.1850 | - |
| 3 | `eli/reg/2024/1689/oj__recital_70` | 0.1650 | - |
| 4 | `eli/reg/2024/1689/oj__art_25` | 0.1240 | ✓ |
| 5 | `eli/reg/2024/1689/oj__art_3` | 0.1101 | - |
| 6 | `eli/reg/2024/1689/oj__art_49` | 0.1045 | - |
| 7 | `eli/reg/2024/1689/oj__recital_122` | 0.0931 | - |
| 8 | `eli/reg/2024/1689/oj__recital_81` | 0.0843 | - |
| 9 | `eli/reg/2024/1689/oj__recital_22` | 0.0810 | - |
| 10 | `eli/reg/2024/1689/oj__recital_23` | 0.0708 | - |
| 11 | `eli/reg/2024/1689/oj__recital_21` | 0.0700 | - |
| 12 | `eli/reg/2024/1689/oj__art_80` | 0.0635 | - |
| 13 | `eli/reg/2024/1689/oj__recital_140` | 0.0579 | - |
| 14 | `eli/reg/2024/1689/oj__art_16` | 0.0450 | - |
| 15 | `eli/reg/2024/1689/oj__recital_53` | 0.0442 | - |
| 16 | `eli/reg/2024/1689/oj__art_10` | 0.0408 | - |
| 17 | `eli/reg/2024/1689/oj__art_71` | 0.0333 | - |
| 18 | `eli/reg/2024/1689/oj__recital_93` | 0.0323 | - |
| 19 | `eli/reg/2024/1689/oj__art_74` | 0.0152 | - |
| 20 | `eli/reg/2024/1689/oj__art_47` | 0.0149 | - |

**Gold position**:
- `eli/reg/2024/1689/oj__art_25` → rank 4
- `eli/reg/2016/679/oj__art_44` → ASSENTE
- `eli/reg/2016/679/oj__art_28` → ASSENTE
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24` → ASSENTE
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies` → ASSENTE

**Norme rappresentate nei top-20**:
- AI Act: 20

## Q71 — Una regione italiana intende mettere in produzione un sistema di IA per supporta

**Tipo query**: `positive`

**Query**: Una regione italiana intende mettere in produzione un sistema di IA per supportare l'attribuzione di punteggi nelle graduatorie di accesso ai servizi residenziali per anziani: quali sono i principali profili giuridici da considerare integrando GDPR, AI Act, L. 132/2025 e NIS2?

**Gold attesi** (5 chunk):
- `eli/reg/2024/1689/oj__annex_III__point_5`  _(AI Act)_
- `eli/reg/2024/1689/oj__art_27`  _(AI Act)_
- `eli/reg/2016/679/oj__art_22`  _(GDPR)_
- `akn/it/act/legge/stato/2025-09-23/132__art_3`  _(L. 132/2025)_
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`  _(NIS2)_

**Top-20 retrieval** (config produttiva v1.0):

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_31` | 0.1890 | - |
| 2 | `eli/reg/2024/1689/oj__recital_58` | 0.1781 | - |
| 3 | `eli/reg/2024/1689/oj__recital_140` | 0.1158 | - |
| 4 | `eli/reg/2024/1689/oj__recital_8` | 0.1156 | - |
| 5 | `eli/reg/2024/1689/oj__recital_1` | 0.0910 | - |
| 6 | `eli/reg/2024/1689/oj__recital_27` | 0.0542 | - |
| 7 | `eli/reg/2024/1689/oj__art_111` | 0.0435 | - |
| 8 | `eli/reg/2024/1689/oj__recital_88` | 0.0325 | - |
| 9 | `eli/reg/2024/1689/oj__recital_68` | 0.0283 | - |
| 10 | `eli/reg/2024/1689/oj__recital_7` | 0.0267 | - |
| 11 | `eli/reg/2024/1689/oj__recital_81` | 0.0211 | - |
| 12 | `eli/reg/2024/1689/oj__art_1` | 0.0183 | - |
| 13 | `eli/reg/2024/1689/oj__annex_III__point_5` | 0.0163 | ✓ |
| 14 | `eli/reg/2024/1689/oj__recital_96` | 0.0154 | - |
| 15 | `eli/reg/2024/1689/oj__art_49` | 0.0134 | - |
| 16 | `eli/reg/2024/1689/oj__art_86` | 0.0099 | - |
| 17 | `eli/reg/2024/1689/oj__art_74` | 0.0062 | - |
| 18 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_11` | 0.0023 | - |
| 19 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_132-bis` | 0.0009 | - |
| 20 | `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies` | 0.0006 | - |

**Gold position**:
- `eli/reg/2024/1689/oj__annex_III__point_5` → rank 13
- `eli/reg/2024/1689/oj__art_27` → ASSENTE
- `eli/reg/2016/679/oj__art_22` → ASSENTE
- `akn/it/act/legge/stato/2025-09-23/132__art_3` → ASSENTE
- `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24` → ASSENTE

**Norme rappresentate nei top-20**:
- AI Act: 17
- Codice Privacy: 2
- NIS2: 1

## Pattern osservati

_(da compilare manualmente dopo lettura dei dati)_
