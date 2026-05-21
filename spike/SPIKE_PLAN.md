# Spike Plan — Settimana 0

> Esperimento tecnico breve (1-2 giorni) per validare gli ingredienti del progetto
> **prima** di scrivere architettura o codice di produzione.
>
> Output atteso: 1 file `spike.py` funzionante + 1 file `SPIKE_RESULTS.md` con i findings.

---

## Cos'è uno spike (e cosa NON è)

Uno **spike** è codice **usa-e-getta** per rispondere a domande specifiche prima di prendere decisioni architetturali. Caratteristiche:

- **Breve**: 1-2 giorni totali, mai di più
- **Brutto**: nessuna struttura, nessun test, nessuna pulizia
- **Mirato**: 4 domande precise, non esplorazione "in generale"
- **Si butta via**: il codice spike NON entra nel progetto di produzione

**Lo spike NON è:**
- Un MVP (quello viene dopo, in settimane 1-7)
- L'inizio del progetto vero (il repo vero nasce in settimana 1)
- Un'occasione per "sistemare per bene" la pipeline (la pulizia viene dopo)

---

## Le 4 domande dello spike

Tutto lo spike risponde a queste 4 domande. Se una risposta è negativa, **fermarsi e ridiscutere lo stack** prima di procedere con l'MVP.

### Domanda 1 — Il parser Normattiva funziona sul nostro dominio?

**Verifica:** scaricare e parsare il **GDPR italiano consolidato** (Reg. UE 2016/679) usando [`ondata/normattiva_2_md`](https://github.com/ondata/normattiva_2_md).

**Cosa misurare:**
- Tutti gli articoli del GDPR sono presenti? (99 articoli + considerando)
- La struttura gerarchica è preservata? (Capi → Sezioni → Articoli → Commi → Lettere)
- I metadati URN-NIR sono disponibili? (necessari per le citazioni)
- Quali edge case emergono? (riferimenti incrociati, note, allegati)

**Criterio di accettazione:**
- ≥ 95% degli articoli estratti correttamente
- Struttura gerarchica navigabile programmaticamente
- URN o ID univoci per ogni articolo

**Output:** numero articoli estratti, struttura JSON di esempio (1 articolo intero), lista edge case.

**Se fallisce:** valutare fonti alternative (parsing diretto XML Akoma Ntoso da `dati.normattiva.it`, scraping HTML EUR-Lex).

---

### Domanda 2 — `BAAI/bge-m3` discrimina concetti legali italiani?

**Verifica:** encoding di 15 coppie di concetti italiani legali con misurazione cosine similarity.

**Coppie di test (esempi):**

| # | Concetto A | Concetto B | Atteso |
|---|---|---|---|
| 1 | "trattamento dei dati personali" | "elaborazione dei dati personali" | Alta similarità (sinonimi) |
| 2 | "responsabile del trattamento" | "data controller" | Alta similarità (IT/EN equivalenti) |
| 3 | "responsabile del trattamento" | "responsabile della protezione dei dati" | Media (ruoli diversi, dominio comune) |
| 4 | "DPIA" | "valutazione d'impatto sulla protezione dei dati" | Alta (sigla vs estesa) |
| 5 | "sistema ad alto rischio" | "sistema vietato" | Bassa-media (AI Act, categorie diverse) |
| 6 | "consenso esplicito" | "informativa privacy" | Bassa (concetti GDPR distinti) |
| 7 | "trasferimento extra-UE" | "data transfer outside EU" | Alta |
| 8 | "Garante Privacy" | "Autorità di Controllo" | Alta |
| 9 | "minore di 14 anni" | "trattamento di dati di minori" | Media |
| 10 | "cookie tecnici" | "cookie di profilazione" | Media-bassa |

**Cosa misurare:**
- Score di similarità coerenti con l'atteso?
- Modello distingue sigle da forme estese (DPO, DPIA)?
- Funziona su mix IT/EN (legale italiano usa molto inglese)?

**Criterio di accettazione:**
- ≥ 12/15 coppie restituiscono similarity coerente con l'atteso
- Sigle riconosciute come equivalenti alle forme estese

**Se fallisce:** valutare embedding alternativi (`intfloat/multilingual-e5-large-instruct`, embedding fine-tuned su corpus italiano legale).

---

### Domanda 3 — `Minerva-7B-instruct` è usabile su hardware locale?

**Verifica:** setup Ollama + pull Minerva-7B + 5 prompt italiani legali semplici.

**Setup:**
1. Installare Ollama
2. `ollama pull sapienzanlp/minerva-7b-instruct` (o nome modello disponibile)
3. Verificare versione, quantizzazione disponibile

**Prompt di test:**

1. *"Spiega in 100 parole l'art. 5 del GDPR (principi del trattamento)."*
2. *"Cosa è una DPIA? Quando è obbligatoria?"*
3. *"Differenza tra Titolare e Responsabile del trattamento ai sensi del GDPR."*
4. *"Riassumi in 3 punti i sistemi ad alto rischio secondo l'AI Act."*
5. *"Come si applica il D.Lgs 231/2001 alle decisioni automatizzate?"*

**Cosa misurare:**
- **Latenza time-to-first-token (TTFT)**: secondi
- **Latenza totale per risposta di ~200 parole**: secondi
- **Token/secondo** generazione
- **Qualità risposta** (valutazione qualitativa 1-5):
  - Risposta in italiano corretto?
  - Contenuto fattualmente corretto?
  - Allucinazioni evidenti?
  - Stile professionale appropriato?

**Criterio di accettazione:**
- TTFT < 5s, latenza totale risposta < 30s
- Qualità qualitativa ≥ 3/5 (utilizzabile con prompt engineering)
- Italiano scorrevole, senza errori grammaticali grossolani

**Se fallisce:**
- Se troppo lento → testare `LLaMAntino-3-ANITA-8B` quantizzato Q4, oppure `Maestrale-7B`, oppure `Mistral-7B-Instruct` italiano-aware
- Se qualità scarsa → testare modelli più grandi, valutare se fallback obbligatorio su LLM cloud per la demo pubblica (Minerva resta come opzione self-host)

**Hardware di riferimento per il test:**
- Macchina principale di Federico (verificare RAM/GPU disponibile)
- Eventualmente NAS Debian se RAM sufficiente (~6GB per Q4 a 7B)

---

### Domanda 4 — End-to-end: la pipeline minima produce una risposta sensata?

**Verifica:** assemblare i 3 componenti precedenti in un mini-RAG di 50 righe.

**Pipeline:**
1. Parsare il GDPR (output Domanda 1) → lista di chunk (1 chunk = 1 articolo)
2. Embeddare tutti i chunk con bge-m3 (Domanda 2)
3. Query: *"Quali sono i principi del trattamento dei dati personali?"*
4. Trovare i top-3 chunk più simili (cosine similarity)
5. Costruire prompt minimal: `"Rispondi citando l'articolo. Contesto: {chunks}. Domanda: {query}"`
6. Inviare a Minerva via Ollama (Domanda 3)
7. Stampare risposta

**Cosa misurare:**
- Il top-1 retrievato è davvero l'art. 5 GDPR?
- La risposta cita correttamente l'art. 5?
- La risposta include allucinazioni evidenti?
- Quanto è naturale leggere il risultato?

**Criterio di accettazione:**
- Top-1 retrieval = articolo corretto
- Risposta cita correttamente l'articolo
- Niente allucinazioni evidenti su una query semplice
- "Sembra usabile" come prima impressione qualitativa

**Output:** screenshot/log della prima Q&A end-to-end. Questo è il **primo successo** del progetto, da salvare per il futuro articolo tecnico.

---

## Cosa NON è nello spike

Lista esplicita di cose **da NON fare** in spike (rimandate a settimana 1+):

- ❌ Qdrant o altro vector DB (per spike basta numpy + cosine similarity in-memory)
- ❌ Reranker
- ❌ FastAPI, Streamlit, qualunque UI
- ❌ Docker, docker-compose
- ❌ CI/CD, test automatici
- ❌ Scraping del Garante (docweb)
- ❌ AI Act (lo spike usa solo GDPR per semplicità)
- ❌ Citation verifier
- ❌ LangGraph (per spike basta una funzione Python che chiama Ollama)
- ❌ Knowledge graph
- ❌ Hybrid retrieval (BM25 + dense): solo dense
- ❌ Multi-normativa, cross-reference
- ❌ Setup repo "vero" (basta una cartella `spike/` temporanea)

---

## Struttura attesa del codice spike

Singolo file Python, ~150-250 righe, organizzato in 4 sezioni numerate corrispondenti alle 4 domande.

```
spike/
├── spike.py                 # Tutto qui dentro, in 4 sezioni
├── requirements_spike.txt   # dipendenze minimali
├── data/
│   └── gdpr_parsed.json     # output Domanda 1, caching
└── SPIKE_RESULTS.md         # findings finali (markdown)
```

**Dipendenze minimali:**
- `normattiva_2_md` (o equivalente)
- `sentence-transformers` (per bge-m3)
- `numpy` (per cosine similarity)
- `ollama` (client Python)
- niente altro

---

## Cosa scrivere in `SPIKE_RESULTS.md`

Dopo lo spike (max 1 ora di scrittura), produrre un documento markdown con:

1. **Date e tempo impiegato** (per benchmark futuro)
2. **Hardware utilizzato** (RAM, GPU, OS)
3. **Risposte alle 4 domande**: PASS / FAIL / PARTIAL, con dati numerici
4. **Edge case incontrati** (lista cruda)
5. **Decisioni che derivano dallo spike** (es. "Minerva troppo lento → useremo LLaMAntino")
6. **Aggiornamenti a SCOPE.md o ARCHITECTURE.md necessari**

Questo documento diventa input per la settimana 1.

---

## Tempo stimato per lo spike

| Attività | Tempo |
|---|---|
| Setup ambiente (venv, install Ollama, pull modello) | 1-2h |
| Domanda 1 — Parser Normattiva | 2-3h |
| Domanda 2 — Embedding bge-m3 | 1-2h |
| Domanda 3 — Minerva via Ollama | 2-3h |
| Domanda 4 — End-to-end | 1-2h |
| Scrittura SPIKE_RESULTS.md | 1h |
| **Totale** | **8-13h** (1-2 giornate piene) |

**Se sfora oltre 2 giorni:** tornare in chat Claude.ai e ridiscutere — probabile problema con uno dei componenti che merita decisione architetturale.

---

## Decisione: dove fare lo spike

**Suggerimento:** fare lo spike sulla macchina principale di Federico (non sul NAS), perché:
- Iterazione più rapida (no SSH overhead)
- Più facile vedere output, log, errori
- Il NAS resta libero per Meridian e altri progetti

Il **deploy** del progetto vero su NAS verrà valutato in settimana 6-8 dopo MVP.

---

## D7 (mini-spike post-hoc) — Accesso EUR-Lex per GDPR e AI Act

**Aggiunta dopo D6.** Le 4 domande originali presupponevano implicitamente che le norme UE (GDPR vero, AI Act) fossero accessibili in formato XML analogo a quello di Normattiva. D7 valida questa assunzione.

**Verifica:** test di endpoint Akoma Ntoso su `eur-lex.europa.eu` per due CELEX (`32016R0679`, `32024R1689`); se assente, valutare Formex 4 via Cellar; se anche Formex problematico, valutare HTML rendering o PDF.

**Vincoli:** max 1 ora, niente refactoring, codice esplorativo (shell + lxml inline, non in `spike.py`).

**Output:** `spike/EURLEX_FINDINGS.md` con:
- Disponibilità AKN per ciascun documento
- Disponibilità Formex e complessità di accesso
- Raccomandazione fra le tre opzioni:
  - (a) estendere `italian_legal_parser` come adapter AKN EUR-Lex
  - (b) creare `eur_lex_parser` separato per Formex
  - (c) fallback Docling + PDF

**Trigger di esito:** se nessuna delle opzioni è praticabile entro un orizzonte di 1 settimana di lavoro, ridiscutere il corpus (rimuovere normativa UE dal v1?).

---

## Prossimo passo dopo lo spike

In ordine:

1. ✅ Spike completato + `SPIKE_RESULTS.md` scritto
2. ⏳ Rilettura di `SCOPE.md` alla luce dello spike (eventuali aggiornamenti)
3. ⏳ Scrittura di `ARCHITECTURE.md` ancorato alla realtà dello spike
4. ⏳ Setup del repo vero su GitHub (`italian-legal-rag`)
5. ⏳ **Settimana 1** inizia: ingestion normativa primaria seria (GDPR + Codice Privacy + AI Act + 231 + NIS2)
