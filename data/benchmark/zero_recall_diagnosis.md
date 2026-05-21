# Diagnostica zero-recall benchmark W3

**Data:** 2026-05-19
**Soggetto:** 8 query positive con R@10=0 in tutti e 3 i setup (dense, hybrid, hybrid_rrk) — vedi `BENCHMARK_W3.md`.
**Top-K diagnostico:** 50 (esteso rispetto al benchmark per misurare 'quanto fuori' è il gold).

## Q13 — AI Act Allegato III biometria

**Query:** 'Allegato III AI Act sistemi alto rischio biometria'

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2024/1689/oj__annex_III` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2024/1689/oj__annex_III`** (`annex`, hierarchy: ["Allegato III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2"])

```
ALLEGATO III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2

I sistemi di IA ad alto rischio a norma dell'articolo 6, paragrafo 2, sono i sistemi di IA elencati in uno dei settori indicati di seguito.

1. Biometria, nella misura in cui il pertinente diritto dell'Unione o nazionale ne permette l'uso:
    a) i sistemi di identificazione biometrica remota. Non vi rientrano i sistemi di IA destinati a essere utilizzati per la verifica biometrica la cui unica finalità è confermare che una determinata persona fisica è la persona che dice di essere;
    b) i sistemi di IA destinati a essere utilizzati per la categorizzazione biometrica in base ad attributi o caratteristiche sensibili protetti basati sulla deduzione di tali attributi o caratteristiche;
    c) i sistemi di IA destinati a essere utilizzati per il riconoscimento delle emozioni.

2. Infrastrutture critiche: i sistemi di IA destinati a essere utilizzati come componenti di sicurezza nella gestione e nel funzionamento delle infrastrutture digitali critiche, del traffico stradale o nella fornitura di acqua, gas, riscaldamento o elettricità.

3. Istruzione e formazione professionale:
    a) i sistemi di IA destinati a essere utilizzati per determinare l'accesso, l'ammissione o l'assegnazione di persone fisiche agli istituti di istruzione e formazione professionale a tutti i livelli;
    b) i sistemi di IA destinati a essere utilizzati per valutare i risultati dell'apprendimento, anche nei casi in cui tali 
... [troncato; lunghezza totale 8460 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2024/1689/oj__annex_III` | 20 | 21 | 1 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `eli/reg/2024/1689/oj__art_16` (score 0.7858, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 16)
  - rank 2: `eli/reg/2024/1689/oj__art_4` (score 0.7477, Capo I - DISPOSIZIONI GENERALI → art. 4)
  - rank 3: `eli/reg/2024/1689/oj__recital_125` (score 0.7451, Considerando 125)
  - rank 4: `eli/reg/2024/1689/oj__art_3` (score 0.7398, Capo I - DISPOSIZIONI GENERALI → art. 3)
  - rank 5: `eli/reg/2016/679/oj__art_87` (score 0.7369, Capo IX - Disposizioni relative a specifiche situazioni di trattamento → art. 87)

_hybrid_:
  - rank 1: `eli/reg/2024/1689/oj__art_49` (score 0.5435, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 49)
  - rank 2: `eli/reg/2024/1689/oj__art_16` (score 0.5123, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 16)
  - rank 3: `eli/reg/2024/1689/oj__art_6` (score 0.4583, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 6)
  - rank 4: `eli/reg/2024/1689/oj__art_4` (score 0.3333, Capo I - DISPOSIZIONI GENERALI → art. 4)
  - rank 5: `eli/reg/2024/1689/oj__recital_159` (score 0.2769, Considerando 159)

_hybrid_rrk_:
  - rank 1: `eli/reg/2024/1689/oj__annex_III` (score 0.9939, Allegato III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2)
  - rank 2: `eli/reg/2024/1689/oj__art_7` (score 0.9731, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 7)
  - rank 3: `eli/reg/2024/1689/oj__art_43` (score 0.9569, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 43)
  - rank 4: `eli/reg/2024/1689/oj__art_49` (score 0.9450, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 49)
  - rank 5: `eli/reg/2024/1689/oj__art_6` (score 0.9349, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 6)

### STEP 4 — Verdetto: **(d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 1 → fix: rerank_top_k≥20**

---

## Q15 — AI Act timeline divieti

**Query:** "Quando scattano i divieti dell'AI Act sui sistemi a rischio inaccettabile?"

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2024/1689/oj__art_113` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2024/1689/oj__art_113`** (`article`, hierarchy: ['Capo XIII - DISPOSIZIONI FINALI', 'art. 113'])

```
Articolo 113 - Entrata in vigore e applicazione
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2024/1689/oj__art_113` | fuori top-50 | fuori top-50 | fuori top-50 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `eli/reg/2024/1689/oj__recital_177` (score 0.7544, Considerando 177)
  - rank 2: `eli/reg/2024/1689/oj__recital_179` (score 0.7511, Considerando 179)
  - rank 3: `eli/reg/2024/1689/oj__art_111` (score 0.7316, Capo XIII - DISPOSIZIONI FINALI → art. 111)
  - rank 4: `eli/reg/2024/1689/oj__art_79` (score 0.7215, Capo IX - MONITORAGGIO SUCCESSIVO ALL'IMMISSIONE SUL MERCATO, CONDIVISIONE DELLE INFORMAZIONI E VIGILANZA DEL MERCATO → art. 79)
  - rank 5: `eli/reg/2024/1689/oj__art_6` (score 0.7039, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 6)

_hybrid_:
  - rank 1: `eli/reg/2024/1689/oj__recital_179` (score 0.8333, Considerando 179)
  - rank 2: `eli/reg/2024/1689/oj__recital_177` (score 0.5192, Considerando 177)
  - rank 3: `eli/reg/2024/1689/oj__recital_157` (score 0.4242, Considerando 157)
  - rank 4: `eli/reg/2024/1689/oj__art_60` (score 0.2672, Capo VI - MISURE A SOSTEGNO DELL'INNOVAZIONE → art. 60)
  - rank 5: `eli/reg/2024/1689/oj__art_111` (score 0.2606, Capo XIII - DISPOSIZIONI FINALI → art. 111)

_hybrid_rrk_:
  - rank 1: `eli/reg/2024/1689/oj__recital_179` (score 0.9889, Considerando 179)
  - rank 2: `eli/reg/2024/1689/oj__recital_26` (score 0.3546, Considerando 26)
  - rank 3: `eli/reg/2024/1689/oj__recital_177` (score 0.2365, Considerando 177)
  - rank 4: `eli/reg/2024/1689/oj__recital_46` (score 0.1880, Considerando 46)
  - rank 5: `eli/reg/2024/1689/oj__recital_61` (score 0.1687, Considerando 61)

### STEP 4 — Verdetto: **(b) GOLD_EXIST_BUT_NOT_RETRIEVED**

---

## Q19 — DPIA + FRIA scoring bancario

**Query:** 'Una banca che usa AI per scoring creditizio deve condurre la FRIA oltre alla DPIA?'

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2016/679/oj__art_35` — esiste
- ✓ `eli/reg/2024/1689/oj__annex_III` — esiste
- ✓ `eli/reg/2024/1689/oj__art_27` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2016/679/oj__art_35`** (`article`, hierarchy: ['Capo IV - Titolare del trattamento e responsabile del trattamento', 'art. 35'])

```
Articolo 35 - Valutazione d'impatto sulla protezione dei dati

1. Quando un tipo di trattamento, allorché prevede in particolare l'uso di nuove tecnologie, considerati la natura, l'oggetto, il contesto e le finalità del trattamento, può presentare un rischio elevato per i diritti e le libertà delle persone fisiche, il titolare del trattamento effettua, prima di procedere al trattamento, una valutazione dell'impatto dei trattamenti previsti sulla protezione dei dati personali. Una singola valutazione può esaminare un insieme di trattamenti simili che presentano rischi elevati analoghi.

2. Il titolare del trattamento, allorquando svolge una valutazione d'impatto sulla protezione dei dati, si consulta con il responsabile della protezione dei dati, qualora ne sia designato uno.

3. La valutazione d'impatto sulla protezione dei dati di cui al paragrafo 1 è richiesta in particolare nei casi seguenti: a) una valutazione sistematica e globale di aspetti personali relativi a persone fisiche, basata su un trattamento automatizzato, compresa la profilazione, e sulla quale si fondano decisioni che hanno effetti giuridici o incidono in modo analogo significativamente su dette persone fisiche; b) il trattamento, su larga scala, di categorie particolari di dati personali di cui all'articolo 9, paragrafo 1, o di dati relativi a condanne penali e a reati di cui all'articolo 10; o c) la sorveglianza sistematica su larga scala di una zona accessibile al pubblico.

4. L'autorità di controllo re
... [troncato; lunghezza totale 4661 char]
```

**`eli/reg/2024/1689/oj__annex_III`** (`annex`, hierarchy: ["Allegato III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2"])

```
ALLEGATO III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2

I sistemi di IA ad alto rischio a norma dell'articolo 6, paragrafo 2, sono i sistemi di IA elencati in uno dei settori indicati di seguito.

1. Biometria, nella misura in cui il pertinente diritto dell'Unione o nazionale ne permette l'uso:
    a) i sistemi di identificazione biometrica remota. Non vi rientrano i sistemi di IA destinati a essere utilizzati per la verifica biometrica la cui unica finalità è confermare che una determinata persona fisica è la persona che dice di essere;
    b) i sistemi di IA destinati a essere utilizzati per la categorizzazione biometrica in base ad attributi o caratteristiche sensibili protetti basati sulla deduzione di tali attributi o caratteristiche;
    c) i sistemi di IA destinati a essere utilizzati per il riconoscimento delle emozioni.

2. Infrastrutture critiche: i sistemi di IA destinati a essere utilizzati come componenti di sicurezza nella gestione e nel funzionamento delle infrastrutture digitali critiche, del traffico stradale o nella fornitura di acqua, gas, riscaldamento o elettricità.

3. Istruzione e formazione professionale:
    a) i sistemi di IA destinati a essere utilizzati per determinare l'accesso, l'ammissione o l'assegnazione di persone fisiche agli istituti di istruzione e formazione professionale a tutti i livelli;
    b) i sistemi di IA destinati a essere utilizzati per valutare i risultati dell'apprendimento, anche nei casi in cui tali 
... [troncato; lunghezza totale 8460 char]
```

**`eli/reg/2024/1689/oj__art_27`** (`article`, hierarchy: ['Capo III - SISTEMI DI IA AD ALTO RISCHIO', 'art. 27'])

```
Articolo 27 - Valutazione d'impatto sui diritti fondamentali per i sistemi di IA ad alto rischio

1. Prima di utilizzare un sistema di IA ad alto rischio di cui all'articolo 6, paragrafo 2, ad eccezione dei sistemi di IA ad alto rischio destinati a essere usati nel settore elencati nell'allegato III, punto 2, i deployer che sono organismi di diritto pubblico o sono enti privati che forniscono servizi pubblici e i deployer di sistemi di IA ad alto rischio di cui all'allegato III, punto 5, lettere b) e c), effettuano una valutazione dell'impatto sui diritti fondamentali che l'uso di tale sistema può produrre. A tal fine, i deployer effettuano una valutazione che comprende gli elementi seguenti: a) una descrizione dei processi del deployer in cui il sistema di IA ad alto rischio sarà utilizzato in linea con la sua finalità prevista; b) una descrizione del periodo di tempo entro il quale ciascun sistema di IA ad alto rischio è destinato a essere utilizzato e con che frequenza; c) le categorie di persone fisiche e gruppi verosimilmente interessati dal suo uso nel contesto specifico; d) i rischi specifici di danno che possono incidere sulle categorie di persone fisiche o sui gruppi di persone individuati a norma della lettera c), del presente paragrafo tenendo conto delle informazioni trasmesse dal fornitore a norma dell'articolo 13; e) una descrizione dell'attuazione delle misure di sorveglianza umana, secondo le istruzioni per l'uso; f) le misure da adottare qualora tali rischi s
... [troncato; lunghezza totale 3116 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2016/679/oj__art_35` | fuori top-50 | fuori top-50 | fuori top-50 |
| `eli/reg/2024/1689/oj__annex_III` | fuori top-50 | fuori top-50 | fuori top-50 |
| `eli/reg/2024/1689/oj__art_27` | fuori top-50 | fuori top-50 | fuori top-50 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `eli/reg/2024/1689/oj__recital_1` (score 0.6704, Considerando 1)
  - rank 2: `eli/reg/2024/1689/oj__art_75` (score 0.6538, Capo IX - MONITORAGGIO SUCCESSIVO ALL'IMMISSIONE SUL MERCATO, CONDIVISIONE DELLE INFORMAZIONI E VIGILANZA DEL MERCATO → art. 75)
  - rank 3: `eli/reg/2024/1689/oj__recital_164` (score 0.6500, Considerando 164)
  - rank 4: `eli/reg/2024/1689/oj__art_1` (score 0.6460, Capo I - DISPOSIZIONI GENERALI → art. 1)
  - rank 5: `eli/reg/2024/1689/oj__recital_158` (score 0.6439, Considerando 158)

_hybrid_:
  - rank 1: `eli/reg/2024/1689/oj__recital_1` (score 0.5000, Considerando 1)
  - rank 2: `eli/reg/2016/679/oj__recital_116` (score 0.5000, Considerando 116)
  - rank 3: `eli/reg/2024/1689/oj__recital_131` (score 0.3690, Considerando 131)
  - rank 4: `eli/reg/2024/1689/oj__art_75` (score 0.3333, Capo IX - MONITORAGGIO SUCCESSIVO ALL'IMMISSIONE SUL MERCATO, CONDIVISIONE DELLE INFORMAZIONI E VIGILANZA DEL MERCATO → art. 75)
  - rank 5: `eli/reg/2024/1689/oj__art_71` (score 0.2682, Capo VIII - BANCA DATI DELL'UE PER I SISTEMI DI IA AD ALTO RISCHIO → art. 71)

_hybrid_rrk_:
  - rank 1: `eli/reg/2024/1689/oj__recital_158` (score 0.0057, Considerando 158)
  - rank 2: `akn/it/act/legge/stato/2025-09-23/132__art_20` (score 0.0030, Capo III → art. 20)
  - rank 3: `eli/reg/2024/1689/oj__recital_58` (score 0.0027, Considerando 58)
  - rank 4: `eli/reg/2024/1689/oj__recital_53` (score 0.0024, Considerando 53)
  - rank 5: `eli/reg/2024/1689/oj__recital_34` (score 0.0018, Considerando 34)

### STEP 4 — Verdetto: **(b) GOLD_EXIST_BUT_NOT_RETRIEVED**

---

## Q24 — 231 modello organizzativo + AI HR

**Query:** "Il modello organizzativo 231 deve essere aggiornato per coprire i rischi connessi all'uso di sistemi AI per decisioni HR?"

### STEP 1 — Esistenza chunk_id gold

- ✓ `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` — esiste
- ✓ `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7` — esiste
- ✓ `eli/reg/2024/1689/oj__art_26` — esiste

### STEP 2 — Testo dei gold esistenti

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6`** (`article`, hierarchy: ['Capo I', 'Sezione I', 'art. 6'])

```
Art. 6 - Soggetti in posizione apicale e modelli di organizzazione dell'ente

1. Se il reato e' stato commesso dalle persone indicate nell'articolo 5, comma 1, lettera a), l'ente non risponde se prova che: a) l'organo dirigente ha adottato ed efficacemente attuato, prima della commissione del fatto, modelli di organizzazione e di gestione idonei a prevenire reati della specie di quello verificatosi; b) il compito di vigilare sul funzionamento e l'osservanza dei modelli di curare il loro aggiornamento e' stato affidato a un organismo dell'ente dotato di autonomi poteri di iniziativa e di controllo; c) le persone hanno commesso il reato eludendo fraudolentemente i modelli di organizzazione e di gestione; d) non vi e' stata omessa o insufficiente vigilanza da parte dell'organismo di cui alla lettera b).

2. In relazione all'estensione dei poteri delegati e al rischio di commissione dei reati, i modelli di cui alla lettera a), del comma 1, devono rispondere alle seguenti esigenze: a) individuare le attivita' nel cui ambito possono essere commessi reati; b) prevedere specifici protocolli diretti a programmare la formazione e l'attuazione delle decisioni dell'ente in relazione ai reati da prevenire; c) individuare modalita' di gestione delle risorse finanziarie idonee ad impedire la commissione dei reati; d) prevedere obblighi di informazione nei confronti dell'organismo deputato a vigilare sul funzionamento e l'osservanza dei modelli; e) introdurre un sistema disciplinare idoneo a
... [troncato; lunghezza totale 2894 char]
```

**`akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7`** (`article`, hierarchy: ['Capo I', 'Sezione I', 'art. 7'])

```
Art. 7 - Soggetti sottoposti all'altrui direzione e modelli di organizzazione dell'ente

1. Nel caso previsto dall'articolo 5, comma 1, lettera b), l'ente e' responsabile se la commissione del reato e' stata resa possibile dall'inosservanza degli obblighi di direzione o vigilanza.

2. In ogni caso, e' esclusa l'inosservanza degli obblighi di direzione o vigilanza se l'ente, prima della commissione del reato, ha adottato ed efficacemente attuato un modello di organizzazione, gestione e controllo idoneo a prevenire reati della specie di quello verificatosi.

3. Il modello prevede, in relazione alla natura e alla dimensione dell'organizzazione nonche' al tipo di attivita' svolta, misure idonee a garantire lo svolgimento dell'attivita' nel rispetto della legge e a scoprire ed eliminare tempestivamente situazioni di rischio.

4. L'efficace attuazione del modello richiede: a) una verifica periodica e l'eventuale modifica dello stesso quando sono scoperte significative violazioni delle prescrizioni ovvero quando intervengono mutamenti nell'organizzazione o nell'attivita'; b) un sistema disciplinare idoneo a sanzionare il mancato rispetto delle misure indicate nel modello.
```

**`eli/reg/2024/1689/oj__art_26`** (`article`, hierarchy: ['Capo III - SISTEMI DI IA AD ALTO RISCHIO', 'art. 26'])

```
Articolo 26 - Obblighi dei deployer dei sistemi di IA ad alto rischio

1. I deployer di sistemi di IA ad alto rischio adottano idonee misure tecniche e organizzative per garantire di utilizzare tali sistemi conformemente alle istruzioni per l'uso che accompagnano i sistemi, a norma dei paragrafi 3 e 6.

2. I deployer affidano la sorveglianza umana a persone fisiche che dispongono della competenza, della formazione e dell'autorità necessarie nonché del sostegno necessario.

3. Gli obblighi di cui ai paragrafi 1 e 2 lasciano impregiudicati gli altri obblighi dei deployer previsti dal diritto dell'Unione o nazionale e la libertà del deployer di organizzare le proprie risorse e attività al fine di attuare le misure di sorveglianza umana indicate dal fornitore.

4. Fatti salvi i paragrafi 1 e 2, nella misura in cui esercita il controllo sui dati di input, il deployer garantisce che tali dati di input siano pertinenti e sufficientemente rappresentativi alla luce della finalità prevista del sistema di IA ad alto rischio.

5. I deployer monitorano il funzionamento del sistema di IA ad alto rischio sulla base delle istruzioni per l'uso e, se del caso, informano i fornitori a tale riguardo conformemente all'articolo 72. Qualora abbiano motivo di ritenere che l'uso del sistema di IA ad alto rischio in conformità delle istruzioni possa comportare che il sistema di IA presenti un rischio ai sensi dell'articolo 79, paragrafo 1, i deployer ne informano, senza indebito ritardo, il fornitore 
... [troncato; lunghezza totale 8083 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` | fuori top-50 | fuori top-50 | fuori top-50 |
| `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7` | fuori top-50 | fuori top-50 | fuori top-50 |
| `eli/reg/2024/1689/oj__art_26` | fuori top-50 | 12 | 28 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `eli/reg/2024/1689/oj__recital_57` (score 0.6966, Considerando 57)
  - rank 2: `eli/reg/2024/1689/oj__recital_118` (score 0.6953, Considerando 118)
  - rank 3: `eli/reg/2024/1689/oj__art_55` (score 0.6906, Capo V - MODELLI DI IA PER FINALITÀ GENERALI → art. 55)
  - rank 4: `eli/reg/2024/1689/oj__recital_114` (score 0.6785, Considerando 114)
  - rank 5: `eli/reg/2024/1689/oj__recital_177` (score 0.6691, Considerando 177)

_hybrid_:
  - rank 1: `eli/reg/2024/1689/oj__recital_115` (score 0.5667, Considerando 115)
  - rank 2: `eli/reg/2024/1689/oj__recital_57` (score 0.5101, Considerando 57)
  - rank 3: `eli/reg/2024/1689/oj__recital_65` (score 0.3529, Considerando 65)
  - rank 4: `eli/reg/2024/1689/oj__recital_118` (score 0.3333, Considerando 118)
  - rank 5: `eli/reg/2024/1689/oj__art_55` (score 0.2833, Capo V - MODELLI DI IA PER FINALITÀ GENERALI → art. 55)

_hybrid_rrk_:
  - rank 1: `eli/reg/2024/1689/oj__recital_65` (score 0.2615, Considerando 65)
  - rank 2: `eli/reg/2024/1689/oj__recital_57` (score 0.1665, Considerando 57)
  - rank 3: `akn/it/act/legge/stato/2025-09-23/132__art_3` (score 0.1584, Capo I → art. 3)
  - rank 4: `eli/reg/2024/1689/oj__recital_53` (score 0.1273, Considerando 53)
  - rank 5: `eli/reg/2024/1689/oj__recital_61` (score 0.1239, Considerando 61)

### STEP 4 — Verdetto: **(d) GOLD_NEAR_MISS**

---

## Q30 — stress: Allegato III punto 4 AI Act

**Query:** 'Allegato III punto 4 lettera a AI Act'

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2024/1689/oj__annex_III` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2024/1689/oj__annex_III`** (`annex`, hierarchy: ["Allegato III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2"])

```
ALLEGATO III - Sistemi di IA ad alto rischio di cui all'articolo 6, paragrafo 2

I sistemi di IA ad alto rischio a norma dell'articolo 6, paragrafo 2, sono i sistemi di IA elencati in uno dei settori indicati di seguito.

1. Biometria, nella misura in cui il pertinente diritto dell'Unione o nazionale ne permette l'uso:
    a) i sistemi di identificazione biometrica remota. Non vi rientrano i sistemi di IA destinati a essere utilizzati per la verifica biometrica la cui unica finalità è confermare che una determinata persona fisica è la persona che dice di essere;
    b) i sistemi di IA destinati a essere utilizzati per la categorizzazione biometrica in base ad attributi o caratteristiche sensibili protetti basati sulla deduzione di tali attributi o caratteristiche;
    c) i sistemi di IA destinati a essere utilizzati per il riconoscimento delle emozioni.

2. Infrastrutture critiche: i sistemi di IA destinati a essere utilizzati come componenti di sicurezza nella gestione e nel funzionamento delle infrastrutture digitali critiche, del traffico stradale o nella fornitura di acqua, gas, riscaldamento o elettricità.

3. Istruzione e formazione professionale:
    a) i sistemi di IA destinati a essere utilizzati per determinare l'accesso, l'ammissione o l'assegnazione di persone fisiche agli istituti di istruzione e formazione professionale a tutti i livelli;
    b) i sistemi di IA destinati a essere utilizzati per valutare i risultati dell'apprendimento, anche nei casi in cui tali 
... [troncato; lunghezza totale 8460 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2024/1689/oj__annex_III` | fuori top-50 | fuori top-50 | fuori top-50 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `eli/reg/2024/1689/oj__art_4` (score 0.8309, Capo I - DISPOSIZIONI GENERALI → art. 4)
  - rank 2: `eli/reg/2016/679/oj__art_4` (score 0.8195, Capo I - Disposizioni generali → art. 4)
  - rank 3: `eli/reg/2024/1689/oj__art_3` (score 0.8133, Capo I - DISPOSIZIONI GENERALI → art. 3)
  - rank 4: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_75` (score 0.8032, Sezione IX → art. 75)
  - rank 5: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_1` (score 0.8006, art. 1)

_hybrid_:
  - rank 1: `eli/reg/2024/1689/oj__art_49` (score 0.5137, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 49)
  - rank 2: `eli/reg/2024/1689/oj__art_4` (score 0.5000, Capo I - DISPOSIZIONI GENERALI → art. 4)
  - rank 3: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_1_11` (score 0.3333, Capo V → art. 38)
  - rank 4: `eli/reg/2016/679/oj__art_4` (score 0.3333, Capo I - Disposizioni generali → art. 4)
  - rank 5: `eli/reg/2024/1689/oj__art_43` (score 0.2606, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 43)

_hybrid_rrk_:
  - rank 1: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_38__paras_12_16` (score 0.2370, Capo V → art. 38)
  - rank 2: `eli/reg/2024/1689/oj__art_7` (score 0.1507, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 7)
  - rank 3: `eli/reg/2024/1689/oj__art_12` (score 0.1499, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 12)
  - rank 4: `eli/reg/2024/1689/oj__art_49` (score 0.1329, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 49)
  - rank 5: `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_3` (score 0.1210, Capo I → art. 3)

### STEP 4 — Verdetto: **(b) GOLD_EXIST_BUT_NOT_RETRIEVED**

---

## Q34 — stress: art 9 GDPR

**Query:** 'art 9 GDPR categorie particolari'

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2016/679/oj__art_9` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2016/679/oj__art_9`** (`article`, hierarchy: ['Capo II - Principi', 'art. 9'])

```
Articolo 9 - Trattamento di categorie particolari di dati personali

1. È vietato trattare dati personali che rivelino l'origine razziale o etnica, le opinioni politiche, le convinzioni religiose o filosofiche, o l'appartenenza sindacale, nonché trattare dati genetici, dati biometrici intesi a identificare in modo univoco una persona fisica, dati relativi alla salute o alla vita sessuale o all'orientamento sessuale della persona.

2. Il paragrafo 1 non si applica se si verifica uno dei seguenti casi: a) l'interessato ha prestato il proprio consenso esplicito al trattamento di tali dati personali per una o più finalità specifiche, salvo nei casi in cui il diritto dell'Unione o degli Stati membri dispone che l'interessato non possa revocare il divieto di cui al paragrafo 1; b) il trattamento è necessario per assolvere gli obblighi ed esercitare i diritti specifici del titolare del trattamento o dell'interessato in materia di diritto del lavoro e della sicurezza sociale e protezione sociale, nella misura in cui sia autorizzato dal diritto dell'Unione o degli Stati membri o da un contratto collettivo ai sensi del diritto degli Stati membri, in presenza di garanzie appropriate per i diritti fondamentali e gli interessi dell'interessato; c) il trattamento è necessario per tutelare un interesse vitale dell'interessato o di un'altra persona fisica qualora l'interessato si trovi nell'incapacità fisica o giuridica di prestare il proprio consenso; d) il trattamento è effettuato, nell'am
... [troncato; lunghezza totale 4716 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2016/679/oj__art_9` | 36 | 38 | 2 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `akn/it/act/legge/stato/2025-09-23/132__art_19` (score 0.7346, Capo III → art. 19)
  - rank 2: `eli/reg/2024/1689/oj__art_109` (score 0.7315, Capo XIII - DISPOSIZIONI FINALI → art. 109)
  - rank 3: `eli/reg/2016/679/oj__art_4` (score 0.7289, Capo I - Disposizioni generali → art. 4)
  - rank 4: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` (score 0.7277, Sezione IX → art. 81)
  - rank 5: `eli/reg/2024/1689/oj__art_3` (score 0.7271, Capo I - DISPOSIZIONI GENERALI → art. 3)

_hybrid_:
  - rank 1: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_107` (score 0.5909, art. 107)
  - rank 2: `akn/it/act/legge/stato/2025-09-23/132__art_19` (score 0.5000, Capo III → art. 19)
  - rank 3: `eli/reg/2024/1689/oj__recital_70` (score 0.3503, Considerando 70)
  - rank 4: `eli/reg/2024/1689/oj__art_109` (score 0.3333, Capo XIII - DISPOSIZIONI FINALI → art. 109)
  - rank 5: `eli/reg/2016/679/oj__art_4` (score 0.2500, Capo I - Disposizioni generali → art. 4)

_hybrid_rrk_:
  - rank 1: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-sexies` (score 0.9802, art. 2-sexies)
  - rank 2: `eli/reg/2016/679/oj__art_9` (score 0.9795, Capo II - Principi → art. 9)
  - rank 3: `akn/it/act/legge/stato/2025-09-23/132__art_9` (score 0.9018, Capo II → art. 9)
  - rank 4: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_107` (score 0.8808, art. 107)
  - rank 5: `eli/reg/2024/1689/oj__recital_70` (score 0.8184, Considerando 70)

### STEP 4 — Verdetto: **(d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 2 → fix: rerank_top_k≥36**

---

## Q35 — stress: art 27 AI Act FRIA

**Query:** 'art 27 AI Act FRIA'

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2024/1689/oj__art_27` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2024/1689/oj__art_27`** (`article`, hierarchy: ['Capo III - SISTEMI DI IA AD ALTO RISCHIO', 'art. 27'])

```
Articolo 27 - Valutazione d'impatto sui diritti fondamentali per i sistemi di IA ad alto rischio

1. Prima di utilizzare un sistema di IA ad alto rischio di cui all'articolo 6, paragrafo 2, ad eccezione dei sistemi di IA ad alto rischio destinati a essere usati nel settore elencati nell'allegato III, punto 2, i deployer che sono organismi di diritto pubblico o sono enti privati che forniscono servizi pubblici e i deployer di sistemi di IA ad alto rischio di cui all'allegato III, punto 5, lettere b) e c), effettuano una valutazione dell'impatto sui diritti fondamentali che l'uso di tale sistema può produrre. A tal fine, i deployer effettuano una valutazione che comprende gli elementi seguenti: a) una descrizione dei processi del deployer in cui il sistema di IA ad alto rischio sarà utilizzato in linea con la sua finalità prevista; b) una descrizione del periodo di tempo entro il quale ciascun sistema di IA ad alto rischio è destinato a essere utilizzato e con che frequenza; c) le categorie di persone fisiche e gruppi verosimilmente interessati dal suo uso nel contesto specifico; d) i rischi specifici di danno che possono incidere sulle categorie di persone fisiche o sui gruppi di persone individuati a norma della lettera c), del presente paragrafo tenendo conto delle informazioni trasmesse dal fornitore a norma dell'articolo 13; e) una descrizione dell'attuazione delle misure di sorveglianza umana, secondo le istruzioni per l'uso; f) le misure da adottare qualora tali rischi s
... [troncato; lunghezza totale 3116 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2024/1689/oj__art_27` | fuori top-50 | 22 | 1 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_75` (score 0.8434, Sezione IX → art. 75)
  - rank 2: `akn/it/act/legge/stato/2025-09-23/132__art_19` (score 0.8376, Capo III → art. 19)
  - rank 3: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_82` (score 0.8203, Sezione IX → art. 82)
  - rank 4: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_80` (score 0.8162, Sezione IX → art. 80)
  - rank 5: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` (score 0.8146, Sezione IX → art. 81)

_hybrid_:
  - rank 1: `akn/it/act/legge/stato/2025-09-23/132__art_27` (score 0.5189, Capo VI → art. 27)
  - rank 2: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_75` (score 0.5000, Sezione IX → art. 75)
  - rank 3: `eli/reg/2016/679/oj__recital_27` (score 0.3333, Considerando 27)
  - rank 4: `akn/it/act/legge/stato/2025-09-23/132__art_19` (score 0.3333, Capo III → art. 19)
  - rank 5: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_27` (score 0.2500, Sezione I → art. 27)

_hybrid_rrk_:
  - rank 1: `eli/reg/2024/1689/oj__art_27` (score 0.3626, Capo III - SISTEMI DI IA AD ALTO RISCHIO → art. 27)
  - rank 2: `eli/reg/2016/679/oj__art_27` (score 0.1893, Capo IV - Titolare del trattamento e responsabile del trattamento → art. 27)
  - rank 3: `akn/it/act/legge/stato/2025-09-23/132__art_27` (score 0.0848, Capo VI → art. 27)
  - rank 4: `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_27` (score 0.0504, Sezione I → art. 27)
  - rank 5: `eli/reg/2024/1689/oj__recital_27` (score 0.0239, Considerando 27)

### STEP 4 — Verdetto: **(d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 1 → fix: rerank_top_k≥22**

---

## Q39 — stress: art 6 GDPR base giuridica

**Query:** 'art 6 GDPR base giuridica del trattamento'

### STEP 1 — Esistenza chunk_id gold

- ✓ `eli/reg/2016/679/oj__art_6` — esiste

### STEP 2 — Testo dei gold esistenti

**`eli/reg/2016/679/oj__art_6`** (`article`, hierarchy: ['Capo II - Principi', 'art. 6'])

```
Articolo 6 - Liceità del trattamento

1. Il trattamento è lecito solo se e nella misura in cui ricorre almeno una delle seguenti condizioni: a) l'interessato ha espresso il consenso al trattamento dei propri dati personali per una o più specifiche finalità; b) il trattamento è necessario all'esecuzione di un contratto di cui l'interessato è parte o all'esecuzione di misure precontrattuali adottate su richiesta dello stesso; c) il trattamento è necessario per adempiere un obbligo legale al quale è soggetto il titolare del trattamento; d) il trattamento è necessario per la salvaguardia degli interessi vitali dell'interessato o di un'altra persona fisica; e) il trattamento è necessario per l'esecuzione di un compito di interesse pubblico o connesso all'esercizio di pubblici poteri di cui è investito il titolare del trattamento; f) il trattamento è necessario per il perseguimento del legittimo interesse del titolare del trattamento o di terzi, a condizione che non prevalgano gli interessi o i diritti e le libertà fondamentali dell'interessato che richiedono la protezione dei dati personali, in particolare se l'interessato è un minore.

2. Gli Stati membri possono mantenere o introdurre disposizioni più specifiche per adeguare l'applicazione delle norme del presente regolamento con riguardo al trattamento, in conformità del paragrafo 1, lettere c) ed e), determinando con maggiore precisione requisiti specifici per il trattamento e altre misure atte a garantire un trattamento lecit
... [troncato; lunghezza totale 3092 char]
```

### STEP 3 — Rank dei gold nei top-50 per setup

| chunk_id gold | rank dense | rank hybrid | rank hybrid_rrk |
|---|---:|---:|---:|
| `eli/reg/2016/679/oj__art_6` | 33 | 38 | 2 |

**Top-5 effettivi recuperati**

_dense_:
  - rank 1: `eli/reg/2024/1689/oj__art_106` (score 0.7933, Capo XIII - DISPOSIZIONI FINALI → art. 106)
  - rank 2: `eli/reg/2016/679/oj__art_29` (score 0.7932, Capo IV - Titolare del trattamento e responsabile del trattamento → art. 29)
  - rank 3: `eli/reg/2016/679/oj__art_16` (score 0.7857, Capo III - Diritti dell'interessato → art. 16)
  - rank 4: `eli/reg/2016/679/oj__art_98` (score 0.7829, Capo XI - Disposizioni finali → art. 98)
  - rank 5: `eli/reg/2024/1689/oj__art_104` (score 0.7772, Capo XIII - DISPOSIZIONI FINALI → art. 104)

_hybrid_:
  - rank 1: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_45-bis` (score 0.5476, art. 45-bis)
  - rank 2: `eli/reg/2024/1689/oj__art_106` (score 0.5000, Capo XIII - DISPOSIZIONI FINALI → art. 106)
  - rank 3: `eli/reg/2024/1689/oj__recital_140` (score 0.3451, Considerando 140)
  - rank 4: `eli/reg/2016/679/oj__art_29` (score 0.3333, Capo IV - Titolare del trattamento e responsabile del trattamento → art. 29)
  - rank 5: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-ter` (score 0.2778, art. 2-ter)

_hybrid_rrk_:
  - rank 1: `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-ter` (score 0.9617, art. 2-ter)
  - rank 2: `eli/reg/2016/679/oj__art_6` (score 0.8999, Capo II - Principi → art. 6)
  - rank 3: `eli/reg/2024/1689/oj__recital_140` (score 0.7778, Considerando 140)
  - rank 4: `eli/reg/2016/679/oj__recital_47` (score 0.7623, Considerando 47)
  - rank 5: `eli/reg/2016/679/oj__recital_50` (score 0.7500, Considerando 50)

### STEP 4 — Verdetto: **(d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 2 → fix: rerank_top_k≥33**

---

## Summary

| qid | gold_count | esistono | rank_dense | rank_hybrid | rank_rrk | verdetto |
|---|---:|---:|---:|---:|---:|---|
| Q13 | 1 | 1/1 | 20 | 21 | 1 | (d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 1 → fix: rerank_top_k≥20 |
| Q15 | 1 | 1/1 | — | — | — | (b) GOLD_EXIST_BUT_NOT_RETRIEVED |
| Q19 | 3 | 3/3 | — | — | — | (b) GOLD_EXIST_BUT_NOT_RETRIEVED |
| Q24 | 3 | 3/3 | — | 12 | 28 | (d) GOLD_NEAR_MISS |
| Q30 | 1 | 1/1 | — | — | — | (b) GOLD_EXIST_BUT_NOT_RETRIEVED |
| Q34 | 1 | 1/1 | 36 | 38 | 2 | (d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 2 → fix: rerank_top_k≥36 |
| Q35 | 1 | 1/1 | — | 22 | 1 | (d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 1 → fix: rerank_top_k≥22 |
| Q39 | 1 | 1/1 | 33 | 38 | 2 | (d) GOLD_NEAR_MISS — rrk_top50 lo promuove a rank 2 → fix: rerank_top_k≥33 |

## Suggested fixes

_Nessun verdetto (a) o (c): nessun fix automatico da proporre. I fail di tipo (b) richiedono indagine separata (indicizzazione o pattern semantico)._
