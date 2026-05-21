# BENCHMARK W3 v2 — pipeline outputs su gold_answers_v2.json

**Start (UTC):** 2026-05-20T19:24:40.885402+00:00
**End (UTC):** 2026-05-20T19:54:47.615664+00:00
**Provider:** anthropic · model: `claude-sonnet-4-6`
**Pipeline params:** top_k=5, rerank_top_k=20, use_graph=False, max_output_tokens=1000.
**Reranker device:** MPS (topologia S1). Collection: `italian_legal_v1_hybrid`.

## 1. Sintesi globale (100 query)

| metrica | mediana |
|---|---:|
| R@5 (su query con gold)  | 0.875 |
| R@10 (su query con gold) | 1.000 |
| R@20 (su query con gold) | 1.000 |
| MRR (su query con gold)  | 0.500 |
| n query con R@10=1.0     | 45 |
| n query con R@10=0.0     | 14 |

## 2. Per query_type

| type | n | R@5 | R@10 | R@20 | MRR | n R@10=1 | n R@10=0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| positive | 77 | 1.000 | 1.000 | 1.000 | 0.500 | 45 | 14 |
| negative+edge | 23 | — | — | — | — | — | — |

- Negative+edge con pattern canonico 'corpus_limit' nella answer: **0 / 23** → []
- Negative+edge con risposta sostantiva (>200 char, no pattern): **23** → ['Q4', 'Q5', 'Q20', 'Q21', 'Q22', 'Q23', 'Q41', 'Q42', 'Q44', 'Q46', 'Q47', 'Q48', 'Q90', 'Q91', 'Q92', 'Q93', 'Q94', 'Q95', 'Q96', 'Q97', 'Q98', 'Q99', 'Q100']

## 3. Per cluster v2 (Q51-Q100)

Aggregati per use_case (proxy del cluster). Soglia outlier: R@10 mediana < globale - 0.20.

| use_case | n | R@10 med | MRR med |
|---|---:|---:|---:|
| 231 corruzione fattispecie | 1 | 0.500 | 0.250 | ⚠ outlier
| 231 riciclaggio condotte e cornici | 1 | 1.000 | 1.000 |
| 231 sanzioni interdittive condizioni | 1 | 0.500 | 0.500 | ⚠ outlier
| 231 sicurezza lavoro omicidio colposo | 1 | 1.000 | 1.000 |
| 231+GDPR integrazione modello accesso abusivo | 1 | 0.250 | 0.200 | ⚠ outlier
| AI Act sanzioni GPAI rischio sistemico | 1 | 1.000 | 0.250 |
| AI Act+GDPR deployer vs titolare | 1 | 0.250 | 0.333 | ⚠ outlier
| AI Act+GDPR informativa | 1 | 0.500 | 0.500 | ⚠ outlier
| Banca outsourcing IA AML extra-UE | 1 | 0.200 | 0.250 | ⚠ outlier
| Diritto accesso tempi e modalità | 1 | 1.000 | 1.000 |
| GDPR sanzione violazione diritto accesso | 1 | 1.000 | 0.200 |
| Garante composizione collegio | 1 | 1.000 | 1.000 |
| Garante poteri ispettivi | 1 | 1.000 | 0.500 |
| Industria IA monitoraggio lavoratori | 1 | 0.250 | 0.200 | ⚠ outlier
| L.132 IA in ambito sanitario | 1 | 0.000 | 0.000 | ⚠ outlier
| L.132 coordinamento con AI Act | 1 | 0.000 | 0.000 | ⚠ outlier
| L.132 deepfake fattispecie penale | 1 | 1.000 | 1.000 |
| L.132 trattamento dati per sviluppo IA | 1 | 0.500 | 0.200 | ⚠ outlier
| NIS2 comunicazione destinatari servizio | 1 | 1.000 | 0.500 |
| NIS2 governance organi amministrativi | 1 | 1.000 | 1.000 |
| NIS2 misure gestione rischio multi-rischio | 1 | 1.000 | 1.000 |
| NIS2 sanzioni soggetti essenziali | 1 | 0.000 | 0.091 | ⚠ outlier
| NIS2 sanzioni soggetti importanti | 1 | 0.000 | 0.062 | ⚠ outlier
| NIS2 sospensione dirigenti | 1 | 1.000 | 0.200 |
| NIS2 supply chain ICT responsabilità | 1 | 1.000 | 1.000 |
| NIS2+GDPR comunicazione interessato | 1 | 1.000 | 0.500 |
| NIS2+GDPR data breach tempistiche doppia notifica | 1 | 0.500 | 0.250 | ⚠ outlier
| NIS2+GDPR misure sicurezza preventive | 1 | 1.000 | 1.000 |
| Oblio vs finalità giornalistica | 1 | 1.000 | 1.000 |
| Opposizione marketing diretto | 1 | 1.000 | 1.000 |
| PA regionale IA graduatorie sociali | 1 | 0.000 | 0.077 | ⚠ outlier
| Pharma IA farmacovigilanza | 1 | 0.000 | 0.000 | ⚠ outlier
| Portabilità dati derivati | 1 | 1.000 | 1.000 |
| Procedura DPIA passi e contenuti | 1 | 1.000 | 1.000 |
| Reclusione art.167 trattamento illecito | 1 | 1.000 | 1.000 |
| Registro trattamenti art.30 contenuti | 1 | 1.000 | 1.000 |
| Sanità chatbot AI triage paziente | 1 | 0.200 | 0.500 | ⚠ outlier
| Trattamento condanne penali in gare pubbliche | 1 | 1.000 | 1.000 |
| Trattamento dati forze di polizia | 1 | 1.000 | 0.500 |

**Outlier identificati (16)**: `231 corruzione fattispecie` (0.50), `231 sanzioni interdittive condizioni` (0.50), `231+GDPR integrazione modello accesso abusivo` (0.25), `AI Act+GDPR deployer vs titolare` (0.25), `AI Act+GDPR informativa` (0.50), `Banca outsourcing IA AML extra-UE` (0.20), `Industria IA monitoraggio lavoratori` (0.25), `L.132 IA in ambito sanitario` (0.00), `L.132 coordinamento con AI Act` (0.00), `L.132 trattamento dati per sviluppo IA` (0.50), `NIS2 sanzioni soggetti essenziali` (0.00), `NIS2 sanzioni soggetti importanti` (0.00), `NIS2+GDPR data breach tempistiche doppia notifica` (0.50), `PA regionale IA graduatorie sociali` (0.00), `Pharma IA farmacovigilanza` (0.00), `Sanità chatbot AI triage paziente` (0.20)

## 4. Per norma toccata

| norma | n query | R@10 med |
|---|---:|---:|
| AI Act | 29 | 0.500 |
| Codice Privacy | 6 | 1.000 |
| D.Lgs 231/2001 | 12 | 0.500 |
| GDPR | 33 | 1.000 |
| L. 132/2025 | 10 | 0.292 |
| NIS2 | 16 | 1.000 |

## 5. Confronto v1 (Q1-Q50) vs v2 (Q51-Q100)

| metrica | v1 (n positive) | v2 (n positive) | cumulato |
|---|---:|---:|---:|
| R@5 med | 0.875 (38) | 1.000 (39) | 1.000 |
| R@10 med | 1.000 | 1.000 | 1.000 |
| R@20 med | 1.000 | 1.000 | 1.000 |
| MRR med | 1.000 | 0.500 | 0.500 |

Nota drift: confronto vs `BENCHMARK_W3.md` (W7-prep) per pipeline drift. Se R@10 v1 attuale differisce >0.05 da W3-prep → indagare.

## 6. Paired queries intenzionali

| Tema | qid coppia | R@10 entrambi | answer differente? |
|---|---|---|---|
| art_38__paras_1_11 NIS2 sanzioni | Q55,Q83 | 0.00 / 0.00 | sì |
| NIS2 art_25 notifica | Q54,Q57 | 1.00 / 0.50 | sì |
| L.132 art_9 trattamento dati | Q64,Q67 | 0.00 / 0.50 | sì |

## 7. Runtime corpus_limit observed (post-eval)

Query positive con `has_corpus_limit_declaration=false` ma pattern canonico presente nella answer: **0 / 77**


Drift lessicale (has_corpus_limit_declaration=true ma pattern canonico non rilevato): **19**
Lista qid:
- `Q9` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q12` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q13` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q15` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q24` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q25` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q26` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q27` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q43` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q45` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q49` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q63` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q66` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q72` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q76` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q85` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q86` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q87` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex
- `Q88` — verificare se è drift lessicale benigno o pattern legittimo non catturato dalla regex

**Decisione**: pattern documentato qui, dataset `gold_answers_v2.json` non aggiornato. Eventuale fix runtime_corpus_limit_observed in v1.1.

