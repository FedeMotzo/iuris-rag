"""Step 0.B — verifica troncamento Q69: rigenera a max_tokens=6000.

Q69 usa cassette V2 per le sub-query (no live sub-query cost), 1 sola
generation call. Costo ~$0.05.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

Q69 = (
    "Un'azienda farmaceutica italiana, qualificata come soggetto essenziale "
    "NIS2 per il settore sanitario, intende impiegare un sistema di IA per "
    "supportare le attività di farmacovigilanza con dati provenienti da "
    "operatori sanitari e pazienti: quali sono gli obblighi cumulativi ai "
    "sensi di AI Act, GDPR e NIS2?"
)
CASSETTE = ROOT / "tests/cross_norm/cassettes/subquery_responses.json"
_SHORT_TO_ID = {"GDPR":"gdpr","AI Act":"ai_act","D.Lgs 231/2001":"dlgs_231",
                "NIS2":"nis2","Codice Privacy":"codice_privacy","L. 132/2025":"l_132_2025"}


class _Res:
    def __init__(self, t): self.text=t


class CassetteOrLive:
    def __init__(self, live, cass, label):
        self._live=live; self._c=cass; self.label=label
    @property
    def provider_name(self): return self._live.provider_name
    @property
    def model_name(self): return self._live.model_name
    def generate(self, prompt, system=None, max_tokens=500, temperature=0.0):
        nid=None
        for line in prompt.splitlines():
            if line.startswith("Norma target:"):
                tail=line[len("Norma target:"):].strip()
                for s,i in _SHORT_TO_ID.items():
                    if tail.startswith(s): nid=i; break
                break
        if nid:
            k=f"{self.label}:{nid}"
            if k in self._c: return _Res(self._c[k])
        return self._live.generate(prompt=prompt, system=system, max_tokens=max_tokens, temperature=temperature)


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env", override=False)
    from qdrant_client import QdrantClient
    from fastembed import SparseTextEmbedding
    from sentence_transformers import CrossEncoder
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    from core.hybrid_retriever.types import RetrievalResult
    from core.cross_norm import CrossNormRetriever
    from core.rag_prompt import build_user_prompt, load_system_prompt
    from core.llm_provider.config import load_provider_from_env

    enc=BgeM3Encoder.get(device="mps"); bm=SparseTextEmbedding(model_name="Qdrant/bm25")
    rr=CrossEncoder("BAAI/bge-reranker-v2-m3", device="mps", max_length=512)
    rr.predict([("a","b")], show_progress_bar=False)
    hybrid=HybridRetriever(QdrantClient(host="localhost",port=6333),enc,bm,"italian_legal_v1_hybrid",reranker=rr)
    cass=json.loads(CASSETTE.read_text(encoding="utf-8"))
    llm=CassetteOrLive(load_provider_from_env(), cass, "q69")
    cn=CrossNormRetriever(hybrid_retriever=hybrid, llm_client=llm, top_k_final=20,
                          rerank_top_k_per_norm=20, rerank_top_k_global=20)
    top20=cn.retrieve(Q69, top_k=20)
    top5=RetrievalResult(list(top20)[:5])
    prompt=build_user_prompt(Q69, top5, include_expanded=False)
    sysp=load_system_prompt("it")

    for mt in [1000, 6000]:
        gen=llm._live.generate(prompt=prompt, system=sysp, max_tokens=mt, temperature=0.0)
        completed = gen.finish_reason != "length"
        print(f"\n=== max_tokens={mt} ===")
        print(f"len(chars)={len(gen.text)} out_tokens={gen.n_output_tokens} finish_reason={gen.finish_reason} completata={completed}")
        print("ends:", repr(gen.text[-120:]))
        if mt==6000:
            Path(ROOT/"spike/_q69_6000.txt").write_text(gen.text, encoding="utf-8")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
