# Card UC1 — q102_edilizia_popolare (positivo)

**Scenario**: Un comune italiano usa un sistema AI per calcolare automaticamente il punteggio di accesso agli alloggi di edilizia popolare: è classificato ad alto rischio ai sensi dell'Allegato III?

**Esito**: alto rischio via Allegato III (high_risk_annex=True)

## 0. Giudizio per-candidato (insieme chiuso)

**Allegato III (8 punti):**
- punto 1: no — Il sistema non utilizza dati biometrici né identificazione/categorizzazione biometrica né riconoscimento delle emozioni. Calcola punteggi di accesso a edilizia popolare su base socio-economica/amministrativa. (cite: None)
- punto 2: no — Il sistema non riguarda infrastrutture critiche (traffico, acqua, gas, elettricità, infrastrutture digitali critiche). (cite: None)
- punto 3: no — Il sistema non riguarda istruzione o formazione professionale, ma l'assegnazione di alloggi pubblici. (cite: None)
- punto 4: no — Il sistema non riguarda occupazione, selezione del personale o gestione dei lavoratori. (cite: None)
- punto 5: **APPLIES** — Il sistema è usato da un'autorità pubblica (comune italiano) per valutare l'ammissibilità di persone fisiche a prestazioni e servizi pubblici essenziali (edilizia popolare = servizio di assistenza pubblica essenziale), rientrando chiaramente nell'art. III punto 5(a). (cite: eli/reg/2024/1689/oj__annex_III__point_5)
- punto 6: no — Il sistema non riguarda attività di contrasto, forze dell'ordine o valutazione di rischi criminali. (cite: None)
- punto 7: no — Il sistema non riguarda migrazione, asilo o controllo delle frontiere. (cite: None)
- punto 8: no — Il sistema non riguarda l'amministrazione della giustizia né processi democratici/elettorali. (cite: None)
**Art. 5 — pratiche vietate (8 candidati):**
- a) Tecniche subliminali/manipolative/ingannevoli che distorcono materialmente il comportamento causando danno significativo: no — Il sistema non utilizza tecniche subliminali, manipolative o ingannevoli per distorcere il comportamento degli utenti. (cite: None)
- b) Sfruttamento di vulnerabilità (età, disabilità, situazione socio-economica) per distorcere il comportamento causando danno: no — Sebbene i destinatari possano trovarsi in situazioni di vulnerabilità socio-economica, il sistema non è progettato per sfruttare tali vulnerabilità al fine di distorcere il loro comportamento causando danno. Si limita a calcolare un punteggio amministrativo. (cite: None)
- c) Social scoring che porta a trattamento pregiudizievole/sfavorevole: no — Il sistema calcola un punteggio specifico per l'accesso a un servizio (edilizia popolare) basato su criteri di ammissibilità pertinenti (reddito, situazione abitativa, ecc.), non su comportamento sociale generale o caratteristiche della personalità in contesti non collegati. Non integra il social scoring generalizzato vietato dall'art. 5(1)(c). (cite: None)
- d) Valutazione del rischio di reato basata unicamente su profilazione/tratti di personalità (polizia predittiva individuale): no — Il sistema non valuta rischi di commissione di reati né effettua profilazione a fini di polizia predittiva. (cite: None)
- e) Creazione/ampliamento di banche dati di riconoscimento facciale tramite scraping non mirato di immagini: no — Il sistema non crea né amplia banche dati di riconoscimento facciale tramite scraping di immagini. (cite: None)
- f) Inferenza delle emozioni sul luogo di lavoro e negli istituti di istruzione (salvo motivi medici/sicurezza): no — Il sistema non inferisce emozioni né opera in contesti lavorativi o scolastici. (cite: None)
- g) Categorizzazione biometrica per inferire attributi sensibili (razza, opinioni politiche, appartenenza sindacale, convinzioni religiose/filosofiche, vita sessuale, orientamento): no — Il sistema non effettua categorizzazione biometrica per inferire attributi sensibili (razza, opinioni politiche, ecc.). (cite: None)
- h) Identificazione biometrica remota in tempo reale in spazi pubblici a fini di contrasto (salvo eccezioni): no — Il sistema non effettua identificazione biometrica remota in tempo reale in spazi pubblici a fini di contrasto. (cite: None)
- art. 6(1) componente di sicurezza: no — Il sistema non è un componente di sicurezza di un prodotto regolato da normativa di armonizzazione dell'Unione elencata nell'Allegato I. Si tratta di un sistema software amministrativo per la gestione di graduatorie di edilizia popolare.
- art. 6(3) eccezione: no — Il sistema calcola automaticamente il punteggio che determina l'accesso all'alloggio popolare, influenzando materialmente il risultato del processo decisionale (assegnazione o esclusione dall'alloggio). Non si tratta di un compito procedurale limitato né di un supporto meramente preparatorio: la decisione finale dipende direttamente dal punteggio generato dall'AI. La deroga ex art. 6(3) non è applicabile.

## 1. Verdetto

Aree Allegato III potenzialmente rilevanti dal giudizio sui riferimenti del set di classificazione: Allegato III, punto 5 — Il sistema è usato da un'autorità pubblica (comune italiano) per valutare l'ammissibilità di persone fisiche a prestazioni e servizi pubblici essenziali (edilizia popolare = servizio di assistenza pubblica essenziale), rientrando chiaramente nell'art. III punto 5(a). Verificare l'eccezione art. 6(3). Decisione finale al DPO.

- pratica vietata (art. 5): **False**

## 2. Categoria Allegato III

Allegato III, punto 5 — Il sistema è usato da un'autorità pubblica (comune italiano) per valutare l'ammissibilità di persone fisiche a prestazioni e servizi pubblici essenziali (edilizia popolare = servizio di assistenza pubblica essenziale), rientrando chiaramente nell'art. III punto 5(a)

## 3. Eccezione art. 6(3)

Eccezione art. 6(3) non applicabile: Il sistema calcola automaticamente il punteggio che determina l'accesso all'alloggio popolare, influenzando materialmente il risultato del processo decisionale (assegnazione o esclusione dall'alloggio). Non si tratta di un compito procedurale limitato né di un supporto meramente preparatorio: la decisione finale dipende direttamente dal punteggio generato dall'AI. La deroga ex art. 6(3) non è applicabile.

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