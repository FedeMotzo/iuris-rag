# Pre-push security audit — italian-legal-rag (futuro iuris-rag)

**Data audit**: 2026-05-21
**Stato repo**: non-git locale, primo `git init && git push` previsto post-rilascio v1.0 (vedi `SCOPE.md` registro 2026-05-21)
**Audit tool**: ispezione manuale + grep ricorsivo + scan PII su `gold_answer`
**Esiti**: per item — severity (BLOCKER | WARNING | INFO) + azione suggerita (DELETE | GITIGNORE | REVIEW | IGNORE)

Nessuna modifica applicata automaticamente. Decisione operativa su delete/gitignore resta manuale.

---

## Tabella sintetica

| # | Item | Severity | Azione |
|---|---|---|---|
| 1 | `.env` con `ANTHROPIC_API_KEY` (108 chars) presente in root | **BLOCKER** | REVIEW (è in .gitignore — verificare che non sia stato staged prima del primo commit; valutare rotation post-push) |
| 2 | `.ragas_cache/` (480K) e `.ragas_cache_v2/` (1.2M) — SQLite cache API responses | WARNING | GITIGNORE |
| 3 | `.ruff_cache/` (12K) — cache linter | WARNING | GITIGNORE |
| 4 | `data/qdrant_w2_baseline.tar.gz` (8.2M) — backup non coperto dalla regola `data/qdrant/` | WARNING | GITIGNORE (o DELETE se baseline è ricostruibile dal codice) |
| 5 | `data/cache/eurlex/` (2.5M) + `data/cache/normattiva/` (2.8M) — sorgenti normative scaricate | WARNING | REVIEW (decidere se committare come fallback ufficiale post-WAF o gitignore) |
| 6 | `.DS_Store` non coperto da .gitignore (assente oggi ma macOS-recurrent) | WARNING | GITIGNORE (preventivo) |
| 7 | Credenziali hardcoded in `core/`, `spike/`, `scripts/` (.py / .yaml / .json) | INFO | IGNORE (0 match) |
| 8 | Editor configs personali (`.vscode/`, `.idea/`, `.vim/`) | INFO | IGNORE (0 trovati) |
| 9 | PII reali in `gold_answer` (CF, P.IVA, email, phone, IBAN, nomi propri) | INFO | IGNORE (0 match su v1+v2) |
| 10 | `__pycache__/` (21 dir) | INFO | IGNORE (già coperto da .gitignore) |
| 11 | `data/qdrant/` (64M binary storage) | INFO | IGNORE (già coperto da .gitignore) |
| 12 | `.pytest_cache/` (32K) | INFO | IGNORE (già coperto da .gitignore) |
| 13 | `.gitignore` esistente — copertura | INFO | REVIEW (vedi sezione dedicata) |

---

## 1. File .env — BLOCKER

**File**: `.env` (495 byte), `.env.example` (628 byte)

`.env` contiene:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=<108 chars — chiave reale Anthropic>
ANTHROPIC_MODEL=claude-sonnet-4-6
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
OLLAMA_NUM_CTX=8192
```

La chiave `ANTHROPIC_API_KEY` di 108 caratteri è una **chiave Anthropic reale e funzionante** (formato `sk-ant-...`). Usata nei run F.2 ($6.82 spesi su questa key, vedi `BENCHMARK_RAGAS_F2.md`).

**Stato gitignore**: `.env` è coperto dalla riga `.env` di `.gitignore` ✓.

**`.env.example` è committato senza valori sensibili** (i campi `ANTHROPIC_API_KEY=` sono vuoti) ✓.

**Severity**: BLOCKER pre-push. Anche se gitignore lo copre, va verificato che:
1. Quando si farà `git init && git add .`, `.env` non finisca nello stage per nessun motivo (es. `git add -f .env` accidentale, glob che lo include).
2. Eseguire `git status` dopo il primo `add .` e confermare che `.env` appaia in untracked/ignored, **non** in changes to be committed.
3. Se per qualsiasi motivo `.env` finisce in un commit (anche locale), il rimedio è `git rm --cached .env` + nuovo commit, ma è già rischio: il primo push pubblico cristallizza la chiave nello storia se non si fa squash. Valutare rotation della key Anthropic post-push come misura di igiene (la key è stata trasmessa al machine builder, ai backup macOS, eventualmente ad agenti AI durante i task) anche se non c'è evidenza di leak.

**Azione suggerita**: REVIEW + verifica `git status` pre-commit + decisione su rotation post-push.

---

## 2. Cache Ragas — WARNING

**File**: `.ragas_cache/cache.db` (480K) + `.ragas_cache_v2/cache.db` (1.2M)

Entrambi sono cache SQLite di Ragas. Hex dump di `.ragas_cache_v2/cache.db` mostra header SQLite standard. Non ho ispezionato il contenuto interno, ma per design Ragas cacha:
- prompt inviati al judge LLM (faithfulness extraction, faithfulness verification, answer_relevancy generation)
- risposte ricevute

Quindi le cache **possono contenere**:
- testo di tutte le 100 query del benchmark (già pubblico — è in `gold_answers_v2.json`)
- testo delle 100 risposte pipeline (già pubblico — è in `ragas_pipeline_outputs_v2.json`)
- testo dei chunk recuperati (già pubblico — corpus normativo)
- **eventuali metadata API Anthropic** (request_id, timing) — non secret in sé ma debug info

Non sono secret keys. Ma sono bloat e duplicano informazioni già in JSON. NOT in `.gitignore`.

**Stato gitignore**: NON coperto.

**Azione suggerita**: GITIGNORE. Aggiungere `.ragas_cache/` e `.ragas_cache_v2/` (o pattern generico `.ragas_cache*/`).

---

## 3. Cache Ruff — WARNING

**File**: `.ruff_cache/` (12K, 3 file)

Cache standard del linter Ruff. Zero contenuto sensibile. Bloat puro.

**Stato gitignore**: NON coperto.

**Azione suggerita**: GITIGNORE.

---

## 4. Backup Qdrant W2 — WARNING

**File**: `data/qdrant_w2_baseline.tar.gz` (8.2M)

Tar.gz del Qdrant storage al baseline W2 (probabilmente snapshot pre-W3 per
poter rilanciare il confronto W2 vs W3 in modo deterministico).

`.gitignore` ha `data/qdrant/` (con trailing slash) — NON copre file
fratelli come `data/qdrant_w2_baseline.tar.gz`. La regola dovrebbe essere
`data/qdrant*` per essere completa.

**Severity**: WARNING. Non è secret ma 8.2M di binario non vanno in git.

**Azione suggerita**:
- GITIGNORE (modificare `data/qdrant/` → `data/qdrant*` per coprire entrambi)
- DELETE se il baseline è ricostruibile da script (vedi
  `BENCHMARK_BASELINE.md` § "Come riprodurre") — l'avere il snapshot è una
  convenience, non un asset necessario.

---

## 5. Cache normative scaricate — WARNING

**File**:
- `data/cache/eurlex/` (2.5M) — HTML EUR-Lex (GDPR consolidata, GDPR iniziale, AI Act iniziale)
- `data/cache/normattiva/` (2.8M) — XML AKN Normattiva (Codice Privacy, 231, NIS2, L. 132/2025)

Sono i sorgenti normativi scaricati una tantum dai parser. Per design v1 sono il "corpus statico" — vedi `PROJECT_CONTEXT.md` voce 15: l'`eur_lex_client` è bloccato da AWS WAF al 2026-05-18, quindi i fixture HTML in `data/cache/eurlex/IT/` sono il workaround di v1.

**Profilo licenza**:
- EUR-Lex: contenuto re-usable secondo policy "free reuse" della UE (https://eur-lex.europa.eu/content/legal-notice). Citare la fonte.
- Normattiva XML AKN: norme italiane in formato open. Riusabile.

Quindi committarli non è violazione legale. Ma è 5.3M di dati che potrebbero essere ricostruiti da `normattiva_client` / `eur_lex_client`. Trade-off:

- **Pro commit**: il workaround AWS WAF di EUR-Lex (PROJECT_CONTEXT voce 15) dipende dai fixture statici → senza i file in repo, il client EUR-Lex non funziona per chi clona; il benchmark non è riproducibile senza re-download manuale.
- **Contro commit**: 5.3M binari nel repo, replicabilità via codice persa.

**Severity**: WARNING (decisione di design, non bug).

**Azione suggerita**: REVIEW. Tre opzioni:
1. Commit con disclaimer in `CORPUS_OVERVIEW.md` su licenza + fonte (raccomandato per riproducibilità).
2. GITIGNORE + script di download riproducibile (`scripts/download_corpus.py`) + istruzioni in `BENCHMARK_BASELINE.md` § "Come riprodurre".
3. Commit del solo EUR-Lex (bloccato da WAF, quindi necessario per riproducibilità) + GITIGNORE del Normattiva (ri-scaricabile via `normattiva_client`).

---

## 6. `.DS_Store` — WARNING

Nessun `.DS_Store` attualmente presente nel repo. Ma è macOS-recurrent: ogni `cd` in Finder ne può creare uno.

**Stato gitignore**: NON coperto.

**Azione suggerita**: GITIGNORE preventivo (`.DS_Store` e `**/.DS_Store`).

---

## 7. Credenziali hardcoded — INFO (0 match)

Scan ricorsivo su `.py`, `.yaml`, `.yml`, `.json`, `.md`, `.toml` in tutto il repo (escluse `.venv/`, `.pytest_cache/`, `.ragas_cache*/`):

| pattern | match |
|---|---:|
| `sk-ant-[A-Za-z0-9_-]{10,}` (Anthropic) | 0 |
| `sk-(proj-\|live-\|test-)?[A-Za-z0-9_-]{20,}` (OpenAI/altre) | 0 |
| `Bearer +[A-Za-z0-9_.-]{15,}` (token in header) | 0 |
| `(api_key\|secret\|password\|access_token)\s*[:=]\s*"[...]"` con valore ≥12 char | 0 |

Tutti i secret sono correttamente esternalizzati in `.env`. Nessuna credenziale hardcoded nel codice di `core/`, `spike/`, `scripts/`.

**Azione suggerita**: IGNORE.

---

## 8. Editor configs personali — INFO (0 match)

Cercati: `.vscode/`, `.idea/`, `.vim/`, `*.swp`, `*.swo`, `Thumbs.db`, `Desktop.ini` — nessuno presente.

**Azione suggerita**: IGNORE.

---

## 9. PII in `gold_answer` — INFO (0 match)

Scan su `gold_answers_v1.json` (50 entry) + `gold_answers_v2.json` (100 entry) per:

| pattern | v1 | v2 |
|---|---:|---:|
| Codice fiscale italiano (formato `XXXXXX99X99X999X`) | 0 | 0 |
| P.IVA (11 cifre standalone) | 0 | 0 |
| Email (`x@y.z`) | 0 | 0 |
| Telefono italiano (`+39 xxx`, `3xx xxx xxxx`) | 0 | 0 |
| IBAN italiano (`IT99X22caratteri`) | 0 | 0 |
| Titoli + nome (`Sig./Dott./Avv./Prof. X`) | 0 | 0 |

Le `gold_answer` sono genuinamente generiche, come da disegno di curatela (vedi `BENCHMARK_V2_CURATION_BRIEF.md`). Nessun PII reale infiltrato.

**Azione suggerita**: IGNORE.

---

## 10. `__pycache__/` — INFO

21 directory `__pycache__/` distribuite per i moduli `core/` + `tests/` + `spike/`. Tutte coperte da `.gitignore` (`__pycache__/`).

**Azione suggerita**: IGNORE.

---

## 11. Qdrant binary storage `data/qdrant/` — INFO

64MB totali in `data/qdrant/collections/italian_legal_v1*/` (~30 file da 32MB ciascuno: WAL, payload storage, vector storage dense+bm25). Coperto da `.gitignore` con la regola `data/qdrant/`.

Lato sicurezza: contiene gli embedding del corpus pubblico, nessun dato personale. Lato bloat: 64MB sono troppi per git, gitignore è la scelta giusta.

**Azione suggerita**: IGNORE.

---

## 12. `.pytest_cache/` — INFO

32K. Coperto da `.gitignore`.

**Azione suggerita**: IGNORE.

---

## 13. Stato `.gitignore` esistente — REVIEW

Contenuto attuale (9 righe sostantive):

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/

# Qdrant local storage
data/qdrant/

# Secrets (l'env.example committato, .env no)
.env
```

**Coperto** ✓: `__pycache__/`, `*.py[cod]`, `*.egg-info/`, `.pytest_cache/`, `.venv/`, `data/qdrant/`, `.env`

**Non coperto** ✗ (da aggiungere):
- `.ragas_cache/` e `.ragas_cache_v2/` (o pattern `.ragas_cache*/`)
- `.ruff_cache/`
- `.DS_Store` e `**/.DS_Store`
- `data/qdrant_w2_baseline.tar.gz` (estendere `data/qdrant/` → `data/qdrant*` per coprire)
- `data/cache/` (in attesa decisione item 5)
- Eventuali `*.swp`, `*.swo`, `.idea/`, `.vscode/` (preventivi)
- `dist/`, `build/`, `*.egg-info/` (già presente ma per packaging pip futuro)

**Patch suggerita** (append-only sul .gitignore esistente, evita rewriting):

```gitignore

# Tool caches
.ragas_cache/
.ragas_cache_v2/
.ruff_cache/

# macOS / editor
.DS_Store
**/.DS_Store
*.swp
*.swo
.vscode/
.idea/

# Build artifacts (per packaging pip futuro v1.0)
dist/
build/

# Qdrant baseline backup (ricostruibile da script, vedi BENCHMARK_BASELINE.md)
data/qdrant*

# Cache normative scaricate (decisione condizionale — vedi audit item 5)
# data/cache/
```

L'ultima riga è commentata in attesa della decisione su item 5.

---

## Sintesi pre-push

**Da risolvere prima del primo `git push`**:

1. **BLOCKER**: confermare che `.env` non finisca nel primo commit. Eseguire `git status` dopo `git add .` e verificare che `.env` sia in untracked/ignored. Considerare rotation della key Anthropic post-push.
2. **WARNING × 5**: aggiornare `.gitignore` con i pattern mancanti (`.ragas_cache*/`, `.ruff_cache/`, `.DS_Store`, `data/qdrant*`, eventualmente `data/cache/`).
3. **WARNING singolo decisione di design**: decidere se committare `data/cache/` (sorgenti EUR-Lex+Normattiva) come asset di riproducibilità o gitignore + script di download.

**Pulito**:

- 0 credenziali hardcoded nel codice (8 pattern controllati)
- 0 PII in `gold_answer` v1 e v2 (6 pattern controllati)
- 0 editor configs personali
- gitignore esistente copre correttamente Python + Qdrant binary + `.env`

Nessuna azione automatica eseguita. Tutte le decisioni di delete / gitignore restano a Federico.
