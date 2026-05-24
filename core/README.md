# iuris-rag

RAG su normativa italiana per privacy, AI e cybersecurity.

v0.5.0 — beta. Verdict fase G: ready-with-followup (vedi
[BENCHMARK_RAGAS_F2.md](../data/benchmark/BENCHMARK_RAGAS_F2.md)).

Corpus v1: 6 norme primarie (GDPR, AI Act, Codice Privacy, D.Lgs
231/2001, NIS2, L. 132/2025). Input: domanda in italiano. Output:
risposta con citazioni `[cite:CHUNK_ID]` verificate strutturalmente
contro il set di chunk recuperati.

Per il quadro tecnico vedi [`docs/architecture/`](../docs/architecture/README.md);
per metriche e riproducibilità vedi
[`data/benchmark/`](../data/benchmark/BENCHMARK_BASELINE.md).

---

## Installazione

Richiede **Python 3.11+**.

Pubblicazione su PyPI prevista al tag v1.0. Per ora installa da git.

Uso completo (libreria + BM25 backend di default):

```bash
pip install "iuris-rag[runtime] @ git+https://github.com/fmotzo/iuris-rag.git"
```

Solo libreria (porta tu il BM25 backend):

```bash
pip install git+https://github.com/fmotzo/iuris-rag.git
```

Per sviluppo locale:

```bash
git clone https://github.com/fmotzo/iuris-rag.git
cd iuris-rag
pip install -e ".[runtime,dev]"
```

Il pacchetto richiede inoltre:

- **Qdrant** raggiungibile (locale via `docker-compose.yml` o remoto)
- **corpus indicizzato** nella collection `italian_legal_v1_hybrid`
  (procedura in [`BENCHMARK_BASELINE.md`](../data/benchmark/BENCHMARK_BASELINE.md)
  § "Come riprodurre")
- chiave **`ANTHROPIC_API_KEY`** se si usa il provider cloud (default),
  oppure Ollama locale con `qwen2.5:14b` per il fallback offline

---

## Quick start

Setup `.env` (copia da [`.env.example`](../.env.example)):

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
RAG_TOP_K=5
RAG_RERANK_TOP_K=20
```

Query end-to-end (sync):

```python
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder
from fastembed import SparseTextEmbedding

from core.embedding import BgeM3Encoder
from core.hybrid_retriever import HybridRetriever
from core.serving import build_default_pipeline

load_dotenv()

# Modelli (iniettati: lifecycle a carico del caller — vedi serving/README.md).
client = QdrantClient(url="http://localhost:6333")
encoder = BgeM3Encoder()
bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps")

retriever = HybridRetriever(
    client=client, encoder=encoder, bm25=bm25, reranker=reranker
)
pipeline = build_default_pipeline(retriever=retriever)

response = pipeline.query("Quando è obbligatoria la DPIA?")
print(response.annotated_answer)
print(f"Citazioni verificate: {response.verification.n_verified}/{response.verification.n_total}")
print(f"Timings: {response.timings_ms}")
```

Streaming dei token:

```python
for event_type, payload in pipeline.query_stream("Quali compiti del DPO?"):
    if event_type == "chunk":
        print(payload.text, end="", flush=True)
    elif event_type == "final":
        # payload è RAGResponse completo (annotated_answer + verification)
        ...
```

Caveat sulla topologia MPS del reranker (cloud → MPS, Ollama → CPU)
in [`core/serving/README.md`](serving/README.md) § "Topologia MPS".

---

## Moduli pubblici

| Modulo | Scopo | Doc |
|---|---|---|
| `core.italian_legal_parser` | Parser XML Akoma Ntoso (Normattiva) | docstring |
| `core.eur_lex_parser` | Parser HTML EUR-Lex dual-template + Annex III AI Act | docstring |
| `core.normattiva_client` | Transport HTTP Normattiva (session-based) | docstring |
| `core.eur_lex_client` | Transport HTTP EUR-Lex (caveat WAF, vedi limiti) | docstring |
| `core.chunking` | Chunking gerarchico AKN/EUR-Lex (article / recital / annex_point) | docstring |
| `core.embedding` | Wrapper bge-m3 con instruction prefix italiano obbligatorio | docstring |
| `core.vector_store` | Ingestion idempotente UUID v5 + named vectors Qdrant | docstring |
| `core.hybrid_retriever` | Dense + sparse + RRF server-side + reranker post-hoc | docstring |
| `core.terminology` | Query expansion via `aliases.yaml` (sigle DPIA/FRIA/…) | docstring |
| `core.normative_graph` | Espansione 1-hop su 22 link cross-norma curati | docstring |
| `core.citation_verifier` | Validazione strutturale `[cite:CHUNK_ID]`, soft warning | docstring |
| `core.llm_provider` | Astrazione `AnthropicProvider` + `OllamaProvider`, streaming | docstring |
| `core.rag_prompt` | Builder user prompt + loader system prompt italiano | docstring |
| `core.serving` | Pipeline orchestrator end-to-end | [serving/README.md](serving/README.md) |

---

## Configurazione

Variabili principali (lettura via `python-dotenv` o env di sistema).
Lista completa con default e note in [`core/serving/README.md`](serving/README.md)
§ "Configurazione".

| Variabile | Default | Note |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic` o `ollama` |
| `ANTHROPIC_API_KEY` | — | richiesto se `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | |
| `OLLAMA_MODEL` | `qwen2.5:14b` | fallback locale |
| `RAG_TOP_K` | `5` | chunk post-rerank nel prompt |
| `RAG_RERANK_TOP_K` | `20` | candidati al reranker |

Template completo in [`.env.example`](../.env.example).

---

## Limiti noti v0.5.0

Lista ridotta per scelta di adozione. Versione estesa con fonti in
[`docs/architecture/README.md`](../docs/architecture/README.md)
§ "Limiti noti v1".

- **Citation verifier strutturale, non semantico**. La verifica
  semantica è delegata a Ragas (F.2: faith 0.886, rel 0.815 — sopra
  soglie SCOPE). Vedi
  [`BENCHMARK_RAGAS_F2.md`](../data/benchmark/BENCHMARK_RAGAS_F2.md).
- **UC4 Garante rinviato a v1.1**. Corpus docweb eterogeneo fuori
  scope tecnico v1; il sistema risponde "non trovo riferimenti
  pertinenti" alle query Garante.
- **Detection regex "dichiarazione di limite corpus" obsoleta**.
  Drift lessicale 23/23 su F.2; sostituzione con LLM-as-judge in v1.1.
- **Topologia MPS reranker condizionale al provider = TODO non attivo**.
  Il caller deve costruire `CrossEncoder` con device giusto (MPS con
  cloud, CPU con Ollama). Vedi
  [`core/serving/README.md`](serving/README.md) § "Topologia MPS".
- **Ingestion EUR-Lex bloccata da AWS WAF**. Il modulo `core.eur_lex_client`
  funziona contro fixture in cache; il fetch live dei testi UE è
  bloccato da AWS WAF challenge dal 2026-05-18. Workaround: corpus
  v1 fornisce 3 HTML pre-scaricati in `data/cache/eurlex/IT/`.
  Re-evaluation v1.1: Cellar SPARQL endpoint.
- **Niente async, multi-turn, caching risposte**. Pipeline sync con
  streaming, stateless. Tutti rinviati post-v1.

---

## Sviluppo

```bash
git clone https://github.com/fmotzo/iuris-rag.git
cd iuris-rag
pip install -e ".[dev]"
pytest
```

Test che caricano il reranker (~2.3 GB) sono dietro flag esplicito:

```bash
RUN_RERANKER_TESTS=1 pytest -m requires_reranker
```

---

## Licenza

Apache-2.0. Vedi [LICENSE](../LICENSE).

---

## Citazione

Se usi `iuris-rag` in ricerca o pubblicazione:

```bibtex
@software{motzo_iurisrag_2026,
  author  = {Motzo, Federico},
  title   = {iuris-rag: RAG su normativa italiana per privacy, AI e cybersecurity},
  year    = {2026},
  version = {0.5.0},
  url     = {https://github.com/fmotzo/iuris-rag}
}
```

Forma testuale:

> Motzo, F. (2026). *iuris-rag: RAG su normativa italiana per
> privacy, AI e cybersecurity* (v0.5.0).
> https://github.com/fmotzo/iuris-rag
