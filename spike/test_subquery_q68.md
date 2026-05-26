## GDPR
### Prompt:
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

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sul GDPR, non sull'AI Act né sulla L. 132/2025.

### Answer Sonnet:
Trattamento di categorie particolari di dati personali (dati sanitari) su larga scala mediante processo decisionale automatizzato in ambito ospedaliero: base giuridica ex art. 9, obbligo di DPIA ex art. 35, misure di sicurezza adeguate ex art. 32, nomina del responsabile del trattamento ex art. 28.

### Answer Haiku:
Trattamento dati sanitari mediante processo decisionale automatizzato (chatbot AI): base giuridica, DPIA, misure di sicurezza, diritti dell'interessato, notifica violazioni, responsabilità titolare e responsabile del trattamento.

## AI ACT
### Prompt:
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

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sull'AI Act, non sul GDPR né sulla L. 132/2025.

### Answer Sonnet:
Obblighi del fornitore e del deployer per sistema di IA ad alto rischio in ambito sanitario (Allegato III): sistema di gestione dei rischi, governance dei dati di addestramento, sorveglianza umana, registrazione automatica eventi e valutazione di conformità ante-commercializzazione.

### Answer Haiku:
Sistema di IA ad alto rischio per servizi essenziali pubblici: obblighi fornitore e deployer per applicazione legge e gestione dati clinici, valutazione d'impatto diritti fondamentali, sorveglianza umana, conformità e marcatura CE.

## L. 132
### Prompt:
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

Output: solo la sub-query, senza preamboli o spiegazioni. La sub-query deve essere sulla L. 132/2025, non sull'AI Act né sul GDPR.

### Answer Sonnet:
Obblighi per l'uso di sistemi di intelligenza artificiale in ambito sanitario a supporto di decisioni cliniche: supervisione del medico, riservatezza dei dati dei pazienti, trasparenza verso il paziente e responsabilità del soggetto deployer ai sensi della L. 132/2025.

### Answer Haiku:
Uso dell'intelligenza artificiale in ambito sanitario per supporto a decisioni cliniche: requisiti di supervisione umana, trasparenza verso il paziente, riservatezza dei dati e responsabilità del medico secondo la L. 132/2025.