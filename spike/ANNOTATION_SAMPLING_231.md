# Sampling annotazione gold 231/2001 — benchmark v1

Sorgente: `data/benchmark/gold_validated_v2.json` (50 query). Filtro: candidates con `doc_urn = akn/it/act/decreto_legislativo/stato/2001-06-08/231` e `is_gold=true`.

Output puramente diagnostico. Nessuna euristica di flagging — la valutazione giuridica di coerenza spetta alla revisione manuale.

## A — Query con almeno 1 gold 231/2001

| qid | use_case | n_gold_231 | gold article_eid(s) |
|---|---|---:|---|
| Q9 | Reati 231 trattamento illecito dati | 3 | art_24-bis, art_25-undecies |
| Q24 | 231 modello organizzativo + AI HR | 2 | art_6, art_7 |
| Q25 | 231 fattispecie informatica art 24-bis | 2 | art_5, art_24-bis |
| Q26 | stress: art 24-bis 231 | 1 | art_24-bis |
| Q27 | stress: art 25-undecies | 2 | art_25-undecies |
| Q49 | edge: mix in/off corpus | 2 | art_6, art_7 |

**Totale query 231-related: 6**

## B — Entry diagnostiche per ispezione

### Q9 — Reati 231 trattamento illecito dati

**Query**: Quali sono i reati presupposto in materia di trattamento illecito di dati personali ai sensi del 231?

**Gold 231 attivi (3)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` (art_24-bis):
  > Art. 24-bis - (Delitti informatici e trattamento illecito di dati).  1. In relazione alla commissione dei delitti di cui agli articoli 615-ter, 617-quater, 617-quinquies, 635-bis, 635-ter, 635-quater e 635-quinquies del codice penale, si applica all'ente la sanzione pecuniaria ((da duecento a settec...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6` (art_25-undecies):
  > Art. 25-undecies - (Reati ambientali)  1. In relazione alla commissione dei reati previsti dal codice penale, si applicano all'ente le seguenti sanzioni pecuniarie: a) per la violazione dell'articolo 452-bis, la sanzione pecuniaria da quattrocento a seicento quote; b) per la violazione dell'articolo...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` (art_25-undecies):
  > Art. 25-undecies - (Reati ambientali)  7. Nei casi di condanna per i reati indicati al comma 2, (( lettera a) )), numero 2), e al comma 5, lettere b) e c), si applicano le sanzioni interdittive previste dall'articolo 9, comma 2, per una durata non superiore a sei mesi. Nei casi di condanna per i rea...

**Altri gold non-231 (1)**:

- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167` (196/2003, art_167)

**Altri candidates 231 NON gold (0)**:

- (nessun altro candidate 231 in questa query)

---

### Q24 — 231 modello organizzativo + AI HR

**Query**: Il modello organizzativo 231 deve essere aggiornato per coprire i rischi connessi all'uso di sistemi AI per decisioni HR?

**Gold 231 attivi (2)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` (art_6):
  > Art. 6 - Soggetti in posizione apicale e modelli di organizzazione dell'ente  1. Se il reato e' stato commesso dalle persone indicate nell'articolo 5, comma 1, lettera a), l'ente non risponde se prova che: a) l'organo dirigente ha adottato ed efficacemente attuato, prima della commissione del fatto,...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7` (art_7):
  > Art. 7 - Soggetti sottoposti all'altrui direzione e modelli di organizzazione dell'ente  1. Nel caso previsto dall'articolo 5, comma 1, lettera b), l'ente e' responsabile se la commissione del reato e' stata resa possibile dall'inosservanza degli obblighi di direzione o vigilanza.  2. In ogni caso, ...

**Altri gold non-231 (1)**:

- `eli/reg/2024/1689/oj__art_26` (AI Act, art_26)

**Altri candidates 231 NON gold (9)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_12` (art_12):
  > Art. 12 - Casi di riduzione della sanzione pecuniaria  1. La sanzione pecuniaria e' ridotta della meta' e non puo' comunque essere superiore a lire duecento milioni se: a) l'autore del reato ha commes...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_17` (art_17):
  > Art. 17 - Riparazione delle conseguenze del reato  1. Ferma l'applicazione delle sanzioni pecuniarie, le sanzioni interdittive non si applicano quando, prima della dichiarazione di apertura del dibatt...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_18` (art_18):
  > Art. 18 - Pubblicazione della sentenza di condanna  1. La pubblicazione della sentenza di condanna puo' essere disposta quando nei confronti dell'ente viene applicata una sanzione interdittiva.  3. La...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_28` (art_28):
  > Art. 28 - Trasformazione dell'ente  1. Nel caso di trasformazione dell'ente, resta ferma la responsabilita' per i reati commessi anteriormente alla data in cui la trasformazione ha avuto effetto.
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_41` (art_41):
  > Art. 41 - Contumacia dell'ente  1. L'ente che non si costituisce nel processo e' dichiarato contumace.
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_66` (art_66):
  > Art. 66 - Sentenza di esclusione della responsabilita' dell'ente  1. Se l'illecito amministrativo contestato all'ente non sussiste, il giudice lo dichiara con sentenza, indicandone la causa nel dispos...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_70` (art_70):
  > Art. 70 - Sentenza in caso di vicende modificative dell'ente  1. Nel caso di trasformazione, fusione o scissione dell'ente responsabile, il giudice da' atto nel dispositivo che la sentenza e' pronunci...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_72` (art_72):
  > Art. 72 - Estensione delle impugnazioni  1. Le impugnazioni proposte dall'imputato del reato da cui dipende l'illecito amministrativo e dall'ente, giovano, rispettivamente, all'ente e all'imputato, pu...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_83` (art_83):
  > Art. 83 - Concorso di sanzioni  1. Nei confronti dell'ente si applicano soltanto le sanzioni interdittive stabilite nel presente decreto legislativo anche quando diverse disposizioni di legge prevedon...

---

### Q25 — 231 fattispecie informatica art 24-bis

**Query**: Un dipendente accede abusivamente al sistema informatico di un concorrente per favorire l'azienda: l'ente risponde ai sensi del 231?

**Gold 231 attivi (2)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_5` (art_5):
  > Art. 5 - Responsabilita' dell'ente  1. L'ente e' responsabile per i reati commessi nel suo interesse o a suo vantaggio: a) da persone che rivestono funzioni di rappresentanza, di amministrazione o di direzione dell'ente o di una sua unita' organizzativa dotata di autonomia finanziaria e funzionale n...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` (art_24-bis):
  > Art. 24-bis - (Delitti informatici e trattamento illecito di dati).  1. In relazione alla commissione dei delitti di cui agli articoli 615-ter, 617-quater, 617-quinquies, 635-bis, 635-ter, 635-quater e 635-quinquies del codice penale, si applica all'ente la sanzione pecuniaria ((da duecento a settec...

**Altri gold non-231 (0)**:

- (nessuno: i gold di questa query sono solo 231)

**Altri candidates 231 NON gold (16)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` (art_6):
  > Art. 6 - Soggetti in posizione apicale e modelli di organizzazione dell'ente  1. Se il reato e' stato commesso dalle persone indicate nell'articolo 5, comma 1, lettera a), l'ente non risponde se prova...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_15` (art_15):
  > Art. 15 - Commissario giudiziale  1. Se sussistono i presupposti per l'applicazione di una sanzione interdittiva che determina l'interruzione dell'attivita' dell'ente, il giudice, in luogo dell'applic...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_17` (art_17):
  > Art. 17 - Riparazione delle conseguenze del reato  1. Ferma l'applicazione delle sanzioni pecuniarie, le sanzioni interdittive non si applicano quando, prima della dichiarazione di apertura del dibatt...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_18` (art_18):
  > Art. 18 - Pubblicazione della sentenza di condanna  1. La pubblicazione della sentenza di condanna puo' essere disposta quando nei confronti dell'ente viene applicata una sanzione interdittiva.  3. La...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` (art_25-undecies):
  > Art. 25-undecies - (Reati ambientali)  7. Nei casi di condanna per i reati indicati al comma 2, (( lettera a) )), numero 2), e al comma 5, lettere b) e c), si applicano le sanzioni interdittive previs...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_27` (art_27):
  > Art. 27 - Responsabilita' patrimoniale dell'ente  1. Dell'obbligazione per il pagamento della sanzione pecuniaria risponde soltanto l'ente con il suo patrimonio o con il fondo comune.  2. I crediti de...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_28` (art_28):
  > Art. 28 - Trasformazione dell'ente  1. Nel caso di trasformazione dell'ente, resta ferma la responsabilita' per i reati commessi anteriormente alla data in cui la trasformazione ha avuto effetto.
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_29` (art_29):
  > Art. 29 - Fusione dell'ente  1. Nel caso di fusione, anche per incorporazione, l'ente che ne risulta risponde dei reati dei quali erano responsabili gli enti partecipanti alla fusione.
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_33` (art_33):
  > Art. 33 - Cessione di azienda  1. Nel caso di cessione dell'azienda nella cui attivita' e' stato commesso il reato, il cessionario e' solidalmente obbligato, salvo il beneficio della preventiva escuss...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_41` (art_41):
  > Art. 41 - Contumacia dell'ente  1. L'ente che non si costituisce nel processo e' dichiarato contumace.
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_45` (art_45):
  > Art. 45 - Applicazione delle misure cautelari  1. Quando sussistono gravi indizi per ritenere la sussistenza della responsabilita' dell'ente per un illecito amministrativo dipendente da reato e vi son...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_66` (art_66):
  > Art. 66 - Sentenza di esclusione della responsabilita' dell'ente  1. Se l'illecito amministrativo contestato all'ente non sussiste, il giudice lo dichiara con sentenza, indicandone la causa nel dispos...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_70` (art_70):
  > Art. 70 - Sentenza in caso di vicende modificative dell'ente  1. Nel caso di trasformazione, fusione o scissione dell'ente responsabile, il giudice da' atto nel dispositivo che la sentenza e' pronunci...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_72` (art_72):
  > Art. 72 - Estensione delle impugnazioni  1. Le impugnazioni proposte dall'imputato del reato da cui dipende l'illecito amministrativo e dall'ente, giovano, rispettivamente, all'ente e all'imputato, pu...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` (art_81):
  > Art. 81
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_83` (art_83):
  > Art. 83 - Concorso di sanzioni  1. Nei confronti dell'ente si applicano soltanto le sanzioni interdittive stabilite nel presente decreto legislativo anche quando diverse disposizioni di legge prevedon...

---

### Q26 — stress: art 24-bis 231

**Query**: art 24-bis 231 delitti informatici

**Gold 231 attivi (1)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-bis` (art_24-bis):
  > Art. 24-bis - (Delitti informatici e trattamento illecito di dati).  1. In relazione alla commissione dei delitti di cui agli articoli 615-ter, 617-quater, 617-quinquies, 635-bis, 635-ter, 635-quater e 635-quinquies del codice penale, si applica all'ente la sanzione pecuniaria ((da duecento a settec...

**Altri gold non-231 (0)**:

- (nessuno: i gold di questa query sono solo 231)

**Altri candidates 231 NON gold (13)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24` (art_24):
  > Art. 24 - Indebita percezione di erogazioni, truffa in danno dello Stato, di un ente pubblico o dell'Unione europea o per il conseguimento di erogazioni pubbliche, frode informatica in danno dello Sta...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_24-ter` (art_24-ter):
  > Art. 24-ter - (( (Delitti di criminalita' organizzata). ))  1. In relazione alla commissione di taluno dei delitti di cui agli articoli 416, sesto comma, 416-bis, 416-ter e 630 del codice penale, ai d...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25` (art_25):
  > Art. 25  1. In relazione alla commissione dei delitti di cui agli articoli 318, 321, 322, commi primo e terzo, e 346-bis del codice penale, si applica la sanzione pecuniaria fino a duecento quote. La ...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-quinquies` (art_25-quinquies):
  > Art. 25-quinquies - (Delitti contro la personalita' individuale).  1. In relazione alla commissione dei delitti previsti dalla sezione I del capo III del titolo XII del libro II del codice penale si a...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies` (art_25-octies):
  > Art. 25-octies  1. In relazione ai reati di cui agli articoli 648, 648-bis ((, 648-ter e 648-ter.1)) del codice penale, si applica all'ente la sanzione pecuniaria da 200 a 800 quote. Nel caso in cui i...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-novies` (art_25-novies):
  > Art. 25-novies - (Delitti in materia di violazione del diritto d'autore).
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-duodecies` (art_25-duodecies):
  > Art. 25-duodecies - (Impiego di cittadini di paesi terzi il cui soggiorno e' irregolare)  1. In relazione alla commissione del delitto di cui all'articolo 22, comma 12-bis, del decreto legislativo 25 ...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-terdecies` (art_25-terdecies):
  > Art. 25-terdecies - (( (Razzismo e xenofobia). ))  1. In relazione alla commissione dei delitti di cui all'articolo 3, comma 3-bis, della legge 13 ottobre 1975, n. 654, si applica all'ente la sanzione...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-bis.1` (art_25-bis.1):
  > Art. 25-bis - (( (Delitti contro l'industria e il commercio). ))  1. In relazione alla commissione dei delitti contro l'industria e il commercio previsti dal codice penale, si applicano all'ente le se...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_53` (art_53):
  > Art. 53 - Sequestro preventivo  1. Il giudice puo' disporre il sequestro delle cose di cui e' consentita la confisca a norma dell'articolo 19. Si osservano le disposizioni di cui agli articoli 321, co...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_75` (art_75):
  > Art. 75
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` (art_81):
  > Art. 81
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_82` (art_82):
  > Art. 82

---

### Q27 — stress: art 25-undecies

**Query**: art 25-undecies reati ambientali

**Gold 231 attivi (2)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_1_6` (art_25-undecies):
  > Art. 25-undecies - (Reati ambientali)  1. In relazione alla commissione dei reati previsti dal codice penale, si applicano all'ente le seguenti sanzioni pecuniarie: a) per la violazione dell'articolo 452-bis, la sanzione pecuniaria da quattrocento a seicento quote; b) per la violazione dell'articolo...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-undecies__paras_7_8` (art_25-undecies):
  > Art. 25-undecies - (Reati ambientali)  7. Nei casi di condanna per i reati indicati al comma 2, (( lettera a) )), numero 2), e al comma 5, lettere b) e c), si applicano le sanzioni interdittive previste dall'articolo 9, comma 2, per una durata non superiore a sei mesi. Nei casi di condanna per i rea...

**Altri gold non-231 (0)**:

- (nessuno: i gold di questa query sono solo 231)

**Altri candidates 231 NON gold (12)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_13` (art_13):
  > Art. 13 - Sanzioni interdittive  1. Le sanzioni interdittive si applicano in relazione ai reati per i quali sono espressamente previste, quando ricorre almeno una delle seguenti condizioni: a) l'ente ...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-quinquies` (art_25-quinquies):
  > Art. 25-quinquies - (Delitti contro la personalita' individuale).  1. In relazione alla commissione dei delitti previsti dalla sezione I del capo III del titolo XII del libro II del codice penale si a...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-sexies` (art_25-sexies):
  > Art. 25-sexies - (( (Abusi di mercato). ))  1. In relazione ai reati di abuso di informazioni privilegiate e di manipolazione del mercato previsti dalla parte V, titolo I-bis, capo II, del testo unico...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies` (art_25-octies):
  > Art. 25-octies  1. In relazione ai reati di cui agli articoli 648, 648-bis ((, 648-ter e 648-ter.1)) del codice penale, si applica all'ente la sanzione pecuniaria da 200 a 800 quote. Nel caso in cui i...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-novies` (art_25-novies):
  > Art. 25-novies - (Delitti in materia di violazione del diritto d'autore).
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-quaterdecies` (art_25-quaterdecies):
  > Art. 25-quaterdecies - (( (Frode in competizioni sportive, esercizio abusivo di gioco o di scommessa e giochi d'azzardo esercitati a mezzo di apparecchi vietati). ))  1. In relazione alla commissione ...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-octies.2` (art_25-octies.2):
  > Art. 25-octies - (( (Reati in materia di violazione di misure restrittive dell'Unione europea). ))  1. ((In relazione alla commissione dei delitti previsti dal codice penale contro la politica estera ...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_25-septiesdecies` (art_25-septiesdecies):
  > Art. 25-septiesdecies - (( (Delitti contro il patrimonio culturale). ))  1. In relazione alla commissione del delitto previsto dall'articolo 518-novies del codice penale, si applica all'ente la sanzio...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_75` (art_75):
  > Art. 75
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_80` (art_80):
  > Art. 80
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` (art_81):
  > Art. 81
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_82` (art_82):
  > Art. 82

---

### Q49 — edge: mix in/off corpus

**Query**: Posso integrare il modello 231 con il sistema di gestione qualità ISO 9001?

**Gold 231 attivi (2)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_6` (art_6):
  > Art. 6 - Soggetti in posizione apicale e modelli di organizzazione dell'ente  1. Se il reato e' stato commesso dalle persone indicate nell'articolo 5, comma 1, lettera a), l'ente non risponde se prova che: a) l'organo dirigente ha adottato ed efficacemente attuato, prima della commissione del fatto,...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_7` (art_7):
  > Art. 7 - Soggetti sottoposti all'altrui direzione e modelli di organizzazione dell'ente  1. Nel caso previsto dall'articolo 5, comma 1, lettera b), l'ente e' responsabile se la commissione del reato e' stata resa possibile dall'inosservanza degli obblighi di direzione o vigilanza.  2. In ogni caso, ...

**Altri gold non-231 (0)**:

- (nessuno: i gold di questa query sono solo 231)

**Altri candidates 231 NON gold (3)**:

- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_12` (art_12):
  > Art. 12 - Casi di riduzione della sanzione pecuniaria  1. La sanzione pecuniaria e' ridotta della meta' e non puo' comunque essere superiore a lire duecento milioni se: a) l'autore del reato ha commes...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_17` (art_17):
  > Art. 17 - Riparazione delle conseguenze del reato  1. Ferma l'applicazione delle sanzioni pecuniarie, le sanzioni interdittive non si applicano quando, prima della dichiarazione di apertura del dibatt...
- `akn/it/act/decreto_legislativo/stato/2001-06-08/231__art_81` (art_81):
  > Art. 81

---

## C — Statistiche aggregate

- Totale query con ≥1 gold 231: **6**
- Articoli 231 distinti marcati gold: **5**
- Totale marker is_gold=true su 231: **12**

### Distribuzione gold per article_eid

| article_eid | n_gold | qid(s) |
|---|---:|---|
| art_5 | 1 | Q25 |
| art_6 | 2 | Q24, Q49 |
| art_7 | 2 | Q24, Q49 |
| art_24-bis | 3 | Q9, Q25, Q26 |
| art_25-undecies | 4 | Q9, Q27 |

### Top-5 articoli 231 più ricorrenti come gold

| rank | article_eid | n_gold |
|---|---|---:|
| 1 | art_25-undecies | 4 |
| 2 | art_24-bis | 3 |
| 3 | art_6 | 2 |
| 4 | art_7 | 2 |
| 5 | art_5 | 1 |

### Articoli 231 marcati gold solo in 1 query (potenziali outlier)

| article_eid | qid |
|---|---|
| art_5 | Q25 |

