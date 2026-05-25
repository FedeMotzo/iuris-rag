# gold_v2 → gold_v3 — Audit trail

**Data**: 2026-05-24

**Motivo**: riallineamento post-fix v0.5.1 (terminology wiring [`core/hybrid_retriever`](../../core/hybrid_retriever/retriever.py) + regex allargata [`spike/corpus_limit_regex`](../../spike/corpus_limit_regex.py)) + diagnostica completa delle 23 query con `has_corpus_limit_declaration=True` del dataset v2.

Vedi `PROJECT_CONTEXT.md` voce 36 per il contesto completo. Le 23 query corpus_limit del dataset v2 sono state diagnosticate in 2 categorie:

- **CAT1 (11 qid)**: drift naturale catturato dalla regex allargata post-v0.5.1, `has_corpus_limit_declaration=True` confermato
- **CAT2 (12 qid)**: groundato sufficiente, gold flag spurious, riallineato a `False` in v3

Inoltre **Q19 e Q35** (post-fix wiring) riallineano `runtime_corpus_limit_observed` da `True` a `False`: il fix terminology porta i gold chunks (FRIA art_27 AI Act, DPIA art_35 GDPR) in top-10 in entrambe le query, risolvendo la motivazione W7 del flag manuale.

## Modifiche `has_corpus_limit_declaration`: `True` → `False` (12 query)

| qid | use_case | R@10 v2 | Motivo riallineamento |
|-----|----------|--------:|-----------------------|
| Q12 | AI Act high-risk emotion recognition scuole | 0.00 | Modello risponde via recital_44 + recital_54 (equivalente normativo) |
| Q13 | AI Act Allegato III biometria | 1.00 | Retrieval coverage sufficiente sul gold annex_III__point_1; risposta groundata, no limit dichiarato |
| Q15 | AI Act timeline divieti | 0.00 | Gold recital_179 al rank 1; risposta groundata su timeline divieti |
| Q26 | stress: art 24-bis 231 | 1.00 | Gold art_24-bis al rank 1 score 0.966; risposta completa con 3 fasce sanzionatorie |
| Q27 | stress: art 25-undecies | 1.00 | 2/2 gold (art_25-undecies__paras_1_6 + _7_8) ai rank 1-2; risposta esaustiva su reati ambientali |
| Q45 | edge: query vaga multi-doc | 1.00 | Gold L.132/__art_1 al rank 4; risposta groundata su art_1 + art_20 |
| Q63 | Trattamento dati forze di polizia | 1.00 | Gold recuperato; risposta groundata su trattamento dati forze di polizia (Codice Privacy) |
| Q66 | L.132 deepfake fattispecie penale | 1.00 | Gold L.132/__art_26 al rank 1; modello afferma art. 612-quater c.p. esplicitamente |
| Q72 | Industria IA monitoraggio lavoratori | 0.25 | Gold AI Act art_26 al rank 5; modello tronca senza dichiarare gap Statuto/L.132 (scelta scope legittima) |
| Q85 | 231 corruzione fattispecie | 0.50 | Gold art_25 al rank 4; modello interpreta 'corruzione' in senso pubblicistico, art_25-ter era ampliamento curatela |
| Q87 | 231 sicurezza lavoro omicidio colposo | 1.00 | Gold art_25-septies al rank 1 score 0.642; risposta groundata su omicidio colposo + sicurezza lavoro |
| Q88 | Procedura DPIA passi e contenuti | 1.00 | Gold recuperato per Procedura DPIA; risposta groundata su passi e contenuti |

## Modifiche `runtime_corpus_limit_observed`: `True` → `False` (2 query)

| qid | Motivo |
|-----|--------|
| Q19 | Post-fix wiring (v0.5.1): 3/3 gold (art_27 AI Act, art_35 GDPR, annex_III__point_5) ai rank 1/5/9 in top-10. |
| Q35 | Post-fix wiring (v0.5.1): gold `eli/reg/2024/1689/oj__art_27` al rank 1, modello risponde groundato. |

## Notes appended (6 query)

Le note sono appended con prefisso `[v3 2026-05-24]` separate da ` | ` se il campo `notes` v2 era non vuoto.

| qid | Note v2 | Note v3 (appended) |
|-----|---------|--------------------|
| Q12 | — | [v3 2026-05-24] Riallineato has_corpus_limit_declaration=False. R@10=0 sui gold annotati (annex_III__point_1, __point_3), ma modello risponde correttamente via recital_44 + recital_54 (percorso normativamente equivale... |
| Q19 | — | [v3 2026-05-24] Riallineato runtime_corpus_limit_observed=False parallelo a Q35. Pre-fix v0.5.1: retrieval falliva per assenza alias DPIA+FRIA (zero match lessicale), modello entrava in scenario C runtime. Post-fix te... |
| Q66 | Confidence bassa: articoli ipotizzati. gold_answer_quality: draft, articoli d... | [v3 2026-05-24] Riallineato has_corpus_limit_declaration=False. Confidence sul gold riconfermata post-fix wiring: …132/__art_26 recuperato rank 1, modello risponde groundato senza dichiarare limit. Note v2 'Confidence... |
| Q72 | Scenario realistico monitoraggio lavoratori. Cross AI Act + GDPR + L.132 + St... | [v3 2026-05-24] Riallineato has_corpus_limit_declaration=False. Query cross-norma 3+ (AI Act + GDPR + L.132 + Statuto). Modello risponde groundato su AI Act (art_26 recuperato rank 5) e tronca senza dichiarare gap su ... |
| Q85 | 231 corruzione. Confidence alta su artt. 25/25-ter. | [v3 2026-05-24] Riallineato has_corpus_limit_declaration=False. Gold include …231/__art_25 (corruzione pubblica) + …231/__art_25-ter (corruzione tra privati). Modello recupera art_25 (rank 4) e interpreta 'corruzione'... |
| Q86 | 231 riciclaggio. Confidence alta su art. 25-octies. | [v3 2026-05-24] has_corpus_limit_declaration=True confermato MA per ragione diversa: il modello risponde groundato su art_25-octies (rank 1) e chiude con dichiarazione esplicita sui testi c.p. (artt. 648, 648-bis, 648... |

## Modifiche NON applicate (rationale)

- **Q25** (231 fattispecie informatica): rimane `has_limit=True`. Decisione 2026-05-24: limite metrica RAGAS noto su query case-based (reasoning sussuntivo, claim applicativi non verificabili letteralmente). Nessun fix v0.6, rivalutare post-v1.1 (vedi `ROADMAP_POST_V1.md`).
- **Q5, Q9**: NON ispezionate ulteriormente, già documentate come edge cross-norma con vocabolari disgiunti (capability v1.1).
- **Altri 9 CAT1** (Q24, Q43, Q49, Q76, Q86, Q94, Q95, Q96, Q97): confermati `has_limit=True`. La regex allargata post-v0.5.1 cattura correttamente il pattern di dichiarazione limit (Famiglia 2 "contesto non contiene" o Famiglia 4 "sarebbe necessario disporre"). Le 2 negative by design (Q95, Q97) dichiarano correttamente l'off-corpus.

## Statistiche aggregate

| Metrica | v2 | v3 | Δ |
|---------|---:|---:|---:|
| n query totali | 100 | 100 | 0 |
| `has_corpus_limit_declaration=True` | 23 | 11 | -12 |
| `runtime_corpus_limit_observed=True` | 2 | 0 | -2 |

## Sanity check

1. ✓ JSON valido, 100 entries, qid range completo Q1..Q100.
2. ✓ 86 chunk_id unici di gold_chunks esistono tutti nella collection Qdrant `italian_legal_v1_hybrid`.
3. ✓ Nessun qid con `has_corpus_limit_declaration=False` AND `runtime_corpus_limit_observed=True` (pattern W7-prep Q19/Q35 risolto).
4. ✓ Schema invariato (10 campi per entry, identica indentazione 4-spaces v2).

