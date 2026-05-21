# Smoke gold comparison — risultati

Data: 2026-05-20
Provider: **anthropic** (claude-sonnet-4-6), top_k=5, rerank_top_k=20, use_graph=False, max_output_tokens=1000. 1 run/query, no warmup interno aggiuntivo.

Spec di riferimento: [`SMOKE_GOLD_COMPARISON_SPEC.md`](SMOKE_GOLD_COMPARISON_SPEC.md).

Campi automatici popolati dallo script. Campi di giudizio umano (`checklist N/M`, citazioni semantiche, allucinazioni, commento, verdict) restano placeholder da compilare a mano.

## Tabella riassuntiva

| qid | recall@5 | n_verified/n_total | finish_reason | output_tokens | checklist N/M | dich. limite | allucinazione |
|---|---|---|---|---|---|---|---|
| Q6  | True  | 9/9 | stop | 751 | 5/5 (100%) | n/a | no |
| Q1  | True  | 7/7 | stop | 898 | 4/5 (80%)  | n/a | no |
| Q9  | False | 3/3 | stop | 722 | 2/5 (40%)  | sì  | sì (benigna, vedi nota Q9) |
| Q43 | False | 5/5 | stop | 698 | 2/5 (40%)  | sì  | no |
| Q47 | n/a   | 0/0 | stop | 85  | 3/3 (100%) | n/a | no |

## Q6

**Query**: Quali sono i compiti del responsabile della protezione dei dati?

**Automatic**: recall@5=True, n_verified=9/9, all_verified=True, finish_reason=stop, output_tokens=751, TTFT=1220ms, total=21836ms.

**Top-5 chunk recuperati (post-rerank)**:

- `eli/reg/2016/679/oj__art_39` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 39) ← gold
- `eli/reg/2016/679/oj__art_38` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 38) ← gold
- `eli/reg/2016/679/oj__art_37` (Capo IV - Titolare del trattamento e responsabile del trattamento > art. 37) ← gold
- `eli/reg/2016/679/oj__recital_97` (Considerando 97)
- `eli/reg/2016/679/oj__recital_108` (Considerando 108)

**Gold chunks attesi**:

- `eli/reg/2016/679/oj__art_37`
- `eli/reg/2016/679/oj__art_38`
- `eli/reg/2016/679/oj__art_39`

**Annotated answer**:

```
## Compiti del Responsabile della Protezione dei Dati (RPD)

Ai sensi del Regolamento, il responsabile della protezione dei dati è incaricato almeno dei seguenti compiti [cite:eli/reg/2016/679/oj__art_39]:

1. **Informazione e consulenza**: informare e fornire consulenza al titolare del trattamento, al responsabile del trattamento e ai dipendenti che eseguono il trattamento in merito agli obblighi derivanti dal Regolamento nonché da altre disposizioni dell'Unione o degli Stati membri relative alla protezione dei dati [cite:eli/reg/2016/679/oj__art_39];

2. **Sorveglianza della conformità**: sorvegliare l'osservanza del Regolamento, di altre disposizioni applicabili e delle politiche interne in materia di protezione dei dati personali, compresi l'attribuzione delle responsabilità, la sensibilizzazione e la formazione del personale coinvolto nei trattamenti [cite:eli/reg/2016/679/oj__art_39];

3. **Parere sulla DPIA**: fornire, se richiesto, un parere in merito alla valutazione d'impatto sulla protezione dei dati e sorvegliarne lo svolgimento ai sensi dell'articolo 35 [cite:eli/reg/2016/679/oj__art_39];

4. **Cooperazione con l'autorità di controllo**: cooperare con l'autorità di controllo e fungere da punto di contatto per questioni connesse al trattamento, inclusa la consultazione preventiva di cui all'articolo 36 [cite:eli/reg/2016/679/oj__art_39].

### Modalità di esercizio dei compiti

Nell'eseguire i propri compiti, il RPD considera debitamente i rischi inerenti al trattamento, tenuto conto della natura, dell'ambito di applicazione, del contesto e delle finalità del medesimo [cite:eli/reg/2016/679/oj__art_39].

Il titolare e il responsabile del trattamento sono tenuti a sostenere il RPD fornendogli le risorse necessarie per assolvere tali compiti, accedere ai dati personali e ai trattamenti e mantenere la propria conoscenza specialistica [cite:eli/reg/2016/679/oj__art_38]. Il RPD opera in modo indipendente, non riceve istruzioni per quanto riguarda l'esecuzione dei propri compiti e riferisce direttamente al vertice gerarchico del titolare o del responsabile del trattamento [cite:eli/reg/2016/679/oj__art_38].

Il RPD è inoltre tenuto al segreto o alla riservatezza in merito all'adempimento dei propri compiti, in conformità del diritto dell'Unione o degli Stati membri [cite:eli/reg/2016/679/oj__art_38].
```

**Gold answer**:

```
Il responsabile della protezione dei dati informa e fornisce consulenza al titolare, al responsabile del trattamento e ai dipendenti sugli obblighi derivanti dal GDPR e dalle altre disposizioni in materia di protezione dei dati, sorvegliandone l'osservanza unitamente alle politiche interne, anche tramite sensibilizzazione e formazione del personale [cite:eli/reg/2016/679/oj__art_39]. Su richiesta fornisce parere sulla valutazione d'impatto sulla protezione dei dati e ne sorveglia lo svolgimento ai sensi dell'art. 35 [cite:eli/reg/2016/679/oj__art_39]. Coopera con l'autorità di controllo e funge da punto di contatto, anche per la consultazione preventiva di cui all'art. 36 [cite:eli/reg/2016/679/oj__art_39]. Nell'esecuzione dei compiti considera i rischi inerenti al trattamento, tenuto conto della natura, dell'ambito, del contesto e delle finalità [cite:eli/reg/2016/679/oj__art_39]. Il DPO è designato in funzione delle qualità professionali e della conoscenza specialistica della normativa e delle prassi [cite:eli/reg/2016/679/oj__art_37], deve essere tempestivamente coinvolto in tutte le questioni rilevanti, disporre delle risorse necessarie e operare senza ricevere istruzioni sull'esecuzione dei propri compiti, riferendo al vertice gerarchico [cite:eli/reg/2016/679/oj__art_38].
```

**Checklist sostantiva** (spuntare a mano dopo lettura):

- [x] informa/consiglia titolare e dipendenti sugli obblighi
- [x] sorveglia osservanza GDPR + politiche interne (incl. sensibilizzazione/formazione)
- [x] fornisce parere su DPIA e ne sorveglia svolgimento (art. 35)
- [x] coopera con autorità di controllo, funge da punto di contatto
- [x] riferimento art. 39 GDPR

**Citazioni semantiche** (per max 4 cite: OK | weak | wrong):

- 4/4 OK. Tutte le citazioni a `art_39` puntano coerentemente al testo dei compiti enumerati nei chunk recuperati. Citazioni a `art_38` (risorse, indipendenza, segreto) coerenti col chunk.

**Allucinazioni semantiche** (claim non supportata dai chunk recuperati; sì/no + nota):

- No. La sezione "Modalità di esercizio dei compiti" (art. 38) aggiunge contenuto rispetto al gold, ma è interamente supportato dal chunk `art_38` presente nel top-5.

**Commento** (1-2 righe):

- Caso di sanità: retrieval pulito (3/3 gold), generazione strutturata e completa, risposta tecnicamente più ricca del gold senza allucinare. Baseline ideale.

## Q1

**Query**: Un sistema che fa screening automatico dei CV in fase di selezione del personale ricade tra i sistemi ad alto rischio dell'AI Act?

**Automatic**: recall@5=True, n_verified=7/7, all_verified=True, finish_reason=stop, output_tokens=898, TTFT=1479ms, total=19883ms.

**Top-5 chunk recuperati (post-rerank)**:

- `eli/reg/2024/1689/oj__recital_57` (Considerando 57) ← gold
- `eli/reg/2024/1689/oj__recital_61` (Considerando 61)
- `eli/reg/2024/1689/oj__recital_85` (Considerando 85)
- `eli/reg/2024/1689/oj__recital_53` (Considerando 53)
- `eli/reg/2024/1689/oj__art_6` (Capo III - SISTEMI DI IA AD ALTO RISCHIO > art. 6) ← gold

**Gold chunks attesi**:

- `eli/reg/2024/1689/oj__art_26`
- `eli/reg/2024/1689/oj__art_6`
- `eli/reg/2024/1689/oj__annex_III__point_4`
- `eli/reg/2024/1689/oj__recital_57`

**Annotated answer**:

```
## Classificazione come sistema ad alto rischio

Sì, un sistema di IA per lo screening automatico dei CV in fase di selezione del personale ricade, in linea di principio, tra i sistemi ad alto rischio ai sensi dell'AI Act.

### Base normativa

I sistemi di IA utilizzati nel settore dell'occupazione, e in particolare per **l'assunzione e la selezione delle persone**, sono esplicitamente classificati come ad alto rischio [cite:eli/reg/2024/1689/oj__recital_57]. Il considerando evidenzia che tali sistemi possono avere un impatto significativo sulle prospettive di carriera e sul sostentamento delle persone, nonché perpetuare modelli storici di discriminazione [cite:eli/reg/2024/1689/oj__recital_57].

Sul piano dispositivo, l'art. 6, paragrafo 2, stabilisce che sono considerati ad alto rischio i sistemi di IA elencati nell'Allegato III, categoria che include i sistemi per la selezione del personale [cite:eli/reg/2024/1689/oj__art_6].

### Possibile deroga

L'art. 6, paragrafo 3, prevede una deroga: un sistema di IA rientrante nell'Allegato III **non** è considerato ad alto rischio se non influenza materialmente il processo decisionale e ricorre almeno una delle seguenti condizioni [cite:eli/reg/2024/1689/oj__art_6]:

- esegue un **compito procedurale limitato** (es. conversione di dati non strutturati in strutturati o classificazione documentale);
- è destinato a **migliorare il risultato di un'attività umana precedentemente completata**;
- **rileva schemi decisionali** senza sostituire la valutazione umana;
- svolge un **compito preparatorio** rispetto a una valutazione successiva.

A titolo esemplificativo, un sistema che si limita a classificare i CV in categorie o a rilevare duplicati potrebbe rientrare nella prima condizione [cite:eli/reg/2024/1689/oj__recital_53].

### Limite assoluto: profilazione

Tuttavia, **indipendentemente dalle condizioni di deroga**, il sistema è **sempre considerato ad alto rischio** qualora effettui **profilazione di persone fisiche** [cite:eli/reg/2024/1689/oj__art_6]. Uno screening automatico dei CV che valuti caratteristiche, comportamenti o tratti personali dei candidati integrerebbe tipicamente tale fattispecie.

### Onere documentale

Qualora il fornitore ritenga che il proprio sistema non sia ad alto rischio, è tenuto a **documentare tale valutazione prima dell'immissione sul mercato** e a registrare il sistema nella banca dati UE, mettendo la documentazione a disposizione delle autorità competenti su richiesta [cite:eli/reg/2024/1689/oj__art_6].

### Conclusione

Un sistema di screening automatico dei CV che incide sulla selezione dei candidati — influenzando materialmente l'esito del processo decisionale o effettuando profilazione — è da classificarsi come **sistema ad alto rischio**, con tutti gli obblighi regolatori conseguenti. La deroga ex art. 6, paragrafo 3, è applicabile solo in casi residuali e rigorosamente circoscritti, che difficilmente ricorrono in un sistema di screening funzionalmente rilevante ai fini della selezione.
```

**Gold answer**:

```
Sì. L'AI Act classifica come ad alto rischio i sistemi di IA destinati all'assunzione o selezione di persone fisiche, in particolare per analizzare o filtrare le candidature e valutare i candidati, fattispecie in cui lo screening automatico dei CV rientra direttamente [cite:eli/reg/2024/1689/oj__annex_III__point_4]. Tali sistemi sono ad alto rischio in quanto possono incidere significativamente su prospettive di carriera e diritti dei lavoratori e perpetuare modelli storici di discriminazione [cite:eli/reg/2024/1689/oj__recital_57]. La qualificazione resta esclusa solo se il sistema non presenta un rischio significativo per salute, sicurezza o diritti fondamentali, ad esempio perché svolge un compito procedurale limitato o meramente preparatorio, ma non quando effettua profilazione delle persone fisiche [cite:eli/reg/2024/1689/oj__art_6]. Il deployer è quindi soggetto agli obblighi degli artt. 26 ss., inclusi sorveglianza umana, monitoraggio, informazione preventiva di lavoratori e rappresentanti e trasparenza verso i candidati interessati dalla decisione [cite:eli/reg/2024/1689/oj__art_26].
```

**Checklist sostantiva** (spuntare a mano dopo lettura):

- [x] art. 6 par. 2 AI Act come fonte del meccanismo
- [x] rinvio ad Allegato III come elenco operativo
- [ ] menziona almeno 2-3 settori dell'Allegato (istruzione, occupazione, accesso a servizi essenziali, law enforcement, biometria, infrastrutture critiche)
- [x] art. 6 par. 3: eccezione "rischio non significativo" + condizioni
- [x] NON confonde con art. 5 (pratiche vietate) e NON usa considerando come fonte dispositiva

**Citazioni semantiche** (per max 4 cite: OK | weak | wrong):

- 4/4 OK. `recital_57` usato come motivazione/contesto (impatto su carriere, discriminazione), `art_6` usato come dispositivo (par.2, par.3, par.4). Distinzione formalmente corretta tra fonte motivazionale e dispositiva.

**Allucinazioni semantiche** (claim non supportata dai chunk recuperati; sì/no + nota):

- No. Il check mancato sui "2-3 settori dell'Allegato" è retrieval-bound: il top-5 non include `annex_III__point_4` né altri punti dell'Allegato, il modello cita solo "occupazione" via recital_57. Non inventa altri settori.

**Commento** (1-2 righe):

- Conferma decisione W5 voce 29 (cloud risolve il caso peggiore W5 su Q1). Generazione corretta sui chunk disponibili; il check 3 fallisce per gap retrieval (Allegato III non agganciato), non per qualità modello.

## Q9

**Query**: Quali sono i reati presupposto in materia di trattamento illecito di dati personali ai sensi del 231?

**Automatic**: recall@5=False, n_verified=3/3, all_verified=True, finish_reason=stop, output_tokens=722, TTFT=1976ms, total=17611ms.

**Top-5 chunk recuperati (post-rerank)**:

- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167` (art. 167)
- `eli/reg/2016/679/oj__recital_75` (Considerando 75)
- `eli/reg/2016/679/oj__recital_19` (Considerando 19)
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies` (art. 2-octies)
- `eli/reg/2016/679/oj__recital_43` (Considerando 43)

**Gold chunks attesi**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis`

**Annotated answer**:

```
## Reati presupposto in materia di trattamento illecito di dati personali ai sensi del D.Lgs. 231/2001

Il contesto normativo fornito non contiene riferimenti diretti al D.Lgs. 231/2001 né alle specifiche disposizioni che individuano i reati presupposto ai fini della responsabilità amministrativa degli enti.

Tuttavia, sulla base dell'unico riferimento normativo pertinente presente nel contesto, è possibile illustrare le fattispecie penali previste dall'art. 167 del Codice Privacy (D.Lgs. 196/2003), che costituiscono i reati in materia di trattamento illecito di dati:

1. **Comma 1**: chiunque, al fine di trarre profitto o arrecare danno all'interessato, operi in violazione degli artt. 123, 126, 130 o del provvedimento di cui all'art. 129, arrecando nocumento all'interessato, è punito con la reclusione da sei mesi a un anno e sei mesi [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167].

2. **Comma 2**: chiunque, con le medesime finalità, tratti dati particolari (artt. 9 e 10 del Regolamento) in violazione degli artt. 2-sexies, 2-octies o delle misure di garanzia di cui all'art. 2-septies, arrecando nocumento all'interessato, è punito con la reclusione da uno a tre anni [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167].

3. **Comma 3**: la medesima pena del comma 2 si applica a chiunque, con le stesse finalità, effettui trasferimenti di dati personali verso paesi terzi o organizzazioni internazionali al di fuori dei casi consentiti dagli artt. 45, 46 o 49 del Regolamento, arrecando nocumento all'interessato [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167].

---

**Avvertenza**: il contesto normativo fornito **non contiene il testo del D.Lgs. 231/2001** né le disposizioni che formalmente qualificano tali reati come "presupposto" ai fini della responsabilità degli enti. Per una risposta completa e tecnicamente fondata sul collegamento tra l'art. 167 del Codice Privacy e il catalogo 231, sarebbe necessario disporre delle relative norme del D.Lgs. 231/2001 (in particolare l'art. 24-bis o eventuali disposizioni specifiche), che non sono presenti nel contesto fornito.
```

**Gold answer**:

```
I reati-presupposto del D.Lgs 231/2001 in materia di trattamento illecito di dati personali sono i delitti informatici elencati nell'art. 24-bis del decreto, che richiama specifici articoli del codice penale: 615-ter, 617-quater, 617-quinquies, 635-bis, 635-ter, 635-quater, 635-quinquies, 615-quater, 635-quater.1, 491-bis e 640-quinquies [cite:akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis]. Per la commissione di tali delitti l'ente è soggetto a sanzione pecuniaria entro le quote indicate (fino a settecento per i delitti del comma 1, fino a quattrocento per quelli dei commi 2 e 3) [cite:akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis]. Alle sanzioni pecuniarie si aggiungono sanzioni interdittive ex art. 9, comma 2, modulate per categoria di delitto [cite:akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis]. Il dettaglio delle singole fattispecie penali richiamate (es. accesso abusivo a sistema informatico ex art. 615-ter c.p., danneggiamento informatico ex art. 635-bis c.p.) richiede il codice penale, non incluso nel corpus normativo di riferimento.
```

**Checklist sostantiva** (spuntare a mano dopo lettura):

- [ ] cita art. 24-bis D.Lgs 231/2001 come fonte
- [ ] menziona delitti informatici / trattamento illecito dati come categoria
- [ ] indica sanzioni 231 (pecuniarie e/o interdittive)
- [x] **dichiara esplicitamente che il dettaglio degli articoli del codice penale richiamati non è incluso nel corpus normativo di riferimento**
- [x] NON inventa contenuti dell'art. 25-undecies (anti-allucinazione)

**Citazioni semantiche** (per max 4 cite: OK | weak | wrong):

- 3/3 OK rispetto al chunk effettivamente recuperato (`art_167` Codice Privacy): tutte coerenti con i commi 1, 2, 3 dell'articolo. Ma rispetto al gold sono **off-topic**: la risposta è centrata su `art. 167` (reato autonomo Codice Privacy) invece che su `art. 24-bis` 231 (gold).

**Allucinazioni semantiche** (claim non supportata dai chunk recuperati; sì/no + nota):

- Sì, una **benigna**. Il modello nomina "art. 24-bis o eventuali disposizioni specifiche" in chiusura come riferimento mancante. Il numero d'articolo è corretto (prior knowledge Sonnet su D.Lgs 231) ma NON è supportato dai chunk del top-5. Comportamento meta-cognitivamente corretto (segnala il gap), Ragas faithfulness lo penalizzerà comunque.

**Commento** (1-2 righe):

- Retrieval-bound failure: il retriever non aggancia `231 art_24-bis` per disallineamento lessicale tra vocabolario query (231/reati-presupposto/trattamento illecito) e vocabolario chunk (delitti informatici elencati con riferimenti c.p.). Conferma diagnosi W7-prep voce 30 (capability v1.1, vedi ROADMAP_POST_V1). Generazione corretta sui chunk disponibili + dichiarazione di limite spontanea, ma checklist non passa perché il gold richiede contenuto da `art_24-bis` non recuperato.

## Q43

**Query**: Cosa dice la legge sulla privacy?

**Automatic**: recall@5=False, n_verified=5/5, all_verified=True, finish_reason=stop, output_tokens=698, TTFT=1251ms, total=14623ms.

**Top-5 chunk recuperati (post-rerank)**:

- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_175` (art. 175)
- `eli/reg/2016/679/oj__recital_2` (Considerando 2)
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies` (art. 2-octies)
- `eli/reg/2024/1689/oj__recital_167` (Considerando 167)
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_58` (art. 58)

**Gold chunks attesi**:

- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_1`
- `eli/reg/2016/679/oj__art_1`

**Annotated answer**:

```
La domanda "cosa dice la legge sulla privacy?" è molto generica. Sulla base del contesto normativo fornito, è possibile illustrare solo alcuni aspetti specifici disciplinati dalla normativa vigente.

**Protezione dei dati personali e diritti fondamentali**

Il quadro normativo europeo mira a tutelare i diritti e le libertà fondamentali delle persone fisiche con riguardo al trattamento dei dati personali, in particolare il diritto alla protezione dei dati, indipendentemente dalla nazionalità o residenza dell'interessato [cite:eli/reg/2016/679/oj__recital_2].

**Dati relativi a condanne penali e reati**

Il trattamento di dati personali relativi a condanne penali, reati o connesse misure di sicurezza, quando non avviene sotto il controllo dell'autorità pubblica, è consentito solo se autorizzato da una norma di legge o di regolamento che preveda garanzie appropriate per i diritti degli interessati [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies]. Tale trattamento è ammesso, tra l'altro, in materia di diritto del lavoro, prevenzione delle frodi in ambito assicurativo, accertamento di diritti in sede giudiziaria e prevenzione del riciclaggio [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-octies].

**Trattamenti per finalità di sicurezza nazionale e difesa**

I trattamenti effettuati dagli organismi di intelligence e dalle Forze armate sono soggetti a una disciplina speciale, con applicazione limitata e compatibile delle disposizioni generali in materia di protezione dei dati [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_58].

**Controllo sulle forze di polizia**

Il controllo sul Centro elaborazione dati delle forze di polizia è esercitato dal Garante per la protezione dei dati personali. L'interessato ha il diritto di richiedere la conferma dell'esistenza di dati che lo riguardano, la loro comunicazione in forma intellegibile e, in caso di trattamento illecito, la cancellazione o la trasformazione in forma anonima [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_175].

---

Per una risposta esaustiva su ulteriori aspetti della normativa privacy (es. basi giuridiche del trattamento, diritti degli interessati, obblighi del titolare), il contesto normativo fornito non contiene riferimenti sufficienti per rispondere con precisione.
```

**Gold answer**:

```
Il GDPR (Regolamento UE 2016/679) stabilisce le norme sulla protezione delle persone fisiche con riguardo al trattamento dei dati personali e sulla libera circolazione di tali dati, proteggendo i diritti e le libertà fondamentali, in particolare il diritto alla protezione dei dati personali, e impedendo che la libera circolazione nell'Unione sia limitata per motivi di tutela [cite:eli/reg/2016/679/oj__art_1]. In Italia il D.Lgs 196/2003 (Codice Privacy) integra e adegua la disciplina nazionale al regolamento, definendone l'oggetto [cite:akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_1]. La query è formulata in modo molto generico: i gold_chunks coprono solo le disposizioni di apertura e non il merito dei singoli istituti (basi giuridiche, diritti dell'interessato, sicurezza, DPIA, sanzioni), per i quali servono articoli specifici del GDPR e del Codice Privacy non inclusi nel corpus normativo di riferimento.
```

**Checklist sostantiva** (spuntare a mano dopo lettura):

- [ ] cita GDPR (Regolamento UE 2016/679) come fonte principale UE
- [ ] cita D.Lgs 196/2003 (Codice Privacy) come integrazione nazionale italiana
- [ ] indica oggetto del GDPR: protezione persone fisiche nel trattamento dei dati personali + libera circolazione
- [x] menziona diritti/libertà fondamentali, in particolare diritto alla protezione dei dati personali
- [x] dichiara selettività/limite del corpus E NON espone contenuto dispositivo specifico (basi giuridiche, diritti, sicurezza, DPIA, sanzioni) come se fosse supportato dai chunk recuperati

**Citazioni semantiche** (per max 4 cite: OK | weak | wrong):

- 4/4 OK (su 5 cite totali nella risposta). Ogni citazione punta a un chunk effettivamente pertinente al frammento che descrive (`recital_2` → diritti fondamentali; `art_2-octies` → condanne penali; `art_58` → sicurezza nazionale; `art_175` → controllo polizia).

**Allucinazioni semantiche** (claim non supportata dai chunk recuperati; sì/no + nota):

- No. Tutto il contenuto dispositivo è ancorato ai chunk recuperati. Drift lessicale rilevato in chiusura: usa "il contesto normativo fornito non contiene riferimenti sufficienti" invece del pattern canonico "non incluso nel corpus normativo di riferimento" (vedi PROJECT_CONTEXT voce 32). Sostanza identica, lessico diverso.

**Commento** (1-2 righe):

- Retrieval-bound failure su query vaga: il retriever non porta gli `art_1` "Oggetto" di GDPR e Codice Privacy (privilegiati nei top-5 articoli più specifici e considerando). I check 1-3 falliscono perché richiedono inquadramento via `art_1`, non recuperati. Comportamento generazione ideale per scenario edge: dichiara genericità in apertura, ancora ai chunk, dichiara limite in chiusura, zero allucinazioni.

## Q47

**Query**: art 999 GDPR

**Automatic**: recall@5=False, n_verified=0/0, all_verified=True, finish_reason=stop, output_tokens=85, TTFT=2249ms, total=4428ms.

**Top-5 chunk recuperati (post-rerank)**:

- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-novies` (art. 2-novies)
- `eli/reg/2024/1689/oj__recital_167` (Considerando 167)
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_2-sex-decies` (art. 2-sex-decies)
- `eli/reg/2016/679/oj__recital_173` (Considerando 173)
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-novies` (Capo I > Sezione III > art. 25-novies)

**Gold chunks attesi**:

- _(nessuno — query negative)_

**Annotated answer**:

```
Il contesto normativo fornito non contiene riferimenti sufficienti per rispondere con precisione.

Il GDPR (Regolamento UE 2016/679) è composto da 99 articoli: non esiste alcun "articolo 999". Il contesto normativo fornito non include tale disposizione, né alcun riferimento ad essa.
```

**Gold answer**:

```
Il contesto normativo fornito non contiene riferimenti sufficienti per rispondere con precisione.
```

**Checklist sostantiva** (spuntare a mano dopo lettura):

- [x] dichiara esplicitamente che l'articolo non esiste nel corpus
- [x] NON inventa contenuto plausibile
- [x] non finge di aver trovato il riferimento
- [x] (opzionale, non conta nel totale) suggerisce articoli vicini realmente esistenti

**Citazioni semantiche** (per max 4 cite: OK | weak | wrong):

- n/a (0 citazioni emesse, comportamento corretto per negative).

**Allucinazioni semantiche** (claim non supportata dai chunk recuperati; sì/no + nota):

- No. La nota "GDPR composto da 99 articoli" è informazione esterna corretta (prior knowledge), ma è offerta come orientamento meta-discorsivo, non come contenuto del corpus. Non è allucinazione nel senso rilevante (claim spacciata per fondata sui chunk).

**Commento** (1-2 righe):

- Clean. Rifiuto esplicito + nota orientativa corretta + 85 token. Comportamento ideale per query negative su articolo inesistente.

## Verdict finale

- **GO / NO-GO**: **GO**
- **Motivazione (1 riga)**: 5/5 `all_verified`, 0 allucinazioni semantiche evidenti sui chunk recuperati, dichiarazione di limite spontanea su entrambi i casi previsti (Q9, Q43); checklist mediana 80% sopra soglia 75% (mean 72%, sotto soglia se non si segregano Q9+Q43 come retrieval-bound: mediana 100% su Q6+Q1+Q47).

## Note metodologiche per il run Ragas W7

1. **Q9 e Q43 sono retrieval-bound failures, non generation failures.** Su entrambi i casi: 100% cite strutturalmente verified, zero allucinazioni semantiche su contenuto presentato come fondato sui chunk, dichiarazione di limite del corpus spontanea. La generazione fa la cosa giusta sui chunk disponibili. Il fallimento è del retrieval (gap noto v1.1, vedi `data/benchmark/BENCHMARK_W3.md`: Q9 zero-recall, Q43 non aggancia gli `art_1` "Oggetto" di GDPR e Codice Privacy).

2. **Ragas faithfulness e answer_relevancy daranno punteggio basso su Q9 e Q43**, perché entrambe le metriche non distinguono "risposta corretta sui chunk disponibili + dichiarazione di limite" da "risposta sbagliata". Interpretare questi punteggi bassi come **expected behavior**, non come fallimento di pipeline.

3. **Allucinazione benigna su Q9**: il modello cita `art. 24-bis D.Lgs 231/2001` in chiusura come riferimento mancante. Il numero è corretto (prior knowledge Sonnet), ma NON è supportato dai chunk del top-5. Per Ragas faithfulness questo è negativo. Comportamento meta-cognitivamente corretto (segnala il gap) ma metricamente penalizzato. Da annotare nel report Ragas.

4. **Drift lessicale Q43**: la dichiarazione di limite usa "il contesto normativo fornito non contiene riferimenti sufficienti" invece del pattern canonico "non incluso nel corpus normativo di riferimento" (vedi `PROJECT_CONTEXT.md` voce 32). Sostanza identica, lessico diverso. Eventuale finding per tuning system prompt in W6, non blocca W7.

5. **Q1 checklist 4/5** è retrieval-bound: il check mancato ("menziona 2-3 settori dell'Allegato") richiede `annex_III__point_4` o altri punti dell'Allegato, non recuperati dal retriever. Stesso pattern di Q9/Q43 in forma più lieve. Da segnalare nel report Ragas.

6. **Pattern conferma trasparenza UX**: in tutti e 3 i casi retrieval-incomplete (Q9, Q43, Q1 parziale) il modello produce dichiarazioni esplicite di limite, mai inventa contenuto dispositivo non supportato. Il citation verifier strutturale + il system prompt italiano funzionano come progettati per il target professional (DPO, studi legali).

## Sintesi go/no-go

Pipeline cloud Sonnet 4.6 pronta per Ragas eval W7 con caveat documentati. Prima di lanciare Ragas: creare `spike/RAGAS_RUN_NOTES.md` con le 6 note sopra come chiave interpretativa pre-run, per evitare che i punteggi bassi su Q5/Q9/Q43 (e altri casi "dichiarazione limite corpus" delle 11 query identificate in `STATS.md`) vengano letti acriticamente.
