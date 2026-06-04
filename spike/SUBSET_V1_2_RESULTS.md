# Subset v1.2 — misurazione paid (fusion z-normalized + gated)

**Branch**: `feat/cross-norm-v1-2`
**Data (UTC)**: 2026-05-29T11:42Z
**Config**: enable_cross_norm=True, gen Sonnet 4.6 max_tokens=4000, judge Sonnet 4.6.
**Fusion v1.2**: sigmoid(max_logit) + floor 0.5 + IQR threshold 0.05 + gated threshold 0.6 + z-normalization per source ad alta varianza.
**Costo**: cassette $0.08 + run paid (gen+judge) **$1.82** = **$1.90** (vs budget $1.55).
**Subset**: 19 query (6 target + 4 sentinelle + 2 corpus_limit + 3 mono-stress + 4 gold-recital).
**Baseline v1.1 rescue@5**: ricalcolato da `data/benchmark/ragas_pipeline_outputs_cross_norm_v1_1.json` (retrieval indipendente da max_tokens).

---

## 1. Tabelle per gruppo

### Target cross-norma (6)

| qid | path | rescue@5 v1.1 → v1.2 | rescue@20 v1.1 → v1.2 | faith v1.1 → v1.2 | ar v1.1 → v1.2 |
|-----|------|:--------------------:|:---------------------:|:------------------:|:--------------:|
| Q9 | cross-norm | 1.000 → 1.000 | 1.000 → 1.000 | 0.960 → **0.478** | 0.853 → 0.929 |
| Q25 | fallback | 0.500 → 0.500 | 0.500 → 0.500 | 0.737 → 0.562 | 0.000 → 0.000 |
| Q68 | cross-norm | 0.400 → **0.200** | 0.600 → 0.600 | 0.412 → 0.742 | 0.903 → 0.000 |
| Q69 | cross-norm | 0.400 → **0.200** | 0.800 → 0.800 | 0.412 → 0.900 | 0.907 → 0.000 |
| Q70 | cross-norm | 0.200 → 0.200 | 0.800 → **0.400** | 0.349 → 0.321 | 0.726 → 0.000 |
| Q71 | cross-norm | 0.400 → **0.000** | 0.800 → **0.400** | 0.731 → 0.481 | 0.859 → 0.783 |

### Sentinelle (4) + corpus_limit (2) — path fallback

| qid | rescue@5 v1.2 | rescue@20 v1.2 | faith v1.2 | ar v1.2 |
|-----|:-------------:|:--------------:|:----------:|:-------:|
| Q6 | 1.000 | 1.000 | 1.000 | 0.786 |
| Q7 | 1.000 | 1.000 | 1.000 | 0.866 |
| Q63 | 1.000 | 1.000 | 0.955 | 0.987 |
| Q87 | 1.000 | 1.000 | 0.800 | 0.936 |
| Q43 | 0.000 | 0.500 | 0.783 | 0.000 |
| Q94 | n/a | n/a | 0.900 | 0.000 |

Tutte fallback → retrieval byte-identico vs v1.1; le Δ residue sono rumore gen/judge.

### Mono-stress (3) + gold-recital (4)

| qid | path | rescue@5 v1.2 | faith v1.2 |
|-----|------|:-------------:|:----------:|
| Q34 | fallback | 1.000 | 0.893 |
| Q35 | fallback | 1.000 | 1.000 |
| Q38 | fallback | 1.000 | 0.632 |
| Q1 | fallback | 0.500 | 0.818 |
| Q3 | cross-norm | 0.500 | nan† |
| Q8 | fallback | 1.000 | 1.000 |
| Q29 | fallback | 1.000 | 1.000 |

† Q3 faith=nan: judge RAGAS fallito (max_tokens interno).

### Mediane per gruppo

| gruppo | rescue@5 v1.1 | rescue@5 v1.2 | Δ | faith v1.1 | faith v1.2 | Δ |
|--------|:-------------:|:-------------:|:--:|:----------:|:----------:|:--:|
| target cross-norma | 0.400 | **0.200** | **−0.200** | 0.571 | 0.522 | −0.049 |
| sentinelle | 1.000 | 1.000 | 0 | 0.934 | 0.977 | +0.043 |
| corpus_limit | 0.000 | 0.000 | 0 | 0.820 | 0.841 | +0.021 |
| mono-stress | 1.000 | 1.000 | 0 | 1.000 | 0.893 | −0.107 |
| gold-recital | 0.750 | 0.750 | 0 | 0.945 | 1.000 | +0.055 |

---

## 2. Verdetto C1–C6

**Soglie (ricalcolate)**: baseline target rescue@5 v1.1 = **0.400** (non 0.70: il brief diceva 0.70 a rank≤20 e chiedeva ricalcolo a rank≤5). C1 threshold = 0.400 + 0.10 = **0.500**.

| # | criterio | soglia | risultato | esito |
|---|----------|--------|-----------|:-----:|
| **C1** | target rescue@5 mediana ≥ 0.500 | – | **0.200** (regressione −0.20) | **FAIL** |
| **C2** | target faith mediana ≥ 0.55 + 0.05 = 0.60 | – | **0.522** | **FAIL** |
| **C3** | mono-stress no degrado faith > 0.05 | – | Q38 1.000 → 0.632 (−0.37) | FAIL noise† |
| **C4** | gold-recital no degrado faith > 0.05 | – | Q1 0.889 → 0.818 (−0.07) | FAIL noise† |
| **C5** | sentinelle+corpus_limit Δfaith/ar ≤ 0.02 | – | Q87 ar −0.025 borderline; resto entro rumore | FAIL noise† |
| **C6** | dei 5 mancanti v1.1: ≥3 in A E 0 in B | – | **0 A, 4 B, 2 C** | **FAIL HARD** |

† C3/C4/C5 sono path fallback (retrieval byte-identico): Δ sono rumore gen/judge (nondeterminismo Sonnet a temp=0 + RAGAS stocastico). Non attribuibili al fix.

### Telemetria C6 — A/B/C/D dei 5 mancanti

| qid | gold | concetto nominato | in top-5 | fusion_rank | categoria |
|-----|------|:-----------------:|:--------:|:-----------:|:---------:|
| Q68 | AI Act `art_6` | sì (sub-q [0] ai_act) | no | >20 | **B** |
| Q68 | GDPR `art_9` | sì (sub-q [0] gdpr) | no | 19 | **B** |
| Q69 | AI Act `art_6` | sì (sub-q [0] ai_act) | no | >20 | **B** |
| Q70 | GDPR `art_44` | no (gdpr enumera 28/35/32, non 44 in sub-q corrente) | no | >20 | **C** |
| Q70 | 231 `art_25-octies` | sì (sub-q [4] dlgs_231) | no | >20 | **B** |
| Q71 | `annex_III__point_5` | no | no | >20 | **C** |

Aggregato: **0 A, 4 B, 2 C, 0 D**. Brief richiedeva ≥3 A E 0 B → fallisce
catastroficamente. La presenza di 4 B significa: il concetto è nominato dalla
sub-query mono-concetto MA il chunk resta fuori dal top-5 → la fusion z-norm
non lo recupera.

### Lettura ordinata (clausola del brief aggiornato)

Il brief consentiva commit se *"C2 passa con margine ≥0.10 ma C1 fallisce
solo su gold ai_act"*. **Nessuna delle due condizioni è soddisfatta**:
1. C2 NON passa (0.522 < 0.60).
2. C1 fallisce ANCHE su gold non-ai_act: Q70 `art_44` (GDPR, regressione
   netta), Q71 `point_5` (annex_III, ma anche `art_22` GDPR è perso vs
   baseline), Q70 `art_25-octies` (231).

Clausola non applicabile → **verdetto: NO-GO sul commit in main.**

---

## 3. Diagnostica fusion_stats — perché ha fallito

I log fusion_stats per le 5 query cross-norma rivelano una **distribuzione
asimmetrica delle source che la z-normalizzazione amplifica**.

| query | source | n | median | IQR | max σ | z_max | esito |
|-------|--------|--:|:------:|:---:|:-----:|:-----:|-------|
| Q68 | gdpr | 89 | 0.512 | 0.056 | 0.728 | **3.86** | domina |
| Q68 | ai_act | 79 | **0.723** | 0.081 | 0.731 | **0.10** | compresso (saturo al top) |
| Q68 | l_132 | 25 | 0.532 | 0.117 | 0.730 | 1.69 | intermedio |
| Q68 | global | 17 | 0.500 | 0.002 | 0.532 | – | gated, 0 ingressi |
| Q70 | gdpr | 90 | 0.554 | 0.122 | 0.728 | 1.43 | normalizzato |
| Q70 | ai_act | 65 | 0.720 | **0.035** | 0.731 | – | **GATED** (IQR < 0.05) |
| Q70 | dlgs_231 | 45 | 0.501 | **0.023** | 0.702 | – | **GATED** |
| Q70 | nis2 | 43 | 0.555 | 0.102 | 0.731 | 1.73 | normalizzato |
| Q70 | global | 7 | 0.518 | 0.013 | 0.541 | – | gated |
| Q71 | gdpr | 84 | 0.515 | 0.068 | 0.729 | 3.15 | domina |
| Q71 | ai_act | 71 | 0.720 | 0.053 | 0.731 | 0.21 | compresso (z≈0) |

`n_gated_in_top_k = 0` per **TUTTE** le query: con 20 candidati normalizzati a
z > floor, i 20 slot finali sono saturi prima che alcun gated entri. **AI Act e
Dlgs 231 sono effettivamente esclusi dal top-20 nelle query in cui finiscono
gated.**

### Modalità di fallimento strutturale

La z-normalizzazione assume distribuzioni roughly simmetriche attorno alla
mediana. Sui dati reali del corpus:

- **AI Act** ha vocabolario tecnico denso ("sistema di IA ad alto rischio",
  "fornitore", "deployer") che il reranker matcha con altissima specificità:
  molti chunk saturano vicino a logit 1.0 → σ→0.73 → mediana alta, top tail
  compressa, **z_max ≈ 0.1-0.2** (anche se i gold ai_act hanno σ alto in
  assoluto).
- **GDPR** ha vocabolario più discorsivo: distribuzione σ ampia da 0.5 a 0.73
  → mediana bassa, **z_max ≈ 3-4**. Domina sempre.
- **Dlgs 231 / NIS2 / L.132**: distribuzioni intermedie, talvolta low_signal
  (Q70 dlgs_231 IQR 0.023 → gated → escluso).

**Il fix v1.2 ha solo SPOSTATO il bias**: prima ai_act vinceva sempre per
saturazione assoluta; ora gdpr vince sempre per ampia z relativa, e ai_act
viene sistematicamente compresso a z≈0 o gated fuori. Non è una soluzione,
è uno scambio di bias.

### Q9 — anche dove rescue è invariato, faith crolla

Q9 ha 2 norme (dlgs_231 + codice_privacy). Smoke retrieval r@5=1.0 (gold
`art_24-bis` al rank 3, invariato vs v1.1). MA faith crolla 0.96 → 0.48:

```
Q9 top-5 v1.2: art_5, art_17, art_24-bis (gold), art_25-quinquies, art_23
```

I 4 chunk non-gold in top-5 sono **diversi** da quelli che baseline v1.1
aveva: la composizione del contesto generation cambia (normalizzazione
seleziona chunk diversi a parità di gold inclusione) e Sonnet produce
risposta con citazioni meno coerenti → faith crolla. **Anche con rescue
invariato, il fix degrada la qualità generation**, perché la z-norm
seleziona la coda meno calibrata della source ad alto spread.

---

## 4. Conclusione

**Verdetto: NO-GO sul commit in main.**

Il design v1.2 aggiornato (sigmoid + floor + IQR-gated + z-normalizzazione per
source ad alta varianza) **non risolve** il problema dei 5 gold mancanti e
**introduce regressioni** su:
- target rescue@5: −0.20 mediana (regressione netta sui 6 target).
- target faith: −0.05 (sotto baseline).
- Q70/Q71 r@20 perdono 0.4 di rescue ciascuno (gold ai_act e dlgs_231
  esclusi via gating).
- Q9 faith crolla 0.96 → 0.48 anche con rescue invariato (compositione top-5
  diversa).
- C6 telemetria: 0 in A, 4 in B (residuo Classe 3 catastrofico).

La causa strutturale è **asimmetria delle distribuzioni σ per source**: la
z-normalizzazione, pensata per equalizzare le source, in realtà amplifica
la differenza tra distribuzioni a coda compressa (ai_act, saturo) e
distribuzioni a spread ampio (gdpr). Il bias si sposta, non si rimuove.

### Cosa NON va in main

Il branch `feat/cross-norm-v1-2` resta. **NON merge**.

### Direzioni residue (fuori scope di questo round)

1. **Equalizzazione robusta dei range σ pre-fusion** (es. percentile-rank entro
   source, dove ogni source contribuisce con la sua distribuzione 0-1 di
   percentili): rimuove l'asimmetria di z-norm.
2. **Quote per-source garantite nel top-K finale** (es. ogni filtered:* deve
   contribuire ≥3 slot): forza diversità.
3. **Fusione rank-based pesata** (RRF con pesi che dipendono dal "match
   quality" della sub-query alla source, non dalla calibrazione assoluta).
4. **Rivedere il decomposer per generare meno sub-query per source ad alta
   saturazione** (riduce il rischio di sub-query ridondanti che tutte saturano):
   ortogonale ma complementare.

Nessuna è gratuita. Ognuna richiede un brief con pre-misurazione (come
Verifica 8 fece per le 4 varianti, ora però con cassette V3).

### Cosa SI può portare a casa

- **Cassette V3 mono-concetto** (in `tests/cross_norm/cassettes/`): cleanly
  formatted JSON arrays, parser robusto a code fences sbilanciati, costo
  fisso ~$0.08. Sono migliori delle V2 per leggibilità e granularità del
  concetto.
- **Il `subquery_generator.py` con return list[str]**: backward compatible
  via parser fallback (legge anche string singole legacy V2).
- **fusion_stats nel trace** (n_below_floor, IQR, source_stats, z_top_k_*):
  diagnostiche utili in qualsiasi futura iterazione fusion.

Questi sono pezzi di valore indipendentemente dal verdetto sulla fusion: una
ipotetica v1.3 con design fusion diverso potrebbe ri-usare cassette V3 e
fusion_stats senza ri-pagare.
