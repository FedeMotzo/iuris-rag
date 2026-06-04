"""Debug: per-source logit distribution, per-subquery top-3, fusion competition."""
from __future__ import annotations
import json, sys
from dataclasses import dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

Q68 = ("Un'azienda ospedaliera intende mettere in produzione un chatbot AI per "
       "supportare il triage telefonico dei pazienti: quali adempimenti integrati "
       "AI Act, GDPR e L. 132/2025 devono essere previsti prima dell'avvio?")
GOLD = {"eli/reg/2024/1689/oj__art_6","eli/reg/2024/1689/oj__art_27",
        "eli/reg/2016/679/oj__art_9","eli/reg/2016/679/oj__art_35",
        "akn/it/act/legge/stato/2025-09-23/132__art_7"}

@dataclass
class _R:
    text: str

class CassetteLLM:
    def __init__(self,c,qid): self.c=c; self.qid=qid
    def generate(self,prompt,system=None,max_tokens=200,temperature=0.0):
        S2I={"GDPR":"gdpr","AI Act":"ai_act","L. 132/2025":"l_132_2025"}
        for ln in prompt.splitlines():
            if ln.startswith("Norma target:"):
                tail=ln[len("Norma target:"):].strip()
                for s,n in S2I.items():
                    if tail.startswith(s):
                        v=self.c[f"{self.qid}:{n}"]
                        return _R(json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v)
        raise ValueError("norma?")

def main():
    import logging; logging.basicConfig(level=logging.ERROR)
    from fastembed import SparseTextEmbedding
    from qdrant_client import QdrantClient
    from sentence_transformers import CrossEncoder
    from core.cross_norm import CrossNormRetriever
    from core.embedding import BgeM3Encoder
    from core.hybrid_retriever import HybridRetriever
    print("Loading models...")
    enc=BgeM3Encoder.get(device="mps")
    bm=SparseTextEmbedding(model_name="Qdrant/bm25")
    rr=CrossEncoder("BAAI/bge-reranker-v2-m3",device="mps",max_length=512)
    rr.predict([("w","w")],show_progress_bar=False)
    cli=QdrantClient(host="localhost",port=6333)
    hybrid=HybridRetriever(cli,enc,bm,"italian_legal_v1_hybrid",reranker=rr)
    cass=json.loads(open(ROOT/"tests/cross_norm/cassettes/subquery_responses.json").read())
    llm=CassetteLLM(cass,"q68")
    cnr=CrossNormRetriever(hybrid_retriever=hybrid,llm_client=llm,
                           top_k_per_norm=20,top_k_global=20,top_k_final=20,
                           rerank_top_k_per_norm=20,rerank_top_k_global=20,debug=False)
    cnr.retrieve(Q68,top_k=20)
    tr=cnr.last_trace

    print("\n=== PER-SUBQUERY TOP-3 (filtered) + GOLD POSITIONS ===")
    for (nid,sq_idx),hits in tr["per_subquery_hits"].items():
        sq=tr["sub_queries"][nid][sq_idx]
        print(f"\n[{nid}#{sq_idx}] {sq[:90]}")
        for r,cid,sc in hits[:3]:
            mark=" ★" if cid in GOLD else ""
            print(f"   {r:>2}. {cid[:55]:<55} logit={sc:.3f}{mark}")
        gold_in = [(r,cid,sc) for r,cid,sc in hits if cid in GOLD]
        for r,cid,sc in gold_in:
            print(f"   GOLD@{r}: {cid.split('__',2)[-1]} logit={sc:.3f}")

    print("\n=== GLOBAL TOP-10 ===")
    for r,cid,sc in tr["global"][:10]:
        mark=" ★" if cid in GOLD else ""
        print(f"  {r:>2}. {cid[:55]:<55} logit={sc:.3f}{mark}")

    print("\n=== FUSED TOP-20 (sigmoid + logit) ===")
    for entry in tr["fused_top"][:20]:
        rank,cid,sig,logit,sources=entry
        mark=" ★ GOLD" if cid in GOLD else ""
        src_short=",".join(s for s,_ in sources[:3])
        print(f"  {rank:>2}. {cid[:50]:<50} logit={logit:.3f} sig={sig:.4f} src={src_short}{mark}")

    print("\n=== GOLD HUNT: per ogni gold, max logit attraverso tutte le sub-query ===")
    for g in GOLD:
        max_logit = -999.0; loc = None
        for (nid,sq_idx),hits in tr["per_subquery_hits"].items():
            for r,cid,sc in hits:
                if cid==g and sc>max_logit:
                    max_logit=sc; loc=f"{nid}#{sq_idx}@r{r}"
        for r,cid,sc in tr["global"]:
            if cid==g and sc>max_logit:
                max_logit=sc; loc=f"global@r{r}"
        print(f"  {g.split('__',2)[-1]:<14} max_logit={max_logit:.4f} loc={loc}")

if __name__=="__main__":
    main()
