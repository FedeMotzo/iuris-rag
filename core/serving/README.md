# `core/serving` — pipeline RAG end-to-end

Orchestratore retrieval → rerank → generate → citation_verify.
Compone i moduli core (`hybrid_retriever`, `llm_provider`, `rag_prompt`,
`citation_verifier`) in un'unica pipeline configurabile via `.env`.

## Uso

```python
from core.serving import build_default_pipeline

# Il retriever va costruito dal caller (richiede QdrantClient,
# BgeM3Encoder, fastembed BM25, CrossEncoder reranker).
pipeline = build_default_pipeline(retriever=my_retriever)

response = pipeline.query("Quando è obbligatoria la DPIA?")
print(response.annotated_answer)
print(response.timings_ms)
print(f"Verificate: {response.verification.n_verified}/{response.verification.n_total}")
```

Streaming:

```python
for event_type, payload in pipeline.query_stream("Quali compiti del DPO?"):
    if event_type == "chunk":
        print(payload.text, end="", flush=True)
    elif event_type == "final":
        # payload è RAGResponse completo con annotated_answer + verification
        ...
```

## Configurazione (`.env`)

| Variabile | Default | Note |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic` o `ollama` |
| `ANTHROPIC_API_KEY` | — | richiesto se `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | |
| `OLLAMA_MODEL` | `qwen2.5:14b` | |
| `OLLAMA_NUM_CTX` | `8192` | |
| `RAG_TOP_K` | `5` | chunk post-rerank nel prompt |
| `RAG_RERANK_TOP_K` | `20` | candidati al reranker |
| `RAG_USE_GRAPH` | `false` | espansione 1-hop `normative_graph` |
| `RAG_MAX_OUTPUT_TOKENS` | `1000` | alzato da 500 dopo smoke cloud 2026-05-19 (vedi `PROJECT_CONTEXT.md` voce 29) |

## Architettura

```
              HybridRetriever
                    │
                    ▼
              RetrievalResult
              (top-K + optional expanded)
                    │
                    ▼
            rag_prompt.builder
                    │
                    ▼
           LLMProvider.generate_stream
                    │
                    ▼
           GenerationResult.text
                    │
                    ▼
        citation_verifier.verify_citations
                    │
                    ▼
               RAGResponse
```

Il citation verifier gira **dopo** lo stream completo, perché lavora
su testo intero (regex `[cite:CHUNK_ID]` + lookup nel set di
`chunk_id` del retrieval, inclusi expanded chunks se `use_graph=True`).

## Topologia MPS

La topologia ottimale del reranker dipende dal provider LLM attivo
(vedi `spike/MPS_COABITATION_RESULTS.md`):

- `provider=anthropic` → reranker su **MPS** (Qwen non in memoria)
- `provider=ollama` → reranker su **CPU** (libera 3 GB MPS per Qwen)

**Oggi non attivo**: `HybridRetriever` non espone `reranker_device`
nel costruttore. TODO esplicito in `core/serving/config.py`. Il caller
costruisce manualmente il `CrossEncoder` con il device giusto quando
serve (es. gli smoke script in `spike/`).

## Limiti noti v1

- **Citation verifier è strutturale, non semantico**. Cattura marker
  malformati ma non riferimenti normativi sbagliati (es. modello cita
  considerando invece di articolo quando entrambi nel contesto). La
  verifica semantica è W7 (Ragas). Smoke cloud su Sonnet 4.6 ha
  mostrato qualità citazione semantica alta out-of-the-box; smoke
  locale su Qwen 14B ha mostrato il caso atteso (Q1 cita considerando
  invece di art. 6) — vedi `spike/SMOKE_RAG_PIPELINE_RESULTS.md`.
- **Expanded chunks dal graph entrano come pointer** (`chunk_id` +
  relation + note), non come testo completo. Il modello può citarli
  anche senza averne letto il contenuto: citazione formalmente
  verified ma semanticamente vuota. Da catturare in Ragas W7.
- **Niente async, niente conversation history / multi-turn, niente
  caching delle risposte**. Tutti rimandati post-v1.
