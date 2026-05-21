"""Spike — Italian Legal RAG. Codice usa-e-getta, NON entra in produzione.

Sezione 1 — Parser Normattiva (Codice Privacy D.Lgs 196/2003)
Sezione 2 — Embedding bge-m3 (TODO)
Sezione 3 — Minerva via Ollama (TODO)
Sezione 4 — End-to-end mini-RAG (TODO)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SPIKE_DIR = Path(__file__).parent
DATA_DIR = SPIKE_DIR / "data"
SOURCE_MD = DATA_DIR / "codice_privacy.md"
PARSED_JSON = DATA_DIR / "codice_privacy_parsed.json"
EMBEDDING_RESULTS = DATA_DIR / "embedding_results.json"
MINERVA_RESULTS = DATA_DIR / "minerva_results.json"
MINERVA_RESULTS_V2 = DATA_DIR / "minerva_results_v2.json"
E2E_RESULTS = DATA_DIR / "e2e_results.json"
COMPARISON_RESULTS = DATA_DIR / "comparison_minerva_vs_qwen.json"
AKN_XML = DATA_DIR / "codice_privacy_akn.xml"
AKN_REPORT = DATA_DIR / "akn_report.json"


# ---------------------------------------------------------------------------
# Sezione 1 — Parser Normattiva
# ---------------------------------------------------------------------------

ART_HEADER_RE = re.compile(r"^###\s+Art\.\s*([0-9]+(?:[-‑][a-zA-Zàèéìòù]+)*)\b\.?\s*[-–—]?\s*(.*)$")
H2_RE = re.compile(r"^##\s+(.+)$")
H4_RE = re.compile(r"^####\s+(.+)$")
FRONT_MATTER_RE = re.compile(r"^---\s*$")

# Commi: "1.", "2.", "1-bis.", "((1.", "1-bis. "
COMMA_RE = re.compile(r"^\(?\(?(\d+(?:-[a-z]+)?)\.\s+")
# Lettere: "- a)", "- b-bis)"
LETTERA_RE = re.compile(r"^\s*-\s+([a-z](?:-[a-z]+)?)\)")
# Note di aggiornamento in fondo agli articoli
AGGIORNAMENTO_RE = re.compile(r"^AGGIORNAMENTO\s+\((\d+)\)")
# Modifiche legislative inline: testo dentro ((...))
MODIFICA_RE = re.compile(r"\(\((.+?)\)\)", re.DOTALL)


def parse_front_matter(lines: list[str]) -> tuple[dict, int]:
    """Estrae il front matter YAML grezzo (chiave: valore). Ritorna (meta, prima_riga_corpo)."""
    if not lines or not FRONT_MATTER_RE.match(lines[0]):
        return {}, 0
    meta = {}
    i = 1
    while i < len(lines) and not FRONT_MATTER_RE.match(lines[i]):
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", lines[i])
        if m:
            meta[m.group(1)] = m.group(2).strip()
        i += 1
    return meta, i + 1  # salta il "---" di chiusura


def split_articolo_body(body_lines: list[str]) -> dict:
    """Spezza il corpo di un articolo in: commi numerati, note di aggiornamento, raw."""
    commi: list[dict] = []
    aggiornamenti: list[dict] = []
    current_comma: dict | None = None
    in_aggiornamento: dict | None = None

    for line in body_lines:
        line_stripped = line.strip()
        if not line_stripped:
            if current_comma is not None:
                current_comma["testo"] += "\n"
            continue

        # Inizio nota di aggiornamento
        agg_match = AGGIORNAMENTO_RE.match(line_stripped)
        if agg_match:
            current_comma = None
            in_aggiornamento = {"numero": agg_match.group(1), "testo": line_stripped}
            aggiornamenti.append(in_aggiornamento)
            continue

        # Se siamo dentro un aggiornamento, continuiamo ad accumularne il testo
        if in_aggiornamento is not None:
            if AGGIORNAMENTO_RE.match(line_stripped):
                in_aggiornamento = {"numero": AGGIORNAMENTO_RE.match(line_stripped).group(1), "testo": line_stripped}
                aggiornamenti.append(in_aggiornamento)
            else:
                in_aggiornamento["testo"] += " " + line_stripped
            continue

        # Inizio di un comma numerato
        comma_match = COMMA_RE.match(line_stripped)
        if comma_match:
            current_comma = {"numero": comma_match.group(1), "testo": line_stripped}
            commi.append(current_comma)
            continue

        # Continuazione del comma (lettere o testo)
        if current_comma is not None:
            current_comma["testo"] += "\n" + line_stripped

    # Pulizia spazi superflui
    for c in commi:
        c["testo"] = c["testo"].strip()
    for a in aggiornamenti:
        a["testo"] = a["testo"].strip()

    return {"commi": commi, "aggiornamenti": aggiornamenti}


def clean_rubrica(raw: str) -> str:
    """La rubrica originale è del tipo '(( (Oggetto). ))' o '(Base giuridica per...)'.
    Restituisce il testo nucleo senza parentesi/markup."""
    s = raw.strip()
    s = re.sub(r"\(\(", "", s)
    s = re.sub(r"\)\)", "", s)
    s = s.strip().rstrip(".").strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    return s.rstrip(".").strip()


def parse_codice_privacy(md_text: str) -> dict:
    """Parser MD → JSON. Output:
    {
      "metadata": {...},
      "sezioni_h2_uniche": [...],
      "articoli": [{"numero": "2-bis", "section_raw": "...", "rubrica": "...",
                    "commi": [...], "aggiornamenti": [...], "raw_body": "..."}],
      "statistiche": {...}
    }
    """
    lines = md_text.splitlines()
    meta, body_start = parse_front_matter(lines)

    current_section = None  # ultimo H2 visto (raw)
    articoli: list[dict] = []
    sezioni_h2_uniche: list[str] = []
    in_article: dict | None = None
    body_buffer: list[str] = []
    in_allegati = False

    def flush_article():
        if in_article is None:
            return
        in_article["raw_body"] = "\n".join(body_buffer).strip()
        in_article.update(split_articolo_body(body_buffer))
        articoli.append(in_article)

    for line in lines[body_start:]:
        # H2 — Titolo/Capo/Sezione (gerarchia compressa in una stringa)
        h2 = H2_RE.match(line)
        if h2:
            flush_article()
            in_article = None
            body_buffer = []
            current_section = h2.group(1).strip()
            if current_section not in sezioni_h2_uniche:
                sezioni_h2_uniche.append(current_section)
            if current_section.lower().startswith("allegati") or current_section.lower().startswith("allegato"):
                in_allegati = True
            continue

        # H3 — articolo
        art_match = ART_HEADER_RE.match(line)
        if art_match:
            flush_article()
            numero = art_match.group(1).strip()
            rubrica_raw = art_match.group(2).strip()
            in_article = {
                "numero": numero,
                "section_raw": current_section,
                "in_allegati": in_allegati,
                "rubrica_raw": rubrica_raw,
                "rubrica": clean_rubrica(rubrica_raw),
            }
            body_buffer = []
            continue

        # Tutto il resto: accumula nel corpo dell'articolo corrente
        if in_article is not None:
            body_buffer.append(line)

    flush_article()

    # Statistiche
    numeri = [a["numero"] for a in articoli]
    unique_numeri = sorted(set(numeri))
    duplicati = {n: numeri.count(n) for n in unique_numeri if numeri.count(n) > 1}
    n_corpo = sum(1 for a in articoli if not a["in_allegati"])
    n_allegati = sum(1 for a in articoli if a["in_allegati"])

    return {
        "metadata": meta,
        "sezioni_h2_uniche": sezioni_h2_uniche,
        "articoli": articoli,
        "statistiche": {
            "articoli_totali": len(articoli),
            "articoli_unici_per_numero": len(unique_numeri),
            "articoli_corpo_principale": n_corpo,
            "articoli_negli_allegati": n_allegati,
            "duplicati_per_numero": duplicati,
            "sezioni_h2": len(sezioni_h2_uniche),
        },
    }


def main_sezione_1():
    print("=== Sezione 1 — Parser Normattiva ===\n")
    md_text = SOURCE_MD.read_text(encoding="utf-8")
    parsed = parse_codice_privacy(md_text)

    stats = parsed["statistiche"]
    print(f"Articoli totali estratti: {stats['articoli_totali']}")
    print(f"  - nel corpo principale: {stats['articoli_corpo_principale']}")
    print(f"  - negli allegati:       {stats['articoli_negli_allegati']}")
    print(f"Articoli unici per numero: {stats['articoli_unici_per_numero']}")
    print(f"Sezioni H2 uniche: {stats['sezioni_h2']}")
    print(f"Numeri articolo che si ripetono: {len(stats['duplicati_per_numero'])}")
    print()

    # Mostra esempio di articolo strutturato (Art. 2-bis "Autorità di controllo")
    esempio = next((a for a in parsed["articoli"] if a["numero"] == "2-bis"), None)
    if esempio:
        print("--- ESEMPIO: Art. 2-bis ---")
        print(json.dumps({
            "numero": esempio["numero"],
            "rubrica": esempio["rubrica"],
            "section_raw": esempio["section_raw"],
            "commi": esempio["commi"],
            "aggiornamenti": esempio["aggiornamenti"],
        }, ensure_ascii=False, indent=2))
        print()

    # Salva JSON completo
    PARSED_JSON.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Output salvato in: {PARSED_JSON.relative_to(SPIKE_DIR)}")
    return parsed


# ---------------------------------------------------------------------------
# Sezione 2 — Embedding bge-m3 su concetti legali italiani
# ---------------------------------------------------------------------------

# Soglie per la valutazione del livello di similarità atteso
SOGLIA_ALTO = 0.75
SOGLIA_BASSO = 0.55

COPPIE_TEST: list[tuple[str, str, str]] = [
    ("trattamento dei dati personali", "elaborazione dei dati personali", "alto"),
    ("responsabile del trattamento", "data controller", "alto"),
    ("responsabile del trattamento", "responsabile della protezione dei dati", "medio"),
    ("DPIA", "valutazione d'impatto sulla protezione dei dati", "alto"),
    ("sistema ad alto rischio", "sistema vietato", "medio"),
    ("consenso esplicito", "informativa privacy", "basso"),
    ("trasferimento extra-UE", "data transfer outside EU", "alto"),
    ("Garante Privacy", "Autorità di Controllo", "alto"),
    ("minore di 14 anni", "trattamento di dati di minori", "medio"),
    ("cookie tecnici", "cookie di profilazione", "medio"),
    ("DPO", "responsabile della protezione dei dati", "alto"),
    ("decisione automatizzata", "profilazione", "medio"),
    ("violazione dei dati personali", "data breach", "alto"),
    ("base giuridica", "finalità del trattamento", "basso"),
    ("AI Act", "Regolamento sull'intelligenza artificiale", "alto"),
]


def classifica_similarity(sim: float) -> str:
    if sim > SOGLIA_ALTO:
        return "alto"
    if sim >= SOGLIA_BASSO:
        return "medio"
    return "basso"


def pick_device() -> str:
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def main_sezione_2():
    import time
    import torch
    from sentence_transformers import SentenceTransformer, util

    print("=== Sezione 2 — Embedding bge-m3 su concetti legali italiani ===\n")

    device = pick_device()
    dtype = torch.float32  # MPS può essere instabile in float16; per spike teniamo float32
    print(f"Device: {device} | dtype: {dtype}")

    t0 = time.perf_counter()
    print("Caricamento modello BAAI/bge-m3 (prima volta ~2 GB di download)...")
    model = SentenceTransformer("BAAI/bge-m3", device=device)
    t_load = time.perf_counter() - t0
    print(f"Modello caricato in {t_load:.1f}s\n")

    # Encoding di tutti i concetti in batch (più efficiente di coppia-per-coppia)
    frasi_a = [c[0] for c in COPPIE_TEST]
    frasi_b = [c[1] for c in COPPIE_TEST]

    t0 = time.perf_counter()
    emb_a = model.encode(frasi_a, convert_to_tensor=True, normalize_embeddings=True)
    emb_b = model.encode(frasi_b, convert_to_tensor=True, normalize_embeddings=True)
    t_encode = time.perf_counter() - t0
    n_coppie = len(COPPIE_TEST)
    tempo_medio_per_coppia = t_encode / n_coppie
    print(f"Encoding di {2 * n_coppie} frasi in {t_encode:.2f}s "
          f"(media per coppia: {tempo_medio_per_coppia * 1000:.0f} ms)\n")

    # cos_sim restituisce una matrice [N x N]; ci interessa la diagonale
    sim_matrix = util.cos_sim(emb_a, emb_b)
    similarities = [float(sim_matrix[i, i]) for i in range(n_coppie)]

    # Tabella + raccolta risultati
    risultati: list[dict] = []
    coerenti = 0
    print(f"{'#':>2}  {'A':<48} {'B':<48} {'sim':>6}  {'atteso':<6} {'osservato':<9} {'esito':<3}")
    print("-" * 130)
    for i, ((a, b, atteso), sim) in enumerate(zip(COPPIE_TEST, similarities), start=1):
        osservato = classifica_similarity(sim)
        ok = osservato == atteso
        coerenti += int(ok)
        print(f"{i:>2}  {a[:48]:<48} {b[:48]:<48} {sim:>6.3f}  "
              f"{atteso:<6} {osservato:<9} {'OK' if ok else 'NO':<3}")
        risultati.append({
            "n": i,
            "concetto_a": a,
            "concetto_b": b,
            "similarity": round(sim, 4),
            "atteso": atteso,
            "osservato": osservato,
            "coerente": ok,
        })

    print()
    if coerenti >= 12:
        verdetto = "PASS"
    elif coerenti >= 9:
        verdetto = "PARTIAL"
    else:
        verdetto = "FAIL"
    print(f"Coppie coerenti con l'atteso: {coerenti}/{n_coppie}  →  {verdetto}")
    print(f"Soglie: alto > {SOGLIA_ALTO}, medio {SOGLIA_BASSO}-{SOGLIA_ALTO}, basso < {SOGLIA_BASSO}")
    print(f"Tempo medio encoding per coppia: {tempo_medio_per_coppia * 1000:.0f} ms")
    print(f"Device: {device} | precisione: float32")

    output = {
        "modello": "BAAI/bge-m3",
        "device": device,
        "dtype": "float32",
        "n_coppie": n_coppie,
        "coerenti": coerenti,
        "verdetto": verdetto,
        "soglie": {"alto": SOGLIA_ALTO, "basso": SOGLIA_BASSO},
        "tempi": {
            "caricamento_modello_s": round(t_load, 2),
            "encoding_totale_s": round(t_encode, 2),
            "encoding_medio_per_coppia_ms": round(tempo_medio_per_coppia * 1000, 1),
        },
        "risultati": risultati,
    }
    EMBEDDING_RESULTS.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOutput salvato in: {EMBEDDING_RESULTS.relative_to(SPIKE_DIR)}")
    return output


# ---------------------------------------------------------------------------
# Sezione 2b — bge-m3 con prompt/instruction (test rapido sui sinonimi-sigla)
# ---------------------------------------------------------------------------

VARIANTI_PROMPT: list[tuple[str, str | None]] = [
    ("base", None),  # come Sezione 2 — baseline di controllo
    ("instr_IT", "Rappresenta questo concetto giuridico italiano per la ricerca semantica: "),
    ("instr_EN", "Represent this Italian legal concept for retrieval: "),
]


def main_sezione_2b():
    import time
    from sentence_transformers import SentenceTransformer, util

    print("=== Sezione 2b — bge-m3 con prompt/instruction ===\n")
    device = pick_device()
    print(f"Device: {device} | dtype: float32\n")

    t0 = time.perf_counter()
    model = SentenceTransformer("BAAI/bge-m3", device=device)
    print(f"Modello caricato in {time.perf_counter() - t0:.1f}s\n")

    frasi_a = [c[0] for c in COPPIE_TEST]
    frasi_b = [c[1] for c in COPPIE_TEST]

    per_variante: dict[str, dict] = {}

    for nome, prompt in VARIANTI_PROMPT:
        kwargs = {"convert_to_tensor": True, "normalize_embeddings": True}
        if prompt:
            kwargs["prompt"] = prompt
        emb_a = model.encode(frasi_a, **kwargs)
        emb_b = model.encode(frasi_b, **kwargs)
        sims = [float(util.cos_sim(emb_a[i], emb_b[i])) for i in range(len(COPPIE_TEST))]
        coerenti = 0
        righe = []
        for (a, b, atteso), sim in zip(COPPIE_TEST, sims):
            oss = classifica_similarity(sim)
            ok = oss == atteso
            coerenti += int(ok)
            righe.append({"a": a, "b": b, "sim": round(sim, 4), "atteso": atteso, "osservato": oss, "coerente": ok})
        per_variante[nome] = {"coerenti": coerenti, "righe": righe, "prompt": prompt}

    # Tabella comparativa: similarity per ogni coppia x variante
    print(f"{'#':>2}  {'A':<42} {'B':<42} " + " ".join(f"{n:>10}" for n, _ in VARIANTI_PROMPT) + f"  {'atteso':<6}")
    print("-" * (2 + 2 + 42 + 1 + 42 + 1 + 11 * len(VARIANTI_PROMPT) + 2 + 6))
    for i, (a, b, atteso) in enumerate(COPPIE_TEST, start=1):
        sims_riga = [per_variante[n]["righe"][i - 1]["sim"] for n, _ in VARIANTI_PROMPT]
        ok_riga = [per_variante[n]["righe"][i - 1]["coerente"] for n, _ in VARIANTI_PROMPT]
        cells = []
        for sim, ok in zip(sims_riga, ok_riga):
            mark = "✓" if ok else "✗"
            cells.append(f"{sim:>7.3f}{mark:>3}")
        print(f"{i:>2}  {a[:42]:<42} {b[:42]:<42} " + " ".join(cells) + f"  {atteso:<6}")

    print()
    for n, _ in VARIANTI_PROMPT:
        c = per_variante[n]["coerenti"]
        verdetto = "PASS" if c >= 12 else ("PARTIAL" if c >= 9 else "FAIL")
        print(f"  {n:<10}: {c}/15  →  {verdetto}")

    out_path = DATA_DIR / "embedding_results_prompts.json"
    out_path.write_text(json.dumps({"device": device, "varianti": per_variante}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOutput salvato in: {out_path.relative_to(SPIKE_DIR)}")
    return per_variante


# ---------------------------------------------------------------------------
# Sezione 3 — Minerva-7B-instruct via Ollama
# ---------------------------------------------------------------------------

MINERVA_MODEL = "hf.co/sapienzanlp/Minerva-7B-instruct-v1.0-GGUF:Q6_K"

PROMPT_TEST = [
    "Spiega in 100 parole l'art. 5 del GDPR (principi del trattamento dei dati personali).",
    "Cosa è una DPIA? Quando è obbligatoria? Rispondi in modo conciso.",
    "Qual è la differenza tra Titolare e Responsabile del trattamento ai sensi del GDPR?",
    "Riassumi in 3 punti i sistemi ad alto rischio secondo l'AI Act.",
    "Come si applica il D.Lgs 231/2001 alle decisioni automatizzate prese da sistemi AI?",
]


SYSTEM_MSG_BENCHMARK = (
    "Sei un assistente esperto in normativa italiana sulla protezione dei dati personali. "
    "Rispondi in italiano corretto, in modo conciso e professionale."
)


def _strip_stop_tokens(text: str) -> str:
    """Filtra eventuali stop tokens ChatML non catturati da Ollama."""
    for tok in ("<|im_end|>", ">|im_end|>", "<|im_start|>"):
        text = text.replace(tok, "")
    return text.strip()


def benchmark_prompt(client, model: str, prompt: str, system_msg: str | None = None) -> dict:
    """Esegue un prompt in streaming via chat (con chat template) e raccoglie metriche."""
    import time

    t_start = time.perf_counter()
    t_first_token: float | None = None
    text_chunks: list[str] = []
    final_chunk: dict | None = None

    messages: list[dict] = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    messages.append({"role": "user", "content": prompt})

    stream = client.chat(
        model=model,
        messages=messages,
        stream=True,
        options={"num_ctx": 16384},
    )
    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content and t_first_token is None:
            t_first_token = time.perf_counter()
        if content:
            text_chunks.append(content)
        if chunk.get("done"):
            final_chunk = dict(chunk)

    t_end = time.perf_counter()
    risposta = _strip_stop_tokens("".join(text_chunks))
    ttft = (t_first_token - t_start) if t_first_token is not None else None
    latenza_totale = t_end - t_start

    eval_count = (final_chunk or {}).get("eval_count")  # output tokens generati
    eval_duration_ns = (final_chunk or {}).get("eval_duration")  # ns
    prompt_eval_count = (final_chunk or {}).get("prompt_eval_count")
    tok_s = None
    if eval_count and eval_duration_ns:
        tok_s = eval_count / (eval_duration_ns / 1e9)

    return {
        "prompt": prompt,
        "risposta": risposta,
        "ttft_s": round(ttft, 3) if ttft is not None else None,
        "latenza_totale_s": round(latenza_totale, 3),
        "tokens_output": eval_count,
        "tokens_input": prompt_eval_count,
        "tokens_per_sec": round(tok_s, 2) if tok_s else None,
    }


def main_sezione_3():
    import ollama

    print(f"=== Sezione 3 — Minerva-7B via Ollama ===\n")
    print(f"Modello: {MINERVA_MODEL}\n")

    # Verifica disponibilità modello
    available = [m.get("model") or m.get("name") for m in ollama.list().get("models", [])]
    if MINERVA_MODEL not in available:
        print(f"⚠️  Modello non trovato in `ollama list`. Disponibili: {available}")
        print(f"   Esegui: ollama pull {MINERVA_MODEL}")
        return

    client = ollama  # usa il client di default (HTTP locale)

    # Warmup: il primo chiamata carica il modello in RAM/VRAM e non è rappresentativo
    print("Warmup (caricamento modello in memoria)...")
    import time
    t0 = time.perf_counter()
    _ = client.chat(model=MINERVA_MODEL, messages=[{"role": "user", "content": "Ciao."}], stream=False)
    print(f"Warmup completato in {time.perf_counter() - t0:.1f}s\n")

    risultati: list[dict] = []
    for i, prompt in enumerate(PROMPT_TEST, start=1):
        print(f"--- Prompt {i}/{len(PROMPT_TEST)} ---")
        print(f"Q: {prompt}\n")
        r = benchmark_prompt(client, MINERVA_MODEL, prompt)
        r["n"] = i
        risultati.append(r)
        print(f"A: {r['risposta']}\n")
        print(f"   TTFT: {r['ttft_s']}s | latenza: {r['latenza_totale_s']}s | "
              f"tokens out: {r['tokens_output']} | tok/s: {r['tokens_per_sec']}")
        print()

    # Tabella riepilogo
    print("=" * 80)
    print(f"{'#':>2}  {'TTFT (s)':>10}  {'Latenza (s)':>12}  {'Tokens out':>11}  {'Tok/s':>8}")
    print("-" * 80)
    for r in risultati:
        print(f"{r['n']:>2}  {r['ttft_s']:>10}  {r['latenza_totale_s']:>12}  "
              f"{(r['tokens_output'] or 0):>11}  {(r['tokens_per_sec'] or 0):>8}")

    ttft_vals = [r["ttft_s"] for r in risultati if r["ttft_s"] is not None]
    lat_vals = [r["latenza_totale_s"] for r in risultati]
    toks_vals = [r["tokens_per_sec"] for r in risultati if r["tokens_per_sec"]]
    ttft_avg = sum(ttft_vals) / len(ttft_vals) if ttft_vals else None
    lat_avg = sum(lat_vals) / len(lat_vals)
    toks_avg = sum(toks_vals) / len(toks_vals) if toks_vals else None
    ttft_max = max(ttft_vals) if ttft_vals else None
    lat_max = max(lat_vals)

    print("-" * 80)
    print(f"Media TTFT: {ttft_avg:.2f}s | max TTFT: {ttft_max:.2f}s   (target < 5s)")
    print(f"Media latenza totale: {lat_avg:.2f}s | max: {lat_max:.2f}s   (target < 30s)")
    print(f"Media tok/s: {toks_avg:.1f}" if toks_avg else "Tok/s non disponibili")

    # Verdetto vs target del piano
    pass_ttft = (ttft_max or 0) < 5
    pass_lat = lat_max < 30
    if pass_ttft and pass_lat:
        verdetto = "PASS (latenza)"
    elif pass_ttft or pass_lat:
        verdetto = "PARTIAL (latenza)"
    else:
        verdetto = "FAIL (latenza)"
    print(f"\nVerdetto latenza: {verdetto}")
    print("Qualità: valutazione qualitativa a cura di Federico (legge le risposte sopra).")

    output = {
        "modello": MINERVA_MODEL,
        "n_prompt": len(PROMPT_TEST),
        "verdetto_latenza": verdetto,
        "target_piano": {"ttft_max_s": 5, "latenza_max_s": 30},
        "aggregati": {
            "ttft_media_s": round(ttft_avg, 3) if ttft_avg else None,
            "ttft_max_s": round(ttft_max, 3) if ttft_max else None,
            "latenza_media_s": round(lat_avg, 3),
            "latenza_max_s": round(lat_max, 3),
            "tokens_per_sec_media": round(toks_avg, 2) if toks_avg else None,
        },
        "risultati": risultati,
    }
    MINERVA_RESULTS.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOutput salvato in: {MINERVA_RESULTS.relative_to(SPIKE_DIR)}")
    return output


def main_sezione_3_v2():
    """Variante della Sezione 3 con system message esplicito e filtro stop-tokens.
    Confronta i numeri con la run originale (minerva_results.json)."""
    import ollama

    print(f"=== Sezione 3 (v2) — Minerva-7B con system message + chat template ===\n")
    print(f"Modello: {MINERVA_MODEL}")
    print(f"System: {SYSTEM_MSG_BENCHMARK[:80]}...\n")

    available = [m.get("model") or m.get("name") for m in ollama.list().get("models", [])]
    if MINERVA_MODEL not in available:
        print(f"⚠️  Modello non trovato. Esegui: ollama pull {MINERVA_MODEL}")
        return

    import time
    print("Warmup...")
    t0 = time.perf_counter()
    _ = ollama.chat(
        model=MINERVA_MODEL,
        messages=[{"role": "system", "content": SYSTEM_MSG_BENCHMARK},
                  {"role": "user", "content": "Ciao."}],
        stream=False,
    )
    print(f"Warmup in {time.perf_counter() - t0:.1f}s\n")

    risultati = []
    for i, prompt in enumerate(PROMPT_TEST, start=1):
        print(f"--- Prompt {i}/{len(PROMPT_TEST)} ---")
        print(f"Q: {prompt}\n")
        r = benchmark_prompt(ollama, MINERVA_MODEL, prompt, system_msg=SYSTEM_MSG_BENCHMARK)
        r["n"] = i
        # Verifica presenza stop-tokens nel testo grezzo (prima dello strip)
        r["had_stop_tokens"] = any(t in r["risposta"] for t in ("<|im_end|>", ">|im_end|>", "<|im_start|>"))
        risultati.append(r)
        print(f"A: {r['risposta']}\n")
        print(f"   TTFT: {r['ttft_s']}s | latenza: {r['latenza_totale_s']}s | "
              f"tokens out: {r['tokens_output']} | tok/s: {r['tokens_per_sec']}")
        print()

    print("=" * 80)
    print(f"{'#':>2}  {'TTFT (s)':>10}  {'Latenza (s)':>12}  {'Tokens out':>11}  {'Tok/s':>8}")
    print("-" * 80)
    for r in risultati:
        print(f"{r['n']:>2}  {r['ttft_s']:>10}  {r['latenza_totale_s']:>12}  "
              f"{(r['tokens_output'] or 0):>11}  {(r['tokens_per_sec'] or 0):>8}")

    ttft_vals = [r["ttft_s"] for r in risultati if r["ttft_s"] is not None]
    lat_vals = [r["latenza_totale_s"] for r in risultati]
    toks_vals = [r["tokens_per_sec"] for r in risultati if r["tokens_per_sec"]]
    ttft_avg = sum(ttft_vals) / len(ttft_vals) if ttft_vals else None
    lat_avg = sum(lat_vals) / len(lat_vals)
    toks_avg = sum(toks_vals) / len(toks_vals) if toks_vals else None
    lat_max = max(lat_vals)
    ttft_max = max(ttft_vals) if ttft_vals else None
    pass_ttft = (ttft_max or 0) < 5
    pass_lat = lat_max < 30
    verdetto = "PASS (latenza)" if (pass_ttft and pass_lat) else ("PARTIAL (latenza)" if (pass_ttft or pass_lat) else "FAIL (latenza)")
    print("-" * 80)
    print(f"Media TTFT: {ttft_avg:.2f}s | max: {ttft_max:.2f}s   (target < 5s)")
    print(f"Media latenza: {lat_avg:.2f}s | max: {lat_max:.2f}s   (target < 30s)")
    if toks_avg:
        print(f"Media tok/s: {toks_avg:.1f}")
    print(f"Verdetto latenza: {verdetto}")
    print(f"Stop tokens rilevati in qualche risposta: {any(r['had_stop_tokens'] for r in risultati)}")

    output = {
        "modello": MINERVA_MODEL,
        "system_msg": SYSTEM_MSG_BENCHMARK,
        "n_prompt": len(PROMPT_TEST),
        "verdetto_latenza": verdetto,
        "target_piano": {"ttft_max_s": 5, "latenza_max_s": 30},
        "aggregati": {
            "ttft_media_s": round(ttft_avg, 3) if ttft_avg else None,
            "ttft_max_s": round(ttft_max, 3) if ttft_max else None,
            "latenza_media_s": round(lat_avg, 3),
            "latenza_max_s": round(lat_max, 3),
            "tokens_per_sec_media": round(toks_avg, 2) if toks_avg else None,
        },
        "risultati": risultati,
    }
    MINERVA_RESULTS_V2.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOutput salvato in: {MINERVA_RESULTS_V2.relative_to(SPIKE_DIR)}")
    return output


# ---------------------------------------------------------------------------
# Sezione 4 — Mini-RAG end-to-end sul Codice Privacy
# ---------------------------------------------------------------------------

INSTR_PREFIX = "Rappresenta questo concetto giuridico italiano per la ricerca semantica: "
URN_BASE = "urn:nir:stato:decreto.legislativo:2003-06-30;196"

QUERY_E2E = [
    "Quali sono i principi del trattamento dei dati personali?",
    "Quali sono i compiti del responsabile della protezione dei dati?",
    "Quando il Garante può applicare sanzioni amministrative?",
]

SYSTEM_MSG_RAG = (
    "Sei un assistente legale italiano. L'utente ti fornirà uno o più articoli di legge come "
    "contesto, seguiti da una domanda. Rispondi alla domanda usando ESCLUSIVAMENTE le "
    "informazioni del contesto. Cita sempre l'articolo specifico (es. \"secondo l'Art. 166\"). "
    "Se l'informazione non è nel contesto, rispondi: \"Non trovo riferimenti nel testo fornito.\""
)

PROMPT_TEMPLATE_RAG = """Contesto:

{context}

Domanda: {query}"""

# Minerva-7B ha context 4096 token. Tronchiamo ogni chunk per stare comodi.
CHUNK_MAX_CHARS = 1800


def _is_abrogato(art: dict) -> bool:
    raw = art.get("raw_body", "").upper()
    if "ARTICOLO ABROGATO" in raw or "ARTICOLO SOPPRESSO" in raw:
        return True
    # body molto corto e contiene "ABROGATO" → abrogato di fatto
    if len(raw) < 200 and "ABROGAT" in raw:
        return True
    sec = (art.get("section_raw") or "").upper()
    if "TITOLO ABROGATO" in sec or "CAPO ABROGATO" in sec:
        return True
    return False


def main_sezione_4():
    import time
    import ollama
    from sentence_transformers import SentenceTransformer, util

    print("=== Sezione 4 — Mini-RAG end-to-end ===\n")

    # 1. Carica JSON parsato
    parsed = json.loads(PARSED_JSON.read_text(encoding="utf-8"))
    articoli = [a for a in parsed["articoli"] if not a["in_allegati"] and not _is_abrogato(a)]
    print(f"Articoli totali parsed: {len(parsed['articoli'])}")
    print(f"Articoli usati come chunk (corpo, non abrogati): {len(articoli)}\n")

    # 2. Costruisci chunk
    chunks: list[dict] = []
    for a in articoli:
        text = f"Art. {a['numero']} - {a['rubrica']}\n\n{a['raw_body']}".strip()
        chunks.append({
            "numero": a["numero"],
            "rubrica": a["rubrica"],
            "urn": f"{URN_BASE}:articolo:{a['numero']}",
            "section_raw": a.get("section_raw"),
            "text": text,
            "text_len": len(text),
        })

    # 3. Embed tutti i chunk con bge-m3 + prefix IT
    device = pick_device()
    print(f"Caricamento bge-m3 su {device}...")
    t0 = time.perf_counter()
    model = SentenceTransformer("BAAI/bge-m3", device=device)
    print(f"Modello caricato in {time.perf_counter() - t0:.1f}s")

    texts = [c["text"] for c in chunks]
    t0 = time.perf_counter()
    chunk_embeddings = model.encode(
        texts, prompt=INSTR_PREFIX,
        convert_to_tensor=True, normalize_embeddings=True,
        show_progress_bar=False, batch_size=8,
    )
    t_emb = time.perf_counter() - t0
    print(f"Indicizzati {len(chunks)} chunk in {t_emb:.2f}s "
          f"(media: {t_emb / len(chunks) * 1000:.0f} ms/chunk)\n")

    # 4. Loop query → retrieval → generazione
    risultati = []
    for i, q in enumerate(QUERY_E2E, start=1):
        print(f"=== QUERY {i}/{len(QUERY_E2E)} ===")
        print(f"Q: {q}\n")
        t_q0 = time.perf_counter()

        q_emb = model.encode([q], prompt=INSTR_PREFIX, convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(q_emb, chunk_embeddings)[0]
        top_indices = sims.argsort(descending=True)[:3].cpu().tolist()
        top = [{"chunk": chunks[j], "score": float(sims[j])} for j in top_indices]
        t_retrieval = time.perf_counter() - t_q0

        print("Top-3 articoli recuperati:")
        for rank, item in enumerate(top, start=1):
            c = item["chunk"]
            print(f"  {rank}. [score={item['score']:.3f}] Art. {c['numero']} - {c['rubrica'][:80]}")
        print()

        # Tronchiamo i chunk per stare nel context 4096 di Minerva
        chunk_texts = []
        for item in top:
            t = item["chunk"]["text"]
            if len(t) > CHUNK_MAX_CHARS:
                t = t[:CHUNK_MAX_CHARS] + "\n[...articolo troncato...]"
            chunk_texts.append(t)
        context = "\n\n---\n\n".join(chunk_texts)
        prompt = PROMPT_TEMPLATE_RAG.format(context=context, query=q)

        t_gen0 = time.perf_counter()
        resp = ollama.chat(
            model=MINERVA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_MSG_RAG},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            options={"temperature": 0.2, "num_ctx": 16384, "num_predict": 512},
        )
        t_gen = time.perf_counter() - t_gen0
        risposta = _strip_stop_tokens(resp["message"]["content"])
        t_q_total = time.perf_counter() - t_q0

        print(f"A: {risposta}\n")
        print(f"   retrieval: {t_retrieval * 1000:.0f} ms | generation: {t_gen:.2f} s | totale: {t_q_total:.2f} s\n")

        risultati.append({
            "n": i,
            "query": q,
            "top_chunks": [
                {"rank": r + 1, "score": round(item["score"], 4),
                 "numero": item["chunk"]["numero"], "rubrica": item["chunk"]["rubrica"],
                 "urn": item["chunk"]["urn"]}
                for r, item in enumerate(top)
            ],
            "risposta": risposta,
            "tempi": {
                "retrieval_ms": round(t_retrieval * 1000, 1),
                "generation_s": round(t_gen, 3),
                "totale_s": round(t_q_total, 3),
            },
        })

    # 5. Aggregati
    tempi_q = [r["tempi"]["totale_s"] for r in risultati]
    output = {
        "modello_embed": "BAAI/bge-m3",
        "modello_llm": MINERVA_MODEL,
        "instruction_prefix": INSTR_PREFIX,
        "chunk_indicizzati": len(chunks),
        "tempo_indicizzazione_s": round(t_emb, 2),
        "tempo_medio_embed_chunk_ms": round(t_emb / len(chunks) * 1000, 1),
        "tempo_medio_query_totale_s": round(sum(tempi_q) / len(tempi_q), 3),
        "queries": risultati,
        "nota": "Valutazione qualitativa (top-1 sensato, citazione corretta, allucinazioni) a cura di Federico.",
    }
    E2E_RESULTS.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 80)
    print(f"Chunk indicizzati: {output['chunk_indicizzati']}")
    print(f"Tempo medio embedding per chunk: {output['tempo_medio_embed_chunk_ms']} ms")
    print(f"Tempo medio query end-to-end: {output['tempo_medio_query_totale_s']} s")
    print(f"\nOutput salvato in: {E2E_RESULTS.relative_to(SPIKE_DIR)}")
    return output


# ---------------------------------------------------------------------------
# Sezione 5 — Confronto Minerva-7B vs Qwen2.5-14B sulle stesse 3 query (mini-spike 4-bis)
# ---------------------------------------------------------------------------

QWEN_MODEL = "qwen2.5:14b"
COMMON_OPTIONS = {"temperature": 0.2, "num_ctx": 16384, "num_predict": 512}


def _stream_chat(client, model: str, system_msg: str, user_msg: str, options: dict) -> dict:
    """Stream una chiamata chat (system+user) e ritorna metriche+risposta."""
    import time

    t_start = time.perf_counter()
    t_first: float | None = None
    chunks_text: list[str] = []
    final: dict | None = None

    stream = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        stream=True,
        options=options,
    )
    for ch in stream:
        c = ch.get("message", {}).get("content", "")
        if c and t_first is None:
            t_first = time.perf_counter()
        if c:
            chunks_text.append(c)
        if ch.get("done"):
            final = dict(ch)
    t_end = time.perf_counter()
    raw = "".join(chunks_text)
    text = _strip_stop_tokens(raw)

    eval_count = (final or {}).get("eval_count")
    eval_dur = (final or {}).get("eval_duration")
    toks = eval_count / (eval_dur / 1e9) if (eval_count and eval_dur) else None

    return {
        "response": text,
        "ttft_s": round(t_first - t_start, 3) if t_first is not None else None,
        "latency_s": round(t_end - t_start, 3),
        "tokens_out": eval_count,
        "tokens_per_sec": round(toks, 2) if toks else None,
        "had_special_tokens": raw != text,  # se lo strip ha rimosso qualcosa
    }


def main_sezione_5():
    """Confronto Minerva vs Qwen sulle 3 query della Sezione 4, stesso retrieval."""
    import time
    import ollama
    from sentence_transformers import SentenceTransformer, util

    print("=== Sezione 5 — Confronto Minerva-7B vs Qwen2.5-14B ===\n")

    # Verifica modelli
    available = [m.get("model") or m.get("name") for m in ollama.list().get("models", [])]
    missing = [m for m in (MINERVA_MODEL, QWEN_MODEL) if m not in available]
    if missing:
        print(f"⚠️  Modelli mancanti: {missing}")
        return
    print(f"Modelli pronti: {MINERVA_MODEL}, {QWEN_MODEL}")
    print("(Qwen è già scaricato in cache locale → setup 0s)\n")

    # --- Retrieval (stesso logico di Sezione 4, duplicato per non toccarla) ---
    parsed = json.loads(PARSED_JSON.read_text(encoding="utf-8"))
    articoli = [a for a in parsed["articoli"] if not a["in_allegati"] and not _is_abrogato(a)]
    chunks: list[dict] = []
    for a in articoli:
        text = f"Art. {a['numero']} - {a['rubrica']}\n\n{a['raw_body']}".strip()
        chunks.append({
            "numero": a["numero"], "rubrica": a["rubrica"],
            "urn": f"{URN_BASE}:articolo:{a['numero']}",
            "text": text,
        })

    device = pick_device()
    print(f"Caricamento bge-m3 su {device}...")
    t0 = time.perf_counter()
    model = SentenceTransformer("BAAI/bge-m3", device=device)
    print(f"Modello embedding caricato in {time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    chunk_embeddings = model.encode(
        [c["text"] for c in chunks], prompt=INSTR_PREFIX,
        convert_to_tensor=True, normalize_embeddings=True,
        show_progress_bar=False, batch_size=8,
    )
    print(f"Indicizzati {len(chunks)} chunk in {time.perf_counter() - t0:.1f}s\n")

    # --- Loop query → retrieval → generazione doppia ---
    risultati = []
    for i, q in enumerate(QUERY_E2E, start=1):
        print(f"{'=' * 80}")
        print(f"QUERY {i}/{len(QUERY_E2E)}: {q}")
        print('=' * 80)

        q_emb = model.encode([q], prompt=INSTR_PREFIX, convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(q_emb, chunk_embeddings)[0]
        top_idx = sims.argsort(descending=True)[:3].cpu().tolist()
        top = [{"chunk": chunks[j], "score": float(sims[j])} for j in top_idx]

        print("Top-3 articoli recuperati:")
        for rank, item in enumerate(top, start=1):
            c = item["chunk"]
            print(f"  {rank}. score={item['score']:.3f}  Art. {c['numero']} - {c['rubrica'][:70]}")
        print()

        # Stesso troncamento di Sezione 4
        chunk_texts = []
        for item in top:
            t = item["chunk"]["text"]
            if len(t) > CHUNK_MAX_CHARS:
                t = t[:CHUNK_MAX_CHARS] + "\n[...articolo troncato...]"
            chunk_texts.append(t)
        context = "\n\n---\n\n".join(chunk_texts)
        user_msg = PROMPT_TEMPLATE_RAG.format(context=context, query=q)

        # Minerva
        print(f"--- Minerva-7B ---")
        m_res = _stream_chat(ollama, MINERVA_MODEL, SYSTEM_MSG_RAG, user_msg, COMMON_OPTIONS)
        print(m_res["response"])
        print(f"\n   [ttft={m_res['ttft_s']}s | latency={m_res['latency_s']}s | "
              f"tokens={m_res['tokens_out']} | tok/s={m_res['tokens_per_sec']} | "
              f"special_tokens={m_res['had_special_tokens']}]\n")

        # Qwen
        print(f"--- Qwen2.5-14B ---")
        q_res = _stream_chat(ollama, QWEN_MODEL, SYSTEM_MSG_RAG, user_msg, COMMON_OPTIONS)
        print(q_res["response"])
        print(f"\n   [ttft={q_res['ttft_s']}s | latency={q_res['latency_s']}s | "
              f"tokens={q_res['tokens_out']} | tok/s={q_res['tokens_per_sec']} | "
              f"special_tokens={q_res['had_special_tokens']}]\n")

        risultati.append({
            "query_id": i,
            "query": q,
            "retrieved_articles": [
                {"rank": r + 1, "score": round(item["score"], 4),
                 "numero": item["chunk"]["numero"], "rubrica": item["chunk"]["rubrica"],
                 "urn": item["chunk"]["urn"]}
                for r, item in enumerate(top)
            ],
            "minerva": m_res,
            "qwen": q_res,
        })

    # --- Tabella riassuntiva ---
    def _avg(vals): return round(sum(vals) / len(vals), 2) if vals else None
    m_ttft = _avg([r["minerva"]["ttft_s"] for r in risultati if r["minerva"]["ttft_s"]])
    q_ttft = _avg([r["qwen"]["ttft_s"] for r in risultati if r["qwen"]["ttft_s"]])
    m_lat = _avg([r["minerva"]["latency_s"] for r in risultati])
    q_lat = _avg([r["qwen"]["latency_s"] for r in risultati])
    m_toks = _avg([r["minerva"]["tokens_per_sec"] for r in risultati if r["minerva"]["tokens_per_sec"]])
    q_toks = _avg([r["qwen"]["tokens_per_sec"] for r in risultati if r["qwen"]["tokens_per_sec"]])
    m_out = _avg([r["minerva"]["tokens_out"] for r in risultati if r["minerva"]["tokens_out"]])
    q_out = _avg([r["qwen"]["tokens_out"] for r in risultati if r["qwen"]["tokens_out"]])

    print("=" * 80)
    print(f"{'Metrica':<22} {'Minerva-7B':>14} {'Qwen2.5-14B':>14}")
    print("-" * 80)
    print(f"{'TTFT media (s)':<22} {m_ttft!s:>14} {q_ttft!s:>14}")
    print(f"{'Latenza media (s)':<22} {m_lat!s:>14} {q_lat!s:>14}")
    print(f"{'Tok/s media':<22} {m_toks!s:>14} {q_toks!s:>14}")
    print(f"{'Tokens out media':<22} {m_out!s:>14} {q_out!s:>14}")
    print("=" * 80)

    output = {
        "modelli": {"minerva": MINERVA_MODEL, "qwen": QWEN_MODEL},
        "options_comuni": COMMON_OPTIONS,
        "system_msg": SYSTEM_MSG_RAG,
        "aggregati": {
            "minerva": {"ttft_media_s": m_ttft, "latency_media_s": m_lat,
                        "tok_s_media": m_toks, "tokens_out_media": m_out},
            "qwen": {"ttft_media_s": q_ttft, "latency_media_s": q_lat,
                     "tok_s_media": q_toks, "tokens_out_media": q_out},
        },
        "queries": risultati,
    }
    COMPARISON_RESULTS.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOutput salvato in: {COMPARISON_RESULTS.relative_to(SPIKE_DIR)}")
    return output


# ---------------------------------------------------------------------------
# Sezione 6 — Mini-spike XML Akoma Ntoso diretto da dati.normattiva.it
# ---------------------------------------------------------------------------

NORMATTIVA_BASE = "https://www.normattiva.it"
URN_CODICE_PRIVACY = "urn:nir:stato:decreto.legislativo:2003-06-30;196"

# Candidate librerie Python per Akoma Ntoso da verificare su PyPI
AKN_LIB_CANDIDATES = [
    "lexnlp",
    "akoma-ntoso-python",
    "akomantoso",
    "python-akn-parser",
    "cellar-parser",
    "akn-parser",
    "akn",
    "lexml-parser",
    "akoma",
    "indigo-akn",
]


def _pypi_lookup(pkg: str) -> dict | None:
    """Ritorna info da PyPI JSON API, None se non esiste."""
    import time
    import requests
    try:
        r = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=10)
        if r.status_code != 200:
            return None
        d = r.json()
        info = d.get("info", {})
        return {
            "name": info.get("name"),
            "version": info.get("version"),
            "summary": info.get("summary"),
            "license": info.get("license") or info.get("license_expression"),
            "home_page": info.get("home_page") or info.get("project_url"),
            "requires_python": info.get("requires_python"),
            "n_releases": len(d.get("releases", {})),
        }
    finally:
        time.sleep(0.5)  # rate limit cortese


def fetch_akn_xml() -> dict:
    """Riproduce la dance di sessione che fa normattiva2md per ottenere l'XML AKN.
    Ritorna metadati della richiesta."""
    import time
    import requests
    import re

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "iuris-rag-spike/0.1 (research)",
        "Referer": f"{NORMATTIVA_BASE}/",
    })

    # Step 1: GET sulla pagina-norma (per JSESSIONID + link diretto caricaAKN)
    url_norma = f"{NORMATTIVA_BASE}/uri-res/N2Ls?{URN_CODICE_PRIVACY}"
    t0 = time.perf_counter()
    r1 = sess.get(url_norma, timeout=30, allow_redirects=True)
    t1 = time.perf_counter() - t0
    body = r1.text

    # Estraggo il link caricaAKN direttamente dall'HTML (come fa normattiva2md)
    link_match = re.search(r'href="([^"]*caricaAKN[^"]*)"', body, re.I)
    akn_href = link_match.group(1) if link_match else None
    if akn_href and akn_href.startswith("/"):
        akn_href = NORMATTIVA_BASE + akn_href
    if akn_href:
        akn_href = akn_href.replace("&amp;", "&")

    step1 = {
        "url": url_norma,
        "status": r1.status_code,
        "content_type": r1.headers.get("Content-Type"),
        "size_bytes": len(r1.content),
        "time_s": round(t1, 2),
        "akn_link_extracted": akn_href,
        "jsessionid_set": "JSESSIONID" in r1.cookies.get_dict(),
    }

    if not akn_href:
        return {"step1": step1, "step2": None, "error": "Link caricaAKN non presente nella pagina HTML"}

    time.sleep(1.0)  # rate limit 1 req/sec come richiesto

    # Step 2: GET dell'XML AKN con stessa sessione e Referer impostato
    t0 = time.perf_counter()
    r2 = sess.get(akn_href, timeout=60, allow_redirects=True)
    t2 = time.perf_counter() - t0

    head = r2.content[:200].decode("utf-8", errors="replace")
    looks_like_xml = head.lstrip().startswith("<?xml") or "akomaNtoso" in head
    step2 = {
        "url": akn_href,
        "status": r2.status_code,
        "content_type": r2.headers.get("Content-Type"),
        "size_bytes": len(r2.content),
        "time_s": round(t2, 2),
        "looks_like_akn_xml": looks_like_xml,
        "head_preview": head.replace("\n", " ")[:200],
    }

    if looks_like_xml:
        AKN_XML.write_bytes(r2.content)
        step2["saved_to"] = str(AKN_XML.relative_to(SPIKE_DIR))

    return {"step1": step1, "step2": step2, "error": None}


def parse_akn(xml_path: Path) -> dict:
    """Analisi strutturale del documento Akoma Ntoso."""
    from lxml import etree

    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    # AKN usa namespace; lo estraiamo
    ns_uri = root.nsmap.get(None) if root.nsmap else None
    ns = {"akn": ns_uri} if ns_uri else {}

    # Tag <article> — con o senza namespace
    if ns_uri:
        articles = root.findall(".//akn:article", ns)
        bodies = root.findall(".//akn:body", ns)
        ids = [a.get("eId") or a.get("id") for a in articles]
    else:
        articles = root.findall(".//article")
        bodies = root.findall(".//body")
        ids = [a.get("eId") or a.get("id") for a in articles]

    # Profondità: trova l'articolo "art_2-bis" o uno con eId che contiene "2-bis"
    target_article = None
    for a in articles:
        eid = (a.get("eId") or a.get("id") or "")
        if "2-bis" in eid or "2bis" in eid:
            target_article = a
            break
    if target_article is None and articles:
        target_article = articles[1] if len(articles) > 1 else articles[0]

    # Ricostruisco il path dal root all'articolo
    path_to_article: list[str] = []
    if target_article is not None:
        node = target_article
        while node is not None and node is not root:
            tag = etree.QName(node).localname if isinstance(node.tag, str) else str(node.tag)
            path_to_article.insert(0, tag)
            node = node.getparent()
        if root is not None:
            path_to_article.insert(0, etree.QName(root).localname)

    # URN del documento
    doc_urn = None
    if ns_uri:
        frbr_uri = root.find(".//akn:FRBRWork/akn:FRBRuri", ns)
        if frbr_uri is None:
            frbr_uri = root.find(".//akn:FRBRthis", ns)
    else:
        frbr_uri = root.find(".//FRBRWork/FRBRuri") or root.find(".//FRBRthis")
    if frbr_uri is not None:
        doc_urn = frbr_uri.get("value")

    # Marcatori abrogazione / modifiche
    abrogato_count = len(root.xpath("//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'abrogat')]"))
    mod_tags = len(root.findall(".//akn:mod", ns)) if ns_uri else len(root.findall(".//mod"))
    quoted_structure = len(root.findall(".//akn:quotedStructure", ns)) if ns_uri else len(root.findall(".//quotedStructure"))

    # Esempio ID dell'art. 2-bis
    target_id = None
    if target_article is not None:
        target_id = target_article.get("eId") or target_article.get("id")

    # Tag contenitori candidati nel documento
    containers_found = []
    for cname in ["part", "title", "chapter", "section", "subsection", "book"]:
        n = len(root.findall(f".//akn:{cname}", ns)) if ns_uri else len(root.findall(f".//{cname}"))
        if n > 0:
            containers_found.append({"tag": cname, "n": n})

    return {
        "root_tag": etree.QName(root).localname if isinstance(root.tag, str) else str(root.tag),
        "namespace": ns_uri,
        "articoli_count": len(articles),
        "esempio_eId_art_2bis": target_id,
        "path_root_to_article": path_to_article,
        "doc_urn": doc_urn,
        "contenitori_gerarchici": containers_found,
        "mod_inline_tags": mod_tags,
        "quotedStructure_tags": quoted_structure,
        "nodi_con_testo_abrogat": abrogato_count,
    }


def main_sezione_6():
    print("=== Sezione 6 — Mini-spike XML Akoma Ntoso diretto ===\n")

    # --- VERIFICA 1 — Accesso ---
    print("--- VERIFICA 1: download XML AKN da Normattiva ---")
    fetch_report = fetch_akn_xml()
    print(json.dumps(fetch_report, ensure_ascii=False, indent=2))
    print()

    akn_ok = (fetch_report.get("step2") or {}).get("looks_like_akn_xml", False)
    if not akn_ok:
        print("❌ Download AKN fallito. Mi fermo sulle VERIFICHE 2/3.")
        accesso_verdict = "KO"
        parse_report: dict | None = None
    else:
        accesso_verdict = "OK"
        # --- VERIFICA 2 — Parsing ---
        print("--- VERIFICA 2: struttura AKN ---")
        parse_report = parse_akn(AKN_XML)
        print(json.dumps(parse_report, ensure_ascii=False, indent=2))
        print()

    # --- VERIFICA 3 — Librerie Python ---
    print("--- VERIFICA 3: librerie Python su PyPI ---")
    libs_found: list[dict] = []
    libs_missing: list[str] = []
    for name in AKN_LIB_CANDIDATES:
        info = _pypi_lookup(name)
        if info:
            libs_found.append(info)
            print(f"  ✓ {name}: v{info['version']}, {info['n_releases']} releases, "
                  f"license={info['license']!s:.30}, py={info['requires_python']}")
        else:
            libs_missing.append(name)
            print(f"  ✗ {name}: non trovato")
    print()

    # --- DELIVERABLE: verdetto ---
    print("=" * 70)
    print("VERDETTO SINTETICO")
    print("=" * 70)

    if parse_report:
        urn_granular_ok = bool(parse_report["esempio_eId_art_2bis"] and "2-bis" in (parse_report["esempio_eId_art_2bis"] or ""))
        gerarchia_ok = len(parse_report["contenitori_gerarchici"]) >= 2  # almeno 2 livelli sopra article
    else:
        urn_granular_ok = False
        gerarchia_ok = False

    libreria_decente = any(
        l.get("requires_python") and l.get("n_releases", 0) >= 3
        for l in libs_found
    )

    # Stima ore parser custom: basata su numero di contenitori da gestire + edge case già visti
    if parse_report:
        n_levels = len(parse_report["contenitori_gerarchici"])
        # baseline 4-6 ore per gestire 3-5 livelli + abrogazioni + mod inline
        ore_parser = 4 + max(0, n_levels - 3) * 1
    else:
        ore_parser = None

    print(f"Accesso XML AKN da Normattiva: {accesso_verdict}")
    print(f"Struttura AKN risolve URN granulari: {'SI' if urn_granular_ok else 'NO'}")
    print(f"Struttura AKN risolve gerarchia:     {'SI' if gerarchia_ok else 'NO'}")
    print(f"Libreria Python decente: {'SI' if libreria_decente else ('parziale' if libs_found else 'NO')}")
    print(f"Stima ore parser custom lxml/XPath: {ore_parser} h" if ore_parser else "")
    print()

    raccomandazione = (
        "SI — l'XML AKN risolve i due caveat principali (URN granulari + gerarchia esplicita) "
        "e la dance di sessione è semplice da riprodurre."
        if (accesso_verdict == "OK" and urn_granular_ok and gerarchia_ok)
        else "NO o CON CAVEAT — vedi report sopra."
    )
    print(f"Raccomandazione: {raccomandazione}")

    output = {
        "fetch": fetch_report,
        "parse": parse_report,
        "libraries": {"found": libs_found, "missing": libs_missing},
        "verdetto": {
            "accesso": accesso_verdict,
            "urn_granulari_ok": urn_granular_ok,
            "gerarchia_ok": gerarchia_ok,
            "libreria_decente": libreria_decente,
            "ore_parser_custom_stima": ore_parser,
            "raccomandazione": raccomandazione,
        },
    }
    AKN_REPORT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport salvato in: {AKN_REPORT.relative_to(SPIKE_DIR)}")
    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sezione = sys.argv[1] if len(sys.argv) > 1 else "1"
    if sezione == "1":
        main_sezione_1()
    elif sezione == "2":
        main_sezione_2()
    elif sezione == "2b":
        main_sezione_2b()
    elif sezione == "3":
        main_sezione_3()
    elif sezione == "3v2":
        main_sezione_3_v2()
    elif sezione == "4":
        main_sezione_4()
    elif sezione == "5":
        main_sezione_5()
    elif sezione == "6":
        main_sezione_6()
    else:
        print(f"Sezione '{sezione}' non ancora implementata. Disponibili: 1, 2, 2b, 3, 3v2, 4, 5, 6")
        sys.exit(1)
