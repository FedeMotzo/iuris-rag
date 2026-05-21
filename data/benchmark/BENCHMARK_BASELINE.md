# Benchmark baseline — settimana 2 (dense puro)

**Data:** 2026-05-18
**Setup misurato:** bge-m3 dense, instruction prefix italiano, top-10, Qdrant Cosine, **niente BM25, niente reranker**.
**Corpus indicizzato:** 858 chunk in collection `italian_legal_v1` (495 article + 9 article_group + 1 annex + 353 recital).
**Gold set:** 28 chunk annotati manualmente su 10 query custom (9 positive + 1 negative). Validati in `data/benchmark/gold_validated.json`.

Questo documento serve come **baseline contro cui confrontare** il setup ibrido (BM25 + dense + reranker) di settimana 3. Le metriche aggregate qui sono il numero "prima"; senza un confronto numerico esplicito, qualsiasi miglioramento futuro è aneddotico.

---

## Metriche aggregate (positive queries, N=9)

| Metrica | Valore baseline | Target settimana 3 (informale) |
|---|---:|---:|
| Mean Recall@5 | **0.46** | ≥ 0.65 |
| Mean Recall@10 | **0.58** | ≥ 0.80 |
| Mean MRR | **0.62** | ≥ 0.75 |
| Query con zero gold in top-10 | **2/9** (Q5, Q10) | 0/9 |
| Query con MRR = 1.0 | **5/9** | ≥ 7/9 |

I target sono guida, non vincolo contrattuale. Definizione di successo di SCOPE.md (Context Precision RAGAS ≥ 0.80) si misura sul pipeline RAG completo (con generation), non sul retrieval da solo.

---

## Diagnosi per query

| QID | Use case | R@5 | R@10 | MRR | Diagnosi |
|---|---|---:|---:|---:|---|
| Q1 | AI Act HR screening | 0.75 | 0.75 | 1.00 | OK. 3/4 gold, art_26 fuori top-10. |
| Q2 | Timeline AI Act credit scoring | 0.50 | 0.50 | 1.00 | art_111 al rank 1; **art_113 (entrata in vigore) fuori top-10**. Articolo lungo, query timeline-specifica. |
| Q3 | DPIA vs FRIA | 0.75 | 0.75 | 1.00 | OK. recital_84 GDPR fuori top-10 (è top-1 in Q7). |
| Q5 | 231 + AI decisioni HR | 0.00 | **0.00** | 0.00 | **Multi-normativa cross-norma** (231→196→GDPR). Top-1 (recital_57 AI Act) semanticamente perfetto ma non-gold. Caso difficile per design. |
| Q6 | Compiti DPO | 1.00 | 1.00 | 1.00 | Quasi perfetto. Articoli GDPR 37/38/39 ai primi 4 slot. |
| Q7 | Quando DPIA è obbligatoria | 0.67 | 1.00 | 1.00 | OK. recital_91 al rank 6. |
| Q8 | Cos'è FRIA | 0.50 | 1.00 | 0.50 | recital_84 GDPR (DPIA) confonde la query FRIA; art_27 AI Act scivola al rank 2. |
| Q9 | Reati 231 trattamento illecito | 0.00 | 0.25 | 0.12 | **Match lessicale puro** ("D.Lgs 231", "art. 24-bis", "delitti informatici"). Top-7 tutti GDPR. Candidato classico per BM25 hybrid. |
| Q10 | NIS2 soggetti essenziali/importanti | 0.00 | **0.00** | 0.00 | **Articoli definitori lunghi**: art_3 (1401 token, monoblocco) non viene pescato. Top-10 tutti NIS2 ma "sbagliati". Potenziale problema strutturale di chunking. |

**Q4 (negative — Garante riconoscimento facciale):** non in scope per la metrica, ma utile come sanity check. Top-1 score = 0.682 vs Q6 top-1 = 0.884 → c'è separazione di magnitudine tra "query con gold nel corpus" e "query off-topic" (Garante non in corpus v1). I top-10 sono tutti dal Codice Privacy 196 sezione "trattamenti di polizia/sicurezza pubblica" — vicinanza semantica plausibile.

---

## Ipotesi di lavoro per settimana 3

Le tre query con problemi (Q5, Q9, Q10) suggeriscono interventi mirati e ortogonali. Ognuno è già scritto in SCOPE come componente core, quindi non aggiunge scope:

1. **BM25 hybrid (RRF, no peso ottimizzato)** → atteso miglioramento principale su **Q9** (match lessicale esatto su "231", "24-bis", "delitti informatici"). Anche Q10 può beneficiare se i gold contengono i pattern "soggetti essenziali" / "soggetti importanti" letterali.
2. **Reranker `BAAI/bge-reranker-v2-m3`** → atteso miglioramento su **Q8** (riordina art_27 sopra recital_84) e in generale su MRR delle query già con R@10 buono.
3. **Q5 multi-normativa** è quella su cui ho meno fiducia: è il caso che richiede *reasoning cross-norma*. Se hybrid + reranker non chiude, si passa a una soluzione di link cross-norma in settimana 4 (componente "graph multi-normativa base" di SCOPE).
4. **Q10 strutturale**: se rimane a zero dopo settimana 3, riconsiderare la soglia di chunking 2000 token per gli articoli definitori monoblocco. Strategia precisa (split per comma? per definizione? abbassare soglia generale?) da decidere dopo i numeri di settimana 3.

---

## Come riprodurre / rilanciare

Prerequisito: `docker-compose up -d qdrant` attivo, collection `italian_legal_v1` popolata con i 858 chunk del corpus v1.

```bash
# 1. (Re)build dei candidati gold dal corpus chunked
spike/.venv/bin/python scripts/build_gold_candidates.py
# → data/benchmark/gold_candidates.json

# 2. (Re)apply del gold validato (28 chunk_id curati a mano)
spike/.venv/bin/python scripts/build_gold_validated.py
# → data/benchmark/gold_validated.json
# Fallisce loudly se uno dei 28 chunk_id gold non è tra i candidati.

# 3. Esegui benchmark (Qdrant attivo)
spike/.venv/bin/python scripts/run_benchmark.py
# → data/benchmark/results.json + stdout tabella metriche
```

Se cambi il modulo di chunking o re-ingesti con setup diverso (es. hybrid), i punti 1–3 vanno tutti rilanciati: i candidati sono derivati dai chunk concreti, non da una lista hard-coded di articoli.

---

## Confronto post-settimana 3

Per documentare il miglioramento, aggiungi a fine `BENCHMARK_BASELINE.md` (o crea `BENCHMARK_W3.md`) una tabella analoga su per-query + aggregate, intestata con la stessa data + setup, e una riga di delta:

```
| Metrica         | Baseline W2 | W3 (hybrid+reranker) | Delta |
|-----------------|------------:|---------------------:|------:|
| Mean Recall@5   |        0.46 |                  X.X |  +X.X |
| Mean Recall@10  |        0.58 |                  X.X |  +X.X |
| Mean MRR        |        0.62 |                  X.X |  +X.X |
```

Mantieni `data/benchmark/results.json` di settimana 2 come `results_w2_baseline.json` prima di sovrascriverlo, altrimenti il confronto è perso.

---

## Errata corrige

**2026-05-19 — Q9 gold: art. 167 Codice Privacy non è reato presupposto 231.**

La gold di Q9 ("Quali sono i reati presupposto in materia di trattamento illecito di dati personali ai sensi del 231?") include `akn/it/act/decreto_legislativo/stato/2003-06-30/196__art_167`. Verifica condotta in fase di annotazione del benchmark esteso (settimana 3) ha mostrato che:

- Art. 167 D.Lgs 196/2003 è reato in capo a "chiunque" (persona fisica);
- Il D.Lgs 101/2018 di adeguamento al GDPR non ha esteso il catalogo dei reati presupposto 231 al trattamento illecito di dati;
- L'aggancio 231↔privacy passa solo indirettamente per l'art. 24-bis 231 (delitti informatici del codice penale).

Gold semanticamente corretto di Q9: 231/art_24-bis + 231/art_25-undecies__paras_1_6 + 231/art_25-undecies__paras_7_8 (3 chunk).

**Decisione operativa.** La gold baseline di Q9 NON viene corretta retroattivamente. La baseline (R@5=0.46, R@10=0.58, MRR=0.62) resta stabile come riferimento di confronto W2 vs W3. Q11-Q50 vengono annotate con il principio "semantica > lessicale" per evitare l'errore analogo nelle nuove query (UC5 in particolare).
