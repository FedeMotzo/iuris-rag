# Graph multi-normativa — Note estese di curatela

> Documento di supporto a `graph.yaml`. Contiene note lunghe, caveat, mapping
> use case, link in riserva, link scartati e decisioni di metodo.
>
> Lo YAML è la fonte autoritativa per il runtime; questo documento è la
> traccia del ragionamento di curatela per future revisioni (revisore legale
> v1.1, articolo tecnico settimana 7, eventuali estensioni del catalogo).

**Versione:** v1, chiusura curatela 2026-05-19
**Totale link in cassa:** 22
**Riserva:** 2 link
**Scartati documentati:** 3 link

---

## Indice

1. [Decisioni di metodo](#decisioni-di-metodo)
2. [Distribuzione finale](#distribuzione-finale)
3. [Link confermati: note estese](#link-confermati-note-estese)
4. [Link in riserva](#link-in-riserva)
5. [Link scartati](#link-scartati)
6. [Open questions per consolidamento](#open-questions-per-consolidamento)

---

## Decisioni di metodo

1. **Cap operativo: 22 link** (sotto il cap massimo di 30 indicato nel system
   prompt di curatela). Motivazione: link aggiunti oltre questa soglia
   rischiavano di essere filler per arrivare al numero round. Meglio 22
   motivati che 30 di cui parte mediocre. Lazy expansion via riserve in caso
   di gap emersi a settimana 5-7.

2. **Link concettuali ammessi:** il graph v1 accetta link "concettuali" non
   mappati a query del benchmark. Distribuzione finale: 13/22 (59%) mappati
   a UC1/UC3/UC5 di SCOPE, 9/22 (41%) concettuali (architettura del dominio).
   La misurazione del valore sul benchmark si fa solo sui link
   benchmark-motivati tramite metrica `graph-rescued` (settimana 5-7). I link
   concettuali non vengono misurati né degradano la metrica, restano come
   ricchezza per LLM e per l'articolo tecnico finale.

3. **Note brevi (1-2 frasi) nello YAML.** L'LLM riceve la nota nel prompt come
   arricchimento di contesto: una nota di 200 caratteri orienta, una di 2000
   diluisce. Le note estese di questo documento sono per noi (e per il
   revisore legale futuro), non per il sistema a runtime.

4. **Schema invariato:** `from`, `to`, `relation`, `note`, `source`. Niente
   campi `use_case` o `caveat` nello YAML. Il loader di `core/graph_loader`
   ha test scritti sui campi esistenti; aggiungerli ora sarebbe scope creep.

5. **Convenzione direzione:** la norma gerarchicamente più specifica o
   cronologicamente più recente come `from`. Bidirezionale a runtime.

6. **Granularità chunk:** i chunk del corpus sono articoli interi (o
   considerando, o allegati). Quando un link riguarda un comma specifico
   (es. art. 10 comma 5 AI Act, art. 26 comma 9 AI Act), il comma è
   menzionato nella nota per precisione semantica ma il chunk_id corrisponde
   all'articolo monolitico.

7. **Enum relazioni a 5 valori invariato:** `complementare`,
   `presupposto_di`, `rinvia_a`, `attua`, `deroga`. La stessa parola copre
   sfumature diverse (es. `deroga` come eccezione vs come specializzazione
   nazionale): le note del link distinguono il caso concreto. Niente
   sotto-categorie nell'enum.

8. **Disclaimer giuridico:** la curatela è manuale e "not legally validated".
   Le note esprimono interpretazioni dottrinali ragionevoli ma non
   sostituiscono parere professionale. Da menzionare nell'articolo tecnico
   finale e nel README.

9. **Workflow di raffinamento:** i 6 link iniziali del file di partenza sono
   stati conservati come slot, e di questi 3 hanno ricevuto nota raffinata
   senza occupare slot aggiuntivi:
   - Slot iniziale "FRIA ↔ DPIA" → nota raffinata da A3
   - Slot iniziale "GDPR art. 22 ↔ AI Act art. 6" → nota raffinata da A6
   - Slot iniziale "GDPR art. 32 ↔ NIS2 art. 24" → nota raffinata da C1
   I 3 link non raffinati (B1, B2, B3) hanno mantenuto nota equivalente
   nell'YAML finale, riformulata brevemente per coerenza stilistica.

---

## Distribuzione finale

### Per tema

| Tema | Numero link |
|---|---:|
| B — Triangolo 231 ↔ GDPR ↔ AI Act | 3 |
| A — GDPR ↔ AI Act | 9 |
| C — NIS2 trasversale | 7 |
| D — L. 132/2025 + Cod. Privacy ↔ GDPR/AI Act | 3 |
| **Totale** | **22** |

### Per use case

| Use case | Link |
|---|---|
| UC1 — Classificazione AI Act high-risk | 8 (A1, A4, A5, A6, A7, A8, B3, D2) |
| UC3 — DPIA vs FRIA | 2 (A2, A3) |
| UC5 — 231 + AI/cyber | 4 (B1, B2, C6, C7) |
| Concettuali — architettura dominio | 8 (A9, C1, C2, C3, C4, C5, D3, D4) |

UC2 (timeline obblighi AI Act) e UC4 (provvedimenti Garante) non hanno link
dedicati: UC2 perché non emerge un nesso cross-norma forte (è una query
mono-normativa sull'AI Act); UC4 perché il Garante è fuori corpus v1.

### Per relazione

| Relazione | Numero | ID link |
|---|---:|---|
| complementare | 16 | B2, B3, A1, A3, A4, A5, A6, A7, A9, C1, C2, C3, C4, C5, C6, C7 |
| deroga | 3 | A8, D2 (Cod. Privacy 2-ter), D3 (Cod. Privacy 2-sexies) |
| presupposto_di | 1 | B1 |
| rinvia_a | 1 | A2 |
| attua | 1 | D1 (L. 132/2025 art. 11 ↔ Allegato III) |

Lo sbilanciamento verso `complementare` (73%) è fisiologico per il dominio:
la maggior parte dei nessi cross-norma in privacy/AI/cyber sono cumulative
obligations, non eccezioni o rinvii formali.

---

## Link confermati: note estese

Le note estese qui sotto sono la versione "lunga" delle note brevi presenti
nello YAML. Ognuna include caveat, use case mapping, e riferimento alle
discussioni che hanno portato alla formulazione finale.

---

### Tema B — Triangolo 231 ↔ GDPR ↔ AI Act

#### B1 — 231 art. 24-bis ↔ GDPR art. 32

- **Use case:** UC5
- **Caveat:** Il nesso è giurisprudenziale/dottrinale: art. 24-bis non cita il
  GDPR, ma la condotta tipica spesso coincide con un fallimento delle misure
  di sicurezza GDPR.
- **Nota estesa:** Una violazione degli obblighi di sicurezza ex art. 32 GDPR
  può integrare il fatto materiale di reati informatici (es. accesso abusivo,
  danneggiamento dati) che, se commessi nell'interesse o a vantaggio
  dell'ente, attivano la responsabilità 231 ex art. 24-bis. Il "presupposto"
  è qui inteso in senso sostanziale: la condotta GDPR-violante è elemento
  materiale del reato presupposto 231.

#### B2 — 231 art. 6 ↔ AI Act art. 9

- **Use case:** UC5
- **Caveat:** Integrazione operativa è prassi consolidata in compliance
  integrata, non obbligo testuale.
- **Nota estesa:** Per un ente che usa sistemi AI high-risk, il sistema di
  gestione rischi AI Act ex art. 9 è componente naturale del modello 231
  idoneo a prevenire reati presupposto commessi tramite/con l'ausilio del
  sistema AI. I due adempimenti si integrano: il modello 231 non sostituisce
  il risk management AI Act, e viceversa.

#### B3 — AI Act Allegato III punto 4 ↔ GDPR art. 22

- **Use case:** UC1
- **Caveat:** Nessuno. Link testuale e dottrinalmente pacifico.
- **Nota estesa:** I sistemi AI high-risk per HR (screening CV, valutazione
  candidati) tipicamente realizzano trattamenti rientranti nell'art. 22 GDPR:
  decisioni basate unicamente su trattamento automatizzato con effetti
  significativi sulla persona. Obblighi cumulativi: requisiti AI Act
  (governance dati, trasparenza, sorveglianza umana ex artt. 10-14) +
  diritti GDPR (informativa rafforzata, diritto a intervento umano,
  contestazione).
- **Granularità:** Allegato III è chunk monolitico; "punto 4" nella nota per
  precisione semantica.

---

### Tema A — GDPR ↔ AI Act

#### A1 — AI Act art. 10 ↔ GDPR art. 5

- **Use case:** UC1
- **Caveat:** Art. 5 GDPR è chunk monolitico ad alta frequenza nel corpus.
  Link applicabile soprattutto a query training data quality.
- **Nota estesa:** L'art. 10 AI Act impone requisiti di qualità sui dataset
  di training/validazione/test (pertinenza, rappresentatività, accuratezza,
  completezza). Quando i dataset contengono dati personali, questi requisiti
  si cumulano con i principi GDPR art. 5, in particolare esattezza (art.
  5.1.d) e minimizzazione (art. 5.1.c). L'AI Act non sostituisce: integra.

#### A2 — AI Act art. 26 ↔ GDPR art. 35

- **Use case:** UC3
- **Caveat:** Il chunk di art. 26 AI Act include tutti i commi; il rinvio
  specifico è al comma 9 nella versione consolidata IT. Non serve chunk
  separato per il comma.
- **Nota estesa:** L'art. 26(9) AI Act stabilisce che il deployer, quando
  applicabile, usa le informazioni fornite dal fornitore ex art. 13 AI Act
  per assolvere all'obbligo DPIA ex art. 35 GDPR. Rinvio formale esplicito:
  l'AI Act riconosce e si raccorda con la DPIA GDPR.
- **Granularità:** chunk art. 26 monolitico; "comma 9" nella nota.

#### A3 — AI Act art. 27 ↔ GDPR art. 35

- **Use case:** UC3
- **Caveat:** Sostituisce la nota originale del link iniziale "FRIA e DPIA si
  applicano cumulativamente per sistemi AI high-risk che trattano dati
  personali" con versione più ricca.
- **Nota estesa:** FRIA e DPIA coprono dimensioni diverse: la FRIA valuta
  l'impatto sui diritti fondamentali del soggetto destinatario del sistema
  AI high-risk (non solo data subject); la DPIA valuta il rischio per i
  diritti e libertà degli interessati nel trattamento dati. Quando un
  sistema AI high-risk tratta dati personali, vanno fatte entrambe — l'art.
  27 AI Act lo riconosce esplicitamente prevedendo coordinamento ma non
  sostituzione.

#### A4 — AI Act art. 14 ↔ GDPR art. 22

- **Use case:** UC1
- **Caveat:** Nessuna disputa dottrinale rilevante. Link di coordinamento
  progettazione-diritto.
- **Nota estesa:** L'art. 14 AI Act richiede che i sistemi high-risk siano
  progettati per consentire sorveglianza umana effettiva (capacità di
  interpretare l'output, interrompere il sistema, sovrascrivere decisioni).
  L'art. 22 GDPR riconosce all'interessato il diritto a NON essere soggetto
  a decisione unicamente automatizzata, con diritto a intervento umano
  significativo. I due piani sono complementari: art. 14 è obbligo di design
  ex ante sul fornitore + obbligo di garanzia operativa sul deployer; art.
  22 è diritto soggettivo ex post dell'interessato. La sorveglianza umana
  AI Act è la precondizione tecnica che rende esercitabile il diritto GDPR.

#### A5 — AI Act art. 13 ↔ GDPR art. 13

- **Use case:** UC1
- **Caveat:** Limitato alla trasparenza verso interessati che hanno fornito i
  dati direttamente. Per dati raccolti da terze parti (art. 14 GDPR)
  servirebbe link dedicato, non incluso in v1.
- **Nota estesa:** Art. 13 AI Act obbliga il fornitore a fornire al deployer
  istruzioni d'uso e informazioni sul funzionamento del sistema (capacità,
  limitazioni, accuratezza attesa, dati di training pertinenti). L'art. 13
  GDPR obbliga il titolare a informare l'interessato del trattamento. La
  trasparenza AI Act (B2B fornitore→deployer) alimenta la trasparenza GDPR
  (B2C deployer→interessato): senza la prima, il deployer non ha gli
  elementi sostanziali per assolvere alla seconda quando il trattamento usa
  AI.
- **Attenzione:** doppio significato di "art. 13" — uno è AI Act (B2B),
  l'altro è GDPR (B2C). La nota lo disambigua esplicitamente.

#### A6 — AI Act art. 6 ↔ GDPR art. 22

- **Use case:** UC1
- **Caveat:** Sostituisce la nota originale del link iniziale "Decisioni
  esclusivamente automatizzate ex art. 22 GDPR spesso ricadono in sistemi
  high-risk AI Act" con versione più strutturata. Coesiste con B3 (Allegato
  III punto 4 ↔ art. 22): A6 è meccanismo generale, B3 è specifico HR.
  Copertura query distinta: B3 → Q1/Q12 benchmark (HR/scuola); A6 →
  Q11/Q14/Q18 (credit scoring, GPAI, sanzioni).
- **Nota estesa:** L'art. 6 AI Act + Allegato III definisce quali sistemi
  sono high-risk: molti casi d'uso elencati (occupazione, credito, accesso
  a servizi essenziali, giustizia) coincidono con scenari di "decisione
  basata unicamente su trattamento automatizzato con effetti significativi"
  ex art. 22 GDPR. Un sistema classificato high-risk ex Allegato III che
  opera su dati personali con autonomia decisionale ricade tipicamente
  nell'art. 22 GDPR e ne attiva le tutele aggiuntive (consenso esplicito,
  necessità contrattuale, o autorizzazione normativa, oltre al diritto di
  contestazione).

#### A7 — AI Act art. 10 ↔ GDPR art. 6

- **Use case:** UC1
- **Caveat:** Riflette il consenso dottrinale post-AI Act senza riferimenti
  specifici nel corpus v1. Le linee guida EDPB sui modelli AI (Opinion
  28/2024 del 17 dicembre 2024) non sono incluse nel corpus v1, ma la nota
  cattura il consenso post-Opinion.
- **Nota estesa:** L'AI Act art. 10 specifica i requisiti qualitativi dei
  dataset, ma NON fornisce di per sé una base giuridica per il trattamento
  dei dati personali contenuti nei dataset di training. La base giuridica
  resta governata dall'art. 6 GDPR: il fornitore che addestra un sistema AI
  deve identificare una base lecita (tipicamente legittimo interesse ex
  art. 6.1.f, o consenso art. 6.1.a per dati raccolti ad hoc). L'art. 10
  AI Act non sostituisce l'art. 6 GDPR; ne presuppone il rispetto.

#### A8 — AI Act art. 10 (comma 5) ↔ GDPR art. 9

- **Use case:** UC1
- **Caveat:** Il chunk del corpus è art. 10 AI Act intero; la nota esplicita
  "comma 5" per precisione semantica ma il chunk_id corrisponde
  all'articolo monolitico. Q34 del benchmark (stress art. 9 GDPR) potrebbe
  beneficiarne tramite espansione cross-norma.
- **Nota estesa:** L'art. 10, comma 5, AI Act introduce una base giuridica
  specifica e nuova per il trattamento di categorie particolari di dati ex
  art. 9 GDPR: i fornitori di sistemi AI high-risk POSSONO trattare dati
  particolari quando strettamente necessario per rilevare e correggere bias
  del sistema, con garanzie rafforzate (pseudonimizzazione, limitazioni
  d'accesso, no trasferimenti). Si tratta di una deroga settoriale agli
  ordinari divieti dell'art. 9.1 GDPR, creata dall'AI Act per finalità di
  fairness algoritmica.
- **Granularità:** chunk art. 10 monolitico; "comma 5" nella nota.

#### A9 — AI Act art. 99 ↔ GDPR art. 83

- **Use case:** concettuale
- **Caveat:** Rapporto tra ne bis in idem e sanzioni cumulative UE-UE non ha
  giurisprudenza consolidata post-AI Act (riferimento dottrinale: CGUE
  bpost e Nordzucker 2022 su sanzioni cumulative proporzionate).
  Coordinamento tra autorità ex art. 70 AI Act (cooperazione con autorità
  di protezione dati) può mitigare il cumulo in pratica.
- **Nota estesa:** Le sanzioni AI Act (art. 99: fino a 35M€ o 7% fatturato
  globale per pratiche vietate art. 5; fino a 15M€ o 3% per altre
  violazioni) si cumulano con le sanzioni GDPR ex art. 83 (fino a 20M€ o
  4%) quando la stessa condotta viola entrambi i regolamenti. La
  cumulabilità opera nei limiti del principio di proporzionalità
  riconosciuto dalla CGUE per sanzioni amministrative tra normative
  diverse.

---

### Tema C — NIS2 trasversale

#### C1 — NIS2 art. 24 ↔ GDPR art. 32

- **Use case:** concettuale
- **Caveat:** Sostituisce la nota originale del link iniziale "Misure
  sicurezza GDPR e NIS2 si sovrappongono ma con perimetri diversi" con
  versione più articolata. Direzione invertita (NIS2 → GDPR secondo
  convenzione: norma più recente come `from`). Numerazione art. 24
  verificata su Q40 benchmark.
- **Nota estesa:** L'art. 24 D.Lgs 138/2024 (NIS2) impone ai soggetti
  essenziali/importanti misure tecniche e organizzative per gestire i
  rischi cyber (analisi rischio, incident response, business continuity,
  supply chain, crittografia, MFA). L'art. 32 GDPR impone misure tecniche
  e organizzative adeguate per la sicurezza dei dati personali. Le due
  liste sono ampiamente sovrapposte ma NON identiche: NIS2 ha perimetro
  sistemi/servizi ICT, GDPR ha perimetro dati personali. Per un soggetto
  che è sia titolare GDPR sia soggetto NIS2, le misure si coordinano e si
  rinforzano, ma vanno mappate distintamente nelle rispettive evidence di
  compliance.

#### C2 — NIS2 art. 25 ↔ GDPR art. 33

- **Use case:** concettuale
- **Caveat:** Caso d'uso reale e frequente per CISO + DPO che devono
  coordinarsi. Numerazione art. 25 e tempistiche 24h/72h/1 mese verificate
  su D.Lgs 138/2024.
- **Nota estesa:** L'art. 25 NIS2 impone la notifica di incidenti
  significativi al CSIRT Italia con tempistiche scaglionate (pre-notifica
  entro 24h, notifica completa entro 72h, relazione finale entro un mese).
  L'art. 33 GDPR impone la notifica di violazioni di dati personali al
  Garante entro 72h. Un incidente cyber che comporti compromissione di
  dati personali attiva ENTRAMBE le notifiche, verso DESTINATARI DIVERSI
  (CSIRT/ACN per NIS2, Garante per GDPR) e con tempistiche parzialmente
  diverse. Coordinamento operativo: una sola playbook di incident response
  deve produrre due flussi di notifica paralleli.

#### C3 — NIS2 art. 25 ↔ GDPR art. 34

- **Use case:** concettuale
- **Caveat:** Link che aiuta a non confondere la notifica all'autorità (NIS2
  + GDPR art. 33) con la comunicazione all'interessato (solo GDPR art. 34).
  Distinzione spesso confusa nelle policy aziendali.
- **Nota estesa:** Mentre NIS2 art. 25 disciplina la notifica all'autorità,
  l'art. 34 GDPR disciplina la comunicazione all'interessato quando la
  violazione presenta rischio elevato per i suoi diritti e libertà. Su un
  incidente cyber composito, oltre alla doppia notifica alle autorità
  (NIS2 ad ACN, GDPR al Garante), può scattare l'obbligo di comunicazione
  individuale ex art. 34 GDPR — tipicamente in caso di exfiltration di
  dati identificativi non cifrati. NIS2 NON ha obbligo equivalente verso
  utenti/cittadini in generale.

#### C4 — AI Act Allegato III ↔ NIS2 art. 24

- **Use case:** concettuale
- **Caveat:** Sovrapposizione di perimetri parziale, non totale. Esempi
  pratici: un operatore TSO elettrico (soggetto NIS2) che usa un sistema
  AI di previsione carico o grid balancing (AI Act high-risk ex Allegato
  III). Chunk_id corrisponde all'Allegato III monolitico; "punto 2" nella
  nota per precisione semantica.
- **Nota estesa:** L'Allegato III punto 2 AI Act classifica come high-risk
  i sistemi AI usati come componenti di sicurezza nella gestione e
  funzionamento di infrastrutture critiche digitali, traffico stradale,
  forniture idriche, gas, riscaldamento, elettricità. Molti di questi
  settori coincidono con il perimetro di applicazione NIS2 (soggetti
  essenziali ex Allegato I D.Lgs 138/2024: energia, trasporti, acqua
  potabile, digital infrastructure). Un soggetto NIS2 che usa AI
  high-risk per gestire la propria infrastruttura deve coordinare i
  requisiti AI Act sui sistemi (artt. 9-15) con le misure NIS2 sulla
  sicurezza dell'infrastruttura ICT che li ospita.

#### C5 — AI Act art. 73 ↔ NIS2 art. 25

- **Use case:** concettuale
- **Caveat:** La L. 132/2025 italiana dovrebbe chiarire il riparto di
  competenze tra AgID (sorveglianza AI Act) e ACN (NIS2), ma il
  coordinamento operativo è ancora in fase di attuazione al 2026. Il link
  forza una doppia tassonomia di incidenti che la dottrina sta ancora
  consolidando.
- **Nota estesa:** L'art. 73 AI Act impone ai fornitori di sistemi AI
  high-risk la segnalazione di "incidenti gravi" alle autorità di
  sorveglianza del mercato (in Italia, AgID + ACN secondo la L. 132/2025).
  L'art. 25 NIS2 impone la notifica di incidenti significativi al CSIRT.
  Per un soggetto che è sia fornitore AI high-risk sia soggetto NIS2 (caso
  ricorrente in fintech, healthtech, govtech), un incidente che impatta
  sia il sistema AI sia l'infrastruttura ICT attiva due flussi di
  notifica paralleli verso autorità diverse, con definizioni di
  "incidente" sovrapposte ma non identiche.

#### C6 — NIS2 art. 23 ↔ 231 art. 6

- **Use case:** UC5
- **Caveat:** Link operativo-giurisprudenziale, non testuale: né NIS2 art.
  23 né 231 art. 6 si citano reciprocamente. L'integrazione tra le due
  governance è prassi consolidata in compliance integrata. Verifica
  numerazione art. 23 nel D.Lgs 138/2024.
- **Nota estesa:** L'art. 23 NIS2 stabilisce la responsabilità diretta
  degli organi di gestione (CdA, top management) sull'implementazione
  delle misure cyber e sulla formazione in materia di sicurezza
  informatica. L'art. 6 D.Lgs 231 disciplina i modelli organizzativi
  idonei a prevenire reati presupposto. Un modello 231 idoneo per
  un'azienda soggetta a NIS2 deve includere presidi NIS2 (in particolare
  per prevenire reati informatici ex art. 24-bis 231): la conformità
  NIS2 alimenta l'idoneità del modello 231, e viceversa il modello 231 è
  lo strumento attraverso cui un ente NIS2 organizza la propria governance
  cyber con rilevanza penale-amministrativa.

#### C7 — NIS2 art. 24 ↔ 231 art. 24-bis

- **Use case:** UC5
- **Caveat:** Link operativo: NIS2 art. 24 e 231 art. 24-bis non si citano
  reciprocamente. Parallelismo con B1 (GDPR art. 32 ↔ 24-bis 231):
  entrambi spostano il piano del "parametro di diligenza" su normative
  settoriali diverse — GDPR per dati personali, NIS2 per sicurezza ICT.
  Utile per settori dove NIS2 è più stringente di GDPR art. 32.
  Originariamente proposto come `presupposto_di`, riformulato in
  `complementare` perché le misure NIS2 non sono elemento materiale del
  reato, ma parametro di diligenza dell'ente (vedi open question OQ-C1).
- **Nota estesa:** Le misure tecniche e organizzative cyber dovute dai
  soggetti essenziali/importanti ex NIS2 art. 24 (MFA, controlli accesso,
  supply chain, ecc.) costituiscono il parametro di diligenza settoriale
  per valutare l'idoneità del modello 231 a prevenire reati informatici
  richiamati dall'art. 24-bis. L'assenza di tali misure può rilevare nella
  valutazione della responsabilità dell'ente ex art. 6 231.

---

### Tema D — L. 132/2025 + Codice Privacy ↔ GDPR/AI Act

#### D1 — L. 132/2025 art. 11 ↔ AI Act Allegato III

- **Use case:** UC1
- **Caveat:** L'art. 11 L. 132/2025 è prevalentemente ricognitivo del
  quadro normativo italiano esistente (Statuto lavoratori, D.Lgs 152/1997,
  antidiscriminazione). `attua` nel senso di "integra/specifica", non nel
  senso classico di recepimento di direttiva. Numerazione verificata via
  web search durante la curatela (Q38 benchmark conferma art. 11 sulla
  materia del lavoro).
- **Nota estesa:** L'art. 11 L. 132/2025 disciplina l'uso dell'AI in ambito
  lavorativo italiano, imponendo principi (tutela integrità psicofisica,
  sicurezza, trasparenza) e l'obbligo del datore di lavoro di fornire
  informativa ai lavoratori sui sistemi decisionali o di monitoraggio
  integralmente automatizzati, con rinvio all'art. 1-bis D.Lgs 152/1997.
  Costituisce attuazione e specificazione italiana degli obblighi AI Act
  sui sistemi high-risk per HR (Allegato III punto 4).

#### D2 — Cod. Privacy art. 2-ter ↔ GDPR art. 6

- **Use case:** concettuale
- **Caveat:** Relazione `deroga` nel senso di "specializzazione/declinazione
  nazionale", non di "eccezione". Articolo cardine del rapporto
  GDPR-Cod.Privacy post-D.Lgs 101/2018. Caso d'uso reale per PA italiana e
  per fornitori che lavorano con enti pubblici.
- **Nota estesa:** L'art. 2-ter Codice Privacy specifica, per i soggetti
  pubblici italiani, le fonti che possono costituire la base giuridica del
  trattamento ex art. 6 GDPR (legge, regolamento, o atto amministrativo
  generale). Costituisce specializzazione settoriale italiana di una base
  di liceità GDPR (art. 6.1.c per obbligo legale o art. 6.1.e per
  esercizio di pubblici poteri): in Italia il "diritto degli Stati membri"
  richiamato dal GDPR è declinato con queste fonti specifiche.

#### D3 — Cod. Privacy art. 2-sexies ↔ GDPR art. 9

- **Use case:** concettuale
- **Caveat:** Articolo molto consultato in compliance sanitaria, welfare,
  PA. Q34 benchmark sull'art. 9 GDPR potrebbe beneficiare dell'espansione
  verso questo articolo cardine del Codice Privacy.
- **Nota estesa:** L'art. 2-sexies Cod. Privacy elenca tassativamente le
  "finalità di interesse pubblico rilevante" che, in Italia, autorizzano
  il trattamento di dati particolari ex art. 9.2.g GDPR (es. sanità
  pubblica, assistenza, politiche del lavoro, immigrazione, prevenzione
  frodi). Specializzazione nazionale dell'apertura derogatoria dell'art. 9
  GDPR: la lista del 2-sexies è la lex specialis che concretizza il
  "diritto degli Stati membri" per la deroga di interesse pubblico.

---

## Link in riserva

Candidati per v1.1 o per promozione in v1 se a settimana 5-7 emergono gap
specifici sul benchmark. Non sono nel file YAML.

### R-B1 — AI Act Allegato III punto 4 ↔ Cod. Privacy art. 167

- **Relation:** presupposto_di
- **Use case:** concettuale
- **Motivazione riserva:** Nessuna query del benchmark a 50 (Q1-Q50) tocca
  specificamente il reato di trattamento illecito di dati. Q9/Q25 sono sui
  reati informatici 231 (24-bis), non su art. 167. Tenere come candidato se
  a fine catalogo avanzano slot o se emerge una query reale in settimana
  5-6.
- **Nota:** L'uso di sistemi AI HR che violi le basi di liceità del
  trattamento, con dolo specifico di trarre profitto per sé o altri o
  arrecare danno all'interessato, può integrare il reato di trattamento
  illecito di dati ex art. 167 Cod. Privacy nella formulazione post D.Lgs
  101/2018.
- **Caveat:** Fattispecie dolosa a perimetro ristretto: NON qualsiasi
  violazione GDPR integra il reato. Non è reato presupposto 231 (art. 167
  non è richiamato dal D.Lgs 231/2001), quindi il link non chiude UC5 sul
  versante penale-amministrativo.

### R-D5 — Cod. Privacy art. 2-sex-decies ↔ GDPR art. 37

- **Relation:** deroga (specializzazione)
- **Use case:** concettuale (di nicchia)
- **Motivazione riserva:** Q2 baseline mostra che bge-m3 + prefix italiano
  lo recupera già al rank 1 con score 0.785. Asimmetria informativa bassa
  (criterio 2 del manifesto non soddisfatto). Articolo di nicchia (DPO
  presso autorità giudiziarie italiane).
- **Nota:** L'art. 2-sex-decies Cod. Privacy disciplina la figura del
  Responsabile della Protezione dei Dati (DPO/RPD) presso le autorità
  giudiziarie italiane, integrando con specifiche italiane gli obblighi
  generali sull'RPD ex art. 37 GDPR.

---

## Link scartati

Documentati per memoria del processo di curatela. Non riproporre senza
rileggere le motivazioni.

### S-B1 — 231 art. 25-octies.1 ↔ GDPR art. 5

- **Relation proposta:** presupposto_di
- **Motivo scarto:**
  1. La relazione `presupposto_di` non regge — l'art. 5 GDPR è principio
     generale, non condotta tipizzata.
  2. Inflazione di contesto — art. 5 GDPR è il chunk più recuperato del
     corpus.
  3. Caveat originale era essenzialmente un'ammissione di debolezza del
     link.

### S-B2 — AI Act Allegato III punto 4 ↔ 231 art. 25 + 25-ter

- **Relation proposta:** complementare
- **Motivo scarto:**
  1. Link 1-a-2 non ammesso dallo schema.
  2. Art. 25 (concussione/corruzione) e 25-ter (reati societari) non sono i
     reati 231 davvero attivabili da AI HR. Verifica del nesso ha mostrato
     che NESSUN reato 231 è direttamente attivato da uso scorretto di AI
     HR. Discriminazione non è reato 231.
- **Conseguenza:** il triangolo 231-AI-HR è coperto strutturalmente da B2
  (modello ↔ risk management) e non necessita link specifici Allegato III
  ↔ 231.

### S-A1 — AI Act art. 30 ↔ GDPR art. 30

- **Relation proposta:** complementare
- **Motivo scarto:** Tentazione di simmetria numerica. Sono adempimenti
  molto diversi: art. 30 AI Act sono i log automatici di funzionamento del
  sistema (audit trail tecnico); art. 30 GDPR è il registro documentale
  delle attività di trattamento del titolare. Linkarli rischia di
  confondere l'LLM su due obblighi distinti che vanno tenuti separati
  nelle risposte di compliance.

---

## Open questions per consolidamento

Aperte a settimana 5-6, da chiudere quando si vede output LLM reale.

### OQ-A1 — Sovrapposizione su art. 22 GDPR come perno

A6 (art. 6 AI Act ↔ art. 22 GDPR) e B3 (Allegato III punto 4 ↔ art. 22
GDPR) condividono il perno art. 22 GDPR ma sono complementari per
granularità (A6 generale, B3 HR-specifico). Confermati entrambi.
Copertura query benchmark distinta: Q1/Q12 (HR/scuola) → B3;
Q11/Q14/Q18 (credit/GPAI/sanzioni) → A6. **Revisione a settimana 5-6 su
output LLM reale se emerge rumore** (es. se B3 viene quasi sempre
espanso anche su query non-HR, considerare di unificare con A6).

### OQ-C1 — Tassonomia presupposto_di vs complementare per misure di diligenza

C7 (NIS2 art. 24 ↔ 231 art. 24-bis) era originariamente proposto come
`presupposto_di` in parallelo a B1. Riformulato in `complementare` perché
le misure NIS2 non sono elemento materiale del reato, ma parametro di
diligenza dell'ente. Distinzione tassonomica:
- **presupposto del reato** (B1, condotta tipica)
- **presupposto della responsabilità dell'ente** (C7, idoneità modello)
Decisione coerente con la convenzione del catalogo. **Riconsiderare se
emerge una query benchmark che richiede C7 come `presupposto_di` per
recupero corretto.**

### OQ-2 — Verifiche di numerazione da consolidare in Claude Code

Numerazioni segnalate nelle note che vanno verificate contro il chunk_id
reale durante il caricamento del graph:
- D.Lgs 138/2024 (NIS2) art. 23 (responsabilità apicale): verificare
  numerazione esatta.
- L. 132/2025 art. 11: verificato via web search (sulla materia del lavoro),
  ma confermare con chunk_id reale.
- Verificare che tutti i chunk_id usati nello YAML esistano effettivamente
  nella collection `italian_legal_v1_hybrid`. Lo schema URN AKN per il
  Codice Privacy 196/2003 e per il D.Lgs 231/2001 è stato presunto in
  base alla convenzione `akn/it/act/decreto_legislativo/stato/<data>/<num>`:
  verificare che la `data` ("stato/2001-06-08" per 231/2001,
  "stato/2003-06-30" per 196/2003) corrisponda a quanto effettivamente
  presente nei chunk del corpus.

---

*Documento generato al termine della curatela manuale settimana 4. Da
aggiornare se in settimana 5-6 emergono modifiche al graph dalla
validazione contro output LLM o benchmark RAG completo.*