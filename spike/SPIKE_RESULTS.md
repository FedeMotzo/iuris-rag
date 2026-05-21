# Spike Results — Settimana 0

> Aggregato dei finding delle 6 sezioni dello spike tecnico.
> Lo spike è codice usa-e-getta: i file in `spike/` NON entrano nell'MVP.

---

## Setup

- **Data inizio / fine:** 2026-05-16 (giornata singola)
- **Tempo totale impiegato:** ~3h (rispetto a stima del piano: 8-13h → significativamente sotto)
- **Hardware:** Mac mini M4 Pro, 24 GB RAM, macOS 26.3.1, GPU Apple Silicon via MPS
- **Ambiente:** Python 3.12 in `spike/.venv`, `normattiva2md` 2.1.10, `sentence-transformers` 5.5.0, `torch` 2.12.0 (MPS attivo), `ollama` 0.17.7

---

## D1 — Parser Normattiva ⚠️ PARZIALE

**Obiettivo:** verificare che `ondata/normattiva_2_md` parsi il Codice Privacy (D.Lgs 196/2003) — sostituto operativo del GDPR (che è UE, non su Normattiva).

**Esito complessivo:** **PARTIAL** — utilizzabile per lo spike, due caveat noti rimandati a D6.

**Numeri chiave:**

| Metrica | Valore |
|---|---|
| Output MD | 405 KB, 2223 righe |
| Articoli unici (per numero) | 214 |
| Articoli totali (con duplicati negli allegati) | 315 |
| Articoli nel corpo principale | 214 |
| Articoli negli allegati (codici deontologici) | 101 |
| Header H2 (Titoli/Capi) | 59 |
| Articoli con note di aggiornamento | 15 |
| Articoli completamente vuoti | 0 |

**Verifica criteri del piano:**
- ✅ ≥ 95% articoli estratti — niente vuoti, multi-comma e suffissi `bis/ter` riconosciuti correttamente (Art. 2-ter ha 5 commi tutti catturati)
- ⚠️ Struttura gerarchica navigabile — gli articoli (H3) sì; Parte/Titolo/Capo/Sezione **schiacciati in unico H2** (es. `## DISPOSIZIONI GENERALI - - TITOLO I (( PRINCIPI E DISPOSIZIONI GENERALI CAPO I (...) ))`)
- ❌ URN/ID univoci per articolo — il front matter ha URN solo a livello documento, non per articolo

**Edge case raccolti:**
- Modifiche legislative `((...))` inline → rumore per embedding, da pulire
- Titoli `((ABROGATI))` ma testo presente → da filtrare in MVP
- Codici deontologici negli allegati con numerazione propria che ricomincia da 1 → chunk_id deve includere path completo
- Note di aggiornamento `AGGIORNAMENTO (N)` annidate dopo i commi
- Apostrofi al posto degli accenti (`Autorita'` per `Autorità`) — codifica Normattiva
- Periodi soppressi `((PERIODO SOPPRESSO DAL D.L. ...))` interni ai commi

**Decisione derivata:** i due caveat (URN granulari + gerarchia schiacciata) vengono affrontati in D6 con valutazione dell'XML AKN diretto.

**Artefatti:** [data/codice_privacy.md](data/codice_privacy.md), [data/codice_privacy_parsed.json](data/codice_privacy_parsed.json)

---

## D2 — Embedding `BAAI/bge-m3` ⚠️ PARZIALE

**Obiettivo:** verificare che bge-m3 discrimini concetti legali italiani su 15 coppie con classificazione attesa alto/medio/basso.

**Esito complessivo:** **PARTIAL** — il modello base fallisce sulle sigle del dominio; con instruction prefix risolve le sigle ma altera la scala assoluta delle soglie.

**Numeri chiave:**

| Modalità | Coppie coerenti / 15 | Verdetto piano |
|---|---|---|
| Base (no prompt) | 8 | FAIL |
| Con instruction IT | 8 | FAIL |
| Con instruction EN | 8 | FAIL |

Aritmeticamente lo stesso punteggio, ma con composizione opposta:
- **Base** fallisce sulle 5 coppie sigla↔forma-estesa (DPIA 0.378, DPO 0.455, Garante↔Autorità Controllo 0.448, AI Act 0.639, resp. trattamento↔data controller 0.566). Sinonimi linguistici e IT/EN funzionano.
- **Con prompt** le sigle vengono recuperate tutte (>0.75) ma **tutte le similarity si alzano in blocco di ~0.15-0.30**, facendo saltare le soglie per le coppie medie/basse.

**Pattern dominante:** bge-m3 non riconosce nativamente le sigle del diritto italiano. Con instruction prefix la conoscenza emerge ma la scala assoluta delle similarity non è più calibrata sulle soglie del piano (0.55/0.75).

**Tempi (M4 Pro, MPS, float32):**
- Caricamento modello (prima volta + download 3.1 GB): 283.8 s
- Caricamento modello (cache HF): 5.6 s
- Encoding: ~92 ms per coppia, ~46 ms per frase

**Decisione derivata:** per il retrieval in RAG conta il **ranking** (top-k), non le soglie binarie. La domanda vera diventa "il chunk giusto è in top-1?" → questione di D4. Per MVP: usare bge-m3 **con instruction prefix italiano** e valutare per ranking + ipotizzare hybrid (BM25 per match esatti sulle sigle).

**Artefatti:** [data/embedding_results.json](data/embedding_results.json), [data/embedding_results_prompts.json](data/embedding_results_prompts.json)

---

## D3 — Minerva-7B via Ollama 🟢 PASS / 🟡 PARTIAL (in v2)

**Obiettivo:** verificare latenza e qualità di `hf.co/sapienzanlp/Minerva-7B-instruct-v1.0-GGUF:Q6_K` su 5 prompt italiani legali. Target piano: TTFT < 5s, latenza < 30s, qualità ≥ 3/5.

**Esito complessivo:** **PASS** sul lato latenza, qualità sufficiente con caveat fattuali su dettagli normativi.

**Numeri chiave:**

| Metrica | v1 (no system) | v2 (con system + chat template) |
|---|---|---|
| TTFT media | 0.20 s | 3.69 s |
| TTFT max | 0.20 s | 15.58 s ¹ |
| Latenza media | 4.03 s | 13.29 s |
| Latenza max | 6.23 s | 25.14 s |
| Tok/s media | 37.1 | 24.4 |
| Verdetto latenza | PASS | PARTIAL (TTFT max sopra target) |
| Stop tokens `>|im_end|>` filtrati | 1 occorrenza | 0 ✓ |

¹ Il TTFT outlier 15.58s di v2 era con job parallelo Ollama in concorrenza (v2 girava insieme alla Sezione 4). I 4 prompt restanti hanno TTFT < 1.6 s.

**Qualità (valutazione mia, da convalidare):**
- v1: Art. 5 GDPR → 5 principi su 7 (mancano "esattezza" e "limitazione finalità"); AI Act → confonde "alto rischio" con "vietati" (sorveglianza di massa, punteggio sociale); 231/2001 → risposta generica
- v2: Art. 5 GDPR → **tutti e 7 i principi correttamente elencati**; risposte più articolate; manca però il Responsabile nella distinzione con il Titolare; AI Act → persiste l'errore "punteggio sociale = alto rischio" (è vietato)

**Edge case e bug:**
- Chat template ChatML del modello: `<|im_start|>...<|im_end|>`. Senza system message arrivano token speciali non filtrati in output (`>|im_end|>` visto in 1/5 prompt v1)
- Capability registrata in Ollama: `completion` (non `chat`) → comportamento fragile senza prompt strutturato
- Su prompt diretti corti il modello risponde bene; degenera su prompt strutturati complessi (vedi D4)
- Context length modello: **4096 token max** (Ollama dichiara 4096)

**Decisione derivata:** Minerva resta candidato come LLM locale ma con vincoli operativi (system message obbligatorio, post-processing stop tokens, repeat_penalty). Vero verdetto dalla D4 end-to-end.

**Artefatti:** [data/minerva_results.json](data/minerva_results.json), [data/minerva_results_v2.json](data/minerva_results_v2.json)

---

## D4 — End-to-end Mini-RAG 🟢 retrieval / 🟡 generation

**Obiettivo:** assemblare bge-m3 + Minerva in pipeline RAG sul Codice Privacy. 3 query di test.

**Esito complessivo:** **retrieval PASS, generation PARTIAL** — pipeline usabile per dimostrazione, generation con limiti.

**Numeri chiave:**

| Metrica | Valore |
|---|---|
| Chunk indicizzati (corpo, non abrogati) | 105 |
| Tempo medio embedding per chunk | ~133 ms (best run, ~343 ms con job parallelo) |
| Tempo medio query end-to-end | ~16.7 s |

**Top-1 retrieval per query (bge-m3 + instruction prefix IT):**

| Query | Top-1 | Score |
|---|---|---|
| Principi del trattamento dei dati personali | Art. 1 "Oggetto" (rinvia al GDPR) | 0.755 |
| Compiti del responsabile della protezione dei dati | **Art. 2-sex-decies** "RPD per autorità giudiziarie" | 0.785 |
| Quando il Garante può applicare sanzioni amministrative | **Art. 166** "Criteri sanzioni amministrative" | 0.783 |

→ Retrieval recupera l'articolo giusto in top-1 su 3/3 query. Sulla sigla DPO/RPD (Q2) il prefix-IT funziona perfettamente: 0.785, l'articolo corretto. Senza prefix la stessa coppia DPO↔RPD valeva 0.455.

**Bug scoperti (e fix applicati):**
1. **`num_ctx` default Ollama = 2048** → Art. 166 da solo (~3000 token) eccedeva il context → modello faceva text completion del prompt invece di rispondere. Una query è andata in runaway: 180.818 caratteri in 1205 s. Fix: `num_ctx=16384` (ma il modello è capped a 4096 nativo) + `num_predict=512`.
2. **Chat template applicato male senza system message** → il modello rifletteva l'eco del prompt user. Fix: `messages=[{"role":"system",...},{"role":"user",...}]`.
3. **Chunk troppo lunghi** → troncamento a 1800 caratteri per stare comodi nel context. (Trade-off di completezza vs spazio context.)

**Pattern di degenerazione di Minerva su RAG (3/3 query):**
- Le risposte **iniziano correttamente** citando gli articoli del contesto recuperato
- Dopo 100-300 token degenerano:
  - **Repetition loop**: Q1 ripete 25× "La responsabilità dell'organismo che tratta..."
  - **Hallucination cross-norma**: Q2 cita "art. 38 / 39 GDPR" non presenti nel contesto
  - **Echo del contesto**: Q3 riproduce verbatim i commi 1-7 dell'Art. 166 invece di rispondere

**Decisione derivata:** la pipeline funziona, il bottleneck è il generatore. Si è aperta una D4-bis di confronto LLM.

**Artefatti:** [data/e2e_results.json](data/e2e_results.json)

---

## D5 (4-bis) — Confronto Minerva-7B vs Qwen2.5-14B 🟢 PASS per Qwen

**Obiettivo:** capire se i pattern di degenerazione della D4 dipendono dal modello o dal prompt/retrieval. Stesse 3 query, stesso retrieval, stessi parametri Ollama.

**Esito complessivo:** i tre pattern di degenerazione sono **del modello, non del prompt** — Qwen2.5-14B con la stessa pipeline si comporta in modo nettamente più sobrio.

**Aggregati:**

| Metrica | Minerva-7B | Qwen2.5-14B |
|---|---|---|
| TTFT media | 5.08 s | 8.01 s |
| Latenza media | 13.73 s | 11.81 s |
| Tok/s | **36.3** | 25.9 |
| Tokens output medi | 314 | **96** |
| Special tokens residui (Q con `had_special_tokens=True`) | 2/3 | 0/3 |

Minerva è ~40% più veloce in tok/s ma Qwen è più rapido in latenza totale perché risponde in modo conciso (~3.3× più corto).

**Comportamento per query:**

| Q | Minerva | Qwen |
|---|---|---|
| Q1 principi | Repetition loop (25× la stessa frase) fino al cap di 512 token | **"Il contesto non specifica i principi, sono nell'Art. 5 GDPR"** — riconosce il limite del retrieval |
| Q2 compiti DPO | Cita articoli corretti **ma hallucina** "art. 38/39 GDPR" non nel contesto | **"Non trovo riferimenti nel testo fornito"** — onesto |
| Q3 sanzioni | Riassume comma 1 dell'Art. 166 ma residui di stop token | **"Secondo l'Art. 166, comma 3..."** — citazione precisa, conclusione corretta |

**Insight chiave:** Qwen2.5-14B mostra il comportamento RAG corretto out-of-the-box: usa solo le informazioni del contesto, ammette quando mancano, non ripete, non hallucina. Minerva richiederebbe `repeat_penalty` + post-processing + monitor di qualità per arrivare a un livello comparabile.

**Decisione derivata:** **LLM locale default per MVP → Qwen2.5-14B**. Minerva-7B resta come alternativa opzionale per chi voglia stack truly-open italiano.

**Artefatti:** [data/comparison_minerva_vs_qwen.json](data/comparison_minerva_vs_qwen.json)

---

## D6 — XML Akoma Ntoso diretto da Normattiva 🟢 PASS

**Obiettivo:** capire se l'XML AKN nativo da `dati.normattiva.it` risolve i due caveat della D1 (URN granulari mancanti + gerarchia schiacciata).

**Esito complessivo:** **PASS netto** — XML AKN da preferire al Markdown per l'MVP.

**Verifica 1 — Accesso:**
- ✅ HTTP 200, `Content-Type: text/xml`, **1.5 MB** (3.7× il MD), tempo totale <2 s
- Dance di sessione: GET pagina-norma → estrai `href="...caricaAKN..."` dall'HTML (NON ricostruire l'URL manualmente: `dataVigenza` ha più formati nell'HTML) → GET con `Referer: https://www.normattiva.it/`

**Verifica 2 — Struttura AKN:**
- ✅ Root `akomaNtoso`, namespace `http://docs.oasis-open.org/legaldocml/ns/akn/3.0` (standard OASIS LegalDocML 3.0)
- ✅ **221 `<article>`** (vs 214 unici del MD → l'XML ne ha 7 in più; probabili articoli che il parser MD aveva confuso)
- ✅ **eId Art. 2-bis = `"art_2-bis"`** → URN granulare nativo per ogni articolo
- ✅ doc_urn: `/akn/it/act/decreto_legislativo/stato/2003-06-30/196`
- ✅ Path gerarchico esplicito: `akomaNtoso → act → body → chapter → article` (chapter=57, section=2 — tag separati, non concatenati come nei H2 del MD)

**Caveat emersi anche dall'XML:**
- `<mod>` tags: **0** → in questo file le modifiche legislative `((...))` NON sono marcate con tag XML strutturati. Sono inline nel testo come nel MD. Verificare su altre norme.
- `<quotedStructure>` tags: 0 — idem
- 289 occorrenze testuali di "abrogat" senza un attributo strutturato `@status="repealed"` → marker da riconoscere a parser-level
- Profondità varia per norma: il Codice Privacy ha `body → chapter → article` senza `<part>` né `<title>`. Altre norme possono averli; parser deve essere flessibile.

**Verifica 3 — Librerie Python:**
- 10 candidati cercati su PyPI: 9 fantasmi (`akoma-ntoso-python`, `akomantoso`, `python-akn-parser`, `cellar-parser`, `akn-parser`, `akn`, `lexml-parser`, `akoma`, `indigo-akn` — tutti non esistono o irrintracciabili)
- Solo `lexnlp` v2.3.0 esiste, ma è una libreria NLP legale generica con **licenza AGPL** (copy-left, problematica per progetto commerciale)
- **Strada principale: parser custom XPath con `lxml`**, stima 4 ore

**Decisione derivata:** passare a XML AKN come fonte primaria per il parser. Tenere `normattiva2md` come fallback se Normattiva cambia formato.

**Artefatti:** [data/codice_privacy_akn.xml](data/codice_privacy_akn.xml), [data/akn_report.json](data/akn_report.json)

---

## Decisioni architetturali aggregate

| Componente | Pre-spike | Post-spike | Motivazione |
|---|---|---|---|
| **Parser normativo** | `normattiva2md` (Markdown) | **XML Akoma Ntoso diretto** via session-based fetch + parser custom XPath (`lxml`) | URN granulari nativi (`eId="art_2-bis"`) + gerarchia esplicita (chapter/section/...); risolve due caveat D1 al costo di ~4h |
| **LLM locale default** | Minerva-7B-instruct | **Qwen2.5-14B (Q4_K_M)** | D5 mostra che Qwen non degenera, non hallucina, ammette il limite del retrieval; Minerva richiederebbe `repeat_penalty` + monitor + post-processing per arrivare a livello comparabile |
| **LLM locale alternativo** | LLaMAntino-3-ANITA-8B | **Minerva-7B + LLaMAntino** | Minerva rimane come alternativa "truly-open italiano" per chi voglia quello stack; LLaMAntino non testato in spike, resta nelle opzioni del piano |
| **Embedding** | `BAAI/bge-m3` | `BAAI/bge-m3` **+ instruction prefix italiano** obbligatorio | Senza prefix le sigle del dominio (DPIA, DPO, AI Act, Garante) hanno similarity 0.38-0.64; con prefix vanno a >0.75. Confermato dal retrieval D4. |
| **Recupero ibrido** | BM25 + dense | (invariato) — ora con motivazione esplicita | Le sigle del dominio sono il caso d'uso esatto in cui BM25 (match esatto su token) integra il dense retrieval |
| **Ollama options** | Default | `num_ctx=16384` (o 4096 per Minerva), `temperature=0.2`, `num_predict=512`, `repeat_penalty=1.15` (per Minerva), system message **obbligatorio**, post-filter degli stop tokens | Bug scoperti in D3 e D4 |

---

## Da rifare in MVP (codice spike da NON riusare)

Tutto in `spike/` è scaffold usa-e-getta. Cosa va riscritto bene:

1. **Parser**: lo script Python in `spike/spike.py` Sezione 1 parsa Markdown con regex. Nell'MVP servirà parser XPath/lxml su XML AKN. Modulo `core/italian_legal_parser/` da scratch.
2. **Indicizzazione**: in `spike/spike.py` Sezione 4 i chunk sono in-memory numpy array. In MVP serve Qdrant + persistenza + chunking strategy seria (articolo intero non basta per articoli da 3000 token come Art. 166: serve splitting in commi rispettando l'URN).
3. **Filtro abrogati**: ora è regex su `"ABROGATO"` nel testo. Va sostituito con logica strutturata appena si valuta `<lifecycle>` AKN o tag equivalenti.
4. **Citazione articoli**: ora si concatena URN documento + numero articolo a mano. Nell'MVP si usa l'`eId` nativo dell'XML AKN.
5. **Prompt template RAG**: ora hardcoded in `spike.py`. In MVP serve sistema di prompt versionati con jinja2 o equivalente.
6. **Post-processing LLM**: il filtro `_strip_stop_tokens` è inline. In MVP va incapsulato in un wrapper LLM unificato che gestisca pulizia + retry + validazione citazioni.
7. **Embedding caching**: ogni run dello spike ri-encoda i chunk. In MVP gli embedding vanno persistiti in Qdrant.
8. **Sessione Normattiva**: la dance HTTP è in 30 righe inline. Va estratta in un client `NormattivaClient` con rate-limit, retry, gestione errori, persistenza cache.

---

## Rischi residui per MVP (cose che lo spike NON ha coperto)

1. **Multi-normativa**: lo spike ha usato solo Codice Privacy. AI Act è su EUR-Lex (XML diverso da AKN Normattiva, formato Formex). D.Lgs 231/2001 e NIS2 hanno strutture probabilmente diverse. Il parser AKN va validato su tutte le norme primarie del corpus.
2. **Modifiche legislative `((...))`**: nell'XML AKN testato sono inline come nel MD, non strutturate in `<mod>`. Decidere caso per caso se mantenerle nel testo (RAG) o filtrarle (per UI/UX). Da verificare su altre norme se il formato è omogeneo.
3. **Articoli abrogati**: nessun attributo strutturato `@status="repealed"`; riconoscimento solo testuale. Su 289 occorrenze nel Codice Privacy serve una euristica robusta.
4. **Provvedimenti Garante (docweb)**: non sono in formato AKN. Scraping HTML ad-hoc, fuori dallo spike.
5. **Reranker**: non testato. Il piano lo include (`BAAI/bge-reranker-v2-m3`) ma il suo impatto su queste query non è misurato.
6. **Hybrid retrieval BM25+dense**: solo dense testato. BM25 dovrebbe aiutare sulle sigle, ma non c'è misura empirica.
7. **Citation verifier**: non testato. Q2 in D4 con Minerva ha hallucinato "art. 38 GDPR" — un verifier l'avrebbe bloccato? Da provare.
8. **Latenza con corpus reale**: lo spike ha 105 chunk. MVP avrà migliaia di chunk (5 norme primarie + provvedimenti Garante). Tempo retrieval probabilmente cresce, da misurare.
9. **Qualità Qwen su query realmente difficili**: D5 ha 3 query semplici. Qualità di Qwen su domande multi-normativa (es. "FRIA vs DPIA") non testata.
10. **Eval Ragas/Langfuse**: zero misurazione nello spike. Faithfulness e citation accuracy del piano (target ≥ 0.85 e ≥ 0.95) sono da costruire da zero.
11. **Context window Minerva (4096)**: se davvero rimane come alternativa, è un vincolo duro. Per AI Act ed altre norme corpose i prompt RAG vanno tagliati aggressivamente.
12. **Chat template Ollama per modelli HF GGUF**: ho visto fragilità su Minerva. Per Qwen out-of-the-box ha funzionato, ma su altri modelli HF GGUF (es. LLaMAntino) potrebbero ricomparire problemi simili.

---

## Aggiornamenti necessari a SCOPE.md

Vedi `SCOPE.md` sezione "Registro modifiche allo scope", riga 2026-05-16: aggiornamento dello stack LLM locale e del parser normativo a seguito di questo spike.

## ARCHITECTURE.md

Non scritto. Verrà redatto dopo settimana 1 con dati di implementazione vera, non sulla base dello spike.
