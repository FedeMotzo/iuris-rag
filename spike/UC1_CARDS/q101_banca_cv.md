# Card UC1 — q101_banca_cv (positivo)

**Scenario**: Una banca utilizza un sistema AI per analizzare e filtrare automaticamente i CV dei candidati e valutarli in fase di selezione del personale: è classificato ad alto rischio ai sensi dell'Allegato III dell'AI Act?

**Esito**: alto rischio via Allegato III (high_risk_annex=True)

## 0. Giudizio per-candidato (insieme chiuso)

**Allegato III (8 punti):**
- punto 1: no — Il sistema analizza CV testuali e valuta candidati: non utilizza dati biometrici, identificazione remota, categorizzazione biometrica né riconoscimento delle emozioni. (cite: None)
- punto 2: no — Il sistema opera in ambito HR bancario, non come componente di sicurezza di infrastrutture critiche (acqua, gas, traffico, digitale critica). (cite: None)
- punto 3: no — Il sistema è usato per selezione del personale in una banca, non in contesti di istruzione o formazione professionale. (cite: None)
- punto 4: **APPLIES** — Il sistema è esplicitamente destinato ad analizzare e filtrare CV e valutare candidati in fase di selezione del personale, rientrando pienamente nel punto 4(a) dell'Allegato III. (cite: eli/reg/2024/1689/oj__annex_III__point_4)
- punto 5: no — Il sistema non valuta affidabilità creditizia, ammissibilità a prestazioni pubbliche, rischi assicurativi né chiamate di emergenza. Il contesto è la selezione HR interna della banca, non l'erogazione di servizi finanziari ai clienti. (cite: None)
- punto 6: no — Il sistema non è usato da autorità di contrasto né a supporto di esse; opera in ambito privato di selezione del personale. (cite: None)
- punto 7: no — Il sistema non riguarda migrazione, asilo o controllo delle frontiere. (cite: None)
- punto 8: no — Il sistema non è usato da autorità giudiziarie né per influenzare elezioni o referendum. (cite: None)
**Art. 5 — pratiche vietate (8 candidati):**
- a) Tecniche subliminali/manipolative/ingannevoli che distorcono materialmente il comportamento causando danno significativo: no — Il sistema analizza CV in modo automatizzato ma non utilizza tecniche subliminali o manipolative/ingannevoli per distorcere il comportamento dei candidati. (cite: None)
- b) Sfruttamento di vulnerabilità (età, disabilità, situazione socio-economica) per distorcere il comportamento causando danno: no — Non risulta che il sistema sfrutti vulnerabilità legate a età, disabilità o situazione socio-economica per distorcere il comportamento dei candidati. (cite: None)
- c) Social scoring che porta a trattamento pregiudizievole/sfavorevole: no — Il sistema valuta candidati per una specifica finalità lavorativa, non produce un punteggio sociale generalizzato che comporti trattamento pregiudizievole in contesti sociali non collegati alla selezione. (cite: None)
- d) Valutazione del rischio di reato basata unicamente su profilazione/tratti di personalità (polizia predittiva individuale): no — Il sistema non valuta rischi di commissione di reati né effettua profilazione predittiva criminale. (cite: None)
- e) Creazione/ampliamento di banche dati di riconoscimento facciale tramite scraping non mirato di immagini: no — Il sistema non crea né amplia banche dati di riconoscimento facciale tramite scraping di immagini. (cite: None)
- f) Inferenza delle emozioni sul luogo di lavoro e negli istituti di istruzione (salvo motivi medici/sicurezza): no — Dalla descrizione non emerge che il sistema inferisca emozioni dei candidati. Analizza e filtra CV (dati testuali/documentali), senza riconoscimento emotivo. (cite: None)
- g) Categorizzazione biometrica per inferire attributi sensibili (razza, opinioni politiche, appartenenza sindacale, convinzioni religiose/filosofiche, vita sessuale, orientamento): no — Il sistema non effettua categorizzazione biometrica per inferire attributi sensibili (razza, opinioni politiche, ecc.). (cite: None)
- h) Identificazione biometrica remota in tempo reale in spazi pubblici a fini di contrasto (salvo eccezioni): no — Il sistema non utilizza identificazione biometrica remota in tempo reale in spazi pubblici a fini di contrasto. (cite: None)
- art. 6(1) componente di sicurezza: no — Il sistema di screening CV non è plausibilmente un componente di sicurezza di un prodotto regolato da normativa di armonizzazione settoriale (es. dispositivi medici, macchine). Opera in ambito puramente amministrativo/HR.
- art. 6(3) eccezione: plausibile — È ipotizzabile la deroga ex art. 6(3) se il sistema si limita a un filtraggio procedurale preliminare (es. verifica di requisiti formali minimi) senza influenzare materialmente la decisione finale di assunzione, che rimane in capo a valutatori umani. Tuttavia, se il sistema valuta e classifica i candidati in modo sostanziale, la deroga non sarebbe applicabile.

## 1. Verdetto

Aree Allegato III potenzialmente rilevanti dal giudizio sui riferimenti del set di classificazione: Allegato III, punto 4 — Il sistema è esplicitamente destinato ad analizzare e filtrare CV e valutare candidati in fase di selezione del personale, rientrando pienamente nel punto 4(a) dell'Allegato III. Verificare l'eccezione art. 6(3). Decisione finale al DPO.

- pratica vietata (art. 5): **False**

## 2. Categoria Allegato III

Allegato III, punto 4 — Il sistema è esplicitamente destinato ad analizzare e filtrare CV e valutare candidati in fase di selezione del personale, rientrando pienamente nel punto 4(a) dell'Allegato III

## 3. Eccezione art. 6(3)

Possibile deroga ex art. 6(3): È ipotizzabile la deroga ex art. 6(3) se il sistema si limita a un filtraggio procedurale preliminare (es. verifica di requisiti formali minimi) senza influenzare materialmente la decisione finale di assunzione, che rimane in capo a valutatori umani. Tuttavia, se il sistema valuta e classifica i candidati in modo sostanziale, la deroga non sarebbe applicabile.

## 4. Adempimenti (ruolo: deployer (predefinito) — cambia se l'hai costruito/lo vendi)

Lista canonica del ruolo **deployer** (12 voci), tutte mostrate con il tag di condizione (il DPO valuta; le condizioni non sono risolte):

| voce | titolo | descrizione | condizione | note | fonte | GDPR |
|---|---|---|---|---|---|---|
| Art. 26(1) | Uso conforme alle istruzioni | misure tecn./organizzative per usare secondo istruzioni | sempre |  | sì |  |
| Art. 26(2) | Sorveglianza umana | affidare a persone competenti/formate/con autorità | sempre |  | sì |  |
| Art. 26(4) | Pertinenza dati di input | input pertinenti e rappresentativi | se controlla i dati di input |  | sì |  |
| Art. 26(5) | Monitoraggio e segnalazione | monitorare; sospendere+informare in caso di rischio; segnalare incidenti | scatta su rischio/incidente; istituti finanziari via normativa settoriale |  | sì |  |
| Art. 26(6) | Conservazione log | conservare log ≥ 6 mesi | se i log sono sotto controllo del deployer |  | sì |  |
| Art. 26(7) | Informazione dei lavoratori | informare rappresentanti/lavoratori prima dell'uso | solo datore di lavoro che usa sul luogo di lavoro |  | sì |  |
| Art. 26(8) | Registrazione banca dati UE | adempiere art. 49; non usare se non registrato | solo autorità pubbliche / organi UE |  | sì |  |
| Art. 26(9) | Uso info per la DPIA | usare info art. 13 per la DPIA | obbligo DPIA esterno all'AI Act (nasce dal GDPR) | si collega al GDPR (DPIA, art. 35) — incrocio AI Act↔GDPR in arrivo nel prossimo layer | sì | cfr. art. 35 GDPR (risolto) |
| Art. 26(10) | Autorizzazione identificazione biometrica a posteriori | autorizzazione giud./amm. | solo forze dell'ordine + post-remote biometric | rinvio alla Direttiva (UE) 2016/680 (forze dell'ordine), FUORI corpus; caso di nicchia | sì |  |
| Art. 26(11) | Informazione delle persone fisiche | informare chi è soggetto a decisioni del sistema | sistemi All. III che prendono/assistono decisioni su persone |  | sì |  |
| Art. 26(12) | Cooperazione con le autorità | cooperare nelle azioni relative al sistema | sempre |  | sì |  |
| Art. 27 | Valutazione d'impatto diritti fondamentali (FRIA) | svolgere FRIA pre-uso + notificare | organismi di diritto pubblico; privati con servizi pubblici; deployer All. III 5(b)/5(c); esclusi All. III punto 2 |  | sì |  |

## 6. Limiti dichiarati

— nessun limite dichiarato —

## 7. Disclaimer

Questa card raccoglie evidenza normativa a supporto della classificazione effettuata dal DPO / titolare; non è un verdetto vincolante né una consulenza legale. La decisione finale spetta al DPO.