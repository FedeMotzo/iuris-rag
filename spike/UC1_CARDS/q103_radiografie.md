# Card UC1 — q103_radiografie (positivo)

**Scenario**: Un sistema AI che analizza immagini radiografiche per supportare la diagnosi di patologie polmonari è ad alto rischio ai sensi dell'AI Act? Chi è il fornitore e chi è il deployer in un contesto ospedaliero?

**Esito**: possibile alto rischio via art. 6(1) (componente di sicurezza, non verificabile nel corpus) (high_risk_annex=False)

## 0. Giudizio per-candidato (insieme chiuso)

**Allegato III (8 punti):**
- punto 1: no — Il sistema analizza immagini radiografiche per scopi diagnostici, non effettua identificazione biometrica remota, categorizzazione biometrica per attributi sensibili né riconoscimento delle emozioni. (cite: None)
- punto 2: no — Il sistema non è destinato alla gestione di infrastrutture critiche (traffico, acqua, energia, infrastrutture digitali critiche), bensì alla diagnosi medica in ambito ospedaliero. (cite: None)
- punto 3: no — Il sistema non riguarda istruzione, formazione professionale, valutazione di studenti o accesso a istituti formativi. (cite: None)
- punto 4: no — Il sistema non è destinato a gestione del personale, selezione lavoratori, valutazione delle prestazioni o condizioni di lavoro. (cite: None)
- punto 5: no — Il sistema non valuta ammissibilità a prestazioni pubbliche, merito creditizio, prezzi assicurativi né gestisce chiamate di emergenza o triage di emergenza. Il supporto diagnostico radiologico ordinario non rientra nelle fattispecie elencate al punto 5. (cite: None)
- punto 6: no — Il sistema non è destinato ad attività di contrasto, forze dell'ordine o valutazione di rischi criminali. (cite: None)
- punto 7: no — Il sistema non riguarda migrazione, asilo o controllo delle frontiere. (cite: None)
- punto 8: no — Il sistema non è destinato ad autorità giudiziarie né a influenzare processi elettorali o democratici. (cite: None)
**Art. 5 — pratiche vietate (8 candidati):**
- a) Tecniche subliminali/manipolative/ingannevoli che distorcono materialmente il comportamento causando danno significativo: no — Il sistema non utilizza tecniche subliminali, manipolative o ingannevoli per distorcere il comportamento degli utenti. (cite: None)
- b) Sfruttamento di vulnerabilità (età, disabilità, situazione socio-economica) per distorcere il comportamento causando danno: no — Il sistema non sfrutta vulnerabilità di pazienti o operatori per distorcere comportamenti a fini di danno. (cite: None)
- c) Social scoring che porta a trattamento pregiudizievole/sfavorevole: no — Il sistema non effettua social scoring né classifica persone in base a comportamento sociale con effetti pregiudizievoli. (cite: None)
- d) Valutazione del rischio di reato basata unicamente su profilazione/tratti di personalità (polizia predittiva individuale): no — Il sistema non valuta rischi di commissione di reati né effettua profilazione predittiva criminale. (cite: None)
- e) Creazione/ampliamento di banche dati di riconoscimento facciale tramite scraping non mirato di immagini: no — Il sistema non crea né amplia banche dati di riconoscimento facciale tramite scraping di immagini. (cite: None)
- f) Inferenza delle emozioni sul luogo di lavoro e negli istituti di istruzione (salvo motivi medici/sicurezza): no — Il sistema non inferisce emozioni di lavoratori o studenti; analizza immagini radiografiche a fini diagnostici clinici. (cite: None)
- g) Categorizzazione biometrica per inferire attributi sensibili (razza, opinioni politiche, appartenenza sindacale, convinzioni religiose/filosofiche, vita sessuale, orientamento): no — Il sistema non effettua categorizzazione biometrica per inferire attributi sensibili (razza, opinioni politiche, orientamento sessuale, ecc.). (cite: None)
- h) Identificazione biometrica remota in tempo reale in spazi pubblici a fini di contrasto (salvo eccezioni): no — Il sistema non effettua identificazione biometrica remota in tempo reale in spazi pubblici a fini di contrasto. (cite: None)
- art. 6(1) componente di sicurezza: plausibile — Un sistema AI per l'analisi di immagini radiografiche in ambito diagnostico è molto probabilmente qualificabile come dispositivo medico o componente di sicurezza di un dispositivo medico ai sensi del Regolamento (UE) 2017/745 (MDR), normativa di armonizzazione dell'Unione che figura nell'Allegato I dell'AI Act. Se il sistema è soggetto a valutazione della conformità da parte di terzi ai sensi dell'MDR, entrambe le condizioni dell'art. 6(1) sarebbero soddisfatte, rendendo il sistema ad alto rischio per questa via, indipendentemente dall'Allegato III.
- art. 6(3) eccezione: no — Un sistema che analizza immagini radiografiche per supportare la diagnosi di patologie polmonari non esegue un compito meramente procedurale o preparatorio: influenza materialmente il processo decisionale clinico del medico (diagnosi, trattamento). Non è plausibile che ricada nella deroga dell'art. 6(3), che richiede che il sistema non influenzi materialmente il risultato decisionale o svolga solo compiti procedurali limitati.

## 1. Verdetto

Non risulta alto rischio per Allegato III; POSSIBILE alto rischio per via art. 6(1) (componente di sicurezza / dispositivo medico), NON verificabile nel corpus — da approfondire. Un sistema AI per l'analisi di immagini radiografiche in ambito diagnostico è molto probabilmente qualificabile come dispositivo medico o componente di sicurezza di un dispositivo medico ai sensi del Regolamento (UE) 2017/745 (MDR), normativa di armonizzazione dell'Unione che figura nell'Allegato I dell'AI Act. Se il sistema è soggetto a valutazione della conformità da parte di terzi ai sensi dell'MDR, entrambe le condizioni dell'art. 6(1) sarebbero soddisfatte, rendendo il sistema ad alto rischio per questa via, indipendentemente dall'Allegato III. Decisione finale al DPO.

- pratica vietata (art. 5): **False**

## 2. Categoria Allegato III

— nessuna area Allegato III —

## 3. Eccezione art. 6(3)

— non applicabile (nessuna area flaggata) —

## 4. Adempimenti (ruolo: deployer (predefinito) — cambia se l'hai costruito/lo vendi)

— non alto rischio via Allegato III: adempimenti Capo III non dovuti su questa base —

## 6. Limiti dichiarati

- Possibile alto rischio ex art. 6(1) come componente di sicurezza di un prodotto regolato da normativa di armonizzazione settoriale (es. dispositivo medico): tale normativa è fuori corpus, la classificazione su quel pathway non è verificabile sui riferimenti recuperati. Motivo del giudizio: Un sistema AI per l'analisi di immagini radiografiche in ambito diagnostico è molto probabilmente qualificabile come dispositivo medico o componente di sicurezza di un dispositivo medico ai sensi del Regolamento (UE) 2017/745 (MDR), normativa di armonizzazione dell'Unione che figura nell'Allegato I dell'AI Act. Se il sistema è soggetto a valutazione della conformità da parte di terzi ai sensi dell'MDR, entrambe le condizioni dell'art. 6(1) sarebbero soddisfatte, rendendo il sistema ad alto rischio per questa via, indipendentemente dall'Allegato III

## 7. Disclaimer

Questa card raccoglie evidenza normativa a supporto della classificazione effettuata dal DPO / titolare; non è un verdetto vincolante né una consulenza legale. La decisione finale spetta al DPO.