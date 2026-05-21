"""Graph multi-normativa: espansione contesto retrieval cross-norma.

Architettura A: graph statico curato a mano, espansione 1-hop bidirezionale
a valle di `HybridRetriever`, prima del passaggio all'LLM. Nessuna chiamata
LLM, nessun tool calling, nessun multi-hop.
"""

from .expander import expand_context
from .loader import load_graph
from .models import ExpandedChunk, GraphLink, Relation

__all__ = ["GraphLink", "ExpandedChunk", "Relation", "load_graph", "expand_context"]
