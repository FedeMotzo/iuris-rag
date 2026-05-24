# iuris-rag

RAG italiano open-source su normativa privacy, AI e cybersecurity.
Sistema con benchmark esteso (100 query gold annotate) e
metodologia documentata.

![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Version](https://img.shields.io/badge/version-0.5.0--beta-orange)

---

## Cosa è

`iuris-rag` è una pipeline RAG sul corpus delle 6 norme primarie
italiane ed europee in tema privacy / AI / cybersecurity /
responsabilità d'impresa: **GDPR**, **AI Act**, **Codice Privacy**,
**D.Lgs 231/2001**, **NIS2** e **L. 132/2025**. L'input è una
domanda in italiano; l'output è una risposta con citazioni nel
formato `[cite:CHUNK_ID]` verificate strutturalmente contro il set
di chunk recuperati.

Quello che il progetto prova a fare diversamente dalla media dei
RAG verticali:

- **Corpus curato manualmente**, non scraping massivo. 6 norme,
  parser AKN/EUR-Lex dedicati, ingestion idempotente.
- **Benchmark duale**: retrieval (R@K, MRR, NDCG su gold annotati)
  + generazione ([Ragas](https://docs.ragas.io) faithfulness +
  answer_relevancy). Verdict v1 si decide su entrambe le dimensioni.
- **Spec scritte a monte**: ogni fase ha una spec metodologica
  prima del run (es. [`RAGAS_RUN_NOTES.md`](data/benchmark/RAGAS_RUN_NOTES.md)
  per Ragas), e modifiche post-hoc sono dichiarate in coda, non
  sostituiscono la spec.
- **Decisioni datate**: [`SCOPE.md`](SCOPE.md) e
  [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) sono living docs con
  registro append-only. Ogni decisione ha data + motivazione +
  impatto.

Per chi è:

- Ricercatori e practitioner **RAG legal italiano** interessati a
  benchmark e metodologia (audience primaria, decisione pivot
  2026-05-20 in [SCOPE.md](SCOPE.md))
- **DPO / compliance officer** che vogliono uno strumento di
  ricerca normativa self-hosted con trasparenza sulle sue fallenze
- **Developer** che cercano una libreria pip per RAG italiano
  legale

Per chi **non** è:

- Utenti finali che cercano un SaaS pronto: per quello esistono
  prodotti commerciali (Lexroom, Normo.ai, OneFISCALE AI) con UX,
  supporto e SLA pensati per studio professionale.
- Use case certificati (medico, ISO, audit regolamentati): fuori
  scope v1, nessuna pretesa di compliance funzionale.

---

## Stato del progetto

**v0.5.0 — beta.** Backend RAG end-to-end completo (parser,
retrieval ibrido, generazione, citation verifier). Benchmark v2 a
100 query gold-annotate. Verdict Ragas F.2 del 2026-05-21:
**GO ready-with-followup** — soglie metodologiche raggiunte, 3
follow-up identificati per v1.1. Dettaglio in
[`BENCHMARK_RAGAS_F2.md`](data/benchmark/BENCHMARK_RAGAS_F2.md).

Tag **v1.0** previsto dopo pubblicazione su PyPI e completamento
dei follow-up F.2 (detection LLM-as-judge della dichiarazione di
limite, validazione incrociata judge, tuning system prompt).

**Non è ancora consigliabile per produzione.** È un artefatto
tecnico/metodologico, da usare e citare con consapevolezza dei
limiti documentati in
[`docs/architecture/`](docs/architecture/README.md) § "Limiti
noti v1".

---

## Benchmark in 30 secondi

| Metrica | Valore | Soglia | Documento |
|---|---:|---:|---|
| Retrieval R@10 (hybrid + reranker, 39 positive v1) | 0.712 | — | [`BENCHMARK_W3.md`](data/benchmark/BENCHMARK_W3.md) |
| Generation faithfulness mediana (100 query) | **0.886** | ≥0.85 | [`BENCHMARK_RAGAS_F2.md`](data/benchmark/BENCHMARK_RAGAS_F2.md) |
| Generation answer_relevancy mediana (100 query) | **0.815** | ≥0.80 | [`BENCHMARK_RAGAS_F2.md`](data/benchmark/BENCHMARK_RAGAS_F2.md) |

Verdict F.2: **ready-with-followup**. Le soglie metodologiche di
`RAGAS_RUN_NOTES.md` sono raggiunte, ma 3 follow-up restano aperti
per v1.1 (vedi report).

Drift judge/pipeline fra run W7 (2026-05-20) e F.2 (2026-05-21)
sulle 38 positive comuni: **−0.042 faith, −0.007 rel**, sotto la
soglia di stabilità 0.05 dichiarata in spec — judge e pipeline
stabili.

Per il dettaglio metodologico e i report di tutte le fasi di
benchmark: [`docs/benchmark/`](docs/benchmark/README.md).

---

## Architettura in 30 secondi

```
domanda IT → terminology → hybrid retrieval → graph (opz.) → prompt → LLM stream → citation verify → risposta
                                                                                                              + [cite:CHUNK_ID] verificate
```

Stack:

> Parser XML Akoma Ntoso (Normattiva) + HTML EUR-Lex dual-template,
> embedding `BAAI/bge-m3` con instruction prefix italiano,
> retrieval ibrido (BM25 sparse + dense + RRF server-side + reranker
> `BAAI/bge-reranker-v2-m3`), graph cross-norma curato a 22 link,
> LLM Anthropic Claude Sonnet 4.6 (default cloud) o Qwen2.5-14B via
> Ollama (fallback locale), citation verifier strutturale
> deterministico.

Dettaglio in [`docs/architecture/`](docs/architecture/README.md)
(diagramma 2-fasi, decisioni architetturali chiave, stack tecnico).

---

## Installazione e uso

- **Come libreria pip**: vedi [`core/README.md`](core/README.md)
  per quick start, dipendenze e configurazione `.env`.
- **Per replicare il benchmark**: vedi
  [`BENCHMARK_BASELINE.md`](data/benchmark/BENCHMARK_BASELINE.md)
  § "Come riprodurre".
- **Per contribuire**: `CONTRIBUTING.md` in arrivo.

---

## Documentazione

Per chi vuole:

- **Capire il benchmark e la metodologia** →
  [`docs/benchmark/`](docs/benchmark/README.md)
- **Capire l'architettura tecnica** →
  [`docs/architecture/`](docs/architecture/README.md)
- **Usare la libreria pip** → [`core/README.md`](core/README.md)
- **Leggere il verdict Ragas F.2 (verdict v1)** →
  [`data/benchmark/BENCHMARK_RAGAS_F2.md`](data/benchmark/BENCHMARK_RAGAS_F2.md)
- **Capire le decisioni di progetto** → [`SCOPE.md`](SCOPE.md)
  (cosa c'è e cosa no in v1) +
  [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) (registro decisioni
  datato, 35 voci)
- **Conoscere la roadmap v1.1** →
  [`ROADMAP_POST_V1.md`](ROADMAP_POST_V1.md)
- **Leggere le note di curatela del graph cross-norma** →
  [`docs/methodology/graph_curation_notes.md`](docs/methodology/graph_curation_notes.md)

---

## Principi del progetto

Caratterizzano il modo in cui il progetto è stato costruito, oltre
al codice che produce.

- **Spec-first.** Ogni fase ha una spec scritta prima del run (es.
  [`RAGAS_RUN_NOTES.md`](data/benchmark/RAGAS_RUN_NOTES.md) prima
  del run W7 e di F.2). Le modifiche emergenti durante l'esecuzione
  sono dichiarate esplicitamente in coda al documento, non
  riscrivono la spec retroattivamente.
- **Decisioni datate.** [`SCOPE.md`](SCOPE.md) e
  [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) sono registri
  append-only: ogni decisione ha data, motivazione e impatto
  stimato. Il contesto del "perché è fatto così" non si perde
  nella storia di git.
- **Curatela giuridica come secondo livello di validazione.** Il
  benchmark non chiede solo "annotazione corretta?" ma
  "annotazione giuridicamente coerente?". La curatela ha rivelato
  query (es. Q5, Q9) dove l'errore era di metodo, non di sistema —
  riclassificate o riannotate invece di forzate.
- **Onestà metodologica sulle metriche.** Nessun ricalcolo
  silenzioso di aggregati per spostare una mediana sopra soglia.
  Modifiche ex-post sono dichiarate esplicitamente nei report
  Ragas, con la motivazione che le giustifica.
- **No demo, no marketing.** Il pivot 2026-05-20 ha rimosso demo
  pubblica deployata e video promozionale dai deliverable v1: il
  valore distintivo dichiarato è la metodologia + i numeri, non
  l'UX.

---

## Limiti del sistema

Lista breve dei limiti più rilevanti per chi valuta il sistema. La
versione estesa con riferimenti puntuali ai documenti di benchmark
è in [`docs/architecture/`](docs/architecture/README.md) § "Limiti
noti v1".

- **Citation verifier strutturale, non semantico.** Cattura
  marker malformati ma non riferimenti normativi semanticamente
  sbagliati. La verifica semantica è delegata a Ragas faithfulness
  (mediana 0.886 in F.2).
- **UC4 (provvedimenti Garante) rinviato a v1.1.** Corpus docweb
  eterogeneo fuori scope tecnico v1. Sistema risponde "non trovo
  riferimenti pertinenti" su query Garante (fail-graceful, non
  errore).
- **Query cross-norma con vocabolari disgiunti.** Q5 ("AI per
  decisioni HR + responsabilità 231") e simili restano in
  zero-recall: bge-m3 multilingue non chiude il gap lessicale fra
  vocabolario penale-amministrativo e vocabolario HR. Capability
  v1.1 (multi-query / HyDE / query rewriting LLM-assisted).
- **N=77 positive in v2 non è statisticamente potente per claim
  generali.** Il benchmark caratterizza *questo* sistema su
  *questo* corpus, non costituisce un punto di riferimento
  universale per RAG legal italiano.

Per la lista completa (detection regex obsoleta, topologia MPS
condizionale TODO, EUR-Lex WAF, async/multi-turn/caching post-v1):
[`docs/architecture/`](docs/architecture/README.md) § "Limiti
noti v1".

---

## Disclaimer giuridico

`iuris-rag` **non costituisce consulenza legale**. Le risposte
prodotte dal sistema sono uno strumento di supporto alla ricerca
normativa, da validare sempre con un professionista qualificato
prima di qualunque decisione operativa, contrattuale o di
compliance. Il citation verifier è strutturale: garantisce che
un marker `[cite:CHUNK_ID]` corrisponda a un chunk effettivamente
nel contesto retrieval, non che l'affermazione testuale del modello
sia giuridicamente esatta.

---

## Licenza

Apache 2.0 — vedi [LICENSE](LICENSE).

---

## Citazione

Se usi `iuris-rag` in ricerca, pubblicazione o lavoro derivato:

```bibtex
@software{motzo_iurisrag_2026,
  author  = {Motzo, Federico},
  title   = {iuris-rag: RAG italiano open-source su normativa privacy, AI e cybersecurity},
  year    = {2026},
  version = {0.5.0},
  url     = {https://github.com/fmotzo/iuris-rag}
}
```

Forma testuale:

> Motzo, F. (2026). *iuris-rag: RAG italiano open-source su
> normativa privacy, AI e cybersecurity* (v0.5.0).
> https://github.com/fmotzo/iuris-rag

---

## Contatti

Issue tracker:
[github.com/fmotzo/iuris-rag/issues](https://github.com/fmotzo/iuris-rag/issues).
