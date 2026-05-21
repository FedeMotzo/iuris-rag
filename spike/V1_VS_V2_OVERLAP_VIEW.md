# V1 vs V2 overlap view (preparatoria per audit C)

Data: 2026-05-20. Fase B (pre-audit giuridico).
Input: 82 candidate v2 (post-fix B1) ↔ 50 query v1.

Metrica overlap: Jaccard similarity sui token della `question` (lowercase, stopwords italiane filtrate, len>2, no digits).
Pool candidate v1 per ciascuna v2: norme matching first, norme overlap second, fallback completo.

**Soglie**: 🔴 ALTO ≥0.40 · 🟡 MEDIO 0.20-0.39 · 🟢 BASSO/zona nuova <0.20.

## Tabella comparativa

Ordinata per Jaccard DESC (overlap ALTO prima), poi cluster.

| qid_v2 | cluster | question_v2 | norme | v1 più simile | jaccard | flag | nota |
|---|---|---|---|---|---:|---|---|
| C058 | Procedurali 'come si fa X | Quali sono i passi della procedura di valutazione d'impatto sulla protezione d… | GDPR | Q7 | 0.36 | 🟡 | keyword condivisi: d'impatto,dati,dei,protezione |
| C051 | Sanzionatorio puro | Quale è il massimale edittale applicabile a un fornitore di modelli di IA per … | AI Act | Q14 | 0.33 | 🟡 | keyword condivisi: finalità,fornitore,generali,modelli |
| C060 | Procedurali 'come si fa X | Quali sono i passi procedurali e i criteri da seguire per la nomina del respon… | GDPR | Q6 | 0.31 | 🟡 | keyword condivisi: dati,dei,protezione,responsabile |
| C045 | Diritti dell'interessato  | Quali sono le conseguenze concrete per il titolare del trattamento dell'eserci… | GDPR | Q28 | 0.25 | 🟡 | keyword condivisi: art,gdpr,trattamento |
| C024 | L. 132/2025 | Quali principi specifici la L. 132/2025 detta in materia di utilizzo di sistem… | L. 132/2025 | Q38 | 0.25 | 🟡 | keyword condivisi: artificiale,intelligenza,lavoro |
| C039 | Cross-norma scenario 2 no | Il trattamento illecito di dati personali di cui all'art. 167 del Codice Priva… | Codice Privacy+D.Lgs 231/2001 | Q9 | 0.22 | 🟡 | keyword condivisi: dati,illecito,personali,trattamento |
| C050 | Sanzionatorio puro | Quali sono i massimali edittali delle sanzioni amministrative pecuniarie appli… | NIS2 | Q40 | 0.22 | 🟡 | keyword condivisi: incidenti,notifica,obblighi,soggetti |
| C027 | L. 132/2025 | Quali sono le autorità individuate dalla L. 132/2025 per il monitoraggio e la … | L. 132/2025 | Q38 | 0.20 | 🟡 | keyword condivisi: artificiale,intelligenza |
| C001 | NIS2 mono-norma | Un operatore di servizi di trasporto ferroviario regionale, con circa 80 dipen… | NIS2 | Q32 | 0.20 | 🟡 | keyword condivisi: essenziali,importanti,nis2,soggetti |
| C025 | L. 132/2025 | Quali specifiche cautele introduce la L. 132/2025 per l'utilizzo di sistemi di… | L. 132/2025 | Q38 | 0.18 | 🟢 | tematicamente distinto da v1 |
| C008 | NIS2 mono-norma | Quali sono i massimali delle sanzioni amministrative pecuniarie previste dal D… | NIS2 | Q32 | 0.18 | 🟢 | tematicamente distinto da v1 |
| C009 | NIS2 mono-norma | L'autorità competente NIS2 può sospendere temporaneamente dalle funzioni dirig… | NIS2 | Q10 | 0.16 | 🟢 | tematicamente distinto da v1 |
| C080 | Edge: vaghe / mix | Privacy e AI: gli obblighi delle aziende | AI Act+GDPR+L. 132/2025 | Q2 | 0.15 | 🟢 | tematicamente distinto da v1 |
| C029 | L. 132/2025 | La L. 132/2025 introduce nuove fattispecie di responsabilità civile o penale p… | L. 132/2025 | Q38 | 0.15 | 🟢 | tematicamente distinto da v1 |
| C032 | Cross-norma 3+ norme | Un comune capoluogo, qualificato come soggetto essenziale ai sensi della NIS2,… | AI Act+GDPR+NIS2 | Q10 | 0.14 | 🟢 | tematicamente distinto da v1 |
| C015 | NIS2 cross GDPR | Quale rapporto sussiste fra l'obbligo di valutazione del rischio cyber NIS2 e … | GDPR+NIS2 | Q33 | 0.14 | 🟢 | tematicamente distinto da v1 |
| C034 | Cross-norma 3+ norme | Un'azienda farmaceutica italiana, qualificata come soggetto essenziale NIS2 pe… | AI Act+GDPR+NIS2 | Q10 | 0.13 | 🟢 | tematicamente distinto da v1 |
| C035 | Cross-norma 3+ norme | Una banca italiana intende affidare in outsourcing a un fornitore extra-UE la … | AI Act+D.Lgs 231/2001+GDPR+NIS2 | Q1 | 0.13 | 🟢 | tematicamente distinto da v1 |
| C006 | NIS2 mono-norma | Quali sono le tempistiche e i contenuti minimi della notifica di un incidente … | NIS2 | Q40 | 0.13 | 🟢 | tematicamente distinto da v1 |
| C048 | Sanzionatorio puro | Quale è il massimale di sanzione amministrativa pecuniaria applicabile a una v… | GDPR | Q28 | 0.13 | 🟢 | tematicamente distinto da v1 |
| C011 | NIS2 mono-norma | I fornitori di servizi gestiti di sicurezza (MSSP) sono soggetti diretti agli … | NIS2 | Q40 | 0.13 | 🟢 | tematicamente distinto da v1 |
| C040 | Cross-norma scenario 2 no | L'incidente che ha comportato l'esfiltrazione di una banca dati di clienti di … | GDPR+NIS2 | Q10 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C043 | Diritti dell'interessato  | In quali condizioni il diritto all'oblio ex art. 17 GDPR può essere esercitato… | GDPR | Q28 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C044 | Diritti dell'interessato  | Il diritto alla portabilità dei dati di cui all'art. 20 GDPR si applica anche … | GDPR | Q28 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C078 | Edge: vaghe / mix | Cosa devo sapere di NIS2? | NIS2 | Q32 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C082 | L. 132/2025 | La L. 132/2025 introduce un regime di vigilanza nazionale sui sistemi di intel… | AI Act+L. 132/2025 | Q38 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C059 | Procedurali 'come si fa X | Quali sono i contenuti minimi che il registro delle attività di trattamento de… | GDPR | Q28 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C042 | Diritti dell'interessato  | Entro quale termine il titolare è tenuto a riscontrare una richiesta di access… | GDPR | Q28 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C007 | NIS2 mono-norma | In quali casi un soggetto NIS2 è tenuto a informare anche i destinatari dei pr… | NIS2 | Q10 | 0.12 | 🟢 | tematicamente distinto da v1 |
| C013 | NIS2 cross GDPR | Un incidente informatico che compromette i sistemi di un soggetto essenziale N… | GDPR+NIS2 | Q10 | 0.11 | 🟢 | tematicamente distinto da v1 |
| C014 | NIS2 cross GDPR | Se i dati compromessi in un incidente NIS2 non sono dati personali ma soltanto… | GDPR+NIS2 | Q40 | 0.11 | 🟢 | tematicamente distinto da v1 |
| C010 | NIS2 mono-norma | Un istituto bancario italiano già soggetto al Regolamento DORA è tenuto anche … | NIS2 | Q10 | 0.11 | 🟢 | tematicamente distinto da v1 |
| C012 | NIS2 mono-norma | La formazione obbligatoria in materia di cybersicurezza prevista dal D.Lgs 138… | NIS2 | Q10 | 0.11 | 🟢 | tematicamente distinto da v1 |
| C004 | NIS2 mono-norma | La NIS2 impone l'adozione di un approccio multi-rischio: quali sono gli ambiti… | NIS2 | Q40 | 0.10 | 🟢 | tematicamente distinto da v1 |
| C033 | Cross-norma 3+ norme | Uno studio legale boutique intende adottare un sistema di IA generativa per su… | AI Act+D.Lgs 231/2001+GDPR | Q3 | 0.09 | 🟢 | tematicamente distinto da v1 |
| C081 | Cross-norma 3+ norme | Un'impresa industriale italiana adotta un sistema di IA per monitorare in cont… | AI Act+GDPR+L. 132/2025 | Q2 | 0.09 | 🟢 | tematicamente distinto da v1 |
| C003 | NIS2 mono-norma | Quali responsabilità ricadono in modo diretto sugli organi di amministrazione … | NIS2 | Q10 | 0.09 | 🟢 | tematicamente distinto da v1 |
| C005 | NIS2 mono-norma | Un soggetto essenziale che si affida a un fornitore ICT esterno per la gestion… | NIS2 | Q10 | 0.09 | 🟢 | tematicamente distinto da v1 |
| C030 | Cross-norma 3+ norme | Una banca italiana intende adottare un sistema di intelligenza artificiale per… | AI Act+D.Lgs 231/2001+GDPR+L. 132/2025 | Q11 | 0.09 | 🟢 | tematicamente distinto da v1 |
| C023 | Codice Privacy mono-norma | Esistono fattispecie penali nel Codice Privacy diverse dall'art. 167 e quali c… | Codice Privacy | Q43 | 0.08 | 🟢 | tematicamente distinto da v1 |
| C037 | Cross-norma scenario 2 no | Quando un'organizzazione assume la qualifica di deployer di un sistema di IA a… | AI Act+GDPR | Q3 | 0.08 | 🟢 | tematicamente distinto da v1 |
| C028 | L. 132/2025 | La L. 132/2025 contiene disposizioni in materia di utilizzo dell'intelligenza … | L. 132/2025 | Q38 | 0.08 | 🟢 | tematicamente distinto da v1 |
| C031 | Cross-norma 3+ norme | Un'azienda ospedaliera intende mettere in produzione un chatbot AI per support… | AI Act+GDPR+L. 132/2025 | Q1 | 0.07 | 🟢 | tematicamente distinto da v1 |
| C052 | Sanzionatorio puro | Quale è il massimale della sanzione pecuniaria GDPR per un titolare che ometta… | GDPR | Q29 | 0.07 | 🟢 | tematicamente distinto da v1 |
| C036 | Cross-norma 3+ norme | Una regione italiana intende mettere in produzione un sistema di IA per suppor… | AI Act+GDPR+L. 132/2025+NIS2 | Q2 | 0.06 | 🟢 | tematicamente distinto da v1 |
| C054 | 231 fattispecie oltre 24- | Quali condotte costituiscono reati-presupposto del 231 in materia di riciclagg… | D.Lgs 231/2001 | Q9 | 0.06 | 🟢 | tematicamente distinto da v1 |
| C020 | Codice Privacy mono-norma | In quali ipotesi il trattamento illecito di dati personali costituisce reato p… | Codice Privacy | Q43 | 0.06 | 🟢 | tematicamente distinto da v1 |
| C022 | Codice Privacy mono-norma | Quali condizioni devono essere rispettate per il trattamento dei dati personal… | Codice Privacy | Q43 | 0.06 | 🟢 | tematicamente distinto da v1 |
| C053 | 231 fattispecie oltre 24- | Quali fattispecie penali in materia di corruzione e concussione sono inserite … | D.Lgs 231/2001 | Q9 | 0.05 | 🟢 | tematicamente distinto da v1 |
| C046 | Diritti dell'interessato  | Il diritto di opposizione al trattamento per finalità di marketing diretto può… | GDPR | Q28 | 0.05 | 🟢 | tematicamente distinto da v1 |
| C002 | NIS2 mono-norma | Un cloud service provider con sede legale all'estero ma che eroga servizi a so… | NIS2 | Q32 | 0.05 | 🟢 | tematicamente distinto da v1 |
| C049 | Sanzionatorio puro | In quali casi specifici il giudice dispone le sanzioni interdittive nei confro… | D.Lgs 231/2001 | Q9 | 0.05 | 🟢 | tematicamente distinto da v1 |
| C056 | 231 fattispecie oltre 24- | L'adozione di un modello organizzativo idoneo a prevenire il rischio di ricicl… | D.Lgs 231/2001 | Q49 | 0.05 | 🟢 | tematicamente distinto da v1 |
| C041 | Cross-norma scenario 2 no | Le istruzioni per l'uso fornite dal provider del sistema di IA ad alto rischio… | AI Act+GDPR | Q3 | 0.03 | 🟢 | tematicamente distinto da v1 |
| C038 | Cross-norma scenario 2 no | Gli obblighi informativi che il deployer di un sistema di IA ad alto rischio d… | AI Act+GDPR | Q19 | 0.03 | 🟢 | tematicamente distinto da v1 |
| C055 | 231 fattispecie oltre 24- | In quali ipotesi il D.Lgs 231/2001 prevede la responsabilità amministrativa de… | D.Lgs 231/2001 | Q9 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C057 | 231 fattispecie oltre 24- | Quali sono i criteri stabiliti dall'art. 11 del D.Lgs 231/2001 per la determin… | D.Lgs 231/2001 | Q9 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C016 | Codice Privacy mono-norma | Quali sono i poteri ispettivi del Garante per la protezione dei dati personali… | Codice Privacy | Q43 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C017 | Codice Privacy mono-norma | Come è composto il collegio del Garante per la protezione dei dati personali e… | Codice Privacy | Q43 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C018 | Codice Privacy mono-norma | Su quale base giuridica un'amministrazione pubblica italiana può trattare dati… | Codice Privacy+GDPR | Q43 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C019 | Codice Privacy mono-norma | Il trattamento di dati personali da parte dei servizi di informazione per la s… | Codice Privacy | Q43 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C021 | Codice Privacy mono-norma | Il Garante per la protezione dei dati personali può adottare provvedimenti cor… | Codice Privacy | Q43 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C047 | Diritti dell'interessato  | Il diritto di accesso ex art. 15 GDPR può essere esercitato anche da soggetti … | Codice Privacy+GDPR | Q43 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C079 | Edge: vaghe / mix | Compliance AI | AI Act+L. 132/2025 | Q1 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C026 | L. 132/2025 | Come la L. 132/2025 si raccorda con il Regolamento (UE) 2024/1689 in termini d… | L. 132/2025 | Q38 | 0.00 | 🟢 | tematicamente distinto da v1 |
| C072 | Negative: Garante UC4 | Quali sono le prescrizioni contenute nel provvedimento del Garante n. 9870832 … | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C073 | Negative: Garante UC4 | Quale è la posizione del Garante espressa nel provvedimento del 9 marzo 2023 s… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C074 | Negative: Garante UC4 | Cosa ha disposto il Garante Privacy nella decisione del 2024 contro TikTok per… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C064 | Negative: art abrogato Co | Quali sono le misure minime di sicurezza che il titolare deve adottare ai sens… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C065 | Negative: art abrogato Co | Come va redatto il Documento Programmatico sulla Sicurezza (DPS) ex art. 34 de… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C066 | Negative: art abrogato Co | Quali sono i diritti dell'interessato previsti dall'art. 7 del Codice Privacy? | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C067 | Negative: art abrogato Co | Come va effettuata la notificazione preventiva del trattamento al Garante ai s… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C068 | Negative: art abrogato Co | Quali sono le caratteristiche del Garante per la protezione dei dati personali… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C061 | Negative: art inesistente | Cosa prevede l'articolo 250 del D.Lgs 231/2001 in materia di confisca per equi… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C062 | Negative: art inesistente | Quali sono gli obblighi del fornitore di sistemi di IA ad alto rischio previst… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C063 | Negative: art inesistente | Cosa stabilisce l'art. 75 del Regolamento NIS2 sulla cooperazione transfrontal… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C069 | Negative: corpus mancante | Quali sono i requisiti dello standard ISO/IEC 27701 per i sistemi di gestione … | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C070 | Negative: corpus mancante | Cosa stabiliscono le linee guida EDPB 5/2020 sul consenso ai sensi del GDPR? | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C071 | Negative: corpus mancante | Quali sono le condizioni stabilite dalla Direttiva ePrivacy (Direttiva 2002/58… | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C075 | Negative: omonimia numera | Cosa dice l'articolo 9 in materia di sanzioni? | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C076 | Negative: omonimia numera | Articolo 6 paragrafo 1: quali sono le condizioni elencate? | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |
| C077 | Negative: omonimia numera | Cosa stabilisce l'articolo 35 in materia di valutazione? | ∅ | — | 0.00 | 🟢 | zona nuova (norme non coperte da v1 o gold v2 ancora vuoto) |

## Aggregati overlap

| Flag | n candidate |
|---|---:|
| 🔴 ALTO (Jaccard ≥0.40)        | 0 |
| 🟡 MEDIO (Jaccard 0.20-0.39)   | 9 |
| 🟢 BASSO/zona nuova (<0.20)    | 73 |
| **Totale**                     | **82** |

### Per cluster

| Cluster | 🔴 | 🟡 | 🟢 | totale |
|---|---:|---:|---:|---:|
| 231 fattispecie oltre 24-bis | 0 | 0 | 5 | 5 |
| Codice Privacy mono-norma | 0 | 0 | 8 | 8 |
| Cross-norma 3+ norme | 0 | 0 | 8 | 8 |
| Cross-norma scenario 2 norme | 0 | 1 | 4 | 5 |
| Diritti dell'interessato GDPR | 0 | 1 | 5 | 6 |
| Edge: vaghe / mix | 0 | 0 | 3 | 3 |
| L. 132/2025 | 0 | 2 | 5 | 7 |
| NIS2 cross GDPR | 0 | 0 | 3 | 3 |
| NIS2 mono-norma | 0 | 1 | 11 | 12 |
| Negative: Garante UC4 | 0 | 0 | 3 | 3 |
| Negative: art abrogato Codice Privacy | 0 | 0 | 5 | 5 |
| Negative: art inesistente | 0 | 0 | 3 | 3 |
| Negative: corpus mancante | 0 | 0 | 3 | 3 |
| Negative: omonimia numerazione | 0 | 0 | 3 | 3 |
| Procedurali 'come si fa X' | 0 | 2 | 1 | 3 |
| Sanzionatorio puro | 0 | 2 | 3 | 5 |

## Candidate 🔴 ALTO — verifica in fase C

Nessuna candidate 🔴 ALTO. Tutte le candidate sono tematicamente distinte da v1 o solo parzialmente sovrapposte (🟡/🟢).
