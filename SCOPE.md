# SCOPE — Iuris RAG (working name)

> Contratto interno con me stesso. Quando viene voglia di aggiungere feature, riaprire questo file.
> Modifiche allo scope richiedono giustificazione scritta in fondo al documento.

---

## Obiettivo

Costruire un **core RAG italiano riusabile** (libreria `pip`-installabile) + una **demo verticale su AI Act / compliance** che funzioni in produzione locale.

**Priorità in ordine:**
1. Apprendimento tecnico (RAG italiano serio, eval, observability)
2. Portfolio (artefatto dimostrabile per attrarre clienti freelance AI)
3. Riuso futuro su secondo verticale (fiscale al mese 4-6)

**NON è priorità ora:** validazione mercato, monetizzazione, adozione open source di massa.

---

## Vincoli

- **Tempo totale:** 8 settimane, ~30h/settimana = ~240h
- **Budget infrastruttura:** <€500
- **Solo dev:** 1 persona (io)
- **Lingue:** solo italiano in v1
- **Deploy:** Docker Compose su NAS personale + opzione cloud LLM configurabile

**Regola dura:** se a settimana 4 sono al <30% del piano, taglio scope, non aggiungo settimane.

---

## I 5 use case di riferimento ("test set vivente")

Ogni decisione tecnica si valuta contro questi. Se una feature non aiuta a rispondere meglio a questi 5, fuori scope.

1. **Classificazione AI Act:**
   *"Il mio chatbot HR che fa screening CV è high-risk secondo AI Act?"*
   → classificazione rischio + obblighi correlati

2. **Timeline obblighi:**
   *"Quali sono le scadenze AI Act per un sistema di credit scoring?"*
   → estrazione cronologica obblighi + countdown deadline

3. **Distinzione DPIA vs FRIA:**
   *"Devo fare DPIA o FRIA per questo use case?"*
   → reasoning multi-normativa GDPR + AI Act

4. **Ricerca su provvedimenti Garante:**
   *"Cosa dice il Garante sul riconoscimento facciale nei luoghi di lavoro?"*
   → retrieval su corpus docweb + citazione provvedimento esatto

5. **Multi-normativa 231 + AI:**
   *"Quali obblighi 231 si attivano se uso AI per decisioni HR?"*
   → reasoning su D.Lgs 231/2001 + GDPR + AI Act

---

## Componenti core riusabili (libreria `core/`)

Estratti come pacchetto `pip`-installabile, indipendenti dal verticale.

### 1. `italian_legal_parser`
Parser Akoma Ntoso → chunk gerarchici (articolo / comma / lettera) con preservazione URN-NIR e metadati (data vigenza, rubrica). Riusa `ondata/normattiva_2_md` come dipendenza dove possibile.

### 2. `hybrid_retriever`
Retrieval ibrido plug-and-play:
- BM25 (Postgres FTS o tantivy)
- Dense embedding (default: `BAAI/bge-m3`)
- Fusion via Reciprocal Rank Fusion
- Reranker (default: `BAAI/bge-reranker-v2-m3`)
- API neutrale rispetto al vector store (supporto Qdrant + pgvector)

### 3. `citation_verifier`
Validazione strutturale deterministica: ogni marker `[cite:CHUNK_ID]` nell'output LLM è verificato contro il set di chunk_id del contesto retrieval. Politica v1 **soft warning**: i marker non verificati vengono annotati inline come `[cite:X NON VERIFICATA]`, mai rimossi. Hard block / hard fail fuori scope v1. Faithfulness semantica (LLM-as-judge sul contenuto del chunk citato) resta a Ragas settimana 7. Il rendering human-readable dei chunk_id (`GDPR art. 35`, `D.Lgs 196/2003 art. 2-sex-decies`) è in un modulo separato `core/citation_renderer` da settimana 5 — decisione di formato user-facing presa quando si vede l'output LLM reale.

### Componenti complementari

**`core/terminology`** (W4) — query expansion via lookup table (`aliases.yaml`). Sigle e forme estese (FRIA, DPIA, scoring creditizio) espanse pre-retrieval su entrambi i canali dense/sparse. 3 alias iniziali, estensione governata dalla regola "nuovo alias solo se una query del benchmark lo giustifica".

**`core/normative_graph`** (W4) — graph multi-normativa statico curato a mano (`graph.yaml`) per espansione del contesto retrieval cross-norma. Architettura A: espansione 1-hop bidirezionale a valle di `hybrid_retriever`, prima del passaggio all'LLM. Nessuna chiamata LLM, nessun tool calling, nessun multi-hop. Cap 5 chunk espansi per query, deterministico. I chunk espansi sono "bonus context" — le metriche di retrieval R@K/MRR/NDCG restano calcolate sul top-K originale. Integrazione in `HybridRetriever.retrieve(graph_links=...)` opzionale e backward-compatible. Disclaimer "not legally validated, refinement in v1.1" nel YAML. Estensione del catalogo da 6 link iniziali a ~30 è lavoro manuale post-prompt; validazione legale formale e UI di editing rimandate a v1.1 (vedi `ROADMAP_POST_V1.md`).

---

## Metriche di "fatto" (criteri di accettazione v1)

Misurate su set di **≥100 Q&A gold-standard** validati manualmente,
derivati dai 5 use case di riferimento (UC4 in v1.1, vedi sopra).

| Metrica | Soglia v1 | Tool |
|---|---|---|
| Faithfulness (RAGAS) | ≥ 0.85 | Ragas |
| Context precision (RAGAS) | ≥ 0.80 | Ragas |
| Answer relevancy (RAGAS) | ≥ 0.80 | Ragas |
| Citation accuracy | ≥ 0.95 | custom (verifier) |
| Latenza P50 con LLM cloud (Anthropic Sonnet 4.6) | < 3s | smoke RAG completo |
| Coverage dei use case | 4/5 risposte qualitativamente accettabili (UC4 v1.1) | review manuale |

**Definizione di "fatto":** tutte le soglie raggiunte sul benchmark
≥100 query + repo pubblico con README bilingue + 1 articolo tecnico
pubblicato.

---

## Stack tecnico (deciso, non rinegoziabile in v1)

| Layer | Scelta | Note |
|---|---|---|
| Lingua principale | Python 3.11+ | |
| Parser XML normativo | XML Akoma Ntoso diretto da Normattiva via session-based fetch + parser custom XPath (`lxml`) | `normattiva_2_md` come fallback. Decisione post-spike (2026-05-16): URN granulari e gerarchia nativi nell'XML. |
| Parser EUR-Lex | `core/eur_lex_parser` (HTML rendering, dual-template initial+consolidated) | Decisione post-settimana 1: HTML scelto vs Formex (Cellar SPARQL) e vs AKN (non disponibile su EUR-Lex). Considerando estratti dal template iniziale, articoli dalla consolidata quando esiste. |
| Client EUR-Lex | `core/eur_lex_client` (cache stratificata per lingua, guard contro body vuoto) | AWS WAF challenge bloccante al 2026-05-18, workaround corpus statico via download manuale. Post-v1: Cellar SPARQL endpoint. |
| Parser PDF | Docling (IBM) | Fallback OCR: PaddleOCR 3 |
| Embedding | `BAAI/bge-m3` | Multilingue, hybrid nativo |
| Reranker | `BAAI/bge-reranker-v2-m3` | |
| Vector DB | Qdrant | Apache-2.0, hybrid nativo |
| BM25 | Qdrant sparse vectors via FastEmbed (`Qdrant/bm25`) | Stessa collection del dense; RRF nativo server-side da Qdrant 1.10+ |
| LLM locale default | `qwen2.5:14b` (Q4_K_M) via Ollama | Decisione post-spike (2026-05-16): non degenera su prompt RAG strutturati, ammette i limiti del retrieval, no hallucination cross-norma. |
| LLM locale alt | `Minerva-7B-instruct` (Sapienza) | Alternativa opzionale per chi voglia stack truly-open italiano. Richiede `repeat_penalty=1.15`, post-filter stop tokens, system message obbligatorio. |
| LLM locale alt 2 | `LLaMAntino-3-ANITA-8B` | Qualità conversazionale maggiore (non testato in spike) |
| LLM cloud (opzionale) | OpenAI / Anthropic | Configurabile, off di default |
| LLM serving | Ollama (dev) / vLLM (prod) | |
| Orchestrazione | LangGraph | Agenti stateful |
| API | FastAPI | |
| UI demo | Streamlit | MVP rapido, niente frontend custom |
| Eval | Ragas | Faithfulness + Answer Relevancy + Context Precision via Ragas. Langfuse non integrato in v1 (decisione 2026-05-20, vedi registro modifiche). |
| CI/CD | GitHub Actions | |
| Deploy demo | Docker Compose su NAS + Cloudflare Tunnel | Rate limit aggressivo |

---

## Dataset (corpus v1)

Tutti pubblici e legalmente utilizzabili. Vietato includere materiale coperto da copyright.

**Norme primarie (via Normattiva XML Akoma Ntoso):**
- Reg. UE 2016/679 (GDPR) — testo italiano consolidato
- D.Lgs 196/2003 (Codice Privacy)
- Reg. UE 2024/1689 (AI Act) — via EUR-Lex
- D.Lgs 231/2001
- D.Lgs 138/2024 (NIS2)
- L. 132/2025 (Disposizioni AI italiane)

**Prassi / provvedimenti:**
- Provvedimenti Garante Privacy (docweb) — scraping rispettoso, rate limit 1 req/sec
- EDPB guidelines — via edpb.europa.eu

**Building blocks da riusare:**
- `ondata/normattiva_2_md` (parser Normattiva)
- `Ansvar-Systems/italian-law-mcp` (DB già con GDPR, 231, CAD, NIS2)

**Esplicitamente esclusi (copyright/licenza):**
- Testi ISO 27001/27701/42001
- Norme UNI
- Sentenze Cassazione (TOS vietano uso commerciale)
- Contenuti editoriali (Eutekne, IPSOA, Giuffrè)

---

## FUORI SCOPE v1 (lista chiusa)

Sentirsi tentati di aggiungere uno di questi → riaprire il file e chiedersi: vale davvero la pena? Probabilmente no.

- ❌ **Fine-tuning dell'LLM principale** (RAG batte fine-tuning per dominio legale)
- ❌ UI elaborata (Streamlit di base basta)
- ❌ Autenticazione / multi-utente / multi-tenant
- ❌ Mobile / responsive design avanzato
- ❌ Integrazione con gestionali esterni (TeamSystem, Profis, ecc.)
- ❌ Internazionalizzazione (solo italiano)
- ❌ Test di produzione su carico reale / scaling
- ❌ Knowledge graph cronologico avanzato (versione base sì, advanced no)
- ❌ Fine-tuning classificatori (rimandato a v2 / opzionale settimana 7 se in tempo)
- ❌ Secondo verticale (fiscale) — solo dopo v1 stabile
- ❌ Onboarding wizard / setup automatico
- ❌ Dashboard analytics / metriche utenti
- ❌ Export DOCX/PDF di report compliance
- ❌ API multi-tenant / chiavi API gestite
- ❌ Caching avanzato / ottimizzazione costi token

---

## Roadmap settimanale (sintesi)

| Sett. | Focus | Output atteso |
|---|---|---|
| 0 | Setup repo + scope + spike tecnico | Repo creato, primo articolo GDPR parsato end-to-end |
| 1 ✅ | Ingestion Normattiva + EUR-Lex | 4 moduli core completi (italian_legal_parser, normattiva_client, eur_lex_parser, eur_lex_client) + corpus v1 statico (4 XML AKN Normattiva + 3 HTML EUR-Lex) — vedi registro 2026-05-18 |
| 2 | Ingestion norme primarie + chunking + benchmark retrieval | Modulo chunking, ingestion 6 norme in Qdrant, benchmark retrieval su 5-10 query custom derivate dai 5 use case |
| 3 ✅ | hybrid_retriever + reranker + benchmark esteso 50 query | `core/hybrid_retriever` con BM25 sparse Qdrant + dense bge-m3 + RRF server-side + reranker opzionale post-hoc. Benchmark 4 setup (dense/hybrid/hybrid_rrk20/hybrid_rrk50) su 50 query gold annotate. Risultati: hybrid_rrk20 R@10=0.598, MRR=0.621 (+17pp R@10 vs dense, +6pp +18pp MRR vs hybrid). Default produttivo rerank_top_k=20 (strict-dominant). Garante scraper rinviato a v1.1. — vedi registro 2026-05-19 |
| 4 | citation_verifier + graph multi-normativa statico + bug W3 | `core/citation_verifier` deterministico (no LLM, validazione strutturale). Tabella statica self-curated ~30 link cross-norma (231↔GDPR↔AI Act↔NIS2) con disclaimer "not legally validated". Fix dei 3 bug W3 isolati: Q19 vocabolario lookup table (~30 righe sigle/forme estese), Q15 parser EUR-Lex art finali, Q30 chunking annex monoblocco. |
| 5 | LLM locale + generazione risposte | LangGraph agent funzionante, prompt italiano con citazioni |
| 6 | Demo Streamlit + packaging `core/` | `pip install` funziona, demo locale gira |
| 7 | Eval (Ragas + Langfuse) + content | 100 Q&A gold-standard, dashboard eval, 1 articolo |
| 8 | Polish + deploy + README + buffer | Demo pubblica deployata, README bilingue, video 3 min |
| Pivot W8→W10 | Benchmark esteso + articolo, no deploy demo | Vedi `SCOPE.md` registro modifiche 2026-05-20 + `PROJECT_CONTEXT.md` voce 34 |

**Settimana 5-6:** validazione tecnica leggera (3-5 peer tecnici via Discord mii-llm / LinkedIn), non interviste cliente.

---

## Definizione di successo

A fine settimana 8 (o termine equivalente del piano post-pivot):

1. ✅ Repo pubblico Apache-2.0 con README curato (IT + EN)
2. ✅ `pip install` funziona per la libreria core
3. ✅ Metriche eval pubbliche e riproducibili su benchmark ≥100 query gold-standard
4. ✅ 4/5 use case di riferimento risolti con qualità accettabile (UC4 Garante in v1.1, decisione 2026-05-19)
5. ✅ 1 articolo tecnico pubblicato (Medium/Dev.to/LinkedIn)

**Cosa NON è metrica di successo:**
- Numero di star GitHub
- Numero di clienti contattati
- Validazione di mercato
- Monetizzazione
- Demo pubblica live (decisione 2026-05-20 — vedi registro modifiche)

Queste vengono **dopo** v1, se vale la pena.

---

## Registro modifiche allo scope

Ogni modifica a questo documento deve essere giustificata qui sotto con data, motivazione, e impatto stimato sul time-to-completion.

| Data | Modifica | Motivazione | Impatto |
|---|---|---|---|
| (oggi) | v1.0 — documento iniziale | Setup progetto | — |
| 2026-05-16 | Stack tecnico: LLM locale default `Minerva-7B` → `qwen2.5:14b (Q4_K_M)` (Minerva diventa alternativa opzionale). Parser normativo principale `normattiva_2_md` → XML Akoma Ntoso diretto da Normattiva + parser custom XPath (`lxml`). | Spike settimana 0 (vedi `spike/SPIKE_RESULTS.md`): Minerva-7B degenera su prompt RAG (repetition loop, hallucination cross-norma, echo del contesto) mentre Qwen2.5-14B con la stessa pipeline si comporta correttamente. L'XML AKN risolve nativamente URN granulari per articolo (`eId="art_2-bis"`) e gerarchia esplicita (chapter/section/...), eliminando il post-processing del Markdown. | Probabile **−1 giorno** sul time-to-completion grazie a URN e gerarchia nativi dell'XML AKN (meno debito tecnico nel parser); qualità generazione attesa più alta con Qwen (meno glue code per gestire degenerazione del modello). |
| 2026-05-18 | Aggiunti moduli `core/eur_lex_parser` e `core/eur_lex_client` allo stack. Transport EUR-Lex: HTML rendering, dual-template (`initial` OJ + `consolidated` codifica). Considerando UE inclusi in v1 (`parse_recitals`). | (D1) Mini-spike D7 ha mostrato che AKN su EUR-Lex non esiste (404/500) e Formex è dentro Cellar ma richiede SPARQL costoso; l'HTML rendering è strutturato con classi ELI semantiche e id stabili — copre articoli + considerando + capi su GDPR e AI Act. (D2) I considerando contengono interpretazione giuridicamente rilevante (es. considerando 84 GDPR sulla DPIA, citato per use case 3 di SCOPE); estratti dal template iniziale in parallelo agli articoli della consolidata. Per AI Act la consolidata IT non esiste in HTML, si usa solo l'iniziale. (D3) `EurLexClient` bloccato da AWS WAF challenge al 2026-05-18 (HTTP 202 + JS challenge); bypass JS fuori scope; workaround per v1: download manuale dei 3 HTML in `data/cache/eurlex/IT/`. Re-evaluation post-v1 con Cellar SPARQL endpoint (`data.europa.eu`). | Settimana 1 chiusa con 4 moduli core completi e corpus EUR-Lex statico disponibile. Il workaround WAF impone refresh manuale ma non blocca corpus v1 (norme UE cambiano raramente). Nessun impatto sul time-to-completion. |
| 2026-05-18 | Garante scraper slittato dalla settimana 2 alla settimana 3. Settimana 2 ri-focalizzata su ingestion norme primarie + modulo chunking + benchmark retrieval. | Pipeline scraping HTML è architetturalmente disaccoppiata dai parser normativi (non AKN, contenuti eterogenei tra provvedimenti/ordinanze/FAQ, vincoli di rate limit e robots.txt) e copre solo 1 dei 5 use case di SCOPE (use case 4 — ricerca provvedimenti Garante); gli altri 4 use case sono coperti dalle norme primarie. Tenerla in settimana 2 avrebbe accoppiato il disegno del chunking a vincoli inutili. Settimana 2 focalizzata su chunking + Qdrant + benchmark retrieval sulle 6 norme primarie del corpus v1. | Nessun impatto sul time-to-completion globale (8 settimane). Possibile anticipo del Garante a fine settimana 2 se chunking + ingestion + benchmark chiudono prima del previsto. |
| 2026-05-18 | Settimana 2 chiusa: pipeline `core/chunking` + ingestion Qdrant + benchmark retrieval dense puro. Aggiunto parsing ad-hoc Allegato III dell'AI Act (`core/eur_lex_parser.parse_annex_iii_aiact`). Corpus indicizzato: 858 chunk (495 article + 9 article_group + 1 annex + 353 recital). Baseline benchmark (10 query custom, 9 positive): **Recall@5=0.46, Recall@10=0.58, MRR=0.62**, 2 query a zero recall@10 (Q5 multi-normativa, Q10 articoli definitori lunghi). Vedi `data/benchmark/BENCHMARK_BASELINE.md`. | Baseline misurato necessario per quantificare il guadagno di settimana 3 (BM25 hybrid + reranker); senza un numero "prima", il miglioramento "dopo" è aneddotico. La diagnosi per query identifica due classi di fallimento da indirizzare: (a) match lessicale puro (Q9 → BM25), (b) cross-normativa che richiede reasoning multi-hop (Q5 → reranker o gerarchia di link). Q10 è segnalato come potenziale problema strutturale di chunking (articoli definitori monoblocco poco accessibili a dense puro). | Settimana 2 chiusa in tempo. Numeri da battere settimana 3: target informale R@10 ≥ 0.80, MRR ≥ 0.75 con hybrid + reranker. Nessun impatto sul time-to-completion. |
| 2026-05-19 | BM25 backend: Postgres FTS → Qdrant sparse vectors via FastEmbed (`Qdrant/bm25`). | SCOPE originale prevedeva Postgres FTS "per ridurre dipendenze"; quella scelta pre-datava la decisione di tenere Qdrant come vector store. Oggi sparse vectors nella stessa collection eliminano la necessità di sync due-backend e abilitano RRF nativo server-side (Qdrant ≥1.10, in uso 1.18). Smoke test settimana 3 (`spike/smoke_bm25.py`) ha verificato che FastEmbed BM25 preserva i pattern tipici del diritto italiano (suffissi `-bis`/`-undecies`, abbreviazioni come `D.Lgs`). Caveat noto: acronimi cross-lingua (es. `GDPR` ↔ `Regolamento (UE) 2016/679`) sono limite di vocabolario, non di tokenizzazione — da gestire downstream se il benchmark a 50 query lo richiede. | Nessun impatto sul time-to-completion. Single-roundtrip query lato server semplifica `core/hybrid_retriever`. |
| 2026-05-19 | Settimana 3 chiusa: `core/hybrid_retriever` + integrazione reranker opzionale + benchmark esteso a 50 query (gold annotato manualmente, 39 positive + 8 negative + 3 edge). Risultati con setup default rerank_top_k=20: R@5=0.543, R@10=0.598, MRR=0.621, NDCG@10=0.563 (mean su 39 positive). Hybrid puro vs dense baseline W2: +17pp R@10 a parità di latenza. Reranker on top: +6pp R@10, +18pp MRR. Default produttivo: `rerank_top_k=20` (strict-dominant su dense puro; `rerank_top_k=50` esposto come parametro ma non default — guadagno medio +10pp R@10 ma regressioni puntuali su 3-4 query, non strict-dominant). 4 query a zero-recall dopo il fix top-50 (Q15, Q19, Q24, Q30) e diagnosticate come bug isolati: parser EUR-Lex su articoli finali (Q15), acronimi/sigle non in corpus (Q19), graph cross-norma multi-normativa (Q24), chunking annex monoblocco (Q30). Tutti rimandati a settimana 4-5. Vedi `BENCHMARK_W3.md` per dettagli, `zero_recall_diagnosis.md` per la diagnostica delle 8 query a zero-recall iniziali. | Nessun impatto su time-to-completion. Numeri sotto-target SCOPE (R@10≥0.80, MRR≥0.75) sull'aggregato ma sopra-target sul cluster stress lessicali (R@10=0.733, MRR=0.733). Target sono guida non vincolo come da SCOPE: definizione formale di "fatto" si misura sul pipeline RAG completo con generation (Context Precision RAGAS ≥ 0.80, settimana 7). |
| 2026-05-19 | Garante provvedimenti rinviati da v1 a v1.1. UC4 in v1 resta "stub" (test fail-graceful: il sistema risponde correttamente "non trovo riferimenti pertinenti" alle query Garante). Coverage v1 = 4/5 use case (UC1, UC2, UC3, UC5 risolti; UC4 in v1.1). | Decisione presa al termine di settimana 3 sulla base di tre considerazioni: (1) i 15-20 provvedimenti curati a mano avrebbero copertura mirata ma poco rappresentativa per query reali; (2) scraping completo docweb è eterogeneo (provvedimenti, ordinanze, FAQ, comunicati) e fuori scope tecnico v1; (3) il narrative "v1 copre 6 fonti normative primarie con citation verification e graph multi-normativa, Garante in v1.1" è più onesto e professionalmente posizionabile. Settimana 4 guadagna 2 giorni, redistribuiti su bug W3 isolati + buffer. Possibile rientro Garante in settimana 7-8 con opzione "scraping ultimi 12 mesi non curato" (1.5 gg) se il margine lo consente, NON come obiettivo. | Nessun impatto sul time-to-completion 8 settimane. UC4 coverage definita come fail-graceful, non come use case risolto. Da menzionare esplicitamente nell'articolo tecnico finale e nel README come decisione di scope deliberata. |
| 2026-05-19 | `core/citation_verifier` completato come modulo deterministico (no LLM, no normalizzazione, no resolution). Lavora solo su marker `[cite:CHUNK_ID]`. Politica soft warning. Renderer human-readable (chunk_id → "GDPR art. 35") separato in modulo `core/citation_renderer` da settimana 5. | Motivazione: separazione di concerns, decisione formato user-facing rimandata al momento in cui si vede output LLM reale. Il verifier mantiene un confine minimo e testabile (11 test, no dipendenze esterne), il renderer affronterà la mappatura semantica (chunk_id → riferimento normativo naturale) con i casi d'uso reali sotto gli occhi. | Impatto: nessuno sul time-to-completion, anzi mantiene il verifier focalizzato. Aggiunge un modulo `core/citation_renderer` al piano di settimana 5 — già tracciato nel TODO post-W3. |
| 2026-05-19 | `core/normative_graph` base completato: 6 link curati a mano, architettura A (espansione contesto a valle del retrieval, 1 hop bidirezionale, cap 5 chunk espansi). YAML come fixture, schema con campi `source` / `validated_by` / `validated_at` per estensione futura. Integrazione opzionale in `HybridRetriever.retrieve(graph_links=...)` via subclass `RetrievalResult(list)` per non rompere i 16 test esistenti. Misura graph-rescued su benchmark (hybrid_rrk): **0 query da R@10=0 a R@10>0** con il catalogo iniziale — i chunk-anchor (l'altro lato del link) non emergono nei top-10 delle query che avrebbero gold mancanti, quindi l'espansione non si attiva sul nodo giusto. I 6 link aggiungono comunque bonus context per il prompt LLM ma non spostano le metriche di retrieval. Espansione del catalogo a ~30 link è lavoro manuale post-prompt, non in scope di questa implementazione. Validazione legale formale rimandata a v1.1. Vedi `ROADMAP_POST_V1.md` per le evoluzioni identificate (estrazione automatica rinvii, validazione giurista, UI editing). | Nessun impatto sul time-to-completion. Settimana 4 step 3 chiusa. Lezione: il graph come "bonus context per generation" è il framing corretto in v1; come strumento di rescue del retrieval richiede catalogo più denso e/o re-rank consapevole dei link. |
| 2026-05-19 | Riannotazione gold post-split annex_III: 5 entry (Q1, Q11, Q12, Q13, Q19) rimappate dai vecchi gold orfani ai point corretti (Q1→p4 HR, Q11→p5 credit, Q12→p1+p3 dual emozioni/scuola, Q13→p1 biometria, Q19→p5 credit). Propagazione meccanica del fix di granularità, no nuova annotazione legale. Gold totali 72 → 73 (+1 per dual Q12), 0 orfani residui. Benchmark W3 re-run: Q13 chiude su tutti e 3 i setup (R@10 0 → 1.0), Q12 hybrid 0 → 0.5, Q19 hybrid 0.667 → 1.0; Q39 hybrid_rrk regredisce 1.0 → 0 (gold non toccato dal fix, sospetto rumore reranker su query boundary-fragile, flagged). Delta finale W4 hybrid_rrk R@10: **0.598 (baseline W3) → 0.712 (oggi)**, **+11.3 pp cumulativi**; dense_w3 +18.4 pp, hybrid +8.8 pp. | Nessun impatto sul time-to-completion. Settimana 4 effettivamente chiusa sui bug isolati. Zero-recall complessivi calano: dense_w3 14→13, hybrid 12→10, hybrid_rrk invariato. Nessuna nuova zero-recall introdotta. |
| 2026-05-19 | Fix chunking annex_III AI Act: `parse_annex_iii_aiact` ora ritorna `list[EurLexAnnex]` con 1 entry per macro-punto (8 totali) invece di un singolo monoblocco 8460 char. Granularità ferma al punto (non scende a lettera). chunk_id format `__annex_III__point_N`, hierarchy a 2 livelli, metadata `{point, n_letters}`. Cancellato vecchio chunk monoblocco da Qdrant + ingest 8 nuovi → collection 858 → 865 points. Aggiornati 3 link in `core/normative_graph/graph.yaml` (annex_III → annex_III__point_2/4) + gold Q30 → annex_III__point_4. 5 altri gold (Q1, Q11, Q12, Q13, Q19) puntavano allo stesso vecchio monoblocco e restano da rimappare ai point corretti (riannotazione manuale, fuori scope di questo fix). Benchmark W3 re-run: hybrid_rrk R@10 0.692 → **0.712 (+2.0pp)**, MRR +2.6pp; Q30 chiude da 0 a R@10=1 con rank 1 hybrid_rrk; Q39 extra rescue; Q12/Q1 regressioni attese da orfanaggio gold (non difetto del fix). | Nessun impatto sul time-to-completion. Settimana 4 effettivamente chiusa sui bug W3 isolati (Q15 + Q30 entrambi risolti). hybrid_rrk R@10 cumulativo W4 da baseline W3 0.598: +11.4pp via terminology + graph + parser commi + split annex. Riannotazione 5 gold residui = task lavorativo a se stante, non un fix di codice. |
| 2026-05-19 | Fix parser EUR-Lex `_parse_commi`: aggiunto fallback `__body` per articoli con paragrafi non numerati (es. AI Act art_113 con `<p class="oj-normal">` + tabelle a/b/c senza prefissi `1.`/`2.`). Lo scan post-fix ha identificato 35 articoli silently broken con lo stesso pattern (chunk text < 150 char), inclusi Definizioni GDPR art_4 e Definizioni AI Act art_3. Re-ingest completo EUR-Lex (568 chunk, 277.8s) + aggiornamento gold text_excerpt su 5 entry (Q2, Q14, Q15, Q17, Q18). Benchmark W3 re-run: ΔR@10 aggregato +11.5pp `dense_w3`, +0pp `hybrid`, +5.1pp `hybrid_rrk`; ΔMRR rispettivamente +3.1/+4.8/+1.9pp. 9 query positive in miglioramento netto (Q26, Q27, Q33, Q34, Q36, Q39, Q43, Q45) + 1 regressione isolata su Q17 dense_w3 (effetto collaterale strutturale di un chunk-titolo 47char che pre-fix matchava trivialmente; hybrid e hybrid_rrk recuperano correttamente). | Nessun impatto sul time-to-completion. Fix copre bug isolato identificato a chiusura W3 (Q15 zero-recall). Hybrid_rrk R@10 sale da 0.598 (baseline W3) a 0.692 — +9.4pp via terminology+graph+parser fix combinati. |
| 2026-05-19 | Graph multi-normativa portato da 6 a 22 link via curatela manuale strutturata (4 temi: B 231↔GDPR↔AI Act, A GDPR↔AI Act, C NIS2 trasversale, D L. 132/2025 + Cod. Privacy). Aggiunta metrica "coverage concettuale" allo script benchmark (`--phase=graph_rescue --use-graph`): n_queries_with_expansion, mean_expansions_per_query, top-5 link più attivati. Risultati con 22 link su hybrid_rrk: graph-rescued = **1 query (Q39)** via deroga Cod.Privacy art.2-ter ↔ GDPR art.6; coverage concettuale = **25/39 query positive (64%)** con almeno 1 chunk espanso, media 1.41 espansioni/query, totale 55 chunk attivati. 6 su 10 query zero-recall ricevono bonus context (Q5, Q13, Q30, Q34, Q39, Q45); 4 restano senza copertura graph (Q15, Q24, Q43, Q49). Finding architetturale confermato: il graph non risolve query zero-recall del benchmark dove il top-10 retrieval non contiene anchor del graph (Q5, Q24). Funziona come bonus context per generation quando il retrieval aggancia almeno un anchor. Q5/Q24 classificate come limitazione nota di v1, candidate a v1.1 con architetture retrieval avanzate (multi-query, HyDE, query rewriting LLM-assisted). | Nessun impatto sul time-to-completion. Settimana 4 step 3 confermata chiusa con curatela v1 finale a 22 link. Lezione consolidata: il graph in v1 vale come capability di generation context, non come strumento di recall retrieval. 4 link mai attivati su query positive (AI Act art.10↔GDPR art.6/9, AI Act art.99↔GDPR art.83, 196 art.2-sexies↔GDPR art.9) tenuti per copertura concettuale dei 4 temi. |
| 2026-05-19 | LLM cloud **Anthropic Claude Sonnet 4.6** (`claude-sonnet-4-6`) promosso da "opzionale" a **default cloud** della pipeline serving W5. LLM locale Qwen2.5-14B Q4_K_M via Ollama mantiene il ruolo di **fallback / demo offline**. Topologia MPS serving **condizionale al provider**: S1 (reranker MPS) con cloud, S2 (reranker CPU) con locale. LiteLLM rimandato a v1.1 (rivalutazione con Mistral come secondo provider per posizionamento EU). API key gestita via file `.env` (con `.env.example` committato e `.env` in `.gitignore`). Aggiunto modulo `core/llm_provider` al piano W5 (interfaccia astratta + `AnthropicProvider` + `OllamaProvider`). | Smoke MPS coabitazione (2026-05-19, `spike/MPS_COABITATION_RESULTS.md`) ha mostrato che il prefill cold di Qwen 14B Q4_K_M su M4 Pro è 14-22 s per prompt 2k-3k token, indipendentemente dalla topologia MPS. Sulla target audience professional (DPO, studi legali), latenza cloud (TTFT ≤ 3 s atteso) > costo API (~$0.01-0.02/query, trascurabile). Cloud come default cambia il profilo di scelta MPS: con cloud non c'è più pressione memoria, reranker su MPS è gratis. Astrazione `LLMProvider` giustificata da "entrambi i provider girano in v1", non da speculazione futura. | Nessun impatto sul time-to-completion. Aggiunge `core/llm_provider` + `.env` setup alla W5. Costo API stimato per dev/test in 8 settimane: < €30 totali con Sonnet 4.6 ($3 input / $15 output Mtok). Soglie di latenza riformulate da "5 s end-to-end" (riga 94-95 sopra, legacy) a TTFT cold/warm + throughput streaming (vedi PROJECT_CONTEXT.md registro decisioni 2026-05-19, voci 21-22). Compressione prompt RAG SCARTATA in v1 (vedi PROJECT_CONTEXT.md voce 23). |
| 2026-05-19 | **Settimana 5 chiusa in anticipo (~3 giorni di margine sul piano)**. Backend RAG end-to-end completo e funzionante. 3 moduli core nuovi (`core/llm_provider`, `core/rag_prompt`, `core/serving`) per un totale di **19 test nuovi** (suite 173 passed, 1 skipped, 0 falliti). Pipeline `retrieve → rerank → generate → citation_verify` funzionante in streaming, con due provider intercambiabili via env var. Smoke RAG validati su provider **locale** (Ollama Qwen2.5-14B Q4_K_M, 3/3 `all_verified` strutturali, total e2e 30-37 s) e **cloud** (Anthropic `claude-sonnet-4-6`, 3/3 `all_verified` strutturali, total e2e 12-19 s, TTFT mediano 1.6 s, throughput 44-49 tok/s — vedi `spike/SMOKE_RAG_PIPELINE_RESULTS.md`). Default `RAG_MAX_OUTPUT_TOKENS` alzato da 500 → 1000 dopo smoke cloud (`finish_reason=length` su 3/3). Citation verifier deterministico funziona come atteso: cattura tutti i marker formali. Cloud vince con margine netto sul caso peggiore (Q1 cita correttamente art. 6 AI Act + Allegato III; Qwen su Q1 citava considerando invece di articolo) — conferma la divisione di responsabilità con Ragas W7 per la verifica semantica. Topologia MPS condizionale documentata come TODO esplicito in `core/serving/config.py`, non attiva (HybridRetriever non espone device del reranker — vedi PROJECT_CONTEXT.md TODO post-W3). | Tutti i deliverable di settimana 5 chiusi. Cloud diventa default (Anthropic Sonnet 4.6) come deciso a metà W5 dopo smoke MPS (2026-05-19). Locale (Ollama) resta come fallback / demo offline. Compressione prompt scartata in v1 (decisione PROJECT_CONTEXT voce 23). Citation renderer rinviato (decisione presa prima di W5). | **Anticipo di ~3 giorni** sul piano 8 settimane. Margine da redistribuire tra W6 (UI Streamlit), buffer W7 (Ragas eval) o mini-spike preliminare su aperture v1.1 (citation renderer). Decisione di allocazione rimandata a inizio W6. |
| 2026-05-19 | **Q5 riclassificata da `positive` a `edge`** dopo diagnostica W7-prep in 3 step (gold sbagliato da LLM-hint, retrieval lessicale, corpus completo). Benchmark W3 ri-aggregato su 38 positive (era 39) — vedi `data/benchmark/BENCHMARK_W3.md` sezione "Re-aggregazione post-riclassificazione Q5 → edge". Aggiunto a `ROADMAP_POST_V1.md` la sezione "Retrieval avanzato v1.1 — Query cross-norma con vocabolari disgiunti" usando Q5 come use case di validazione per architetture multi-query / HyDE / query rewriting. Aggiunto a `PROJECT_CONTEXT.md` (Note per Claude) il paragrafo "Curatela gold answers W7-prep" che codifica il sanity check giuridico come parte del processo di curatela (annotazione vs corpus vs capability). | La curatela giuridica è metodologicamente più severa del benchmark retrieval-only: ha rivelato 1 query (Q5) su 39 dove l'errore è metodologico (richiede capability v1.1), non di sistema. Forzare un fix terminology/graph mirato per salvare Q5 come positive sarebbe stato scope-creep dentro W7-prep (stima 2-4h per spostare R@10 da 0 a 0.25 su una query strutturalmente v1.1). Onestà metodologica preferita. | Benchmark W3 ora **38 positive + 10 negative + 2 edge = 50 query totali**. Metriche aggregate leggermente migliorate (Q5 era zero-recall su 3 setup su 4). Nessun impatto sul time-to-completion. Lezione di processo replicabile su future iterazioni gold curatela: la curatela giuridica è il secondo livello di validazione, non solo redazione delle gold_answer. |
| 2026-05-19 | **Q9 riannotata post-audit 231**. Gold ridotto da 4 chunk a 1 (solo `art_24-bis`): rimossi `art_25-undecies__paras_1_6` e `art_25-undecies__paras_7_8` (allucinazione LLM, stesso pattern Q5) e `196 art_167` (reato autonomo del Codice Privacy, non reato-presupposto 231). `gold_answer` scritta in **scenario C**: contenuto su `art_24-bis` (delitti informatici richiamati come reati-presupposto + sanzioni) + dichiarazione esplicita di limite (dettaglio c.p. fuori corpus v1). Audit esteso a Q24/Q25/Q26/Q27/Q49: tutte coerenti, bug `25-undecies` isolato a 2 query (Q5+Q9). Introdotta convenzione formale "dichiarazione limite corpus" come pattern stabile per query che richiedono norme fuori corpus v1. Aggiunta a `ROADMAP_POST_V1.md` sezione "Estensione corpus v1.1 — Codice penale articoli richiamati da 231" come capability v1.1. | L'audit giuridico ha confermato che l'allucinazione LLM è circoscritta a 2 query, non sistemica. Q9 mantenuta `positive` ma con risposta onestamente limitata invece di edge (come Q5): `art_24-bis` copre il dispositivo 231 sui delitti informatici, il dettaglio penale è dichiarato fuori corpus. Pattern "dichiarazione di limite" formalizzato come strumento di trasparenza UX per il target professional (DPO, studi legali) — sistema dichiara apertamente cosa sa e cosa no. | Benchmark W3 ri-aggregato su 38 positive con nuovo gold-set Q9: Q9 entra in zero-recall su tutti i 4 setup (`art_24-bis` non emerge nei top-10 del retiver — il vecchio gold contava il match lessicale di `196 art_167`, ora correttamente azzerato). Delta aggregati modesti (MRR `hybrid_rrk` −0.026 il più visibile). Conclusione metodologica: l'aggregato pre-fix sovrastimava Q9 (gold sbagliato agganciato per ragioni lessicali); il fix è strict-better per la baseline Ragas W7. Nessun impatto su time-to-completion. |
| 2026-05-19 | **W7-prep chiusa**: `data/benchmark/gold_answers_v1.json` generato (50 entry: 38 positive curate + 10 negative + 2 edge boilerplate). Curatela LLM-assisted con revisione umana entry-per-entry, audit annotazione benchmark in parallelo (6 query 231-related ispezionate, bug `art_25-undecies` isolato a Q5+Q9). Pattern **"dichiarazione di limite corpus"** formalizzato e applicato in 11 query positive (linguaggio canonico user-facing `"...non incluso nel corpus normativo di riferimento"`). Voci aggiunte a `ROADMAP_POST_V1.md`: (a) "estensione corpus codice penale articoli richiamati da 231" come capability v1.1 (vedi prompt fix Q9, 2026-05-19), (b) "query cross-norma con vocabolari disgiunti" come capability v1.1 (vedi prompt Q5 → edge, 2026-05-19). Statistiche dettagliate del dataset in `data/benchmark/STATS.md` (file separato, vedi voce 32 del registro decisioni PROJECT_CONTEXT.md). | I 3 giorni di anticipo W5 sono stati investiti in W7-prep (~2.5gg curatela + audit + fix documentazione, 0.5gg fix linguistici Q8/dichiarazione di limite). Lavoro previsto in W7, anticipato: W7 diventa esecuzione Ragas + interpretazione, non scoperta dataset. Il dataset è anche un **artefatto portfolio**: 38 `gold_answer` giuridicamente curate sono un argomento metodologico forte per posizionamento DPO/compliance — "abbiamo costruito anche il benchmark per misurare la qualità delle risposte, non solo del retrieval". | Nessun impatto sul time-to-completion 8 settimane. W7 ora ha ~5 giorni effettivi disponibili contro 7 originali (redistribuzione, non guadagno: 3 giorni anticipati in W5 ora non sono più disponibili in W7). Benchmark v1 stabilizzato a **38 positive + 10 negative + 2 edge = 50 query** dopo audit. Tutte le metriche Ragas W7 si calcoleranno su 38 positive con `gold_answer` curate. |
| 2026-05-20 | **Pivot pre-fase G**. Rimossi dai deliverable v1: (a) demo deployata pubblicamente con rate limit, (b) video demo 3 minuti, (c) README bilingue IT+EN (resta solo IT). Aggiunti: (a) benchmark esteso a 100 query gold-standard (era 50), (b) articolo tecnico come deliverable primario, (c) packaging pip del core come deliverable testabile. La "Definizione di successo" e la "Roadmap settimanale" W6/W7/W8 restano nello stato originale a fini storici; questa voce è la lettura attuale. Audience primaria del rilascio pubblico ridefinita: ricercatori e practitioner RAG legal italiano interessati a benchmark e metodologia, non utenti finali della demo. | Decisione maturata in fase F: il valore distintivo del progetto è la metodologia (benchmark curato giuridicamente, specifiche a monte, decisioni datate) e i numeri (Ragas + retrieval), non una demo che il target audience non userebbe come prima porta di ingresso. Demo Streamlit locale resta nel repo per chi vuole testare; deploy pubblico rinviato a v1.1 se la community lo richiede. | Time-to-completion v1 invariato (8 settimane). Effort risparmiato su deploy + video reinvestito in benchmark 100q + articolo. |
| 2026-05-21 | **Decisione fase G: rilascio pubblico v1.0 confermato.** Risultati Ragas F.2 (run completo 100 query, judge Sonnet 4.6): faithfulness mediana globale 0.886 (target ≥0.85 PASS), answer_relevancy mediana globale 0.815 (target ≥0.80 PASS). Drift v1 W7 archived vs ricalcolato su 38 positive Q1-Q50: faithfulness -0.042 sotto soglia 0.05, answer_relevancy -0.007. Judge e pipeline stabili tra run W7 e F.2. Bottom-5 faithfulness: Q35 (0.250, retrieval-bound W7 noto), Q46 (0.308, edge drift lessicale), Q48 (0.375, negative ePrivacy off-corpus), Q41 (0.400, negative Data Act off-corpus), Q79 (0.429, positive portabilità dati derivati — gap testo norma vs dottrina WP29 predetto in curatela). Verdict: GO ready-with-followup. Dettaglio narrativo in `data/benchmark/BENCHMARK_RAGAS_F2.md` (analisi qualitativa bottom-5, modifica metodologica ex-post, follow-up v1.1); artefatti primari del run in `data/benchmark/ragas_aggregates_v2.json` + `ragas_results_v2.json` + `ragas_pipeline_outputs_v2.json`. | Soglie metodologiche definite in RAGAS_RUN_NOTES.md rispettate. Distribuzione bimodale answer_relevancy (mean 0.609 vs median 0.815) attribuibile a failure mode noto Ragas su risposte di scope-out (judge valuta dichiarazioni di limite come "non pertinenti"). 23/23 query con has_corpus_limit_declaration=true mostrano drift lessicale rispetto al pattern canonico "non incluso nel corpus normativo di riferimento": detection regex va sostituita con LLM-as-judge in v1.1. Pattern di onestà metodologica preservato in fase G: nessun ricalcolo silenzioso di aggregati per spostare la mediana sopra soglia. | Sblocco rilascio pubblico v1.0. Time-to-completion rispettato (8 settimane). |
2026-05-24 | **Subset dev mode + 4 finding metodologici post-F.2**. 
Capability nuova: subset benchmarking via --subset path.yaml (20 query 
causali, $2/ciclo vs $10 F.2 completo, output su path *_subset.* per 
non sovrascrivere F.2 archived). 2 fix v1 applicati: 
(1) wiring core/terminology.expand_query in HybridRetriever.retrieve(), 
(2) CORPUS_LIMIT_RE allargata a 4 famiglie lessicali con centralizzazione 
in spike/corpus_limit_regex.py. Numeri: Q35 retrieval da rank>20 a rank 
1, regex detection 0/20→8/20 (subset post-fix). Definition of done 
moduli W*: aggiunto requisito integration test end-to-end. | F.2 ha 
rivelato che metrica "drift 0/23" era artefatto regex troppo stretta 
(non bug modello) e che modulo terminology W4 era orfano (wiring 
mancante). 4 casi consolidano pattern "validazione sostantiva > 
meccanica" (Q5, F.2 drift, Q25, Q35). | Nessun impatto su scope v1. 
2 fix indipendenti merge-ready, candidato release v0.5.1. Baseline F.2 
archived (100 query) resta valida come fotografia W7. Re-run completo 
post-fix rimandato a milestone v0.6 (capability di accumulo numeri, 
non urgente).
| 2026-05-24 | **Curatela gold v3 + script default a v3**. Generato `data/benchmark/gold_answers_v3.json`: 12 qid CAT2 riallineati `has_corpus_limit_declaration True→False` (Q12, Q13, Q15, Q26, Q27, Q45, Q63, Q66, Q72, Q85, Q87, Q88), 2 qid (Q19, Q35) `runtime_corpus_limit_observed True→False`, 6 notes appended con prefisso `[v3 2026-05-24]`. Audit trail completo in `data/benchmark/gold_v2_to_v3_diff.md`. Script `spike/run_pipeline_v2.py` e `spike/run_ragas_eval_v2.py` spostati a v3 (path constant). | Riallineamento metodologico post-fix v0.5.1: il dataset v2 conteneva gold flag spurious su 12/23 corpus_limit (diagnostica completa CAT1/CAT2 sulle 23 query). Curatela v3 riflette stato reale del sistema runtime, non lo stato curatoriale W7-prep. Q25 lasciata invariata (limite metrica RAGAS noto su reasoning sussuntivo, vedi `ROADMAP_POST_V1.md`). | Nessun impatto su scope v1. `gold_answers_v2.json` mantenuto in filesystem come riferimento storico (input default precedente W7/F.2), non più input default. Re-run F.2 completo su v3 atteso dopo eventuali fix retrieval v0.6 (Q15, Q55/Q83 cluster NIS2 fragment).
