# Corpus reference per curatela benchmark v2 (fase C)

Data: 2026-05-20
Fase: pivot W7→W10 — curatela giuridica candidates v2.
Sorgenti: Qdrant `italian_legal_v1_hybrid` (865 chunk) + XML AKN
sorgente Codice Privacy + `data/benchmark/gold_answers_v1.json`.

**Obiettivo:** documento di riferimento per Opus in chat fresh-context
durante la fase C, contenente le informazioni dirette sul corpus che
servono per risolvere ambiguità nelle `gold_chunks_proposed`. READ-ONLY.

---

## Sezione 1 — Indice articoli D.Lgs 138/2024 (NIS2)

44 articoli (1-44), tutti ingeriti. 45 chunk in Qdrant (art_2 e art_38
sono splittati come fragment).

| chunk_id (suffix dopo `…/138__`) | hierarchy | titolo (rubrica) | note |
|---|---|---|---|
| `art_1`                        | Capo I    | Oggetto | |
| `art_2__paras_1_1`             | Capo I    | Definizioni | **splittato** (singolo fragment, 3546 token monoblocco) |
| `art_3`                        | Capo I    | Ambito di applicazione | |
| `art_4`                        | Capo I    | Protezione degli interessi nazionali e commerciali | |
| `art_5`                        | Capo I    | _(rubrica non popolata)_ | |
| `art_6`                        | Capo I    | Soggetti essenziali e soggetti importanti | |
| `art_7`                        | Capo I    | Identificazione ed elencazione dei soggetti essenziali e dei soggetti importanti | |
| `art_8`                        | Capo I    | Protezione dei dati personali | |
| `art_9`                        | Capo II   | Strategia nazionale di cybersicurezza | |
| `art_10`                       | Capo II   | _(rubrica non popolata)_ | |
| `art_11`                       | Capo II   | _(rubrica non popolata)_ | |
| `art_12`                       | Capo II   | Tavolo per l'attuazione della disciplina NIS | |
| `art_13`                       | Capo II   | Quadro nazionale di gestione delle crisi informatiche | |
| `art_14`                       | Capo II   | _(rubrica non popolata)_ | |
| `art_15`                       | Capo II   | _(rubrica non popolata)_ | |
| `art_16`                       | Capo II   | _(rubrica non popolata)_ | |
| `art_17`                       | Capo II   | Accordi di condivisione delle informazioni sulla sicurezza informatica | |
| `art_18`                       | Capo III  | Gruppo di cooperazione NIS | |
| `art_19`                       | Capo III  | Rete delle organizzazioni di collegamento per le crisi informatiche - EU-CyCLONe | |
| `art_20`                       | Capo III  | Rete di CSIRT nazionali | |
| `art_21`                       | Capo III  | Procedura di revisione tra pari | |
| `art_22`                       | Capo III  | Comunicazioni all'Unione europea | |
| `art_23`                       | Capo IV   | **Organi di amministrazione e direttivi** (corporate governance) | |
| `art_24`                       | Capo IV   | **Obblighi in materia di misure di gestione dei rischi per la sicurezza informatica** | **monoblocco** (non splittato) |
| `art_25`                       | Capo IV   | **Obblighi in materia di notifica di incidente** | **monoblocco** (non splittato) |
| `art_26`                       | Capo IV   | Notifica volontaria di informazioni pertinenti | |
| `art_27`                       | Capo IV   | Uso di schemi di certificazione della cybersicurezza | |
| `art_28`                       | Capo IV   | Specifiche tecniche | |
| `art_29`                       | Capo IV   | Banca dei dati di registrazione dei nomi di dominio | |
| `art_30`                       | Capo IV   | _(rubrica non popolata)_ | |
| `art_31`                       | Capo IV   | _(rubrica non popolata)_ | |
| `art_32`                       | Capo IV   | Previsioni settoriali specifiche | |
| `art_33`                       | Capo IV   | Coordinamento con la disciplina del perimetro di sicurezza nazionale cibernetica | |
| `art_34`                       | Capo V    | _(rubrica non popolata)_ | |
| `art_35`                       | Capo V    | Monitoraggio, analisi e supporto | |
| `art_36`                       | Capo V    | Verifiche e ispezioni | |
| `art_37`                       | Capo V    | Misure di esecuzione | |
| `art_38__paras_1_11`           | Capo V    | Sanzioni amministrative (commi 1-11: massimali, criteri) | **splittato** |
| `art_38__paras_12_16`          | Capo V    | Sanzioni amministrative (commi 12-16: reiterazione, sospensione dirigenti) | **splittato** |
| `art_39`                       | Capo V    | Assistenza reciproca | |
| `art_40`                       | Capo VI   | Attuazione | |
| `art_41`                       | Capo VI   | Regime transitorio e abrogazioni | |
| `art_42`                       | Capo VI   | Fase di prima applicazione | |
| `art_43`                       | Capo VI   | Modifiche normative | |
| `art_44`                       | Capo VI   | Disposizioni finanziarie | |

---

## Sezione 2 — Verifica esaustività fragment NIS2

Lista completa fragment NIS2 in Qdrant (3):

- `…/138__art_2__paras_1_1` — Definizioni, comma 1 unico (3546 token monoblocco)
- `…/138__art_38__paras_1_11` — Sanzioni, commi 1-11 (1971 token)
- `…/138__art_38__paras_12_16` — Sanzioni, commi 12-16 (775 token)

**Altri fragment NIS2 oltre questi 3?** → **NO.** Verificato via scroll
completo della collection: solo `art_2` e `art_38` sono splittati. Tutti
gli altri 42 articoli NIS2 sono chunk singoli (intero articolo).

**Verifica specifica richiesta da Opus:**

- `art_24` (misure gestione rischio): **monoblocco**. chunk_id canonico = `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_24`.
- `art_25` (notifica incidenti): **monoblocco**. chunk_id canonico = `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25`.

Entrambi possono essere referenziati come chunk intero senza suffisso `__paras_X_Y`.

---

## Sezione 3 — Allegati NIS2 nel corpus

Query Qdrant per pattern `…/138__annex_*` → **0 risultati.**

**L'Allegato I del D.Lgs 138/2024 (settori ad alta criticità) è nel
corpus?** → **NO.** Nessun allegato NIS2 è ingerito. Nessun chunk_id
canonico esiste per `…/138__annex_I`.

Coerente con `spike/CORPUS_INGESTION_AUDIT.md` (parser annex v1 limitato
ad AI Act Annex III). Implicazione per la curatela: **query del
benchmark v2 che richiederebbero contenuto dispositivo dell'Allegato I
NIS2 (elenco settori ad alta criticità: energia, trasporti, banche,
sanità, ecc.) devono usare `has_corpus_limit_declaration=true`** oppure
appoggiarsi all'art. 6 D.Lgs 138/2024 (che rinvia all'Allegato senza
riportarne il contenuto).

---

## Sezione 4 — Mapping Direttiva (UE) 2022/2555 NIS2 → D.Lgs 138/2024

Mapping basato sulla corrispondenza per titolo/materia degli articoli
del decreto (sezione 1). Tutti i match sotto sono **certi** (titolo
del D.Lgs corrisponde verbatim alla materia dell'articolo della
Direttiva).

| Direttiva NIS2 (UE) 2022/2555 | D.Lgs 138/2024 | titolo D.Lgs | certezza |
|---|---|---|---|
| art. 20 (Corporate governance) | **art. 23** | Organi di amministrazione e direttivi | certo |
| art. 21 (Cybersecurity risk management measures) | **art. 24** | Obblighi in materia di misure di gestione dei rischi per la sicurezza informatica | certo |
| art. 23 (Reporting obligations) | **art. 25** | Obblighi in materia di notifica di incidente | certo |
| art. 24 (Use of European cybersecurity certification schemes) | **art. 27** | Uso di schemi di certificazione della cybersicurezza | certo |
| art. 34 (sanzioni — già noto) | **art. 38** | Sanzioni amministrative (splittato in 2 fragment) | certo |

Nota: l'ordine numerico degli articoli del decreto è **shiftato di +3** rispetto alla Direttiva nei capi sulla parte sostanziale (Dir 20→D.Lgs 23, Dir 21→D.Lgs 24, ecc.). Utile come mnemonica per Opus durante la curatela.

---

## Sezione 5 — Indice articoli L. 132/2025

28 articoli (1-28), tutti ingeriti come chunk singoli (nessun fragment).

| chunk_id (suffix dopo `…/132__`) | hierarchy | titolo (rubrica) |
|---|---|---|
| `art_1`  | Capo I   | _(rubrica non popolata)_ |
| `art_2`  | Capo I   | Definizioni |
| `art_3`  | Capo I   | Principi generali |
| `art_4`  | Capo I   | Principi in materia di informazione e di riservatezza dei dati personali |
| `art_5`  | Capo I   | Principi in materia di sviluppo economico |
| `art_6`  | Capo I   | Disposizioni in materia di sicurezza e difesa nazionale |
| `art_7`  | Capo II  | _(rubrica non popolata)_ |
| `art_8`  | Capo II  | Ricerca e sperimentazione scientifica nella realizzazione di sistemi di intelligenza artificiale in ambito sanitario |
| `art_9`  | Capo II  | Disposizioni in materia di trattamento di dati personali |
| `art_10` | Capo II  | _(rubrica non popolata)_ |
| `art_11` | Capo II  | Disposizioni sull'uso dell'intelligenza artificiale in materia di lavoro |
| `art_12` | Capo II  | Osservatorio sull'adozione di sistemi di intelligenza artificiale nel mondo del lavoro |
| `art_13` | Capo II  | Disposizioni in materia di professioni intellettuali |
| `art_14` | Capo II  | Uso dell'intelligenza artificiale nella pubblica amministrazione |
| `art_15` | Capo II  | _(rubrica non popolata)_ |
| `art_16` | Capo II  | Delega al Governo in materia di dati, algoritmi e metodi matematici per l'addestramento di sistemi di intelligenza artificiale |
| `art_17` | Capo II  | Modifica al codice di procedura civile |
| `art_18` | Capo II  | Uso dell'intelligenza artificiale per il rafforzamento della cybersicurezza nazionale |
| `art_19` | Capo III | _(rubrica non popolata)_ |
| `art_20` | Capo III | _(rubrica non popolata)_ |
| `art_21` | Capo III | Applicazione sperimentale dell'intelligenza artificiale ai servizi forniti dal Ministero degli affari esteri e della cooperazione internazionale |
| `art_22` | Capo III | Misure di sostegno ai giovani e allo sport |
| `art_23` | Capo III | Investimenti nei settori dell'intelligenza artificiale, della cybersicurezza e del calcolo quantistico |
| `art_24` | Capo III | Deleghe al Governo in materia di intelligenza artificiale |
| `art_25` | Capo IV  | Tutela del diritto d'autore delle opere generate con l'ausilio dell'intelligenza artificiale |
| `art_26` | Capo V   | Modifiche al codice penale e ad ulteriori disposizioni penali |
| `art_27` | Capo VI  | Clausola di invarianza finanziaria |
| `art_28` | Capo VI  | Disposizioni finali |

---

## Sezione 6 — Articoli abrogati Codice Privacy (D.Lgs 196/2003)

**114 articoli** abrogati e quindi non ingeriti in Qdrant (107 vigenti
su 221 nel sorgente AKN). Distribuzione norma di abrogazione:

| Norma abrogante | n articoli |
|---|---:|
| **D.Lgs 101/2018** (armonizzazione GDPR) | 110 |
| **D.Lgs 51/2018** (recepimento Dir UE 680/2016 polizia/giustizia) | 4 (artt. 53, 54, 55, 56) |
| **Totale** | **114** |

Lista completa dei `chunk_id` notazionali abrogati (non esistono in
Qdrant — usare solo come riferimento per generare query negative
sull'articolo abrogato):

- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_3` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_4` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_5` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_6` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_7` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_8` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_9` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_10` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_11` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_12` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_13` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_14` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_15` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_16` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_17` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_18` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_19` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_20` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_21` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_22` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_23` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_24` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_25` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_26` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_27` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_28` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_29` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_30` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_31` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_32` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_32-bis` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_33` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_34` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_35` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_36` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_37` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_38` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_39` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_40` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_41` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_42` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_43` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_44` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_45` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_46` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_47` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_48` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_49` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_53` — D.Lgs 51/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_54` — D.Lgs 51/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_55` — D.Lgs 51/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_56` — D.Lgs 51/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_62` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_63` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_64` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_65` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_66` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_67` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_68` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_69` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_70` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_71` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_72` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_73` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_74` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_76` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_81` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_83` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_84` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_85` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_86` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_87` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_88` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_89` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_90` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_91` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_94` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_95` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_98` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_112` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_117` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_118` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_119` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_133` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_134` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_135` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_140` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_145` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_146` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_147` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_148` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_149` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_150` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_151` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_161` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_162` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_162-bis` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_162-ter` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_163` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_164` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_164-bis` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_165` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_169` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_173` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_174` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_176` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_177` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_178` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_179` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_180` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_181` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_182` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_184` — D.Lgs 101/2018
- `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_185` — D.Lgs 101/2018

**Uso operativo per la curatela**: il cluster "Negative: art abrogato
Codice Privacy" di `candidates_v2.json` può attingere a questi 114
articoli per generare query realistiche del tipo *"l'art. N del D.Lgs
196/2003 è ancora in vigore?"* — la risposta canonica è "no, abrogato
dal D.Lgs 101/2018 (o 51/2018), il contenuto è stato armonizzato col
GDPR / D.Lgs 51/2018".

---

## Sezione 7 — Query benchmark v1 che toccano NIS2

3 query positive del benchmark v1 hanno `gold_chunks` con prefisso D.Lgs 138/2024:

### Q10
- **use_case**: NIS2 soggetti essenziali/importanti
- **question**: La mia azienda è considerata soggetto essenziale o importante ai sensi del decreto NIS2?
- **gold_chunks**:
  - `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_3`
  - `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_6`
  - `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_7`

### Q32
- **use_case**: stress: art 6 NIS2
- **question**: art 6 NIS2 soggetti essenziali importanti
- **gold_chunks**:
  - `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_6`

### Q40
- **use_case**: stress: NIS2 obblighi notifica naturale
- **question**: Quali sono gli obblighi di notifica degli incidenti per i soggetti essenziali ai sensi della NIS2?
- **gold_chunks**:
  - `akn/it/act/decreto_legislativo/stato/2024-09-04/138__art_25`

**Implicazione per la curatela v2**: le 12 candidate del cluster "NIS2
mono-norma" non devono ricalcare Q10/Q32/Q40 sui rispettivi temi
(soggetti essenziali/importanti, obblighi notifica). Le aree NIS2 non
ancora coperte da v1: corporate governance (art. 23), misure gestione
rischio (art. 24), uso certificazioni (art. 27), regime sanzionatorio
(art. 38 fragment), strategia nazionale (art. 9), CSIRT (art. 20),
banca dati registrazione nomi dominio (art. 29), regime transitorio
(art. 41).
