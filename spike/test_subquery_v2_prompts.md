# Test prompt V2 — Q68 + Q69 (6 prompt totali)

Validazione del prompt template aggiornato con clausola direttiva sulla nominazione esplicita degli istituti.

**Modello**: Sonnet 4.6 (anthropic console / API playground)
**Temperature**: 0.0
**Max tokens**: 200

Lanciare tutti e 6, copiare gli output sotto ciascun blocco "### Answer:".

---

## Q68 / GDPR

### Prompt:
```
Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: GDPR (Regolamento UE 2016/679)

Vocabolario tecnico tipico della norma GDPR:
- titolare del trattamento, responsabile del trattamento, interessato
- base giuridica del trattamento (art. 6): consenso, contratto, obbligo legale, interesse legittimo, compito di interesse pubblico
- categorie particolari di dati personali (art. 9): dati sanitari, biometrici, genetici, origine razziale o etnica, opinioni politiche, convinzioni religiose, vita sessuale, orientamento sessuale
- processo decisionale automatizzato, profilazione, diritto di non essere sottoposto a decisione unicamente automatizzata (art. 22)
- valutazione d'impatto sulla protezione dei dati (DPIA, art. 35): trattamento sistematico, larga scala, rischio elevato per diritti e libertà
- trasferimento di dati personali verso paesi terzi (artt. 44-49): decisione di adeguatezza, clausole contrattuali tipo, garanzie adeguate
- responsabile del trattamento e contratto di nomina (art. 28), trattamenti per conto del titolare
- sicurezza del trattamento, misure tecniche e organizzative adeguate (art. 32), pseudonimizzazione, cifratura
- notifica violazione dati personali al Garante (art. 33), comunicazione all'interessato (art. 34)
- informativa e trasparenza (artt. 13-14), diritti dell'interessato (artt. 15-22): accesso, rettifica, cancellazione, portabilità, opposizione

Query utente originale:
"Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nel GDPR per questo scenario, usando il vocabolario tecnico della norma GDPR sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus GDPR.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sul GDPR, non sull'AI Act né sulla L. 132/2025.
```

### Answer:
```
Trattamento di dati sanitari (art. 9) tramite processo decisionale automatizzato e profilazione (art. 22) a larga scala: obbligo di DPIA (art. 35), base giuridica del trattamento (art. 6), nomina responsabile del trattamento ex art. 28, misure tecniche e organizzative adeguate (art. 32), informativa (artt. 13-14) e diritti dell'interessato.
```

---

## Q68 / AI Act

### Prompt:
```
Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: AI Act (Regolamento UE 2024/1689)

Vocabolario tecnico tipico della norma AI Act:
- sistema di intelligenza artificiale, modello di IA per finalità generali (GPAI)
- fornitore (provider), deployer (utilizzatore/utente), distributore, importatore, rappresentante autorizzato
- pratiche di intelligenza artificiale vietate (art. 5): manipolazione, sfruttamento vulnerabilità, social scoring, identificazione biometrica remota in tempo reale
- sistema di IA ad alto rischio (art. 6 + Allegato III): occupazione e gestione dei lavoratori, istruzione, accesso a servizi essenziali pubblici e privati, applicazione della legge, migrazione, amministrazione della giustizia
- obblighi del fornitore di sistemi ad alto rischio (Capo III Sezione 2): sistema di gestione dei rischi, governance dei dati di addestramento, documentazione tecnica, registrazione automatica eventi (log), trasparenza verso il deployer, sorveglianza umana, accuratezza, robustezza e cybersicurezza
- obblighi del deployer (art. 26): conformità alle istruzioni d'uso, sorveglianza umana, monitoraggio funzionamento, conservazione log, informativa ai lavoratori
- valutazione d'impatto sui diritti fondamentali (FRIA, art. 27): organismi di diritto pubblico, fornitori di servizi pubblici essenziali, credit scoring, valutazione rischio assicurazioni vita e salute
- valutazione di conformità, marcatura CE, dichiarazione di conformità UE, banca dati UE dei sistemi ad alto rischio
- modifiche sostanziali al sistema, monitoraggio post-commercializzazione, segnalazione incidenti gravi
- sanzioni (art. 99): pratiche vietate fino a 35M€ o 7% fatturato globale; altre violazioni fino a 15M€ o 3%

Query utente originale:
"Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nell'AI Act per questo scenario, usando il vocabolario tecnico della norma AI Act sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus AI Act.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sull'AI Act, non sul GDPR né sulla L. 132/2025.
```

### Answer:
```
Quali obblighi prevede l'AI Act per un fornitore e deployer di sistema di IA ad alto rischio in ambito sanitario (Allegato III), con riferimento a: sistema di gestione dei rischi, governance dei dati di addestramento, documentazione tecnica, registrazione automatica eventi, sorveglianza umana, valutazione di conformità, marcatura CE e FRIA (art. 27)?
```

---

## Q68 / L. 132/2025

### Prompt:
```
Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: L. 132/2025 (Disposizioni nazionali italiane in materia di intelligenza artificiale)

Vocabolario tecnico tipico della norma L. 132/2025:
- principi generali sull'uso dell'intelligenza artificiale: tutela della persona, dei diritti fondamentali, antropocentrismo, trasparenza, supervisione umana
- uso dell'IA in ambito sanitario (art. 7): supporto a decisioni cliniche, riservatezza dati dei pazienti, supervisione del medico
- uso dell'IA in ambito lavorativo (art. 11): obbligo del datore di lavoro di informativa ai lavoratori sui sistemi decisionali o di monitoraggio integralmente automatizzati, tutela integrità psicofisica, principio di non discriminazione
- IA nelle pubbliche amministrazioni: principio di strumentalità, responsabilità del funzionario, decisione finale umana
- IA nelle professioni intellettuali: trasparenza verso il cliente sull'uso di sistemi di IA
- Autorità nazionali competenti per l'IA, coordinamento con AgID e ACN
- tutela dei minori nell'uso dell'IA, consenso del genitore per servizi diretti a minori sotto i 14 anni
- disposizioni penali in materia di contenuti generati o alterati con IA (deepfake illeciti)

Query utente originale:
"Un'azienda ospedaliera intende mettere in produzione un chatbot AI per supportare il triage telefonico dei pazienti: quali adempimenti integrati AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nella L. 132/2025 per questo scenario, usando il vocabolario tecnico della norma L. 132/2025 sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus L. 132/2025.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sulla L. 132/2025, non sull'AI Act né sul GDPR.
```

### Answer:
```
Quali obblighi prevede l'art. 7 L. 132/2025 per l'uso di sistemi di IA a supporto di decisioni cliniche in ambito sanitario, con riferimento alla supervisione del medico, alla riservatezza dei dati dei pazienti e al principio di antropocentrismo, nel contesto di un sistema automatizzato di triage?
```

---

## Q69 / GDPR

### Prompt:
```
Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: GDPR (Regolamento UE 2016/679)

Vocabolario tecnico tipico della norma GDPR:
- titolare del trattamento, responsabile del trattamento, interessato
- base giuridica del trattamento (art. 6): consenso, contratto, obbligo legale, interesse legittimo, compito di interesse pubblico
- categorie particolari di dati personali (art. 9): dati sanitari, biometrici, genetici, origine razziale o etnica, opinioni politiche, convinzioni religiose, vita sessuale, orientamento sessuale
- processo decisionale automatizzato, profilazione, diritto di non essere sottoposto a decisione unicamente automatizzata (art. 22)
- valutazione d'impatto sulla protezione dei dati (DPIA, art. 35): trattamento sistematico, larga scala, rischio elevato per diritti e libertà
- trasferimento di dati personali verso paesi terzi (artt. 44-49): decisione di adeguatezza, clausole contrattuali tipo, garanzie adeguate
- responsabile del trattamento e contratto di nomina (art. 28), trattamenti per conto del titolare
- sicurezza del trattamento, misure tecniche e organizzative adeguate (art. 32), pseudonimizzazione, cifratura
- notifica violazione dati personali al Garante (art. 33), comunicazione all'interessato (art. 34)
- informativa e trasparenza (artt. 13-14), diritti dell'interessato (artt. 15-22): accesso, rettifica, cancellazione, portabilità, opposizione

Query utente originale:
"Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare un sistema di IA per supportare le attività di farmacovigilanza con dati provenienti da operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai sensi di AI Act, GDPR e NIS2?"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nel GDPR per questo scenario, usando il vocabolario tecnico della norma GDPR sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus GDPR.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sul GDPR, non sull'AI Act né sulla NIS2.
```

### Answer:
```
Trattamento di categorie particolari di dati personali (art. 9) — dati sanitari a larga scala da pazienti e operatori sanitari — con obbligo di DPIA (art. 35), base giuridica del trattamento (art. 6), nomina del responsabile del trattamento (art. 28), misure di sicurezza adeguate incluse pseudonimizzazione e cifratura (art. 32), e diritti dell'interessato (artt. 15-22) in contesto di profilazione e processo decisionale automatizzato (art. 22).
```

---

## Q69 / AI Act

### Prompt:
```
Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: AI Act (Regolamento UE 2024/1689)

Vocabolario tecnico tipico della norma AI Act:
- sistema di intelligenza artificiale, modello di IA per finalità generali (GPAI)
- fornitore (provider), deployer (utilizzatore/utente), distributore, importatore, rappresentante autorizzato
- pratiche di intelligenza artificiale vietate (art. 5): manipolazione, sfruttamento vulnerabilità, social scoring, identificazione biometrica remota in tempo reale
- sistema di IA ad alto rischio (art. 6 + Allegato III): occupazione e gestione dei lavoratori, istruzione, accesso a servizi essenziali pubblici e privati, applicazione della legge, migrazione, amministrazione della giustizia
- obblighi del fornitore di sistemi ad alto rischio (Capo III Sezione 2): sistema di gestione dei rischi, governance dei dati di addestramento, documentazione tecnica, registrazione automatica eventi (log), trasparenza verso il deployer, sorveglianza umana, accuratezza, robustezza e cybersicurezza
- obblighi del deployer (art. 26): conformità alle istruzioni d'uso, sorveglianza umana, monitoraggio funzionamento, conservazione log, informativa ai lavoratori
- valutazione d'impatto sui diritti fondamentali (FRIA, art. 27): organismi di diritto pubblico, fornitori di servizi pubblici essenziali, credit scoring, valutazione rischio assicurazioni vita e salute
- valutazione di conformità, marcatura CE, dichiarazione di conformità UE, banca dati UE dei sistemi ad alto rischio
- modifiche sostanziali al sistema, monitoraggio post-commercializzazione, segnalazione incidenti gravi
- sanzioni (art. 99): pratiche vietate fino a 35M€ o 7% fatturato globale; altre violazioni fino a 15M€ o 3%

Query utente originale:
"Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare un sistema di IA per supportare le attività di farmacovigilanza con dati provenienti da operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai sensi di AI Act, GDPR e NIS2?"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nell'AI Act per questo scenario, usando il vocabolario tecnico della norma AI Act sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus AI Act.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sull'AI Act, non sul GDPR né sulla NIS2.
```

### Answer:
```
Sistema di IA ad alto rischio per farmacovigilanza (Allegato III, accesso a servizi essenziali): obblighi del fornitore ex Capo III Sezione 2 (gestione rischi, governance dati addestramento, documentazione tecnica, log, sorveglianza umana) e obbligo FRIA art. 27 per trattamento dati pazienti e operatori sanitari.
```

---

## Q69 / NIS2

### Prompt:
```
Devi generare una sub-query mirata per il retrieval su corpus normativo italiano.

Norma target: NIS2 (D.Lgs 138/2024)

Vocabolario tecnico tipico della norma NIS2:
- soggetto essenziale, soggetto importante, ambito di applicazione, settori critici (sanità, energia, trasporti, finanza, infrastrutture digitali, PA)
- registrazione sulla piattaforma ACN (Agenzia per la Cybersicurezza Nazionale), punto di contatto
- responsabilità degli organi di amministrazione e direzione (art. 23): approvazione misure, supervisione, formazione, responsabilità diretta dei dirigenti
- misure tecniche, operative e organizzative di gestione del rischio di cybersicurezza (art. 24): analisi del rischio, gestione incidenti, continuità operativa, sicurezza supply chain, controllo accessi, autenticazione a più fattori, cifratura
- notifica incidenti significativi al CSIRT Italia (art. 25): pre-notifica entro 24 ore, notifica completa entro 72 ore, relazione finale entro un mese
- comunicazione volontaria di minacce cyber
- obblighi sulla catena di approvvigionamento ICT, fornitori e prestatori di servizi gestiti
- sanzioni amministrative differenziate per soggetti essenziali e importanti, poteri di vigilanza e ispezione dell'ACN

Query utente originale:
"Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 per il settore sanitario, intende impiegare un sistema di IA per supportare le attività di farmacovigilanza con dati provenienti da operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai sensi di AI Act, GDPR e NIS2?"

Compito: produci una singola sub-query (1-2 frasi, max 50 parole) che esprima cosa cercare SPECIFICAMENTE nella NIS2 per questo scenario, usando il vocabolario tecnico della norma NIS2 sopra elencato. La sub-query sarà usata come input testuale per un retrieval dense+sparse sul corpus NIS2.

Vincolo importante: la sub-query DEVE nominare esplicitamente gli istituti giuridici e i riferimenti normativi attivati dallo scenario (es. nomi di istituti come FRIA, DPIA, sigle ufficiali, numeri di articolo come 'art. 27', 'art. 9', 'Allegato III' quando il vocabolario sopra li include e lo scenario li attiva). NON parafrasare gli istituti con descrizioni applicative generiche.

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sulla NIS2, non sull'AI Act né sul GDPR.
```

### Answer:
```
Quali obblighi NIS2 (D.Lgs 138/2024) gravano su un soggetto essenziale del settore sanitario in merito alle misure tecniche e organizzative di gestione del rischio ex art. 24, alla notifica di incidenti significativi al CSIRT Italia ex art. 25 (pre-notifica 24h, notifica 72h), alla sicurezza della supply chain ICT e alla responsabilità degli organi di amministrazione ex art. 23?
```

---

## Tabella di valutazione (compilare dopo i 6 output)

Criterio: la sub-query nomina esplicitamente articoli/istituti rilevanti?

| Query | Norma | Istituti attesi | Citati? |
|---|---|---|---|
| Q68 | GDPR | art. 9, art. 35 (DPIA) | ? |
| Q68 | AI Act | art. 6, art. 27 (FRIA), Allegato III | ? |
| Q68 | L.132 | art. 7 sanitario | ? |
| Q69 | GDPR | art. 9, art. 35 (DPIA) | ? |
| Q69 | AI Act | art. 6, art. 27 (FRIA) | ? |
| Q69 | NIS2 | art. 24, art. 25 | ? |

Verdetto:
- Tutti i 6 nominano gli istituti attesi → fix prompt promosso, applichiamo al codice
- Mismatch su 1-2 → discutere se vale comunque applicare
- Mismatch su 3+ → fix prompt insufficiente, ripensiamo
