# PRE_FIX_DIAG v1.1 — corpus check + filtered retrieval

Branch: `diag/pre-fix-v1-1`. Nessun judge, nessuna generation, nessun commit a main.

## Parte 1 — Q25 corpus check (6 query)

Source retrieval: F.2 archived (`ragas_pipeline_outputs_v2.json`, config produttiva v1.0 hybrid RRF + bge-reranker-v2-m3, top_k=20).

### Q24

**Query**: Il modello organizzativo 231 deve essere aggiornato per coprire i rischi connessi all'uso di sistemi AI per decisioni HR?

**Gold attesi** (3 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6`  _(D.Lgs 231/2001)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7`  _(D.Lgs 231/2001)_
- `eli/reg/2024/1689/oj__art_26`  _(AI Act)_

**Gold position nei top-20 produttivi v1.0** (F.2 archived):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` → **ASSENTE** in top-20
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7` → **ASSENTE** in top-20
- `eli/reg/2024/1689/oj__art_26` → rank 15 (score 0.0118)

**Corpus check e riferimenti c.p.** (fetch da Qdrant):

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

**`eli/reg/2024/1689/oj__art_26`**
- Norma: AI Act
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 15
- Riferimenti c.p. nel testo: nessuno rilevato

### Q25

**Query**: Un dipendente accede abusivamente al sistema informatico di un concorrente per favorire l'azienda: l'ente risponde ai sensi del 231?

**Gold attesi** (2 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`  _(D.Lgs 231/2001)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5`  _(D.Lgs 231/2001)_

**Gold position nei top-20 produttivi v1.0** (F.2 archived):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → **ASSENTE** in top-20
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5` → rank 1 (score 0.0921)

**Corpus check e riferimenti c.p.** (fetch da Qdrant):

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 1
- Riferimenti c.p. nel testo: nessuno rilevato

### Q26

**Query**: art 24-bis 231 delitti informatici

**Gold attesi** (1 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`  _(D.Lgs 231/2001)_

**Gold position nei top-20 produttivi v1.0** (F.2 archived):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → rank 1 (score 0.9664)

**Corpus check e riferimenti c.p.** (fetch da Qdrant):

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 1
- Riferimenti c.p. nel testo: nessuno rilevato

### Q27

**Query**: art 25-undecies reati ambientali

**Gold attesi** (2 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6`  _(D.Lgs 231/2001)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8`  _(D.Lgs 231/2001)_

**Gold position nei top-20 produttivi v1.0** (F.2 archived):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6` → rank 1 (score 0.9770)
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` → rank 2 (score 0.9716)

**Corpus check e riferimenti c.p.** (fetch da Qdrant):

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 1
- Riferimenti c.p. nel testo: nessuno rilevato

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 2
- Riferimenti c.p. nel testo: nessuno rilevato

### Q76

**Query**: Una società ha subito un accesso abusivo a un proprio sistema informatico contenente dati personali di clienti: il fatto può attivare la responsabilità amministrativa dell'ente ex art. 24-bis del D.Lgs 231/2001, e quali misure del modello organizzativo si raccordano con gli obblighi di sicurezza e accountability previsti dal GDPR?

**Gold attesi** (4 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`  _(D.Lgs 231/2001)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6`  _(D.Lgs 231/2001)_
- `eli/reg/2016/679/oj__art_5`  _(GDPR)_
- `eli/reg/2016/679/oj__art_32`  _(GDPR)_

**Gold position nei top-20 produttivi v1.0** (F.2 archived):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` → **ASSENTE** in top-20
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` → rank 5 (score 0.0540)
- `eli/reg/2016/679/oj__art_5` → **ASSENTE** in top-20
- `eli/reg/2016/679/oj__art_32` → **ASSENTE** in top-20

**Corpus check e riferimenti c.p.** (fetch da Qdrant):

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 5
- Riferimenti c.p. nel testo: nessuno rilevato

**`eli/reg/2016/679/oj__art_5`**
- Norma: GDPR
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

**`eli/reg/2016/679/oj__art_32`**
- Norma: GDPR
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

### Q85

**Query**: Quali fattispecie penali in materia di corruzione e concussione sono inserite nell'elenco dei reati-presupposto del D.Lgs 231/2001 e in quali articoli sono richiamate?

**Gold attesi** (2 chunk):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25`  _(D.Lgs 231/2001)_
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-ter`  _(D.Lgs 231/2001)_

**Gold position nei top-20 produttivi v1.0** (F.2 archived):
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25` → rank 4 (score 0.0104)
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-ter` → **ASSENTE** in top-20

**Corpus check e riferimenti c.p.** (fetch da Qdrant):

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: ✅ TROVATO — rank 4
- Riferimenti c.p. nel testo: nessuno rilevato

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-ter`**
- Norma: D.Lgs 231/2001
- In corpus: sì
- Classificazione: 🟡 RETRIEVAL GAP — in corpus ma non nei top-20
- Riferimenti c.p. nel testo: nessuno rilevato

### Tabella sintetica Parte 1

| qid | chunk_id | in corpus? | rank top-20 | classificazione | ref c.p. |
|---|---|:---:|:---:|---|---|
| Q24 | `…art_6` | ✅ | ASSENTE | RETRIEVAL GAP | — |
| Q24 | `…art_7` | ✅ | ASSENTE | RETRIEVAL GAP | — |
| Q24 | `…art_26` | ✅ | 15 | trovato rank 15 | — |
| Q25 | `…art_24-bis` | ✅ | ASSENTE | RETRIEVAL GAP | — |
| Q25 | `…art_5` | ✅ | 1 | trovato rank 1 | — |
| Q26 | `…art_24-bis` | ✅ | 1 | trovato rank 1 | — |
| Q27 | `…paras_1_6` | ✅ | 1 | trovato rank 1 | — |
| Q27 | `…paras_7_8` | ✅ | 2 | trovato rank 2 | — |
| Q76 | `…art_24-bis` | ✅ | ASSENTE | RETRIEVAL GAP | — |
| Q76 | `…art_6` | ✅ | 5 | trovato rank 5 | — |
| Q76 | `…art_5` | ✅ | ASSENTE | RETRIEVAL GAP | — |
| Q76 | `…art_32` | ✅ | ASSENTE | RETRIEVAL GAP | — |
| Q85 | `…art_25` | ✅ | 4 | trovato rank 4 | — |
| Q85 | `…art_25-ter` | ✅ | ASSENTE | RETRIEVAL GAP | — |

**Conteggio**: 0 corpus gap · 7 retrieval gap · 7 trovati nei top-20 (totale gold: 14)

---

## Parte 2 — Q68-Q71 filtered retrieval per-norma

Payload schema Qdrant: nessun payload index (`payload_schema={}`). Filtro su `doc_urn` via full scan — funzionale per diagnostica.

### Q68 — Filtered retrieval per norme assenti

**Query**: Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: qua

**Gold totali**: 5 · **Assenti in globale v1.0**: 4

#### Norma: AI Act
- `doc_urn` filtro: `eli/reg/2024/1689/oj`
- Gold attesi in questa norma: `eli/reg/2024/1689/oj__art_6`, `eli/reg/2024/1689/oj__art_27`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2024/1689/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_179` | 0.1287 | - |
| 2 | `eli/reg/2024/1689/oj__art_1` | 0.0202 | - |
| 3 | `eli/reg/2024/1689/oj__recital_140` | 0.0178 | - |
| 4 | `eli/reg/2024/1689/oj__recital_119` | 0.0110 | - |
| 5 | `eli/reg/2024/1689/oj__recital_7` | 0.0089 | - |
| 6 | `eli/reg/2024/1689/oj__recital_114` | 0.0085 | - |
| 7 | `eli/reg/2024/1689/oj__art_111` | 0.0055 | - |
| 8 | `eli/reg/2024/1689/oj__recital_27` | 0.0053 | - |
| 9 | `eli/reg/2024/1689/oj__art_49` | 0.0026 | - |
| 10 | `eli/reg/2024/1689/oj__recital_58` | 0.0016 | - |

**Gold `eli/reg/2024/1689/oj__art_6`** → filtered rank: ASSENTE
**Gold `eli/reg/2024/1689/oj__art_27`** → filtered rank: ASSENTE

#### Norma: GDPR
- `doc_urn` filtro: `eli/reg/2016/679/oj`
- Gold attesi in questa norma: `eli/reg/2016/679/oj__art_9`, `eli/reg/2016/679/oj__art_35`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2016/679/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2016/679/oj__recital_91` | 0.0076 | - |
| 2 | `eli/reg/2016/679/oj__recital_94` | 0.0058 | - |
| 3 | `eli/reg/2016/679/oj__art_35` | 0.0016 | ✓ |
| 4 | `eli/reg/2016/679/oj__recital_168` | 0.0013 | - |
| 5 | `eli/reg/2016/679/oj__recital_81` | 0.0013 | - |
| 6 | `eli/reg/2016/679/oj__art_28` | 0.0012 | - |
| 7 | `eli/reg/2016/679/oj__recital_79` | 0.0011 | - |
| 8 | `eli/reg/2016/679/oj__art_24` | 0.0011 | - |
| 9 | `eli/reg/2016/679/oj__art_5` | 0.0009 | - |
| 10 | `eli/reg/2016/679/oj__recital_129` | 0.0008 | - |

**Gold `eli/reg/2016/679/oj__art_9`** → filtered rank: ASSENTE
**Gold `eli/reg/2016/679/oj__art_35`** → filtered rank: rank 3

### Q69 — Filtered retrieval per norme assenti

**Query**: Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare 

**Gold totali**: 5 · **Assenti in globale v1.0**: 5

#### Norma: AI Act
- `doc_urn` filtro: `eli/reg/2024/1689/oj`
- Gold attesi in questa norma: `eli/reg/2024/1689/oj__art_6`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2024/1689/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_83` | 0.4678 | - |
| 2 | `eli/reg/2024/1689/oj__recital_68` | 0.1800 | - |
| 3 | `eli/reg/2024/1689/oj__art_1` | 0.1786 | - |
| 4 | `eli/reg/2024/1689/oj__recital_85` | 0.1520 | - |
| 5 | `eli/reg/2024/1689/oj__recital_140` | 0.1421 | - |
| 6 | `eli/reg/2024/1689/oj__recital_132` | 0.1285 | - |
| 7 | `eli/reg/2024/1689/oj__recital_58` | 0.1158 | - |
| 8 | `eli/reg/2024/1689/oj__art_3` | 0.1046 | - |
| 9 | `eli/reg/2024/1689/oj__recital_157` | 0.0990 | - |
| 10 | `eli/reg/2024/1689/oj__art_2` | 0.0902 | - |

**Gold `eli/reg/2024/1689/oj__art_6`** → filtered rank: ASSENTE

#### Norma: GDPR
- `doc_urn` filtro: `eli/reg/2016/679/oj`
- Gold attesi in questa norma: `eli/reg/2016/679/oj__art_9`, `eli/reg/2016/679/oj__art_35`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2016/679/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2016/679/oj__recital_53` | 0.0404 | - |
| 2 | `eli/reg/2016/679/oj__recital_91` | 0.0287 | - |
| 3 | `eli/reg/2016/679/oj__recital_63` | 0.0072 | - |
| 4 | `eli/reg/2016/679/oj__recital_97` | 0.0066 | - |
| 5 | `eli/reg/2016/679/oj__recital_19` | 0.0060 | - |
| 6 | `eli/reg/2016/679/oj__recital_2` | 0.0043 | - |
| 7 | `eli/reg/2016/679/oj__art_4` | 0.0042 | - |
| 8 | `eli/reg/2016/679/oj__art_9` | 0.0040 | ✓ |
| 9 | `eli/reg/2016/679/oj__art_47` | 0.0038 | - |
| 10 | `eli/reg/2016/679/oj__recital_173` | 0.0034 | - |

**Gold `eli/reg/2016/679/oj__art_9`** → filtered rank: rank 8
**Gold `eli/reg/2016/679/oj__art_35`** → filtered rank: ASSENTE

#### Norma: NIS2
- `doc_urn` filtro: `akn/it/act/decreto_legislativo/stato/2024-09-04/138`
- Gold attesi in questa norma: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`, `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25`

**Top-10 retrieval con filter** `doc_urn=akn/it/act/decreto_legislativo/stato/2024-09-04/138`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_31` | 0.1960 | - |
| 2 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_34` | 0.0677 | - |
| 3 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_35` | 0.0465 | - |
| 4 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_1_11` | 0.0382 | - |
| 5 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_14` | 0.0202 | - |
| 6 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_8` | 0.0172 | - |
| 7 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_11` | 0.0167 | - |
| 8 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_37` | 0.0158 | - |
| 9 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_18` | 0.0133 | - |
| 10 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_39` | 0.0111 | - |

**Gold `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`** → filtered rank: ASSENTE
**Gold `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25`** → filtered rank: ASSENTE

### Q70 — Filtered retrieval per norme assenti

**Query**: Una banca italiana intende affidare in outsourcing a un fornitore extra-UE la gestione di un sistema di IA per il rileva

**Gold totali**: 5 · **Assenti in globale v1.0**: 4

#### Norma: D.Lgs 231/2001
- `doc_urn` filtro: `akn/it/act/decreto_legislativo/stato/2001-06-08/231`
- Gold attesi in questa norma: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies`

**Top-10 retrieval con filter** `doc_urn=akn/it/act/decreto_legislativo/stato/2001-06-08/231`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-duodevicies` | 0.0015 | - |
| 2 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies.2` | 0.0004 | - |
| 3 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24` | 0.0003 | - |
| 4 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` | 0.0003 | - |
| 5 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_82` | 0.0003 | - |
| 6 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies` | 0.0002 | ✓ |
| 7 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7` | 0.0002 | - |
| 8 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_75` | 0.0002 | - |
| 9 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-quinquiesdecies` | 0.0002 | - |
| 10 | `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_80` | 0.0002 | - |

**Gold `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies`** → filtered rank: rank 6

#### Norma: GDPR
- `doc_urn` filtro: `eli/reg/2016/679/oj`
- Gold attesi in questa norma: `eli/reg/2016/679/oj__art_44`, `eli/reg/2016/679/oj__art_28`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2016/679/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2016/679/oj__recital_23` | 0.0015 | - |
| 2 | `eli/reg/2016/679/oj__recital_78` | 0.0014 | - |
| 3 | `eli/reg/2016/679/oj__recital_19` | 0.0011 | - |
| 4 | `eli/reg/2016/679/oj__recital_72` | 0.0011 | - |
| 5 | `eli/reg/2016/679/oj__recital_22` | 0.0007 | - |
| 6 | `eli/reg/2016/679/oj__recital_168` | 0.0007 | - |
| 7 | `eli/reg/2016/679/oj__recital_24` | 0.0006 | - |
| 8 | `eli/reg/2016/679/oj__recital_21` | 0.0005 | - |
| 9 | `eli/reg/2016/679/oj__recital_100` | 0.0004 | - |
| 10 | `eli/reg/2016/679/oj__art_30` | 0.0003 | - |

**Gold `eli/reg/2016/679/oj__art_44`** → filtered rank: ASSENTE
**Gold `eli/reg/2016/679/oj__art_28`** → filtered rank: ASSENTE

#### Norma: NIS2
- `doc_urn` filtro: `akn/it/act/decreto_legislativo/stato/2024-09-04/138`
- Gold attesi in questa norma: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`

**Top-10 retrieval con filter** `doc_urn=akn/it/act/decreto_legislativo/stato/2024-09-04/138`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_11` | 0.0093 | - |
| 2 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_28` | 0.0026 | - |
| 3 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_31` | 0.0019 | - |
| 4 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_35` | 0.0019 | - |
| 5 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_14` | 0.0017 | - |
| 6 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_42` | 0.0016 | - |
| 7 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_1` | 0.0015 | - |
| 8 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_21` | 0.0015 | - |
| 9 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_8` | 0.0009 | - |
| 10 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_3` | 0.0008 | - |

**Gold `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`** → filtered rank: ASSENTE

### Q71 — Filtered retrieval per norme assenti

**Query**: Una regione italiana intende mettere in produzione un sistema di IA per supportare l'attribuzione di punteggi nelle grad

**Gold totali**: 5 · **Assenti in globale v1.0**: 4

#### Norma: AI Act
- `doc_urn` filtro: `eli/reg/2024/1689/oj`
- Gold attesi in questa norma: `eli/reg/2024/1689/oj__art_27`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2024/1689/oj`:

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
| 9 | `eli/reg/2024/1689/oj__recital_130` | 0.0308 | - |
| 10 | `eli/reg/2024/1689/oj__recital_68` | 0.0283 | - |

**Gold `eli/reg/2024/1689/oj__art_27`** → filtered rank: ASSENTE

#### Norma: GDPR
- `doc_urn` filtro: `eli/reg/2016/679/oj`
- Gold attesi in questa norma: `eli/reg/2016/679/oj__art_22`

**Top-10 retrieval con filter** `doc_urn=eli/reg/2016/679/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2016/679/oj__recital_72` | 0.0063 | - |
| 2 | `eli/reg/2016/679/oj__recital_2` | 0.0024 | - |
| 3 | `eli/reg/2016/679/oj__recital_53` | 0.0012 | - |
| 4 | `eli/reg/2016/679/oj__art_4` | 0.0010 | - |
| 5 | `eli/reg/2016/679/oj__recital_97` | 0.0009 | - |
| 6 | `eli/reg/2016/679/oj__art_2` | 0.0008 | - |
| 7 | `eli/reg/2016/679/oj__recital_23` | 0.0007 | - |
| 8 | `eli/reg/2016/679/oj__recital_173` | 0.0007 | - |
| 9 | `eli/reg/2016/679/oj__recital_63` | 0.0006 | - |
| 10 | `eli/reg/2016/679/oj__recital_92` | 0.0005 | - |

**Gold `eli/reg/2016/679/oj__art_22`** → filtered rank: ASSENTE

#### Norma: L. 132/2025
- `doc_urn` filtro: `akn/it/act/legge/stato/2025-09-23/132`
- Gold attesi in questa norma: `akn/it/act/legge/stato/2025-09-23/132__art_3`

**Top-10 retrieval con filter** `doc_urn=akn/it/act/legge/stato/2025-09-23/132`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/legge/stato/2025-09-23/132__art_16` | 0.0110 | - |
| 2 | `akn/it/act/legge/stato/2025-09-23/132__art_7` | 0.0087 | - |
| 3 | `akn/it/act/legge/stato/2025-09-23/132__art_3` | 0.0052 | ✓ |
| 4 | `akn/it/act/legge/stato/2025-09-23/132__art_15` | 0.0034 | - |
| 5 | `akn/it/act/legge/stato/2025-09-23/132__art_4` | 0.0033 | - |
| 6 | `akn/it/act/legge/stato/2025-09-23/132__art_2` | 0.0026 | - |
| 7 | `akn/it/act/legge/stato/2025-09-23/132__art_1` | 0.0023 | - |
| 8 | `akn/it/act/legge/stato/2025-09-23/132__art_10` | 0.0016 | - |
| 9 | `akn/it/act/legge/stato/2025-09-23/132__art_5` | 0.0014 | - |
| 10 | `akn/it/act/legge/stato/2025-09-23/132__art_24` | 0.0011 | - |

**Gold `akn/it/act/legge/stato/2025-09-23/132__art_3`** → filtered rank: rank 3

#### Norma: NIS2
- `doc_urn` filtro: `akn/it/act/decreto_legislativo/stato/2024-09-04/138`
- Gold attesi in questa norma: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`

**Top-10 retrieval con filter** `doc_urn=akn/it/act/decreto_legislativo/stato/2024-09-04/138`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_42` | 0.0023 | - |
| 2 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_11` | 0.0023 | - |
| 3 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_31` | 0.0021 | - |
| 4 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_30` | 0.0020 | - |
| 5 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_35` | 0.0015 | - |
| 6 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_14` | 0.0012 | - |
| 7 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_18` | 0.0010 | - |
| 8 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_5` | 0.0007 | - |
| 9 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_39` | 0.0007 | - |
| 10 | `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_22` | 0.0006 | - |

**Gold `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`** → filtered rank: ASSENTE

### Tabella sintetica Parte 2

| Query | Norma | Gold chunk | Rank globale v1.0 | Rank filtered |
|---|---|---|:---:|:---:|
| Q68 | AI Act | `…art_6` | ASSENTE | ASSENTE |
| Q68 | AI Act | `…art_27` | ASSENTE | ASSENTE |
| Q68 | GDPR | `…art_9` | ASSENTE | ASSENTE |
| Q68 | GDPR | `…art_35` | ASSENTE | rank 3 |
| Q69 | AI Act | `…art_6` | ASSENTE | ASSENTE |
| Q69 | GDPR | `…art_9` | ASSENTE | rank 8 |
| Q69 | GDPR | `…art_35` | ASSENTE | ASSENTE |
| Q69 | NIS2 | `…art_24` | ASSENTE | ASSENTE |
| Q69 | NIS2 | `…art_25` | ASSENTE | ASSENTE |
| Q70 | D.Lgs 231/2001 | `…art_25-octies` | ASSENTE | rank 6 |
| Q70 | GDPR | `…art_44` | ASSENTE | ASSENTE |
| Q70 | GDPR | `…art_28` | ASSENTE | ASSENTE |
| Q70 | NIS2 | `…art_24` | ASSENTE | ASSENTE |
| Q71 | AI Act | `…art_27` | ASSENTE | ASSENTE |
| Q71 | GDPR | `…art_22` | ASSENTE | ASSENTE |
| Q71 | L. 132/2025 | `…art_3` | ASSENTE | rank 3 |
| Q71 | NIS2 | `…art_24` | ASSENTE | ASSENTE |

**Filtered rescue ratio**: 4/17 gold trovati in filtered top-10 / gold ASSENTI in globale top-20

---

## Sintesi numerica

### Parte 1 — corpus gap vs retrieval gap (6 query, gold 231 e cross-norma)

- Gold totali analizzati: **14**
- Corpus gap (chunk non in Qdrant): **0**
- Retrieval gap (in corpus, non nei top-20): **7**
- Trovati nei top-20: **7**

### Parte 2 — filtered rescue ratio (Q68-Q71)

- Gold ASSENTI in globale top-20 analizzati: **17**
- Trovati in filtered top-10: **4**
- Filtered rescue ratio: **4/17**
