# BENCHMARK RAGAS W7 v2 — eval Ragas su gold_answers_v2.json

**Date:** 2026-05-21
**Finished (UTC):** 2026-05-21T10:33:32.555971+00:00
**Judge:** `claude-sonnet-4-6` · embeddings `BAAI/bge-m3`
**Metriche:** faithfulness, answer_relevancy (2)
**Cost reale:** $6.8175 · LLM calls 293 · wall 4541s · prompt_caching=disabled

### Note metodologiche

- **`context_precision` non inclusa**: spec F.2 originale chiedeva 3 metriche, ma il dry-run Q51 ha mostrato $0.132/sample (proiezione $13.20 su 100, 13× sopra spec). Drop context_precision per ridurre cost a target $2-4. La dimensione retrieval-quality resta coperta da R@5/R@10/R@20/MRR computati in F.1 su 100 query (vedi `spike/BENCHMARK_W3_v2.md`).
- **Anthropic prompt caching tentato, disabilitato**: il dry-run Q52+Q70 ha mostrato `cache_read_input_tokens=0` su tutte le call. I prompt Ragas tra extract-statements, verify-statements e generate-question hanno prefisso strutturalmente diverso → 0% cache hit pagando +25% overhead di cache_creation. Caching disabilitato, instrumentazione tracker mantenuta. Dettaglio in `spike/PHASE_F2_PREFLIGHT.md`.
- **100 query full coverage**, no stratified subset. Save incrementale per resilienza ai crash (batch=10).

## 1. Sintesi globale (100 query)

| metrica | n | median | mean | p10 | p90 | min | max | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| faithfulness | 100 | 0.886 | 0.826 | 0.500 | 1.000 | 0.250 | 1.000 | 0.188 |
| answer_relevancy | 100 | 0.815 | 0.609 | 0.000 | 0.948 | 0.000 | 1.000 | 0.388 |

## 2. Per query_type

| type | n | faith median | faith mean | rel median | rel mean |
|---|---:|---:|---:|---:|---:|
| positive | 77 | 0.917 | 0.843 | 0.839 | 0.714 |
| negative | 20 | 0.833 | 0.787 | 0.000 | 0.252 |
| edge | 3 | 0.769 | 0.657 | 0.000 | 0.293 |

## 3. Per cluster v2 (use_case, proxy)

Nota: nel dataset v2 ogni qid ha use_case unico (n=1 per use_case). Per cluster-level analysis vera servirebbe mappare qid→cluster dai metadata di `candidates_v2_curated.json` (rinviato a v1.1 / iterazione successiva).

| use_case | n | faith | rel |
|---|---:|---:|---:|
| 231 + AI decisioni HR | 1 | 0.769 | 0.000 |
| 231 + GDPR + AI selezione fornitori | 1 | 0.615 | 0.000 |
| 231 corruzione fattispecie | 1 | 0.960 | 0.915 |
| 231 fattispecie informatica art 24-bis | 1 | 0.750 | 0.000 |
| 231 modello organizzativo + AI HR | 1 | 0.895 | 0.000 |
| 231 riciclaggio condotte e cornici | 1 | 0.667 | 0.834 |
| 231 sanzioni interdittive condizioni | 1 | 1.000 | 0.890 |
| 231 sicurezza lavoro omicidio colposo | 1 | 1.000 | 0.936 |
| 231+GDPR integrazione modello accesso abusivo | 1 | 0.929 | 0.000 |
| AI Act Allegato III biometria | 1 | 1.000 | 0.794 |
| AI Act GPAI vs high-risk obblighi | 1 | 0.824 | 0.850 |
| AI Act art 113 stress | 1 | 0.867 | 0.714 |
| AI Act art.220 inesistente | 1 | 0.875 | 0.902 |
| AI Act high-risk HR screening | 1 | 0.882 | 0.948 |
| AI Act high-risk credit scoring | 1 | 0.889 | 0.920 |
| AI Act high-risk emotion recognition scuole | 1 | 1.000 | 0.738 |
| AI Act sanzioni GPAI rischio sistemico | 1 | 1.000 | 0.966 |
| AI Act timeline GPAI già immessi | 1 | 0.857 | 0.890 |
| AI Act timeline divieti | 1 | 0.900 | 0.959 |
| AI Act timeline sanzioni | 1 | 1.000 | 0.935 |
| AI Act+GDPR deployer vs titolare | 1 | 0.519 | 0.872 |
| AI Act+GDPR informativa | 1 | 0.684 | 0.836 |
| Banca outsourcing IA AML extra-UE | 1 | 0.786 | 0.673 |
| Cod.Privacy art.33 misure minime abrogato | 1 | 0.733 | 0.000 |
| Cod.Privacy art.7 diritti abrogato | 1 | 0.833 | 0.971 |
| Compiti del DPO | 1 | 1.000 | 0.725 |
| Cos'è FRIA e quando si fa | 1 | 1.000 | 0.724 |
| DPIA + FRIA scoring bancario | 1 | 0.556 | 0.000 |
| DPIA vs FRIA | 1 | 0.850 | 0.826 |
| Decreto NIS2 art.75 inesistente | 1 | 0.875 | 0.000 |
| Diritto accesso tempi e modalità | 1 | 1.000 | 0.857 |
| EDPB linee guida 5/2020 corpus mancante | 1 | 1.000 | 0.000 |
| Edge vaga privacy e AI obblighi aziende | 1 | 0.895 | 0.878 |
| GDPR sanzione violazione diritto accesso | 1 | 1.000 | 0.935 |
| Garante composizione collegio | 1 | 1.000 | 0.910 |
| Garante decisione TikTok 2024 | 1 | 0.857 | 0.000 |
| Garante poteri ispettivi | 1 | 1.000 | 0.977 |
| Garante provvedimento ChatGPT 2023 | 1 | 0.800 | 0.000 |
| Garante riconoscimento facciale aeroporti | 1 | 1.000 | 0.000 |
| Garante riconoscimento facciale lavoro (negative) | 1 | 0.778 | 0.000 |
| Garante riconoscimento facciale presenze | 1 | 0.667 | 0.000 |
| Garante sanzioni biometria dipendenti | 1 | 0.857 | 0.992 |
| ISO 27701 corpus mancante | 1 | 0.800 | 0.000 |
| Industria IA monitoraggio lavoratori | 1 | 0.944 | 0.800 |
| L.132 IA in ambito sanitario | 1 | 0.938 | 0.987 |
| L.132 coordinamento con AI Act | 1 | 0.500 | 0.000 |
| L.132 deepfake fattispecie penale | 1 | 0.556 | 0.924 |
| L.132 trattamento dati per sviluppo IA | 1 | 0.944 | 0.907 |
| NIS2 comunicazione destinatari servizio | 1 | 0.857 | 0.852 |
| NIS2 governance organi amministrativi | 1 | 0.643 | 0.844 |
| NIS2 misure gestione rischio multi-rischio | 1 | 1.000 | 0.667 |
| NIS2 sanzioni soggetti essenziali | 1 | 0.714 | 0.000 |
| NIS2 sanzioni soggetti importanti | 1 | 0.714 | 0.000 |
| NIS2 soggetti essenziali/importanti | 1 | 0.682 | 0.000 |
| NIS2 sospensione dirigenti | 1 | 1.000 | 0.902 |
| NIS2 supply chain ICT responsabilità | 1 | 0.720 | 0.930 |
| NIS2+GDPR comunicazione interessato | 1 | 1.000 | 0.852 |
| NIS2+GDPR data breach tempistiche doppia notifica | 1 | 0.947 | 0.864 |
| NIS2+GDPR misure sicurezza preventive | 1 | 0.727 | 0.927 |
| Oblio vs finalità giornalistica | 1 | 0.958 | 0.927 |
| Omonimia art.35 valutazione GDPR vs FRIA | 1 | 1.000 | 0.645 |
| Omonimia art.6 par.1 GDPR vs AI Act | 1 | 1.000 | 0.674 |
| Opposizione marketing diretto | 1 | 0.950 | 0.739 |
| PA regionale IA graduatorie sociali | 1 | 0.450 | 0.822 |
| Pharma IA farmacovigilanza | 1 | 0.625 | 0.900 |
| Portabilità dati derivati | 1 | 0.429 | 0.953 |
| Procedura DPIA passi e contenuti | 1 | 1.000 | 0.826 |
| Quando DPIA è obbligatoria | 1 | 0.905 | 0.866 |
| Reati 231 trattamento illecito dati | 1 | 1.000 | 0.000 |
| Reclusione art.167 trattamento illecito | 1 | 0.900 | 0.916 |
| Registro trattamenti art.30 contenuti | 1 | 1.000 | 0.929 |
| Sanità chatbot AI triage paziente | 1 | 0.542 | 0.903 |
| Timeline AI Act credit scoring | 1 | 0.455 | 1.000 |
| Trattamento condanne penali in gare pubbliche | 1 | 0.800 | 0.882 |
| Trattamento dati forze di polizia | 1 | 1.000 | 0.987 |
| edge: Data Act off-corpus | 1 | 0.400 | 0.000 |
| edge: EDPB off-corpus | 1 | 0.938 | 0.000 |
| edge: ISO 27001 off-scope | 1 | 0.833 | 0.000 |
| edge: art inesistente | 1 | 0.500 | 0.854 |
| edge: ePrivacy off-corpus | 1 | 0.375 | 0.000 |
| edge: mix in/off corpus | 1 | 0.800 | 0.000 |
| edge: operativa ChatGPT | 1 | 0.308 | 0.000 |
| edge: query troppo generica | 1 | 0.789 | 0.000 |
| edge: query vaga multi-doc | 1 | 0.714 | 0.723 |
| edge: vaga ma con anchor lessicale | 1 | 1.000 | 0.713 |
| stress: Allegato III punto 4 AI Act | 1 | 0.929 | 0.728 |
| stress: L. 132/2025 art 11 | 1 | 0.667 | 0.845 |
| stress: NIS2 obblighi notifica naturale | 1 | 1.000 | 0.774 |
| stress: art 111 AI Act | 1 | 0.917 | 0.663 |
| stress: art 22 GDPR | 1 | 0.933 | 0.848 |
| stress: art 24-bis 231 | 1 | 0.500 | 0.737 |
| stress: art 25-undecies | 1 | 1.000 | 0.671 |
| stress: art 27 AI Act FRIA | 1 | 0.250 | 0.000 |
| stress: art 35 disambiguation | 1 | 1.000 | 0.639 |
| stress: art 5 GDPR | 1 | 1.000 | 0.818 |
| stress: art 6 GDPR base giuridica | 1 | 1.000 | 0.779 |
| stress: art 6 NIS2 | 1 | 0.929 | 0.812 |
| stress: art 9 GDPR | 1 | 0.955 | 0.860 |
| stress: considerando 71 vs art 22 GDPR | 1 | 1.000 | 0.839 |
| stress: considerando 84 GDPR | 1 | 0.800 | 0.796 |

## 4. Per has_corpus_limit_declaration

| flag | n | faith median | faith mean | rel median | rel mean |
|---|---:|---:|---:|---:|---:|
| false | 77 | 0.875 | 0.815 | 0.839 | 0.650 |
| true | 23 | 0.900 | 0.864 | 0.723 | 0.472 |

## 5. Per norma toccata

| norma | n | faith median | rel median |
|---|---:|---:|---:|
| AI Act | 29 | 0.882 | 0.822 |
| Codice Privacy | 6 | 0.950 | 0.913 |
| D.Lgs 231/2001 | 12 | 0.912 | 0.672 |
| GDPR | 33 | 0.933 | 0.848 |
| L. 132/2025 | 10 | 0.690 | 0.862 |
| NIS2 | 16 | 0.756 | 0.833 |

## 6. Confronto v1 W7 archived ↔ v1 ricalcolato F.2

Le 50 query v1 (Q1-Q50) includono 38 positive + 10 negative + 2 edge. Il W7 archived ha valutato solo le 38 positive; per confronto omogeneo, filtro v1_subset alle stesse 38 positive sul ricalcolato.

| metrica | W7 archived (38 pos) | F.2 ricalcolato (38 pos) | delta |
|---|---:|---:|---:|
| faithfulness median | 0.944 | 0.902 | -0.042 (ok) |
| answer_relevancy median | 0.763 | 0.756 | -0.007 (ok) |

## 7. Bottom-5 per metrica

### Bottom-5 `faithfulness`

| qid | score | query_type | cluster (use_case) |
|---|---:|---|---|
| Q35 | 0.250 | positive | stress: art 27 AI Act FRIA |
| Q46 | 0.308 | edge | edge: operativa ChatGPT |
| Q48 | 0.375 | negative | edge: ePrivacy off-corpus |
| Q41 | 0.400 | negative | edge: Data Act off-corpus |
| Q79 | 0.429 | positive | Portabilità dati derivati |

### Bottom-5 `answer_relevancy`

| qid | score | query_type | cluster (use_case) |
|---|---:|---|---|
| Q4 | 0.000 | negative | Garante riconoscimento facciale lavoro (negative) |
| Q5 | 0.000 | edge | 231 + AI decisioni HR |
| Q9 | 0.000 | positive | Reati 231 trattamento illecito dati |
| Q10 | 0.000 | positive | NIS2 soggetti essenziali/importanti |
| Q19 | 0.000 | positive | DPIA + FRIA scoring bancario |

## 8. Verdict

Target SCOPE pivotato (vedi `SCOPE.md` Metriche di "fatto" post-2026-05-20):
- `faithfulness` ≥ 0.85
- `answer_relevancy` ≥ 0.80
- `context_precision` ≥ 0.80 (NON misurata in F.2, vedi note metodologiche)

- faithfulness median (positive, n=77): **0.917** (✅ ≥0.85)
- answer_relevancy median (positive, n=77): **0.839** (✅ ≥0.80)

**Verdict: GO ready-with-followup per release v1.**

Follow-up identificati per v1.1 (vedi anche `ROADMAP_POST_V1.md` Finding W7):
- Runtime corpus_limit detection via LLM-as-judge (regex inaffidabile, vedi PHASE_F1_DIAGNOSTIC).
- Estensione corpus codice penale articoli richiamati da 231 (4+ candidate W7-prep richiedono il c.p.).
- Tuning system prompt per uniformare pattern lessicale "dichiarazione di limite".
- Eventuale context_precision in run successivo dedicato (se rilevante).

## 9. Paired queries intenzionali design v2

Da metadata di `candidates_v2_curated.json` (fase C):
| Tema | qid coppia | faith A | faith B | rel A | rel B |
|---|---|---:|---:|---:|---:|
| NIS2 art_38__paras_1_11 (sanzioni) | Q55,Q83 | 0.714 | 0.714 | 0.000 | 0.000 |
| NIS2 art_25 (notifica) | Q54,Q57 | 0.857 | 0.947 | 0.852 | 0.864 |
| L.132 art_9 (trattamento dati) | Q64,Q67 | 0.938 | 0.944 | 0.987 | 0.907 |

---

**Bias del dataset v2 verso il posizionamento DPO/legal mainstream**: la composizione delle 50 query nuove (Q51-Q100) privilegia 6 cluster mirati al target professional (NIS2, Codice Privacy lato italiano, L. 132/2025, cross-norma 3+, diritti dell'interessato, sanzioni). Aggregati v2 vs v1 W7 archived possono divergere proprio per questa scelta di copertura tematica, non solo per qualità pipeline. Quando comunicato esternamente, segnalare che il benchmark è progettato per stressare il sistema sul target professional italiano, non come golden truth neutrale.

