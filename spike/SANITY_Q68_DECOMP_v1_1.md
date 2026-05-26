# Sanity Q68 — decomposition + filter per-norma

Branch: `diag/sanity-q68`. Sub-query scritte a mano. Retrieval hybrid filtered per `doc_urn` (full scan). Nessuna generation, nessun LLM, nessun judge.

**Query originale Q68**: "Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?"

## Sub-query AI Act

**Sub-query**: Classificazione sistema IA ad alto rischio in ambito sanitario, obblighi del fornitore e dell'utilizzatore, valutazione di impatto sui diritti fondamentali (FRIA), conformità ai requisiti dell'AI Act

**Gold attesi in questa norma** (2):
- `eli/reg/2024/1689/oj__art_6`
- `eli/reg/2024/1689/oj__art_27`

**Top-10 retrieval filtered** `doc_urn=eli/reg/2024/1689/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2024/1689/oj__recital_96` | 0.9953 | - |
| 2 | `eli/reg/2024/1689/oj__art_27` | 0.9933 | ✓ |
| 3 | `eli/reg/2024/1689/oj__art_16` | 0.9840 | - |
| 4 | `eli/reg/2024/1689/oj__art_25` | 0.9762 | - |
| 5 | `eli/reg/2024/1689/oj__recital_58` | 0.9689 | - |
| 6 | `eli/reg/2024/1689/oj__recital_52` | 0.9658 | - |
| 7 | `eli/reg/2024/1689/oj__art_6` | 0.9618 | ✓ |
| 8 | `eli/reg/2024/1689/oj__art_24` | 0.9611 | - |
| 9 | `eli/reg/2024/1689/oj__recital_66` | 0.9508 | - |
| 10 | `eli/reg/2024/1689/oj__art_34` | 0.9300 | - |

**Gold position in filtered**:
- `eli/reg/2024/1689/oj__art_6` → rank 7
- `eli/reg/2024/1689/oj__art_27` → rank 2

## Sub-query GDPR

**Sub-query**: Trattamento di dati sanitari come categorie particolari di dati personali, base giuridica art. 9, valutazione d'impatto sulla protezione dei dati (DPIA) per trattamenti automatizzati su larga scala

**Gold attesi in questa norma** (2):
- `eli/reg/2016/679/oj__art_9`
- `eli/reg/2016/679/oj__art_35`

**Top-10 retrieval filtered** `doc_urn=eli/reg/2016/679/oj`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `eli/reg/2016/679/oj__recital_91` | 0.9959 | - |
| 2 | `eli/reg/2016/679/oj__art_9` | 0.9920 | ✓ |
| 3 | `eli/reg/2016/679/oj__art_35` | 0.9857 | ✓ |
| 4 | `eli/reg/2016/679/oj__recital_53` | 0.9725 | - |
| 5 | `eli/reg/2016/679/oj__recital_54` | 0.9147 | - |
| 6 | `eli/reg/2016/679/oj__recital_84` | 0.8615 | - |
| 7 | `eli/reg/2016/679/oj__recital_97` | 0.8078 | - |
| 8 | `eli/reg/2016/679/oj__recital_90` | 0.7443 | - |
| 9 | `eli/reg/2016/679/oj__recital_89` | 0.5742 | - |
| 10 | `eli/reg/2016/679/oj__art_37` | 0.5736 | - |

**Gold position in filtered**:
- `eli/reg/2016/679/oj__art_9` → rank 2
- `eli/reg/2016/679/oj__art_35` → rank 3

## Sub-query L.132/2025

**Sub-query**: Uso di sistemi di intelligenza artificiale in ambito sanitario, principi di tutela della persona, supervisione umana nelle decisioni cliniche

**Gold attesi in questa norma** (1):
- `akn/it/act/legge/stato/2025-09-23/132__art_7`

**Nota**: art_7 era già rank 2 in globale v1.0. Controllo coerenza.

**Top-10 retrieval filtered** `doc_urn=akn/it/act/legge/stato/2025-09-23/132`:

| rank | chunk_id | score | gold? |
|---:|---|---:|:---:|
| 1 | `akn/it/act/legge/stato/2025-09-23/132__art_7` | 0.9910 | ✓ |
| 2 | `akn/it/act/legge/stato/2025-09-23/132__art_3` | 0.9855 | - |
| 3 | `akn/it/act/legge/stato/2025-09-23/132__art_1` | 0.8143 | - |
| 4 | `akn/it/act/legge/stato/2025-09-23/132__art_8` | 0.8052 | - |
| 5 | `akn/it/act/legge/stato/2025-09-23/132__art_10` | 0.8018 | - |
| 6 | `akn/it/act/legge/stato/2025-09-23/132__art_4` | 0.7703 | - |
| 7 | `akn/it/act/legge/stato/2025-09-23/132__art_11` | 0.5300 | - |
| 8 | `akn/it/act/legge/stato/2025-09-23/132__art_16` | 0.5196 | - |
| 9 | `akn/it/act/legge/stato/2025-09-23/132__art_14` | 0.4522 | - |
| 10 | `akn/it/act/legge/stato/2025-09-23/132__art_6` | 0.3748 | - |

**Gold position in filtered**:
- `akn/it/act/legge/stato/2025-09-23/132__art_7` → rank 1

## Rescue summary

| Norma | Gold atteso | Stato globale v1.0 | Rank filtered sub-query |
|---|---|:---:|:---:|
| AI Act | `…art_6` | ASSENTE | rank 7 |
| AI Act | `…art_27` | ASSENTE | rank 2 |
| GDPR | `…art_9` | ASSENTE | rank 2 |
| GDPR | `…art_35` | ASSENTE | rank 3 |
| L.132/2025 | `…art_7` | rank 2 (globale) | rank 1 |

**Rescue ratio** (gold ASSENTI in globale, trovati in filtered top-10): **4/4**
