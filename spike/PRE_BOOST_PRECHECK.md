# PRE_BOOST_PRECHECK — Step 0 v1.1 closeout

Verifiche preliminari prima dell'implementazione boost type-aware.
Zero implementazione. STOP per conferma utente prima dello Step 1.

## A. Query benchmark v3 con ≥1 gold recital

**Conteggio: 7 query.**

| qid | gold recital |
|---|---|
| Q1  | `eli/reg/2024/1689/oj__recital_57` |
| Q3  | `eli/reg/2016/679/oj__recital_84`, `eli/reg/2024/1689/oj__recital_96` |
| Q7  | `eli/reg/2016/679/oj__recital_84`, `eli/reg/2016/679/oj__recital_91` |
| Q8  | `eli/reg/2024/1689/oj__recital_96` |
| Q29 | `eli/reg/2016/679/oj__recital_84` |
| Q37 | `eli/reg/2016/679/oj__recital_71` |
| Q88 | `eli/reg/2016/679/oj__recital_84` |

Esistono → il gruppo gold-recital è popolabile (max 4 nello Step 2). Nota:
Q7 è già nel gruppo mainstream sanity → per evitare overlap, candidati
gold-recital Step 2: **Q1, Q3, Q8, Q29** (4 query, gold recital + tutte
positive con gold article+recital misto).

⚠ Tutti questi gold-recital sono accoppiati ad articoli nel medesimo gold
(es. Q3 ha recital_96 + art): il boost article>recital potrebbe spingere
GIÙ il recital e SU l'articolo dentro lo stesso gold-set. È esattamente lo
stress che il criterio "nessun Δfaith < -0.05 su gold-recital" deve cogliere.

## B. Troncamento Q69 (generation max_tokens)

Rigenerazione Q69 (cassette V2 sub-query, 1 generation call):

| max_tokens | out_tokens | finish_reason | completata | fine answer |
|---|---|---|---|---|
| 1000 (default) | 1000 | `length` | **NO** | "...### 3. Obblighi ai sensi della NIS2... In quanto soggetto essenziale...l'" (taglio netto) |
| 6000 | 1955 | `stop`  | **SÌ** | "...quadro infrastrutturale entro cui il sistema di IA deve operare [cite:...138__art_24]." |

**Troncamento CONFERMATO.** A default 1000 la risposta si interrompe
*all'inizio* della sezione NIS2 (3ª norma): la sezione NIS2 non viene mai
sviluppata. Servono ~1955 token per completare le 3 norme. Questo
**inquina la misura faith su Q69** (e plausibilmente Q70/Q71, 4 norme):
l'answer troncata ha meno affermazioni verificabili + sezione mancante.

→ Bugfix max_tokens generation candidato per v1.2 (o fix immediato se
deciso). NON implementato in questo step.

## C. 3 mono-norma high-faith stress (faith ≥0.85, gold rank ≤3, detect_norms <2)

Selezione (da F.2 v3 archived):

| qid | norma gold | faith F.2 | ar F.2 | gold rank | tipo gold |
|---|---|---|---|---|---|
| **Q34** | GDPR art_9 | 0.917 | 0.818 | 1 | article |
| **Q35** | AI Act art_27 (FRIA) | 0.947 | 0.722 | 1 | article |
| **Q38** | L.132/2025 art_11 | 1.000 | 0.841 | 1 | article |

**Q36 SCARTATA**: faith F.2 = 0.60 < 0.85 (non soddisfa il criterio). Q34/Q35
qualificano come da suggerimento utente; Q38 sostituisce Q36 per coprire una
terza norma (GDPR / AI Act / L.132 → diversità) con gold article e faith
massima. Tutti e 3 hanno gold = articolo → il boost dovrebbe essere
neutro-positivo; servono a verificare che NON degradi (Δfaith ≥ -0.05).

## Riepilogo numeri Step 0

- **A** = 7 query gold-recital (subset Step 2: Q1, Q3, Q8, Q29)
- **B** = Q69 troncato a 1000 (finish=length), completo a 6000 (1955 tok, finish=stop)
- **C** = Q34, Q35, Q38 (mono-norma high-faith stress; Q36 scartata faith 0.60)

---

**STOP. In attesa di conferma utente prima dello Step 1 (implementazione boost).**
